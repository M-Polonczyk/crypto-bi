"""
Enhanced Blockchair ingestor using SQLAlchemy ORM and Pydantic models.
Provides clean integration with the database service layer.
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from src.database import db_service
from src.schemas import (
    BlockchainBlockData, BlockchainTransactionData, BlockchainAddressData,
    DataIngestionLogData, IngestionStatus
)
from src.common.utils import get_yesterday_date_str

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BLOCKCHAIR_BASE_URL = "https://api.blockchair.com"
REQUEST_DELAY_SECONDS = 1
TIMEZONE_SUFFIX = '+00:00'


class BlockchairIngestor:
    """Enhanced Blockchair data ingestor using SQLAlchemy and Pydantic."""
    
    def __init__(self):
        """Initialize the ingestor with database service."""
        self.db = db_service
        self.db.create_tables()
    
    def parse_iso_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Helper function to parse ISO timestamp with UTC timezone."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', TIMEZONE_SUFFIX))
        except (ValueError, AttributeError):
            return None
    
    def fetch_blockchair_data(self, coin: str, endpoint_path: str, params: Optional[dict] = None) -> Optional[dict]:
        """Fetches data from a Blockchair endpoint with proper error handling."""
        url = f"{BLOCKCHAIR_BASE_URL}/{coin}/{endpoint_path}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                logging.info("Successfully fetched data from %s with params %s", url, params)
                return data['data']
            else:
                logging.warning("No 'data' field in response from %s", url)
                return data
                
        except requests.exceptions.RequestException as e:
            logging.error("Error fetching data from %s: %s", url, e)
            return None
        except ValueError as e:
            logging.error("Error decoding JSON from %s: %s", url, e)
            return None
    
    def get_latest_block_height(self, coin_symbol: str) -> Optional[int]:
        """Get the latest block height for a coin."""
        data = self.fetch_blockchair_data(coin_symbol.lower(), "stats")
        if data and 'blocks' in data:
            return data['blocks']
        return None
    
    def process_block_data(self, block_height: int, block_details: dict, coin_symbol: str) -> Optional[BlockchainBlockData]:
        """Process individual block data into Pydantic model."""
        if not isinstance(block_details, dict):
            return None
        
        try:
            block_time = self.parse_iso_timestamp(block_details.get('time'))
            
            return BlockchainBlockData(
                block_id=int(block_height),
                coin_symbol=coin_symbol.upper(),
                block_hash=block_details.get('hash', ''),
                block_time=block_time,
                transaction_count=block_details.get('transaction_count'),
                size_bytes=block_details.get('size'),
                difficulty=Decimal(str(block_details.get('difficulty', 0))) if block_details.get('difficulty') else None
            )
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing block data: {e}")
            return None
    
    def process_transaction_data(self, tx_data: dict, coin_symbol: str) -> Optional[BlockchainTransactionData]:
        """Process individual transaction data into Pydantic model."""
        if not isinstance(tx_data, dict):
            return None
        
        try:
            tx_time = self.parse_iso_timestamp(tx_data.get('time'))
            
            return BlockchainTransactionData(
                tx_hash=tx_data.get('hash', ''),
                coin_symbol=coin_symbol.upper(),
                block_id=tx_data.get('block_id'),
                tx_time=tx_time,
                fee_usd=Decimal(str(tx_data.get('fee_usd', 0))) if tx_data.get('fee_usd') else None,
                output_total_usd=Decimal(str(tx_data.get('output_total_usd', 0))) if tx_data.get('output_total_usd') else None,
                input_count=tx_data.get('input_count'),
                output_count=tx_data.get('output_count'),
                size_bytes=tx_data.get('size'),
                is_coinbase=tx_data.get('is_coinbase', False)
            )
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing transaction data: {e}")
            return None
    
    def process_address_data(self, address: str, addr_data: dict, coin_symbol: str) -> Optional[BlockchainAddressData]:
        """Process individual address data into Pydantic model."""
        if not isinstance(addr_data, dict) or 'address' not in addr_data:
            return None
        
        try:
            addr_info = addr_data['address']
            
            first_seen = self.parse_iso_timestamp(addr_info.get('first_seen_receiving'))
            last_seen = self.parse_iso_timestamp(addr_info.get('last_seen_spending'))
            
            return BlockchainAddressData(
                address=address,
                coin_symbol=coin_symbol.upper(),
                first_seen_time=first_seen,
                last_seen_time=last_seen,
                transaction_count=addr_info.get('transaction_count'),
                received_total_usd=Decimal(str(addr_info.get('received_usd', 0))) if addr_info.get('received_usd') else None,
                spent_total_usd=Decimal(str(addr_info.get('spent_usd', 0))) if addr_info.get('spent_usd') else None,
                balance_usd=Decimal(str(addr_info.get('balance_usd', 0))) if addr_info.get('balance_usd') else None
            )
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing address data: {e}")
            return None
    
    def ingest_blocks_by_height_range(self, coin_symbol: str = "bitcoin", start_height: Optional[int] = None, end_height: Optional[int] = None) -> dict:
        """Ingest blocks within a specific height range."""
        log_data = DataIngestionLogData(
            source="blockchair",
            data_type="blocks",
            coin_symbol=coin_symbol,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now()
        )
        log_id = self.db.log_ingestion(log_data)
        
        try:
            if end_height is None:
                end_height = self.get_latest_block_height(coin_symbol)
                if end_height is None:
                    error_msg = f"Could not determine latest block height for {coin_symbol}"
                    logging.error(error_msg)
                    self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value, 
                                                error_message=error_msg, completed_at=datetime.now())
                    return {"success": False, "error": error_msg}
            
            if start_height is None:
                start_height = max(0, end_height - 100)
            
            # Fetch block data
            block_list = ",".join(str(h) for h in range(start_height, end_height + 1))
            api_data = self.fetch_blockchair_data(coin_symbol.lower(), f"blocks/{block_list}")
            time.sleep(REQUEST_DELAY_SECONDS)
            
            if not api_data:
                error_msg = f"No block data received from Blockchair for {coin_symbol} heights {start_height}-{end_height}"
                logging.warning(error_msg)
                self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                            error_message=error_msg, completed_at=datetime.now())
                return {"success": False, "error": error_msg}
            
            # Process and validate block data
            validated_blocks = []
            for block_height, block_details in api_data.items():
                block_data = self.process_block_data(block_height, block_details, coin_symbol)
                if block_data:
                    validated_blocks.append(block_data)
            
            # Insert into database
            result = self.db.insert_blocks(validated_blocks)
            
            # Update log
            self.db.update_ingestion_log(
                log_id,
                status=IngestionStatus.SUCCESS.value,
                records_processed=len(api_data),
                records_inserted=result["inserted"],
                records_updated=result["updated"],
                completed_at=datetime.now()
            )
            
            logging.info(f"Ingested {result['inserted']} blocks, updated {result['updated']} for {coin_symbol} (heights {start_height}-{end_height})")
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = f"Error ingesting blocks for {coin_symbol}: {str(e)}"
            logging.error(error_msg)
            self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                        error_message=error_msg, completed_at=datetime.now())
            return {"success": False, "error": error_msg}
    
    def ingest_recent_blocks(self, coin_symbol: str = "bitcoin", date_str: Optional[str] = None) -> dict:
        """Ingest blocks for a given coin and date using Blockchair's dashboard API."""
        if date_str is None:
            date_str = get_yesterday_date_str()
        
        log_data = DataIngestionLogData(
            source="blockchair",
            data_type="blocks",
            coin_symbol=coin_symbol,
            target_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
            status=IngestionStatus.RUNNING,
            started_at=datetime.now()
        )
        log_id = self.db.log_ingestion(log_data)
        
        try:
            # Fetch data from Blockchair dashboard API
            api_data = self.fetch_blockchair_data(coin_symbol.lower(), "dashboards/blocks", 
                                                params={"date": date_str, "limit": 1000})
            time.sleep(REQUEST_DELAY_SECONDS)
            
            if not api_data:
                error_msg = f"No block data received from Blockchair for {coin_symbol} on {date_str}"
                logging.warning(error_msg)
                self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                            error_message=error_msg, completed_at=datetime.now())
                return {"success": False, "error": error_msg}
            
            # Process and validate block data
            validated_blocks = []
            for block_data in api_data:
                block_info = self.process_block_data(block_data.get('id', 0), block_data, coin_symbol)
                if block_info:
                    validated_blocks.append(block_info)
            
            # Insert into database
            result = self.db.insert_blocks(validated_blocks)
            
            # Update log
            self.db.update_ingestion_log(
                log_id,
                status=IngestionStatus.SUCCESS.value,
                records_processed=len(api_data),
                records_inserted=result["inserted"],
                records_updated=result["updated"],
                completed_at=datetime.now()
            )
            
            logging.info(f"Ingested {result['inserted']} blocks, updated {result['updated']} for {coin_symbol} on {date_str}")
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = f"Error ingesting blocks for {coin_symbol} on {date_str}: {str(e)}"
            logging.error(error_msg)
            self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                        error_message=error_msg, completed_at=datetime.now())
            return {"success": False, "error": error_msg}
    
    def ingest_transactions_by_date(self, coin_symbol: str = "bitcoin", date_str: Optional[str] = None, limit: int = 10000) -> dict:
        """Ingest transactions for a given coin and date."""
        if date_str is None:
            date_str = get_yesterday_date_str()
        
        log_data = DataIngestionLogData(
            source="blockchair",
            data_type="transactions",
            coin_symbol=coin_symbol,
            target_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
            status=IngestionStatus.RUNNING,
            started_at=datetime.now()
        )
        log_id = self.db.log_ingestion(log_data)
        
        try:
            # Fetch transactions using dashboard API
            api_data = self.fetch_blockchair_data(coin_symbol.lower(), "dashboards/transactions", 
                                                params={"date": date_str, "limit": limit})
            time.sleep(REQUEST_DELAY_SECONDS)
            
            if not api_data:
                error_msg = f"No transaction data received from Blockchair for {coin_symbol} on {date_str}"
                logging.warning(error_msg)
                self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                            error_message=error_msg, completed_at=datetime.now())
                return {"success": False, "error": error_msg}
            
            # Process and validate transaction data
            validated_transactions = []
            for tx_data in api_data:
                tx_info = self.process_transaction_data(tx_data, coin_symbol)
                if tx_info:
                    validated_transactions.append(tx_info)
            
            # Insert into database
            result = self.db.insert_transactions(validated_transactions)
            
            # Update log
            self.db.update_ingestion_log(
                log_id,
                status=IngestionStatus.SUCCESS.value,
                records_processed=len(api_data),
                records_inserted=result["inserted"],
                records_updated=result["updated"],
                completed_at=datetime.now()
            )
            
            logging.info(f"Ingested {result['inserted']} transactions, updated {result['updated']} for {coin_symbol} on {date_str}")
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = f"Error ingesting transactions for {coin_symbol} on {date_str}: {str(e)}"
            logging.error(error_msg)
            self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                        error_message=error_msg, completed_at=datetime.now())
            return {"success": False, "error": error_msg}
    
    def ingest_address_data(self, coin_symbol: str = "bitcoin", addresses: Optional[List[str]] = None) -> dict:
        """Ingest address data for a list of addresses."""
        if not addresses:
            error_msg = "No addresses provided for address data ingestion"
            logging.warning(error_msg)
            return {"success": False, "error": error_msg}
        
        log_data = DataIngestionLogData(
            source="blockchair",
            data_type="addresses",
            coin_symbol=coin_symbol,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now()
        )
        log_id = self.db.log_ingestion(log_data)
        
        try:
            validated_addresses = []
            total_processed = 0
            
            # Process addresses in batches
            batch_size = 10
            for i in range(0, len(addresses), batch_size):
                batch_addresses = addresses[i:i + batch_size]
                address_list = ",".join(batch_addresses)
                
                api_data = self.fetch_blockchair_data(coin_symbol.lower(), f"dashboards/addresses/{address_list}")
                time.sleep(REQUEST_DELAY_SECONDS)
                
                if not api_data:
                    logging.warning(f"No address data for addresses {address_list}")
                    continue
                
                for address, addr_data in api_data.items():
                    addr_info = self.process_address_data(address, addr_data, coin_symbol)
                    if addr_info:
                        validated_addresses.append(addr_info)
                        total_processed += 1
            
            # Insert into database
            result = self.db.insert_addresses(validated_addresses)
            
            # Update log
            self.db.update_ingestion_log(
                log_id,
                status=IngestionStatus.SUCCESS.value,
                records_processed=total_processed,
                records_inserted=result["inserted"],
                records_updated=result["updated"],
                completed_at=datetime.now()
            )
            
            logging.info(f"Ingested {result['inserted']} addresses, updated {result['updated']} for {coin_symbol}")
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = f"Error ingesting addresses for {coin_symbol}: {str(e)}"
            logging.error(error_msg)
            self.db.update_ingestion_log(log_id, status=IngestionStatus.FAILED.value,
                                        error_message=error_msg, completed_at=datetime.now())
            return {"success": False, "error": error_msg}
    
    def run_daily_ingestion(self, coin_symbols: Optional[List[str]] = None, date_str: Optional[str] = None) -> dict:
        """Main function to run daily ingestion for all specified coins."""
        if coin_symbols is None:
            coin_symbols = ["bitcoin", "ethereum", "dogecoin"]
        
        if date_str is None:
            date_str = get_yesterday_date_str()
        
        logging.info(f"Starting daily Blockchair ingestion for {coin_symbols} on {date_str}")
        
        results = {}
        for coin in coin_symbols:
            try:
                logging.info(f"Processing {coin}...")
                
                # Ingest blocks first
                block_result = self.ingest_recent_blocks(coin_symbol=coin, date_str=date_str)
                
                # Then ingest transactions
                tx_result = self.ingest_transactions_by_date(coin_symbol=coin, date_str=date_str)
                
                results[coin] = {
                    "blocks": block_result,
                    "transactions": tx_result
                }
                
                logging.info(f"Completed processing {coin}")
                
            except Exception as e:
                error_msg = f"Error processing {coin}: {str(e)}"
                logging.error(error_msg)
                results[coin] = {"error": error_msg}
                continue
        
        logging.info("Daily Blockchair ingestion completed")
        return results


# Global ingestor instance
blockchair_ingestor = BlockchairIngestor()


if __name__ == '__main__':
    # Example usage
    logging.info("--- Starting Enhanced Blockchair Ingestion Script ---")
    
    ingestor = BlockchairIngestor()
    
    # Run daily ingestion for supported coins
    results = ingestor.run_daily_ingestion(coin_symbols=["bitcoin", "ethereum", "dogecoin"])
    
    # Print results summary
    for coin, result in results.items():
        print(f"\n{coin.upper()} Results:")
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            if "blocks" in result:
                print(f"  Blocks: {result['blocks']}")
            if "transactions" in result:
                print(f"  Transactions: {result['transactions']}")
    
    logging.info("--- Enhanced Blockchair Ingestion Script Finished ---")
