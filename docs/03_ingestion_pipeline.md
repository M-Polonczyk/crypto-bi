# Data Ingestion Pipeline

The data ingestion pipeline is responsible for extracting data from external APIs (Blockchair and CoinGecko) and loading it into raw/staging tables in the PostgreSQL application database. This process is orchestrated by Apache Airflow.

## Core Components

1. **Python Ingestion Scripts (`src/ingestion/`):**
    * **`blockchair_ingestor.py`:** Handles all interactions with the Blockchair API.
        * Fetches block data for specified cryptocurrencies (BTC, ETH, DOGE) for a given date.
        * Fetches transaction data for these cryptocurrencies for a given date.
        * Includes functions to create necessary raw tables in PostgreSQL if they don't exist (`CREATE TABLE IF NOT EXISTS`).
        * Uses `psycopg2` to connect to PostgreSQL and insert data, handling potential conflicts (e.g., `ON CONFLICT DO NOTHING` for idempotent writes).
    * **`coingecko_ingestor.py`:** Handles all interactions with the CoinGecko API.
        * Fetches historical market data (price, volume, market cap) for specified cryptocurrencies for a given date.
        * Creates the raw market data table in PostgreSQL if it doesn't exist.
        * Inserts or updates market data, using `ON CONFLICT DO UPDATE` to ensure the latest data for a given coin and date is stored.
    * **`db_utils.py`:** Contains utility functions for establishing PostgreSQL database connections and executing queries (single, batch). Reads database credentials from environment variables.
    * **Shared Utilities (`src/common/utils.py`):** Provides common helper functions, such as date manipulation (e.g., getting yesterday's date in various formats).

2. **Apache Airflow DAGs (`dags/`):**
    * A primary DAG (e.g., `crypto_data_ingestion_vX.py`) orchestrates the entire ingestion process.
    * **Scheduling:** The DAG is typically scheduled to run daily (e.g., `@daily` or a cron expression like `0 1 * * *` to run at 1 AM UTC).
    * **Tasks:**
        * `PythonOperator` tasks are used to call the main functions within the ingestion scripts (e.g., `ingest_recent_blocks`, `ingest_transactions_for_blocks`, `ingest_coingecko_data_for_date`).
        * Tasks can be defined to run in parallel for different data sources or sequentially if there are dependencies.
        * Error handling, retries, and logging are managed by Airflow.

## Workflow for a Single Daily Run

1. **Trigger:** Airflow's scheduler triggers the main ingestion DAG at the scheduled time.
2. **Parameterization (Date):** The DAG typically processes data for the "previous day" relative to its execution date. Utility functions help determine this target date.
3. **CoinGecko Ingestion Task:**
    * The `ingest_coingecko_data_for_date` function is called.
    * It iterates through the target cryptocurrencies (BTC, ETH, DOGE).
    * For each coin, it calls the CoinGecko API to fetch market data for the target date.
    * A small delay is introduced between API calls to respect rate limits.
    * Fetched data is then inserted/updated into the `raw_market_prices_volumes` table in PostgreSQL.
4. **Blockchair Ingestion Tasks (can run in parallel with CoinGecko or sequentially):**
    * The `ingest_all_blockchair_data_callable` (or similar wrapper function in the DAG) is called.
    * This function iterates through BTC, ETH, and DOGE.
    * For each coin:
        * `ingest_recent_blocks` fetches block data for the target date and inserts it into `raw_blockchain_blocks`.
        * `ingest_transactions_for_blocks` fetches transaction data for the target date (or based on fetched block IDs if implemented that way) and inserts it into `raw_blockchain_transactions`.
    * Rate limiting delays are also applied here.
5. **Logging and Monitoring:**
    * All ingestion steps log their progress, successes, and failures. Airflow captures these logs, making them accessible via the Airflow UI.
    * Airflow monitors task status (running, success, failed) and handles retries as configured.
6. **Completion:** Once all ingestion tasks complete successfully, the raw data for the target day is available in PostgreSQL, ready for dbt transformation.

## Database Interaction

* **Schema for Raw Data:** Ingested data is loaded into tables within the `public` schema (or a dedicated `raw_data` schema if preferred) in the `postgres_app_db`.
* **Table Creation:** Scripts use `CREATE TABLE IF NOT EXISTS` to ensure tables are present.
* **Idempotency:**
  * For blockchain data (blocks, transactions), `ON CONFLICT (primary_key_or_unique_constraint) DO NOTHING` is used. This ensures that if a record already exists (e.g., due to a re-run), it's not duplicated.
  * For market data, `ON CONFLICT (coin_id, price_date) DO UPDATE SET ...` is used. This allows for corrections or updates to historical market data if the source provides them.

## Configuration

* **API Keys:** Optional API keys (e.g., for CoinGecko Pro) are managed via environment variables (e.g., `COINGECKO_API_KEY`).
* **Database Credentials:** Connection details for PostgreSQL (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER_APP`, `DB_PASSWORD_APP`) are sourced from environment variables, which are loaded by Docker Compose into the Airflow worker/scheduler environment.
* **Target Cryptocurrencies:** The list of coins to process (BTC, ETH, DOGE) is typically hardcoded or configurable within the DAG or ingestion scripts.

## Error Handling and Retries

* **API Request Errors:** `requests` library's exception handling (`response.raise_for_status()`, `try-except` blocks) is used to catch HTTP errors or network issues.
* **Database Errors:** `psycopg2` exceptions are caught during database operations.
* **Airflow Retries:** DAG tasks are configured with a retry policy (e.g., retry once after a 5-minute delay) to handle transient failures.
* **Logging:** Comprehensive logging helps in diagnosing issues after a failure.

```
