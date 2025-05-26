# dbt Marts Layer

The **marts layer** (also known as the presentation or reporting layer) is the final transformation layer in our dbt project. Its purpose is to produce data models that are optimized for end-user consumption, typically by BI tools like Power BI, or for direct analytical querying. These models represent the "single source of truth" for specific business areas or analytical use cases.

## Goals of the Marts Layer

1. **Business-Centric View:** Models are designed around business concepts and entities, making them intuitive for analysts and stakeholders.
2. **Performance Optimization:** Data is structured (often in a dimensional model) to ensure fast query performance for common analytical workloads (slicing, dicing, aggregation).
3. **Dimensional Modeling:** This layer typically implements dimensional models, most commonly star schemas or snowflake schemas.
    * **Fact Tables (`fct_`):** Contain quantitative measures (metrics) and foreign keys to dimension tables. They represent business processes or events.
    * **Dimension Tables (`dim_`):** Provide descriptive context to the facts (who, what, where, when, why).
4. **Aggregation (Optional but Common):** Sometimes, aggregated mart tables are created to pre-compute common summaries, further improving query speed for specific dashboards or reports.
5. **Single Source of Truth:** Marts provide a consistent and reliable dataset for specific analytical domains.

## Implementation in dbt

* Mart models are SQL files located in the `dbt_project/models/marts/` directory. They are often further organized into subdirectories based on business domain (e.g., `marts/core/`, `marts/finance/`, `marts/blockchain_activity/`).
* They primarily `SELECT` from staging models (`{{ ref('stg_model_name') }}`) or intermediate models (`{{ ref('int_model_name') }}`).
* Joins are common here, especially between staging/intermediate models to construct facts and dimensions.
* **Naming Convention:**
  * Dimension tables: `dim_<entity_name>.sql` (e.g., `dim_date.sql`, `dim_cryptocurrency.sql`).
  * Fact tables: `fct_<business_process_or_event>.sql` (e.g., `fct_transactions.sql`, `fct_daily_market_summary.sql`).

## Materialization

* Mart models, especially fact tables and frequently used dimension tables, are almost always materialized as **`tables`**.
  * **Pros:** Provides the best query performance for BI tools as the data is physically stored in the transformed structure.
  * **Cons:** Requires more storage space and dbt run times can be longer as data is physically written.
* Some very small or rarely changing dimension tables might occasionally be `views`, but `table` is the norm for marts.
* **Incremental Materialization:** For large fact tables, an incremental materialization strategy (`materialized='incremental'`) is often used. This allows dbt to only process and insert/update new or changed data since the last run, significantly speeding up dbt runs.

**Example `dbt_project.yml` configuration for marts:**

```yaml
models:
  crypto_analytics: # Your project name
    marts:
      +materialized: table # Default for all models in models/marts/
      +schema: analytics   # Output schema in PostgreSQL (or 'marts')
      # Example of configuring a sub-directory for incremental models
      # core:
      #   fct_transactions: # specific model
      #     +materialized: incremental
      #     +unique_key: 'transaction_pk' # if using unique key for updates
```

## Example Mart Models

### Dimension Table Example

**File:** `dbt_project/models/marts/core/dim_cryptocurrency.sql`

```sql
{{
    config(
        materialized='table'
    )
}}

-- Assuming you have a seed file for basic metadata
WITH crypto_seed AS (
    SELECT * FROM {{ ref('cryptocurrency_metadata_seed') }} -- Assuming seed name
),

-- You could potentially join with other sources if more attributes are available
-- For example, if an API provided a 'first_transaction_date' per coin from a staging model
-- enriched_coin_data AS ( ... )

SELECT
    -- Surrogate Key (if not using symbol directly as PK, which is also an option for small dims)
    {{ dbt_utils.generate_surrogate_key(['cs.symbol']) }} AS crypto_key,
    cs.symbol,
    cs.full_name,
    cs.project_website,
    -- Add other relevant attributes from seeds or enriched sources
    LOWER(cs.full_name) AS blockchair_coin_name, -- Example derived attribute for Blockchair API if needed
    LOWER(cs.full_name) AS coingecko_coin_id -- Assuming full name matches CoinGecko ID for simplicity
                                            -- In reality, this would be a proper mapping
FROM crypto_seed cs
-- LEFT JOIN enriched_coin_data ecd ON cs.symbol = ecd.symbol
```

