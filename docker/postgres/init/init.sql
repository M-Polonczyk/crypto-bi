-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

GRANT ALL PRIVILEGES ON DATABASE app_db TO airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;


-- Create tables for app_db
\c app_db;

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

CREATE TABLE IF NOT EXISTS raw_blockchain_addresses (
  address VARCHAR(255) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS raw_market_prices_volumes (
  coin_id VARCHAR(50),
  price_date DATE,
  price_usd NUMERIC,
  volume_usd NUMERIC,
  market_cap_usd NUMERIC,
  PRIMARY KEY (coin_id, price_date)
);