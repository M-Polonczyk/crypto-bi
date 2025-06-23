-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

GRANT ALL PRIVILEGES ON DATABASE app_db TO airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;

\c app_db;

CREATE TABLE Coins (
    coin_symbol VARCHAR(10) PRIMARY KEY,
    coin_name VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO Coins (coin_symbol, coin_name) VALUES ('BTC', 'Bitcoin') ON CONFLICT (coin_symbol) DO NOTHING;
INSERT INTO Coins (coin_symbol, coin_name) VALUES ('ETH', 'Ethereum') ON CONFLICT (coin_symbol) DO NOTHING;
INSERT INTO Coins (coin_symbol, coin_name) VALUES ('DOGE', 'Dogecoin') ON CONFLICT (coin_symbol) DO NOTHING;

CREATE TABLE Blocks (
    block_id BIGINT NOT NULL,
    coin_symbol VARCHAR(10) NOT NULL, 
    hash VARCHAR(300) UNIQUE NOT NULL,
    time_utc TIMESTAMP NOT NULL,
    guessed_miner VARCHAR(255),
    transaction_count INT NOT NULL,
    output_btc DECIMAL(20, 8) NOT NULL,
    output_usd DECIMAL(20, 2) NOT NULL,
    fee_btc DECIMAL(20, 8) NOT NULL,
    fee_usd DECIMAL(20, 2) NOT NULL,
    size_kb DECIMAL(10, 3) NOT NULL,
    
    PRIMARY KEY (block_id, coin_symbol),
    FOREIGN KEY (coin_symbol) REFERENCES Coins(coin_symbol)
);

CREATE TABLE Transactions (
    id SERIAL PRIMARY KEY,
    coin_symbol VARCHAR(10) NOT NULL,
    transaction_hash VARCHAR(64) NOT NULL,
    block_height BIGINT NOT NULL,
    input_count INT NOT NULL,
    output_count INT NOT NULL,
    time_utc TIMESTAMP NOT NULL,
    output_btc DECIMAL(20, 8) NOT NULL,
    output_usd DECIMAL(20, 2) NOT NULL,
    transaction_fee_usd DECIMAL(20, 2) NOT NULL,
    is_coinbase BOOLEAN NOT NULL,
    UNIQUE (coin_symbol, transaction_hash),
        FOREIGN KEY (block_height, coin_symbol) REFERENCES Blocks(block_id, coin_symbol),
    FOREIGN KEY (coin_symbol) REFERENCES Coins(coin_symbol) 
);

CREATE TABLE IF NOT EXISTS raw_market_prices_volumes (
  coin_symbol VARCHAR(50), 
  price_date DATE,
  price_usd NUMERIC,
  volume_usd NUMERIC,
  market_cap_usd NUMERIC,
  PRIMARY KEY (coin_symbol, price_date),
  FOREIGN KEY (coin_symbol) REFERENCES Coins(coin_symbol)
);
