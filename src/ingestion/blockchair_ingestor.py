import requests
import logging
import time
from datetime import datetime
from src.ingestion.db_utils import get_db_connection, execute_query, execute_many
from src.common.utils import get_yesterday_date_str

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BLOCKCHAIR_BASE_URL = "https://api.blockchair.com"
COIN_SYMBOL_MAP = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "dogecoin": "DOGE",
}


def safe_float(value, default=0.0, log_msg=""):
    """Bezpiecznie konwertuje wartość na float, obsługując None, ValueError i TypeError."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        logging.warning(
            f"Nie udało się skonwertować wartości '{value}' na float. {log_msg}. Ustawiono na {default}."
        )
        return default


def safe_int(value, default=0, log_msg=""):
    """Bezpiecznie konwertuje wartość na int, obsługując None, ValueError i TypeError."""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        logging.warning(
            f"Nie udało się skonwertować wartości '{value}' na int. {log_msg}. Ustawiono na {default}."
        )
        return default


def fetch_blockchair_data(coin, endpoint_path, params=None):
    """Fetches data from a Blockchair endpoint."""
    url = f"{BLOCKCHAIR_BASE_URL}/{coin}/{endpoint_path}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info("Successfully fetched data from %s with params %s", url, params)
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        logging.error("Error fetching data from %s: %s", url, e)
        return []
    except ValueError:
        logging.error("Error decoding JSON from %s", url)
        return []

def ingest(coin_symbol="bitcoin", date_str=None):
    """
    Główna funkcja ingestująca bloki i transakcje dla danej kryptowaluty i daty.
    """

    mapped_coin_symbol = COIN_SYMBOL_MAP.get(coin_symbol.lower(), coin_symbol.upper())

    def ingest_recent_blocks():
        nonlocal date_str, coin_symbol
        logging.info(
            "Ingesting recent blocks for %s on %s...", coin_symbol, date_str
        )
        api_data = fetch_blockchair_data(
            coin_symbol.lower(), "blocks", params={"date": date_str, "limit": 100}
        )

        blocks_to_insert = []
        for block_data in api_data:
            if not isinstance(block_data, dict):
                continue
            blocks_to_insert.append(
                (
                    safe_int(block_data.get("id")),
                    mapped_coin_symbol,
                    block_data.get("hash"),
                    block_data.get("time"),
                    block_data.get("guessed_miner", "Unknown"),
                    safe_int(block_data.get("transaction_count")),
                    safe_float(block_data.get("output_total")) / 100_000_000,
                    safe_float(block_data.get("output_total_usd", 0)),
                    safe_float(block_data.get("fee_total")) / 100_000_000,
                    safe_float(block_data.get("fee_total_usd", 0)),
                    safe_float(block_data.get("size", 0)) / 1024,
                )
            )
        return blocks_to_insert

    def ingest_transactions_for_blocks(block_ids=None):
        """
        Ingests transactions for a given list of block IDs.
        This is more efficient if you first get block_ids for a day, then fetch their transactions.
        Blockchair's transaction endpoint can be complex. A common way is to get transactions by block.
        Or query their /<coin>/transactions with `block_id=X` or `date=YYYY-MM-DD`
        The /<coin>/transactions endpoint with a `date` parameter will give transactions *confirmed* on that date.
        """
        nonlocal date_str, coin_symbol

        if block_ids is None:
            # Fallback if no block_ids provided - this part needs refinement for a real scenario
            logging.warning(
                "No block_ids provided for transaction ingestion. Consider fetching transactions by date directly."
            )

        transactions_to_insert = []
        api_data = fetch_blockchair_data(
            coin_symbol.lower(),
            "transactions",
            params={"date": date_str, "limit": 100},
        )

        for tx_data in api_data:
            if not isinstance(tx_data, dict):
                continue

            block_id = tx_data.get("block_id")

            if block_id is None:
                logging.warning("skipping transaction with missing block_id")
                continue

            output_btc_tx = safe_float(tx_data.get("output_total")) / 100_000_000
            output_usd_tx = safe_float(tx_data.get("output_total_usd", 0))
            transaction_fee_usd_tx = safe_float(tx_data.get("fee_usd", 0))
            input_count_tx = safe_int(tx_data.get("input_count"))
            output_count_tx = safe_int(tx_data.get("output_count"))

            transactions_to_insert.append(
                (
                    tx_data.get("hash"),  # transaction_hash
                    mapped_coin_symbol,  # coin_symbol
                    safe_int(block_id),  # block_height
                    input_count_tx,  # input_count
                    output_count_tx,  # output_count
                    tx_data.get("time"),
                    output_btc_tx,  # output_btc
                    output_usd_tx,  # output_usd
                    transaction_fee_usd_tx,  # transaction_fee_usd
                    tx_data.get("is_coinbase", False),
                )
            )
        return transactions_to_insert

    if date_str is None:
        date_str = get_yesterday_date_str()

    conn = get_db_connection()
    if not conn:
        return

    try:
        blocks = ingest_recent_blocks()
        insert_blocks_query = """
        INSERT INTO Blocks (block_id, coin_symbol, hash, time_utc, guessed_miner, transaction_count, output_btc, output_usd, fee_btc, fee_usd, size_kb)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (block_id, coin_symbol) DO UPDATE SET -- Poprawiona klauzula ON CONFLICT na klucz złożony
            hash = EXCLUDED.hash,
            time_utc = EXCLUDED.time_utc,
            guessed_miner = EXCLUDED.guessed_miner,
            transaction_count = EXCLUDED.transaction_count,
            output_btc = EXCLUDED.output_btc,
            output_usd = EXCLUDED.output_usd,
            fee_btc = EXCLUDED.fee_btc,
            fee_usd = EXCLUDED.fee_usd,
            size_kb = EXCLUDED.size_kb;
        """
        execute_many(conn, insert_blocks_query, blocks)
        logging.info(
            "Ingested %d blocks for %s on %s.",
            len(blocks),
            coin_symbol,
            date_str,
        )
        transactions = ingest_transactions_for_blocks()
        insert_transactions_query = """
        INSERT INTO Transactions (transaction_hash, coin_symbol, block_height, input_count, output_count, time_utc, output_btc, output_usd, transaction_fee_usd, is_coinbase)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (coin_symbol, transaction_hash) DO UPDATE SET
            block_height = EXCLUDED.block_height,
            input_count = EXCLUDED.input_count,
            output_count = EXCLUDED.output_count,
            time_utc = EXCLUDED.time_utc,
            output_btc = EXCLUDED.output_btc,
            output_usd = EXCLUDED.output_usd,
            transaction_fee_usd = EXCLUDED.transaction_fee_usd,
            is_coinbase = EXCLUDED.is_coinbase;
        """
        execute_many(conn, insert_transactions_query, transactions)
        logging.info(
            "Ingested %d transactions for %s on %s.",
            len(transactions),
            coin_symbol,
            date_str,
        )

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Example usage (you would call these from an Airflow DAG)
    logging.info("--- Starting Blockchair Ingestion Script ---")
    yesterday = get_yesterday_date_str()

    for coin in ["bitcoin"]:
        logging.info(f"Ingesting blocks for {coin} for date {yesterday}...")
        ingest(coin_symbol=coin, date_str=yesterday)

    logging.info("--- Blockchair Ingestion Script Finished ---")
