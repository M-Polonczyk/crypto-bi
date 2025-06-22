import requests
import logging
from datetime import datetime
from src.ingestion.db_utils import get_db_connection, execute_query, execute_many
from src.common.utils import get_yesterday_date_str

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BLOCKCHAIR_BASE_URL = "https://api.blockchair.com"


def fetch_blockchair_data(coin, endpoint_path, params=None):
    """Fetches data from a Blockchair endpoint."""
    url = f"{BLOCKCHAIR_BASE_URL}/{coin}/{endpoint_path}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logging.info("Successfully fetched data from %s with params %s", url, params)
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        logging.error("Error fetching data from %s: %s", url, e)
        return None
    except ValueError:
        logging.error("Error decoding JSON from %s", url)
        return None


def ingest(coin_symbol="bitcoin", date_str=None, block_ids=None):
    """
    Main ingestion function to ingest both blocks and transactions for a given coin and date.
    This is a convenience function that calls the other two ingestion functions.
    """

    def get_api_data(coin, endpoint, params=None):
        api_data = fetch_blockchair_data(coin.lower(), endpoint, params=params)
        if not api_data:
            logging.warning(
                "No block data received from Blockchair for %s on %s",
                coin_symbol,
                date_str,
            )
            return []
        return api_data

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

        api_data = get_api_data(coin_symbol, "blocks", params={"date": date_str})

        blocks_to_insert = []

        for quote in api_data:
            if not isinstance(quote, dict):
                continue
            blocks_to_insert.append(
                (
                    quote.get("id"),
                    coin_symbol.upper(),
                    quote.get("hash"),
                    quote.get("time"),
                    quote.get("transaction_count"),
                    quote.get("size"),
                    quote.get("difficulty"),
                    quote.get("guessed_miner", "Unknown"),
                )
            )

        return blocks_to_insert

    def ingest_transactions_for_blocks(coin_symbol="bitcoin", block_ids=None):
        """
        Ingests transactions for a given list of block IDs.
        This is more efficient if you first get block_ids for a day, then fetch their transactions.
        Blockchair's transaction endpoint can be complex. A common way is to get transactions by block.
        Or query their /<coin>/transactions with `block_id=X` or `date=YYYY-MM-DD`
        The /<coin>/transactions endpoint with a `date` parameter will give transactions *confirmed* on that date.
        """
        if block_ids is None:
            # Fallback if no block_ids provided - this part needs refinement for a real scenario
            logging.warning(
                "No block_ids provided for transaction ingestion. Consider fetching transactions by date directly."
            )

        api_data = get_api_data(
            coin_symbol,
            "transactions",
            params={"date": date_str, "s": "time(asc)"},
        )

        transactions_to_insert = []
        for quote in api_data:
            if not isinstance(quote, dict):
                continue
            transactions_to_insert.append(
                (
                    quote.get("hash"),
                    coin_symbol.upper(),
                    quote.get("id"),
                    quote.get("time"),
                    quote.get("fee_usd"),
                    quote.get("output_total_usd"),
                    quote.get("input_count"),
                    quote.get("output_count"),
                    quote.get("size"),
                    quote.get("is_coinbase"),
                )
            )
        return transactions_to_insert

    if date_str is None:
        date_str = get_yesterday_date_str()  # YYYY-MM-DD

    conn = get_db_connection()
    if not conn:
        return

    try:
        blocks = ingest_recent_blocks(coin_symbol, date_str)
        transactions = ingest_transactions_for_blocks(coin_symbol, block_ids)
        if not (transactions and blocks):
            logging.warning(
                "No data to ingest for %s on %s. Blocks: %s, Transactions: %s",
                coin_symbol,
                date_str,
                blocks,
                transactions,
            )
            return

        insert_query = """
        INSERT INTO raw_blockchain_transactions (
            transaction_hash, coin_symbol, block_id, tx_time, fee_usd, output_total_usd,
            input_count, output_count, size_bytes, is_coinbase
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tx_hash, coin_symbol) DO NOTHING;
        """
        execute_many(conn, insert_query, transactions)
        logging.info(f"Ingested {len(transactions)} transactions for {coin_symbol}.")
        insert_query = """
        INSERT INTO raw_blockchain_blocks (block_id, coin_symbol, block_hash, block_time, transaction_count, size_bytes, difficulty)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (block_id, coin_symbol) DO NOTHING;
        """
        execute_many(conn, insert_query, blocks)
        logging.info(
            "Ingested %d blocks for %s on %s.",
            len(blocks),
            coin_symbol,
            date_str,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    # Example usage (you would call these from an Airflow DAG)
    logging.info("--- Starting Blockchair Ingestion Script ---")
    yesterday = get_yesterday_date_str()

    for coin in ["bitcoin"]:
        logging.info(f"Ingesting blocks for {coin} for date {yesterday}...")
        ingest(coin_symbol=coin, date_str=yesterday)
        logging.info(f"Ingesting transactions for {coin} for date {yesterday}...")

    logging.info("--- Blockchair Ingestion Script Finished ---")