*(Note: `cryptocurrency_metadata_seed` would be a CSV file in your `seeds/` directory loaded via `dbt seed`)*

### Fact Table Example

**File:** `dbt_project/models/marts/core/fct_daily_market_summary.sql`

```sql
{{
    config(
        materialized='table'
        // For incremental:
        // materialized='incremental',
        // unique_key=['price_date', 'crypto_key'] // Or a dedicated surrogate key
        // incremental_strategy='merge' // or 'delete+insert'
    )
}}

WITH stg_prices AS (
    SELECT * FROM {{ ref('stg_coingecko__prices_volumes') }}
),

dim_date AS (
    SELECT full_date, {{ dbt_utils.generate_surrogate_key(['full_date']) }} AS date_key -- Or your date SK logic
    FROM {{ ref('dim_date') }}
),

dim_crypto AS (
    SELECT symbol, crypto_key, coingecko_coin_id
    FROM {{ ref('dim_cryptocurrency') }}
)

SELECT
    -- Surrogate key for the fact table
    {{ dbt_utils.generate_surrogate_key(['sp.price_date', 'dc.crypto_key']) }} AS daily_market_summary_pk,

    -- Foreign Keys
    dd.date_key AS price_date_key,
    dc.crypto_key,

    -- Degenerate Dimensions (natural keys for context)
    sp.price_date,
    dc.symbol AS crypto_symbol,

    -- Measures
    sp.price_usd,
    sp.volume_usd,
    sp.market_cap_usd

FROM stg_prices sp
JOIN dim_date dd ON sp.price_date = dd.full_date
JOIN dim_crypto dc ON LOWER(sp.coin_id) = LOWER(dc.coingecko_coin_id) -- Robust join on CG ID

{% if is_incremental() %}
-- this filter will only be applied on an incremental run
WHERE sp.price_date > (SELECT MAX(price_date) FROM {{ this }})
{% endif %}
```

## Relationship to BI Tools

The tables created in the marts layer are the ones that Power BI (or any other BI tool) will connect to. The clear structure of facts and dimensions, well-defined relationships (enforced by dbt tests), and optimized performance make data analysis much more efficient and reliable.

```

---

**`docs/04_dbt_data_modeling/04_05_testing_and_quality.md`**

```markdown
# dbt Testing and Data Quality

Ensuring data quality is paramount for any analytics project. dbt provides a powerful and convenient framework for defining, executing, and managing data tests directly within your data transformation workflow. This helps build trust in the data and allows for early detection of issues.

## Why Test Your Data?

-   **Accuracy:** Verify that calculations are correct and data reflects reality.
-   **Completeness:** Ensure no critical data is missing.
-   **Consistency:** Check that data is consistent across different tables and models.
-   **Integrity:** Maintain referential integrity between related entities (e.g., foreign keys).
-   **Reliability:** Build confidence that the data powering dashboards and decisions is trustworthy.
-   **Early Detection:** Catch data issues early in the pipeline, before they impact downstream users or reports.

## Types of Tests in dbt

dbt supports several types of tests:

1.  **Schema Tests (Generic Tests):**
    *   These are predefined, out-of-the-box tests that can be applied to specific columns in your models.
    *   They are defined in `.yml` files, typically alongside your model definitions or in a dedicated `schema.yml` file within a model subdirectory.
    *   **Common Schema Tests:**
        *   `unique`: Asserts that all values in a column are unique.
        *   `not_null`: Asserts that there are no null values in a column.
        *   `accepted_values`: Asserts that all values in a column are within a specified list of allowed values.
            *   Example: `tests: - accepted_values: values: ['BTC', 'ETH', 'DOGE']`
        *   `relationships`: Asserts referential integrity. It checks that every value in a column (foreign key) exists in a corresponding column of another model (primary key).
            *   Example: `tests: - relationships: to: ref('dim_date') field: date_key`
    *   Many more generic tests are available through packages like `dbt-utils` (e.g., `equal_rowcount`, `expression_is_true`).

2.  **Singular Data Tests (Custom Tests):**
    *   These are custom SQL queries that you write to validate specific business logic or data conditions.
    *   They are stored as `.sql` files in the `tests/` directory of your dbt project (often in `tests/singular/` or `tests/asserts/`).
    *   **A singular data test PASSES if the SQL query returns ZERO rows.** If it returns one or more rows, the test FAILS, and those rows represent the records that violate the assertion.
    *   **Example:** A test to ensure that a transaction amount is always positive.
        ```sql
        -- tests/singular/assert_transaction_value_positive.sql
        SELECT
            transaction_pk, -- Or any relevant identifier
            transaction_amount_usd
        FROM {{ ref('fct_transactions') }}
        WHERE transaction_amount_usd < 0
        ```

