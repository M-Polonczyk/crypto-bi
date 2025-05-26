# Dimensional Model Overview

The core analytical data model implemented in the `marts` layer of our dbt project is a **dimensional model**. This approach, popularized by Ralph Kimball, structures data for optimal query performance, understandability, and ease of use with BI tools like Power BI.

## Key Concepts

1. **Facts:**
    * Represent business measurements or metrics. These are typically numeric and additive.
    * Stored in **Fact Tables**.
    * Examples: Transaction value, number of transactions, daily trading volume, number of blocks mined.

2. **Dimensions:**
    * Provide the context for the facts. They describe the "who, what, where, when, why, and how" related to a business process event.
    * Stored in **Dimension Tables**.
    * Examples: Date, Cryptocurrency, Block details, Address (if modeled).
    * Dimension tables contain descriptive attributes (e.g., month name, cryptocurrency full name, block hash).

3. **Star Schema (Primary Goal):**
    * The most common dimensional model structure.
    * Characterized by one or more fact tables referencing any number of dimension tables.
    * Visually resembles a star, with the fact table at the center and dimension tables radiating outwards.
    * Generally denormalized for simpler joins and faster queries.

4. **Snowflake Schema (Potential Evolution):**
    * An extension of a star schema where dimension tables are normalized into multiple related tables.
    * Can reduce data redundancy in large dimensions but may lead to more complex queries with more joins.
    * We aim for a star schema initially but may snowflake dimensions if they become very large and have highly redundant attributes.

## Proposed Core Dimensions

1. **`dim_date`:**
    * **Grain:** One row per day.
    * **Attributes:** `date_key` (surrogate key), `full_date`, `year`, `month`, `month_name`, `day_of_month`, `day_of_week_name`, `quarter`, `is_weekend`, etc.
    * **Purpose:** Allows slicing and dicing facts by various time attributes. Essential for time-series analysis.

2. **`dim_cryptocurrency`:**
    * **Grain:** One row per cryptocurrency being analyzed (BTC, ETH, DOGE).
    * **Attributes:** `crypto_key` (surrogate key), `symbol` (e.g., BTC), `full_name` (e.g., Bitcoin), `coin_gecko_id`, `blockchair_coin_name`, relevant project details.
    * **Source:** Primarily from `seeds/cryptocurrency_metadata.csv` and potentially enriched from API responses.
    * **Purpose:** Allows filtering and grouping facts by cryptocurrency.

3. **`dim_block` (Blockchain Specific):**
    * **Grain:** One row per unique block across all analyzed blockchains.
    * **Attributes:** `block_pk` (surrogate key), `block_id` (native ID), `block_hash`, `coin_symbol` (FK to `dim_cryptocurrency`), `block_timestamp_utc`, `block_date_key` (FK to `dim_date`), `transaction_count_in_block`, `block_size_bytes`, `difficulty`.
    * **Purpose:** Provides context for blockchain-related facts, such as transactions.

## Proposed Core Fact Tables

1. **`fct_transactions`:**
    * **Grain:** One row per blockchain transaction.
    * **Foreign Keys:** `transaction_date_key` (to `dim_date`), `crypto_key` (to `dim_cryptocurrency`), `block_pk` (to `dim_block`).
    * **Degenerate Dimensions:** `tx_hash` (transaction hash itself, acting as a descriptive attribute).
    * **Measures (Facts):** `fee_usd`, `output_total_usd`, `input_count`, `output_count`, `tx_size_bytes`, `is_coinbase_flag` (0 or 1).
    * **Purpose:** Central table for analyzing transaction activity, fees, and values.

2. **`fct_daily_market_summary`:**
    * **Grain:** One row per cryptocurrency per day.
    * **Foreign Keys:** `price_date_key` (to `dim_date`), `crypto_key` (to `dim_cryptocurrency`).
    * **Measures (Facts):** `price_usd`, `volume_usd`, `market_cap_usd`.
    * **Purpose:** Tracks daily market performance indicators for each cryptocurrency.

3. **`fct_daily_block_summary` (Potential):**
    * **Grain:** One row per cryptocurrency per day.
    * **Foreign Keys:** `summary_date_key` (to `dim_date`), `crypto_key` (to `dim_cryptocurrency`).
    * **Measures (Facts):** `total_blocks_mined_on_day`, `total_transactions_in_blocks_on_day`, `average_difficulty_on_day`, `total_fees_collected_on_day_usd`.
    * **Purpose:** Provides aggregated daily on-chain activity metrics. This might be derived by aggregating `dim_block` or `fct_transactions`.

## Benefits of this Model

* **Understandability:** Easier for business users and analysts to comprehend the data relationships.
* **Query Performance:** Optimized for common analytical queries (filtering, grouping, aggregation). Joins are typically between a fact table and a few dimension tables.
* **Ease of Use with BI Tools:** Power BI and similar tools are designed to work effectively with star/snowflake schemas.
* **Extensibility:** Relatively straightforward to add new facts or dimensions as business requirements evolve.

## Implementation in dbt

* Dimension tables are created as dbt models in `dbt_project/models/marts/core/dim_*.sql`.
* Fact tables are created as dbt models in `dbt_project/models/marts/core/fct_*.sql`.
* Surrogate keys for dimensions can be generated using `dbt_utils.generate_surrogate_key` or by using database sequences if preferred for `dim_` tables. Fact table primary keys can also be surrogate keys based on the combination of their degenerate dimensions and FKs.
* Relationships between fact and dimension tables are enforced and tested using dbt's `relationships` test.

```
