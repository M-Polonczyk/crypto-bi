-- models/marts/core/fct_transactions.sql
WITH stg_transactions AS (
    SELECT * FROM {{ ref('stg_blockchair_transactions') }}
),
dim_date AS (
    SELECT full_date, year, month, day_of_month FROM {{ ref('dim_date') }} -- Select only needed date fields or a date_key
)
SELECT
    -- Consider generating a surrogate key:
    -- {{ dbt_utils.generate_surrogate_key(['stg_t.tx_hash', 'stg_t.coin_symbol']) }} AS transaction_pk,
    stg_t.tx_hash,
    stg_t.coin_symbol,
    stg_t.block_id,
    stg_t.tx_timestamp_utc,
    stg_t.tx_date,
    d.year AS tx_year,
    d.month AS tx_month,
    d.day_of_month AS tx_day_of_month,
    stg_t.fee_usd,
    stg_t.output_total_usd,
    stg_t.input_count,
    stg_t.output_count,
    stg_t.tx_size_bytes,
    stg_t.is_coinbase
FROM stg_transactions stg_t
LEFT JOIN dim_date d ON stg_t.tx_date = d.full_date