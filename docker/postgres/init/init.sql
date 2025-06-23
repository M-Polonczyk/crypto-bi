-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

GRANT ALL PRIVILEGES ON DATABASE app_db TO airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;


-- Create tables for app_db
\c app_db;

CREATE TABLE Coins (
    coin_id VARCHAR(10) PRIMARY KEY, 
    coin_name VARCHAR(50) UNIQUE NOT NULL
);


CREATE TABLE Blocks (
    coin_id VARCHAR(10) NOT NULL,
    block_id INT NOT NULL, 
    hash VARCHAR(64) UNIQUE NOT NULL,
    time_utc TIMESTAMP NOT NULL,
    guessed_miner VARCHAR(255),
    transaction_count INT NOT NULL,
    output_btc DECIMAL(20, 8) NOT NULL,
    output_usd DECIMAL(20, 2) NOT NULL,
    fee_btc DECIMAL(20, 8) NOT NULL,
    fee_usd DECIMAL(20, 2) NOT NULL,
    size_kb DECIMAL(10, 3) NOT NULL,
    PRIMARY KEY (block_id),
    FOREIGN KEY (coin_id) REFERENCES Coins(coin_id)
);

-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

GRANT ALL PRIVILEGES ON DATABASE app_db TO airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;


CREATE TABLE Coins (
    coin_id VARCHAR(10) PRIMARY KEY, 
    coin_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE Blocks (
    coin_id VARCHAR(10) NOT NULL,
    block_id INT NOT NULL, 
    hash VARCHAR(64) UNIQUE NOT NULL,
    time_utc TIMESTAMP NOT NULL,
    guessed_miner VARCHAR(255),
    transaction_count INT NOT NULL,
    output_btc DECIMAL(20, 8) NOT NULL,
    output_usd DECIMAL(20, 2) NOT NULL,
    fee_btc DECIMAL(20, 8) NOT NULL,
    fee_usd DECIMAL(20, 2) NOT NULL,
    size_kb DECIMAL(10, 3) NOT NULL,
    PRIMARY KEY (block_id),
    FOREIGN KEY (coin_id) REFERENCES Coins(coin_id)
);



CREATE TABLE Transactions (
    id SERIAL PRIMARY KEY,
    coin_symbol VARCHAR(10) NOT NULL, 
    transaction_hash VARCHAR(64) NOT NULL,
    block_height INT NOT NULL,
    input_count INT NOT NULL,
    output_count INT NOT NULL,
    time_utc TIMESTAMP NOT NULL,
    output_btc DECIMAL(20, 8) NOT NULL,
    output_usd DECIMAL(20, 2) NOT NULL,
    transaction_fee_usd DECIMAL(20, 2) NOT NULL,
    is_coinbase BOOLEAN NOT NULL,
    UNIQUE (coin_symbol, transaction_hash),
    FOREIGN KEY (coin_symbol, block_height) REFERENCES Blocks(coin_symbol, block_height), 
    FOREIGN KEY (coin_symbol) REFERENCES Coins(coin_id) 
);
