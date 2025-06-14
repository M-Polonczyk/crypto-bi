import requests
import logging
from datetime import datetime
from src.ingestion.db_utils import get_db_connection, execute_query, execute_many
from src.common.utils import get_yesterday_date_str

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BLOCKCHAIR_BASE_URL = "https://api.blockchair.com"

def create_blockchair_tables(conn):
    """Creates tables for Blockchair data if they don't exist."""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS raw_blockchain_blocks (
            block_id BIGINT,
            coin_symbol VARCHAR(10),
            block_hash VARCHAR(255) UNIQUE,
            block_time TIMESTAMP,
            transaction_count INT,
            size_bytes INT,
            difficulty NUMERIC,
            PRIMARY KEY (block_id, coin_symbol)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw_blockchain_transactions (
            tx_hash VARCHAR(255),
            coin_symbol VARCHAR(10),
            block_id BIGINT,
            tx_time TIMESTAMP,
            fee_usd NUMERIC,
            output_total_usd NUMERIC,
            input_count INT,
            output_count INT,
            size_bytes INT,
            is_coinbase BOOLEAN,
            PRIMARY KEY (tx_hash, coin_symbol)
        );
        """
        # Add more tables as needed (e.g., for addresses, inputs/outputs from your project spec)
    ]
    for query in queries:
        execute_query(conn, query)
    logging.info("Blockchair tables ensured.")

def fetch_blockchair_data(coin, endpoint_path, params=None):
    """Fetches data from a Blockchair endpoint."""
    url = f"{BLOCKCHAIR_BASE_URL}/{coin}/{endpoint_path}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Successfully fetched data from {url} with params {params}")
        return data.get('data', [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return None
    except ValueError:
        logging.error(f"Error decoding JSON from {url}")
        return None

def ingest_recent_blocks(coin_symbol="bitcoin", date_str=None):
    """
    Ingests blocks for a given coin and date.
    Blockchair's block endpoint can be queried by date ranges or specific block heights.
    Example: Fetch blocks from a specific day.
    Note: Blockchair API might not directly support 'give me all blocks for this date' easily.
          Often, you'd iterate through block heights or use their dump files for full history.
          This is a simplified example focusing on 'recent' data or a specific query.
          For a daily DAG, you might query for blocks within a specific time window if the API supports it.
          A common pattern for 'yesterday's blocks' is to query blocks with time in that range.
          Let's assume we query blocks with a time close to the target date_str if direct date filter is hard.
          Or we might need to use their dashboard API which allows time-based queries for some stats.
          For a truly robust solution, you'd explore the advanced query capabilities of Blockchair.
          Let's simplify for now and assume we can get a list of blocks.
          Blockchair's /<coin>/blocks endpoint can take `s=time(asc)` and `limit=X`
          and you can also provide a `date=` parameter to filter blocks for a specific day.
          Example: `date=2023-01-01`
    """
    if date_str is None:
        date_str = get_yesterday_date_str() # YYYY-MM-DD

    conn = get_db_connection()
    if not conn:
        return
    try:
        create_blockchair_tables(conn)
        api_data = fetch_blockchair_data(coin_symbol.lower(), "blocks", params={"date": date_str})
        print(f"Fetched {len(api_data)} blocks for {coin_symbol} on {date_str}")
        if not api_data:
            logging.warning(f"No block data received from Blockchair for {coin_symbol} on {date_str}")
            return
        blocks_to_insert = []
        for block_hash, block_details in api_data.items(): # Blockchair blocks are dicts with hash as key
            if not isinstance(block_details, dict): continue
            blocks_to_insert.append((
                block_details.get('id'),
                coin_symbol.upper(),
                block_hash,
                block_details.get('time'),
                block_details.get('transaction_count'),
                block_details.get('size'),
                block_details.get('difficulty')
            ))

        if blocks_to_insert:
            insert_query = """
            INSERT INTO raw_blockchain_blocks (block_id, coin_symbol, block_hash, block_time, transaction_count, size_bytes, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (block_id, coin_symbol) DO NOTHING;
            """
            execute_many(conn, insert_query, blocks_to_insert)
            logging.info(f"Ingested {len(blocks_to_insert)} blocks for {coin_symbol} on {date_str}.")
        else:
            logging.info(f"No new blocks to ingest for {coin_symbol} on {date_str}.")

    finally:
        if conn:
            conn.close()

def ingest_transactions_for_blocks(coin_symbol="bitcoin", block_ids=None):
    """
    Ingests transactions for a given list of block IDs.
    This is more efficient if you first get block_ids for a day, then fetch their transactions.
    Blockchair's transaction endpoint can be complex. A common way is to get transactions by block.
    Or query their /<coin>/transactions with `block_id=X` or `date=YYYY-MM-DD`
    The /<coin>/transactions endpoint with a `date` parameter will give transactions *confirmed* on that date.
    """
    if block_ids is None: # Fallback if no block_ids provided - this part needs refinement for a real scenario
        logging.warning("No block_ids provided for transaction ingestion. Consider fetching transactions by date directly.")
        # As an alternative, try to fetch transactions directly by date
        date_str = get_yesterday_date_str()
        api_data = fetch_blockchair_data(coin_symbol.lower(), "transactions", params={"date": date_str, "limit": 1000, "s": "time(asc)"}) # Adjust limit
    else:
        # This part would ideally iterate through block_ids and fetch transactions per block if API structure requires it.
        # However, Blockchair's /<coin>/transactions?date=YYYY-MM-DD is simpler if it meets needs.
        logging.info("Fetching transactions by block_ids is more complex with Blockchair's general API. "
                     "Using date-based transaction fetching as a fallback/alternative.")
        date_str = get_yesterday_date_str() # Assuming date for which blocks were fetched
        api_data = fetch_blockchair_data(coin_symbol.lower(), "transactions", params={"date": date_str, "limit": 1000, "s": "time(asc)"})

    conn = get_db_connection()
    if not conn:
        return
    try:
        create_blockchair_tables(conn)

        if not api_data:
            logging.warning(f"No transaction data received from Blockchair for {coin_symbol}")
            return

        transactions_to_insert = []
        for tx_hash, tx_details in api_data.items(): # Blockchair transactions are often dicts with hash as key
            if not isinstance(tx_details, dict) or 'transaction' not in tx_details: continue

            transaction_data = tx_details['transaction']
            transactions_to_insert.append((
                tx_hash,
                coin_symbol.upper(),
                transaction_data.get('block_id'),
                transaction_data.get('time'),
                transaction_data.get('fee_usd'),
                transaction_data.get('output_total_usd'),
                transaction_data.get('input_count'),
                transaction_data.get('output_count'),
                transaction_data.get('size'),
                transaction_data.get('is_coinbase')
            ))

        if transactions_to_insert:
            insert_query = """
            INSERT INTO raw_blockchain_transactions (
                tx_hash, coin_symbol, block_id, tx_time, fee_usd, output_total_usd,
                input_count, output_count, size_bytes, is_coinbase
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tx_hash, coin_symbol) DO NOTHING;
            """
            execute_many(conn, insert_query, transactions_to_insert)
            logging.info(f"Ingested {len(transactions_to_insert)} transactions for {coin_symbol}.")
        else:
            logging.info(f"No new transactions to ingest for {coin_symbol}.")

    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example usage (you would call these from an Airflow DAG)
    logging.info("--- Starting Blockchair Ingestion Script ---")
    yesterday = get_yesterday_date_str()

    for coin in ["bitcoin", "ethereum", "dogecoin"]:
        logging.info(f"Ingesting blocks for {coin} for date {yesterday}...")
        ingest_recent_blocks(coin_symbol=coin, date_str=yesterday)
        logging.info(f"Ingesting transactions for {coin} for date {yesterday}...")
        # In a real DAG, you might get block_ids from the previous step
        # For simplicity here, we'll let ingest_transactions_for_blocks use its date-based fallback.
        ingest_transactions_for_blocks(coin_symbol=coin)

    logging.info("--- Blockchair Ingestion Script Finished ---")