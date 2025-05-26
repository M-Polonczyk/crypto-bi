-- models/staging/blockchain/stg_blockchair_transactions.sql
WITH source_data AS (
    SELECT * FROM {{ source('raw_blockchair', 'raw_blockchain_transactions') }}
)
SELECT
    tx_hash,
    coin_symbol,
    block_id,
    tx_time AS tx_timestamp_utc,
    fee_usd,
    output_total_usd,
    input_count,
    output_count,
    size_bytes AS tx_size_bytes,
    is_coinbase,
    DATE(tx_time) AS tx_date
FROM source_data