3.  **Source Freshness (Specialized Test):**
    *   Defined in `sources.yml` to monitor the timeliness of your raw data loads.
    *   Requires a `loaded_at_field` in your source table that indicates when the data was last updated.
    *   You can configure `warn_after` and `error_after` thresholds.

## Implementation Strategy

1.  **Test at Every Layer:**
    *   **Sources:** Basic `not_null` on key identifiers, `unique` where expected, and `freshness` checks.
    *   **Staging Models:** `unique` and `not_null` on primary keys/business keys, `accepted_values` for categorical columns.
    *   **Mart Models (Dimensions):** `unique` and `not_null` on surrogate keys and natural keys.
    *   **Mart Models (Facts):** `not_null` on foreign keys and key measures. `relationships` tests to ensure all foreign keys correctly point to existing dimension records. Custom business logic tests (e.g., sum of debits equals sum of credits).

2.  **Define Tests in `.yml` Files:**
    For schema tests, co-locate them with your model definitions in `.yml` files. This keeps the model's contract (columns, descriptions, tests) in one place.

    **Example:** `models/marts/core/fct_transactions.yml`
    ```yaml
    version: 2

    models:
      - name: fct_transactions
        description: "Fact table containing individual blockchain transactions with their associated measures and dimensional foreign keys."
        columns:
          - name: transaction_pk # Assuming a surrogate key for the fact table
            description: "Surrogate primary key for the transaction fact."
            tests:
              - unique
              - not_null
          - name: tx_hash
            description: "The original transaction hash."
            tests:
              - not_null
          - name: price_date_key
            description: "Foreign key to dim_date, representing the date of the transaction."
            tests:
              - not_null
              - relationships:
                  to: ref('dim_date')
                  field: date_key # Assuming 'date_key' is the PK in dim_date
          - name: crypto_key
            description: "Foreign key to dim_cryptocurrency."
            tests:
              - not_null
              - relationships:
                  to: ref('dim_cryptocurrency')
                  field: crypto_key
          - name: fee_usd
            description: "Transaction fee in USD."
            tests:
              - dbt_utils.expression_is_true: # Using a test from dbt_utils package
                  expression: ">= 0" # Fee should not be negative
                  # This could also be a singular test for more complex logic
          # ... other columns and their tests
    ```

3.  **Leverage dbt Packages:**
    *   Install and use packages like `dbt-utils` which provide a rich set of additional generic tests (e.g., `dbt_utils.not_accepted_values`, `dbt_utils.equal_rowcount`, `dbt_utils.expression_is_true`).
    *   Add to `packages.yml`:
        ```yaml
        packages:
          - package: dbt-labs/dbt_utils
            version: [">=1.1.0", "<1.2.0"] # Specify version range
        ```
    *   Run `dbt deps` to install.

4.  **Write Custom SQL Tests for Business Logic:**
    If a validation cannot be expressed with a generic schema test, write a singular data test in the `tests/` directory.

## Running Tests

-   **Command:** `dbt test`
    *   `dbt test`: Runs all tests (schema and singular).
    *   `dbt test --select model_name`: Runs tests defined on a specific model.
    *   `dbt test --select source:source_name`: Runs tests on a specific source.
    *   `dbt test --select tag:my_tag`: Runs tests associated with a specific tag.
-   **Output:** dbt will report the status (PASS, FAIL, WARN, ERROR) of each test. For failing singular tests, it often shows the rows that failed the assertion.
-   **Integration with Airflow:** Include a `BashOperator` task in your Airflow DAGs to execute `dbt test` after `dbt run`. The DAG can be configured to fail if any dbt tests fail, preventing bad data from being used downstream.

    ```python
    # In Airflow DAG
    task_dbt_test = BashOperator(
        task_id='dbt_run_tests',
        bash_command=f"dbt test --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}",
        # ...
    )
    # task_dbt_run >> task_dbt_test
    ```

By consistently applying tests throughout your dbt project, you significantly improve the reliability and trustworthiness of your data warehouse, providing a solid foundation for your BI and analytics efforts.
