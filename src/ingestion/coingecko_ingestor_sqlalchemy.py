"""
Enhanced CoinGecko ingestor using SQLAlchemy ORM and Pydantic models.
Provides clean integration with the database service layer.
"""

import requests
import logging
import time
import os
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict
from decimal import Decimal

from src.database import db_service
from src.schemas import MarketPriceData, DataIngestionLogData, IngestionStatus
from src.common.utils import get_date_str_for_coingecko

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
REQUEST_DELAY_SECONDS = 3


class CoinGeckoIngestor:
    """Enhanced CoinGecko data ingestor using SQLAlchemy and Pydantic."""
    
    def __init__(self):
        """Initialize the ingestor with database service."""
        self.db = db_service
        self.db.create_tables()
    
    def fetch_coingecko_historical_price(self, coin_id: str, date_str_ddmmyyyy: str) -> Optional[dict]:
        """
        Fetches historical price, volume, and market cap for a coin on a specific date.
        CoinGecko API endpoint: /coins/{id}/history?date={date}&localization=false
        date format: dd-mm-yyyy
        """
        api_key = os.getenv("COINGECKO_API_KEY")
        headers = {}
        params = {"date": date_str_ddmmyyyy, "localization": "false"}
        
        if api_key:
            base_url = "https://pro-api.coingecko.com/api/v3"
            params['x_cg_pro_api_key'] = api_key
        else:
            base_url = COINGECKO_BASE_URL

        url = f"{base_url}/coins/{coin_id}/history"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            logging.info(f"Successfully fetched CoinGecko data for {coin_id} on {date_str_ddmmyyyy}")
            return data
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching CoinGecko data for {coin_id} on {date_str_ddmmyyyy}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None
        except ValueError as e:
            logging.error(f"Error decoding JSON from CoinGecko for {coin_id} on {date_str_ddmmyyyy}: {e}")
            return None
    
    def process_market_data(self, coin_id: str, price_date: date, market_data: dict) -> Optional[MarketPriceData]:
        """Process market data into Pydantic model."""
        try:
            price = market_data.get("current_price", {}).get("usd")
            volume = market_data.get("total_volume", {}).get("usd")
            market_cap = market_data.get("market_cap", {}).get("usd")
            
            return MarketPriceData(
                coin_id=coin_id,
                price_date=price_date,
                price_usd=Decimal(str(price)) if price is not None else None,
                volume_usd=Decimal(str(volume)) if volume is not None else None,
                market_cap_usd=Decimal(str(market_cap)) if market_cap is not None else None
            )
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing market data for {coin_id}: {e}")
            return None
    
    def ingest_coingecko_data_for_date(self, coin_id_map: Dict[str, str], target_date_obj: Optional[datetime] = None) -> dict:
        """
        Ingests price, volume, and market cap for a list of coins for a specific date.
        coin_id_map: e.g., {"BTC": "bitcoin", "ETH": "ethereum", "DOGE": "dogecoin"}
        target_date_obj: datetime object for the target date. Defaults to yesterday.
        """
        if target_date_obj is None:
            target_date_obj = datetime.now() - timedelta(days=1)

        date_str_coingecko = get_date_str_for_coingecko(target_date_obj)  # dd-mm-yyyy
        price_date = target_date_obj.date()  # date object for DB
        
        log_data = DataIngestionLogData(
            source="coingecko",
            data_type="prices",
            target_date=price_date,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now()
        )
        log_id = self.db.log_ingestion(log_data)
        
        try:
            validated_prices = []
            processed_count = 0
            
            for symbol, cg_id in coin_id_map.items():
                logging.info(f"Fetching CoinGecko data for {symbol} ({cg_id}) on {date_str_coingecko}")
                
                data = self.fetch_coingecko_historical_price(cg_id, date_str_coingecko)
                time.sleep(REQUEST_DELAY_SECONDS)
                processed_count += 1
                
                if data and "market_data" in data:
                    market_data = data["market_data"]
                    price_data = self.process_market_data(cg_id, price_date, market_data)
                    
                    if price_data:
                        validated_prices.append(price_data)
                        logging.info(f"Processed price data for {symbol}: ${price_data.price_usd}")
                    else:
                        logging.warning(f"Could not process market data for {cg_id} on {date_str_coingecko}")
                else:
                    logging.warning(f"No market data found for {cg_id} on {date_str_coingecko}")
            
            # Insert into database
            if validated_prices:
                result = self.db.insert_market_prices(validated_prices)
                
                # Update log
                self.db.update_ingestion_log(
                    log_id,
                    status=IngestionStatus.SUCCESS.value,
                    records_processed=processed_count,
                    records_inserted=result["inserted"],
                    records_updated=result["updated"],
                    completed_at=datetime.now()
                )
                
                logging.info(f"Ingested {result['inserted']} price records, updated {result['updated']} for date {price_date}")
                return {"success": True, "result": result}
            else:
                error_msg = f"No valid price data to ingest for date {price_date}"
                logging.info(error_msg)
                self.db.update_ingestion_log(
                    log_id,
                    status=IngestionStatus.PARTIAL.value,
                    records_processed=processed_count,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error ingesting CoinGecko data for date {price_date}: {str(e)}"
            logging.error(error_msg)
            self.db.update_ingestion_log(
                log_id,
                status=IngestionStatus.FAILED.value,
                error_message=error_msg,
                completed_at=datetime.now()
            )
            return {"success": False, "error": error_msg}
    
    def ingest_multiple_dates(self, coin_id_map: Dict[str, str], start_date: date, end_date: date) -> dict:
        """Ingest price data for multiple dates."""
        logging.info(f"Ingesting CoinGecko data from {start_date} to {end_date}")
        
        results = {}
        current_date = start_date
        
        while current_date <= end_date:
            try:
                result = self.ingest_coingecko_data_for_date(
                    coin_id_map, 
                    datetime.combine(current_date, datetime.min.time())
                )
                results[current_date.isoformat()] = result
                
                # Add delay between date requests to be respectful to the API
                time.sleep(REQUEST_DELAY_SECONDS)
                
            except Exception as e:
                error_msg = f"Error processing date {current_date}: {str(e)}"
                logging.error(error_msg)
                results[current_date.isoformat()] = {"success": False, "error": error_msg}
            
            current_date += timedelta(days=1)
        
        return results
    
    def backfill_missing_data(self, coin_id_map: Dict[str, str], days_back: int = 30) -> dict:
        """Backfill missing price data for the last N days."""
        end_date = datetime.now().date() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back)
        
        logging.info(f"Starting backfill for {days_back} days ({start_date} to {end_date})")
        
        # Get existing price dates from database to avoid unnecessary API calls
        existing_prices = self.db.get_market_prices(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        existing_dates_by_coin = {}
        for price in existing_prices:
            if price.coin_id not in existing_dates_by_coin:
                existing_dates_by_coin[price.coin_id] = set()
            existing_dates_by_coin[price.coin_id].add(price.price_date)
        
        # Only fetch missing dates
        missing_dates = []
        current_date = start_date
        while current_date <= end_date:
            for coin_id in coin_id_map.values():
                if (coin_id not in existing_dates_by_coin or 
                    current_date not in existing_dates_by_coin[coin_id]):
                    missing_dates.append(current_date)
                    break  # Only add the date once, not per coin
            current_date += timedelta(days=1)
        
        if not missing_dates:
            logging.info("No missing dates found, backfill not needed")
            return {"success": True, "message": "No missing data"}
        
        logging.info(f"Found {len(missing_dates)} missing dates, starting backfill")
        
        results = {}
        for missing_date in missing_dates:
            try:
                result = self.ingest_coingecko_data_for_date(
                    coin_id_map,
                    datetime.combine(missing_date, datetime.min.time())
                )
                results[missing_date.isoformat()] = result
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:
                error_msg = f"Error in backfill for date {missing_date}: {str(e)}"
                logging.error(error_msg)
                results[missing_date.isoformat()] = {"success": False, "error": error_msg}
        
        return results


# Global ingestor instance
coingecko_ingestor = CoinGeckoIngestor()


if __name__ == '__main__':
    # Example usage
    logging.info("--- Starting Enhanced CoinGecko Ingestion Script ---")
    
    ingestor = CoinGeckoIngestor()
    
    coin_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum", 
        "DOGE": "dogecoin"
    }
    
    # Ingest for yesterday
    result = ingestor.ingest_coingecko_data_for_date(coin_map)
    print(f"Daily ingestion result: {result}")
    
    # Example backfill for last 7 days
    # backfill_result = ingestor.backfill_missing_data(coin_map, days_back=7)
    # print(f"Backfill result: {backfill_result}")
    
    logging.info("--- Enhanced CoinGecko Ingestion Script Finished ---")
