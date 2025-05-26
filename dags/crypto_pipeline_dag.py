from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Import your ingestion functions
# Ensure your 'src' directory is in PYTHONPATH for Airflow workers
# or install your project as a package.
# A common way is to add the project directory to sys.path in the DAG file
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Add project root to path

from src.ingestion.blockchair_ingestor import ingest_recent_blocks, ingest_transactions_for_blocks
from src.ingestion.coingecko_ingestor import ingest_coingecko_data_for_date
from src.common.utils import get_yesterday_date_str

# Define your CoinGecko coin map
COIN_GECKO_COIN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "DOGE": "dogecoin"
}
BLOCKCHAIN_COINS = ["bitcoin", "ethereum", "dogecoin"]


def ingest_all_blockchair_data_callable():
    yesterday = get_yesterday_date_str()
    for coin in BLOCKCHAIN_COINS:
        ingest_recent_blocks(coin_symbol=coin, date_str=yesterday)
        # Consider how you want to link transactions to blocks or just fetch by date
        ingest_transactions_for_blocks(coin_symbol=coin) # Uses date-based fetching

def ingest_all_coingecko_data_callable():
    ingest_coingecko_data_for_date(COIN_GECKO_COIN_MAP)


with DAG(
    dag_id='crypto_data_ingestion_v1',
    schedule_interval='@daily', # Run daily
    start_date=datetime(2023, 1, 1), # Adjust start date
    catchup=False, # Set to True if you want to backfill
    tags=['crypto', 'ingestion'],
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    }
) as dag:

    task_ingest_coingecko = PythonOperator(
        task_id='ingest_coingecko_prices_volumes',
        python_callable=ingest_all_coingecko_data_callable,
    )

    task_ingest_blockchair = PythonOperator(
        task_id='ingest_blockchair_blocks_transactions',
        python_callable=ingest_all_blockchair_data_callable,
    )

    # Define dependencies (optional, can run in parallel if no strict dependency)
    # For example, if your transformations depend on both being present:
    # task_ingest_coingecko >> some_transformation_task
    # task_ingest_blockchair >> some_transformation_task
    # If they can run independently for raw ingestion:
    # [task_ingest_coingecko, task_ingest_blockchair] # implies parallel

    # For this example, let's assume they can run in parallel for raw ingestion