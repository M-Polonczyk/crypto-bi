# dbt Data Modeling

Data modeling in this project is handled by **dbt (Data Build Tool)**. dbt allows us to transform the raw data ingested into PostgreSQL into a clean, reliable, and analytics-ready dimensional model. All dbt files reside in the `dbt_project/` directory.

## Core Principles of dbt Usage Here

1. **ELT (Extract, Load, Transform):** We first load raw data into PostgreSQL, then use dbt to perform transformations *within* the database.
2. **Modularity:** Transformations are broken down into small, understandable SQL models.
3. **Version Control:** All dbt models (SQL files) are version controlled with Git, treating analytics code like software.
4. **Testing:** Data quality and integrity are enforced through dbt tests.
5. **Documentation:** dbt helps generate documentation for the data models.

## Directory Structure and Key Files

Refer to `dbt_project/README.md` or the main project `README.md` for a detailed breakdown of the `dbt_project/` directory structure. Key components include:

- **`dbt_project.yml`:** Main project configuration.
- **`profiles.yml`:** Database connection details (managed outside Git for security).
- **`models/`:** Contains all SQL transformation logic.
  - **`sources.yml`:** Defines and documents raw source tables.
  - **`staging/`:** Basic cleaning, renaming, and type casting of source data.
  - **`intermediate/` (Optional):** For complex, multi-step transformations.
  - **`marts/`:** Final, user-facing fact and dimension tables.
- **`seeds/`:** For static lookup data.
- **`tests/`:** Custom data quality tests (schema tests are often defined in model `.yml` files).
- **`macros/`:** Reusable SQL snippets.

## Data Modeling Layers

The transformation process is typically structured in layers:

1. **Sources (Defined in `models/**/sources.yml`):**
    - These aren't models themselves but declarations that point dbt to the raw tables created by the ingestion pipeline (e.g., `raw_blockchain_blocks`, `raw_market_prices_volumes` in the `public` schema).
    - Allows for basic testing (e.g., freshness, row counts) and documentation at the source level.
    - Referenced in staging models using `{{ source('source_name', 'table_name') }}`.
    - See: [Sources Documentation](./04_dbt_data_modeling/04_02_sources.md)

2. **Staging Layer (`models/staging/`):**
    - **Purpose:** To perform light transformations on each source table. This layer acts as a "cleaned" version of the raw data.
    - **Transformations:**
        - Renaming columns to consistent, business-friendly names (e.g., `block_time` to `block_timestamp_utc`).
        - Casting data types to appropriate SQL types (e.g., string timestamps to `TIMESTAMP`).
        - Basic calculations (e.g., extracting date parts from timestamps).
        - Filtering out test records or unnecessary data (if applicable).
    - **Materialization:** Often materialized as `view`s for faster development iterations and to avoid data duplication, but can be `table`s if performance is critical for downstream models.
    - **Naming Convention:** `stg_<source_system>__<object_name>` (e.g., `stg_blockchair__blocks`, `stg_coingecko__prices_volumes`).
    - Referenced by intermediate or mart models using `{{ ref('staging_model_name') }}`.
    - See: [Staging Layer Documentation](./04_dbt_data_modeling/04_03_staging_layer.md)

3. **Intermediate Layer (`models/intermediate/` - Optional):**
    - **Purpose:** To break down complex transformations that might involve joining multiple staging models or performing multi-step aggregations before building the final facts or dimensions.
    - **Use Cases:** Pre-aggregating data, complex joins, preparing data for multiple downstream marts.
    - **Materialization:** Can be `ephemeral` (CTE within downstream models), `view`, or `table`.
    - **Naming Convention:** `int_<description_of_transformation>`.

4. **Marts Layer (`models/marts/`):**
    - **Purpose:** To create the final, analytics-ready tables that Power BI users will query. This layer typically implements a dimensional model (star or snowflake schema).
    - **Dimension Tables (`dim_`):** Describe the "who, what, where, when, why" of the data.
        - Examples: `dim_date`, `dim_cryptocurrency`, `dim_block`.
        - Contain descriptive attributes and usually have a surrogate primary key.
    - **Fact Tables (`fct_`):** Contain measurable facts (metrics) and foreign keys that link to dimension tables.
        - Examples: `fct_transactions`, `fct_daily_market_summary`.
        - Granularity is key (e.g., one row per transaction, one row per coin per day).
    - **Materialization:** Almost always materialized as `table`s for optimal query performance by BI tools.
    - See: [Marts Layer Documentation](./04_dbt_data_modeling/04_04_marts_layer.md) and [Dimensional Model Documentation](./04_dbt_data_modeling/04_01_dimensional_model.md)

## Dimensional Model

The target data model for the marts layer is a **dimensional model** (likely a star schema for simplicity or a snowflake schema if dimensions become complex and normalized). This structure is optimized for analytical queries and BI tools.

- **Facts:** Quantitative measures (e.g., transaction value, number of blocks, trading volume).
- **Dimensions:** Qualitative context for the facts (e.g., date, cryptocurrency type, block details).

See [Dimensional Model Documentation](./04_dbt_data_modeling/04_01_dimensional_model.md) for more details.

## Testing and Data Quality

dbt provides a robust framework for testing data:

- **Schema Tests:** Defined in `.yml` files alongside model definitions. Common tests include:
  - `unique`: Ensures values in a column are unique.
  - `not_null`: Ensures a column does not contain null values.
  - `accepted_values`: Ensures column values are within a predefined set.
  - `relationships`: Tests referential integrity between tables (e.g., a foreign key in a fact table must exist in the corresponding dimension table).
- **Custom Data Tests (Singular Tests):** SQL queries written in the `tests/` directory that should return zero rows if the test passes. Used for more complex business logic validation.
- **`dbt test` command:** Executes all defined tests. Airflow DAGs should include a step to run `dbt test` after `dbt run`.

See [Testing and Quality Documentation](./04_dbt_data_modeling/04_05_testing_and_quality.md).

## Orchestration with Airflow

Airflow DAGs trigger dbt commands in the correct sequence:

1. `dbt deps` (if `packages.yml` is used, to install dependencies)
2. `dbt seed` (to load static data)
3. `dbt run` (to materialize all models)
4. `dbt test` (to validate data quality)

This ensures that transformations are executed only after new raw data is available and that data quality is checked before it's consumed by Power BI.
