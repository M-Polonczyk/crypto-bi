-- models/staging/market/stg_coingecko_prices_volumes.sql
WITH source_data AS (
    SELECT * FROM {{ source('raw_coingecko', 'raw_market_prices_volumes') }}
)
SELECT
    coin_id,
    price_date,
    price_usd,
    volume_usd,
    market_cap_usd
FROM source_data