-- models/staging/blockchain/stg_blockchair_blocks.sql
WITH source_data AS (
    SELECT * FROM {{ source('raw_blockchair', 'raw_blockchain_blocks') }}
)
SELECT
    block_id,
    coin_symbol,
    block_hash,
    block_time AS block_timestamp_utc,
    transaction_count,
    size_bytes,
    difficulty,
    DATE(block_time) AS block_date
FROM source_data