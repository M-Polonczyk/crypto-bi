# dbt Sources

In dbt, **sources** are a way to declare and document the raw data tables that your dbt project ingests from external systems. They are the starting point for your dbt transformations. In our project, these are the tables in PostgreSQL populated by the Python ingestion scripts.

## Purpose of Defining Sources

1. **Documentation:** Clearly document where your raw data comes from, its schema, and expected columns.
2. **Data Lineage:** `dbt docs generate` uses source definitions to build a lineage graph, showing how raw data flows into your final models.
3. **Testing at Source:** You can apply basic tests directly to source tables, such as:
    * **Freshness checks:** Ensure the data isn't stale.
    * **Row count checks:** Monitor if data loading is happening as expected.
    * Basic column-level tests (`not_null`, `unique` on expected keys).
4. **Abstraction:** Staging models can then reference these sources using the `{{ source('source_name', 'table_name') }}` macro, making it easy to change the underlying raw table name or schema in one place (`sources.yml`) if needed.

## Implementation

Source definitions are typically located in `.yml` files within your `dbt_project/models/` directory, often grouped logically (e.g., `models/staging/schema.yml`, or a dedicated `models/sources.yml`).

**File Example:** `dbt_project/models/sources.yml` (or could be `models/staging/sources.yml`)

```yaml
version: 2

sources:
  - name: raw_blockchair # A logical grouping for Blockchair data
    description: "Raw data ingested from the Blockchair API for various cryptocurrencies."
    # You can specify the database and schema if it's different from your target profile's default
    # database: your_raw_database 
    schema: public # The schema where ingestion scripts load Blockchair data (e.g., 'public' or 'raw_data')
    # loader: "Airflow Ingestion DAGs" # Optional metadata
    # loaded_at_field: "etl_loaded_at_timestamp" # If you have a load timestamp in raw tables for freshness

    tables:
      - name: raw_blockchain_blocks
        description: "Raw blocks data ingested from Blockchair API for BTC, ETH, DOGE."
        # freshness: # Example freshness check (requires loaded_at_field)
        #   warn_after: {count: 24, period: hour}
        #   error_after: {count: 48, period: hour}
        columns:
          - name: block_id
            description: "The unique ID (height) of the block."
            tests:
              - not_null
              # - unique # Block ID is unique per coin, so a composite unique test might be better
          - name: coin_symbol
            description: "Symbol of the cryptocurrency (BTC, ETH, DOGE)."
            tests:
              - not_null
          - name: block_hash
            description: "The unique hash of the block."
            tests:
              - unique # Block hash should be globally unique
              - not_null
          - name: block_time
            description: "Timestamp when the block was mined."
          # Add all other relevant columns from your raw_blockchain_blocks table

      - name: raw_blockchain_transactions
        description: "Raw transactions data from Blockchair API."
        columns:
          - name: tx_hash
            description: "The unique hash of the transaction."
            tests:
              - unique # Transaction hash should be globally unique
              - not_null
          - name: coin_symbol
            description: "Symbol of the cryptocurrency."
            tests:
              - not_null
          - name: block_id
            description: "ID of the block containing this transaction."
          # Add all other relevant columns

  - name: raw_coingecko # A logical grouping for CoinGecko data
    description: "Raw market data ingested from the CoinGecko API."
    schema: public # The schema where ingestion scripts load CoinGecko data
    tables:
      - name: raw_market_prices_volumes
        description: "Raw daily prices, volumes, and market caps from CoinGecko API."
        # loaded_at_field: "updated_at" # If CoinGecko provides an update timestamp
        # freshness:
        #   warn_after: {count: 2, period: day} # Expect daily updates
        columns:
          - name: coin_id
            description: "CoinGecko's unique identifier for the cryptocurrency."
            tests:
              - not_null
          - name: price_date
            description: "The date for which the market data is recorded."
            tests:
              - not_null
          - name: price_usd
            description: "Price in USD."
          - name: volume_usd
            description: "Trading volume in USD."
          - name: market_cap_usd
            description: "Market capitalization in USD."
          # Add composite unique test for coin_id and price_date
        tests:
          - unique:
              column_names: [coin_id, price_date]
```

## Key Configuration Options in `sources.yml`

* **`name` (for source block):** A unique name for the source system (e.g., `raw_blockchair`).
* **`schema`:** The schema in your database where these raw tables reside.
* **`database` (Optional):** If the source tables are in a different database than your dbt target database.
* **`tables`:** A list of tables belonging to this source.
  * **`name` (for table block):** The actual name of the table in your database.
  * **`description`:** Human-readable description of the table.
  * **`columns`:** A list of columns in the table.
    * **`name` (for column block):** The actual column name.
    * **`description`:** Human-readable description of the column.
    * **`tests`:** A list of schema tests to apply to this column (e.g., `unique`, `not_null`, `accepted_values`, `relationships`).
  * **`tests` (at table level):** A list of tests that apply to the whole table (e.g., a multi-column unique test).
  * **`freshness` (Optional):** Defines acceptable data latency. Requires a timestamp column in the source table (`loaded_at_field`) indicating when the data was last updated.
  * **`loaded_at_field` (Optional):** Specifies the column used for freshness checks.

## Referencing Sources in Models

In your staging models (e.g., `models/staging/stg_blockchair__blocks.sql`), you will refer to these source tables using the `source()` macro:

```sql
SELECT *
FROM {{ source('raw_blockchair', 'raw_blockchain_blocks') }}
```

