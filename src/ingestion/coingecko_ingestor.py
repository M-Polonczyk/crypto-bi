import requests
import logging
import time
import os
from datetime import datetime, timedelta
from .db_utils import get_db_connection, execute_query, execute_many
from ..common.utils import get_date_str_for_coingecko # For dd-mm-yyyy format

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
REQUEST_DELAY_SECONDS = 3


def fetch_coingecko_historical_price(coin_id, date_str_ddmmyyyy, vs_currency="usd"):
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
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Successfully fetched CoinGecko data for {coin_id} on {date_str_ddmmyyyy}")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching CoinGecko data for {coin_id} on {date_str_ddmmyyyy}: {e}")
        if response is not None:
             logging.error(f"Response content: {response.text}")
        return None
    except ValueError:
        logging.error(f"Error decoding JSON from CoinGecko for {coin_id} on {date_str_ddmmyyyy}")
        return None

def ingest_coingecko_data_for_date(coin_id_map, target_date_obj=None):
    """
    Ingests price, volume, and market cap for a list of coins for a specific date.
    coin_id_map: e.g., {"BTC": "bitcoin", "ETH": "ethereum", "DOGE": "dogecoin"}
    target_date_obj: datetime object for the target date. Defaults to yesterday.
    """
    if target_date_obj is None:
        target_date_obj = datetime.now() - timedelta(days=1)

    date_str_coingecko = get_date_str_for_coingecko(target_date_obj) # dd-mm-yyyy
    price_date_sql = target_date_obj.strftime("%Y-%m-%d") # YYYY-MM-DD for DB

    conn = get_db_connection()
    if not conn:
        return
    try:
        prices_to_insert = []

        for symbol, cg_id in coin_id_map.items():
            logging.info(f"Fetching CoinGecko data for {symbol} ({cg_id}) on {date_str_coingecko}")
            data = fetch_coingecko_historical_price(cg_id, date_str_coingecko)
            time.sleep(REQUEST_DELAY_SECONDS)

            if data and "market_data" in data:
                md = data["market_data"]
                price = md.get("current_price", {}).get("usd")
                volume = md.get("total_volume", {}).get("usd")
                market_cap = md.get("market_cap", {}).get("usd")

                if price is not None and volume is not None:
                    prices_to_insert.append((
                        cg_id, # Store CoinGecko ID for consistency
                        price_date_sql,
                        price,
                        volume,
                        market_cap
                    ))
                else:
                    logging.warning(f"Missing price/volume data for {cg_id} on {date_str_coingecko}. Price: {price}, Volume: {volume}")
            else:
                logging.warning(f"No market data found for {cg_id} on {date_str_coingecko}")

        if prices_to_insert:
            insert_query = """
            INSERT INTO raw_market_prices_volumes (coin_id, price_date, price_usd, volume_usd, market_cap_usd)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (coin_id, price_date) DO UPDATE SET
                price_usd = EXCLUDED.price_usd,
                volume_usd = EXCLUDED.volume_usd,
                market_cap_usd = EXCLUDED.market_cap_usd;
            """
            execute_many(conn, insert_query, prices_to_insert)
            logging.info(f"Ingested/Updated {len(prices_to_insert)} market price records for date {price_date_sql}.")
        else:
            logging.info(f"No new market prices to ingest for date {price_date_sql}.")

    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example usage (you would call these from an Airflow DAG)
    logging.info("--- Starting CoinGecko Ingestion Script ---")
    coin_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "DOGE": "dogecoin"
    }
    # Ingest for yesterday
    ingest_coingecko_data_for_date(coin_map)
    logging.info("--- CoinGecko Ingestion Script Finished ---")