This decouples your staging logic from the exact physical location of the raw data, making your dbt project more maintainable.

```

---

**`docs/04_dbt_data_modeling/04_03_staging_layer.md`**

```markdown
# dbt Staging Layer

The **staging layer** is the first transformation layer in our dbt project. Its primary purpose is to take the raw data ingested from external sources (as defined in `sources.yml`) and prepare it for more complex transformations and modeling in downstream layers (intermediate and marts).

## Goals of the Staging Layer

1.  **One-to-One Mapping (Generally):** Typically, there is one staging model for each source table.
2.  **Light Transformations:** Only basic, necessary transformations are performed here. Avoid complex business logic or joins between different source concepts in this layer.
3.  **Data Cleansing:**
    *   **Renaming Columns:** Rename columns to consistent, clear, and business-friendly names (e.g., `tx_time` to `transaction_timestamp_utc`).
    *   **Type Casting:** Convert columns to their correct data types (e.g., string representations of dates to `DATE` or `TIMESTAMP`, string numbers to `NUMERIC` or `INTEGER`).
    *   **Basic Formatting:** Apply minimal formatting if necessary (e.g., trimming whitespace, standardizing case for certain string fields – though this can also be done later).
4.  **Deriving Basic Attributes:** Create simple derived columns if universally useful (e.g., extracting the date part from a timestamp: `DATE(transaction_timestamp_utc) AS transaction_date`).
5.  **Filtering (Minimal):** Remove records that are unequivocally irrelevant for any downstream analysis (e.g., test records from a source system, completely malformed rows if not handled during ingestion). However, be cautious with filtering at this stage; it's often better to filter in downstream models where the business context is clearer.
6.  **No Joins Between Different Source Entities:** Staging models should focus on a single source table. Joins to bring together different concepts (e.g., transactions with block details from a separate blocks table, if they were separate sources) happen in intermediate or mart layers.

## Implementation in dbt

-   Staging models are SQL files located in the `dbt_project/models/staging/` directory.
-   They typically use Common Table Expressions (CTEs) for readability, often starting with a CTE that selects from a `{{ source(...) }}`.
-   **Naming Convention:** `stg_<source_name>__<object_name>.sql` (e.g., `stg_blockchair__blocks.sql`, `stg_coingecko__prices_volumes.sql`). The double underscore `__` is a common convention to separate the source system from the object.

## Materialization

-   Staging models are often materialized as **`views`** in the database.
    -   **Pros:** No additional storage used (queries are executed against underlying raw tables on-the-fly), always reflect the latest raw data, faster dbt runs during development as no data is physically moved.
    -   **Cons:** Can be slower to query if the underlying raw tables are very large or if the view definition involves many calculations.
-   Alternatively, they can be materialized as **`tables`** if:
    -   Downstream models frequently query them, and performance is critical.
    *   You want to "snapshot" a version of the cleaned data.
-   The default materialization for the staging layer can be set in `dbt_project.yml`.

**Example `dbt_project.yml` configuration for staging:**
```yaml
models:
  crypto_analytics: # Your project name
    staging:
      +materialized: view # Default for all models in models/staging/
      +schema: staging    # Output schema in PostgreSQL
```

## Example Staging Model

**File:** `dbt_project/models/staging/blockchain/stg_blockchair__transactions.sql`

```sql
-- This CTE selects from the raw source table defined in sources.yml
WITH source_data AS (
    SELECT *
    FROM {{ source('raw_blockchair', 'raw_blockchain_transactions') }}
)

-- This CTE performs the light transformations
SELECT
    -- Identifiers & Keys
    tx_hash,                                 -- Already a good name
    coin_symbol,                             -- Already a good name
    block_id,                                -- Already a good name

    -- Timestamps & Dates (Casting and Renaming)
    tx_time::TIMESTAMP AS transaction_timestamp_utc, -- Casting to TIMESTAMP
    DATE(tx_time) AS transaction_date,               -- Deriving date part

    -- Monetary Values (Casting to NUMERIC if they are strings in raw)
    fee_usd::NUMERIC AS fee_usd,
    output_total_usd::NUMERIC AS output_total_usd,

    -- Counts
    input_count::INTEGER AS input_count,
    output_count::INTEGER AS output_count,

    -- Other Attributes
    size_bytes::INTEGER AS transaction_size_bytes,  -- Renaming and casting
    is_coinbase::BOOLEAN AS is_coinbase_transaction -- Casting if it's not already boolean

    -- Columns to exclude (if any) can be omitted from the SELECT list
    -- e.g., raw_api_response_column_we_dont_need

FROM source_data
-- Add WHERE clause for incremental processing if this model becomes incremental
-- e.g., WHERE tx_time >= (SELECT MAX(transaction_timestamp_utc) FROM {{ this }}) -- For incremental tables
```

## Benefits of a Staging Layer

* **DRY (Don't Repeat Yourself):** Common cleaning logic is centralized, so you don't have to repeat it in multiple downstream models.
* **Clarity and Readability:** Downstream models (`intermediate` and `marts`) can then build upon this cleaned and consistently named data, making their logic simpler.
* **Debugging:** Easier to trace data issues back to their source. If a problem exists in a mart table, you can check the staging layer, and then the raw source.
* **Improved Lineage:** Provides a clear step in the data lineage graph.
* **Performance (Potentially):** If staging models are materialized as tables, they can pre-compute some transformations, speeding up downstream queries.

The staging layer is a foundational part of a robust dbt project, ensuring that all subsequent transformations start from a common, clean baseline.

```
