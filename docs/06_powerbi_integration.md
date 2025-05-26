# Power BI Integration Guide

This document provides guidance on connecting Microsoft Power BI Desktop to the PostgreSQL data warehouse populated by this ELT pipeline, and some best practices for building effective reports and dashboards.

## Connecting Power BI to PostgreSQL

The transformed data resides in the `postgres_app_db` service, specifically within the analytical schemas created by dbt (e.g., `analytics` or `marts`).

**Steps to Connect:**

1. **Ensure Services are Running:**
    * Verify that your Docker Compose services are up and running, especially the `postgres_app_db` container.
    * You can check with `docker ps`.

2. **Open Power BI Desktop.**

3. **Get Data:**
    * On the "Home" ribbon, click "Get Data".
    * Select "Database" from the categories on the left.
    * Choose "PostgreSQL database" from the list and click "Connect".

4. **PostgreSQL Database Connection Details:**
    * **Server:** `localhost`
        * *Explanation:* The `docker-compose.yaml` maps port `5432` of the `postgres_app_db` container to port `5432` on your host machine (`localhost`).
    * **Database:** Enter the name of your application database. This is defined by the `DB_NAME_APP` variable in your `.env` file (e.g., `crypto_raw_db`).
    * **Data Connectivity mode:**
        * **Import (Recommended for most scenarios):** Power BI imports a copy of the data into its internal VertiPaq engine. This generally provides the best performance for report interaction and allows for complex DAX calculations. Suitable for datasets that fit in memory.
        * **DirectQuery:** Power BI sends queries directly to the PostgreSQL database each time a visual is interacted with. Use this if your dataset is extremely large and cannot fit in memory, or if you need near real-time data (though our pipeline is batch-oriented). DirectQuery can be slower and has limitations on DAX functions.
    * *(Advanced options like SQL statement or command timeout are usually not needed for initial connection.)*

5. **Credentials:**
    * When prompted for credentials, select the "Database" tab on the left.
    * **User name:** Enter the database user defined by `DB_USER_APP` in your `.env` file.
    * **Password:** Enter the password defined by `DB_PASSWORD_APP` in your `.env` file.
    * **Encryption:** You can choose the level of encryption if your PostgreSQL server is configured for SSL (our basic Docker setup is not, but a production setup would be). For local development, "None" might be acceptable if connecting to `localhost`.
    * Click "Connect".

6. **Navigator Window:**
    * Once connected, the Navigator window will appear, showing all schemas and tables available in the specified database.
    * Expand the schema where your dbt marts reside (e.g., `analytics` or `marts`).
    * Select the fact tables (e.g., `fct_transactions`, `fct_daily_market_summary`) and dimension tables (e.g., `dim_date`, `dim_cryptocurrency`, `dim_block`) that you need for your analysis.
    * You can preview the data for each selected table.
    * Click "Load" (to import data directly) or "Transform Data" (to open the Power Query Editor for further shaping before loading). It's generally good practice to at least briefly review in Power Query Editor.

## Best Practices in Power BI

1. **Use the Marts Layer:**
    * Always connect to the tables in your dbt `marts` (or `analytics`) schema. These tables are cleaned, modeled, and optimized for reporting. Avoid connecting directly to raw or staging tables.

2. **Data Modeling in Power BI (if needed):**
    * **Relationships:** Power BI will attempt to auto-detect relationships based on column names. Verify these and create them manually if needed. Ensure relationships are correctly defined between fact tables and dimension tables using their respective primary and foreign keys (e.g., `dim_date.date_key` to `fct_transactions.transaction_date_key`).
    * **Cardinality:** Set the correct cardinality (one-to-many, many-to-one) and cross-filter direction for your relationships.
    * **Hide Foreign Keys:** In the "Model" view, hide foreign key columns in fact tables from the "Report" view to simplify the field list for end-users. They should use attributes from dimension tables for filtering and grouping.

3. **DAX for Measures:**
    * Create explicit measures using DAX (Data Analysis Expressions) for all calculations and aggregations (e.g., `Total Transaction Value = SUM(fct_transactions[output_total_usd])`).
    * Avoid using implicit measures (dragging numeric fields directly into visuals and relying on Power BI's default aggregation). Explicit measures offer more control and reusability.
    * Organize measures into dedicated tables or using display folders.

4. **Dimension Tables for Slicers and Filters:**
    * Use columns from your dimension tables (`dim_date`, `dim_cryptocurrency`, etc.) for slicers, filters, and as axes in your visuals.

5. **Optimize Performance:**
    * **Reduce Cardinality:** High cardinality columns (many unique values) can impact performance.
    * **Calculated Columns vs. Measures:** Prefer measures over calculated columns where possible, especially for aggregations. Calculated columns are computed row-by-row during data refresh and consume memory.
    * **Filter Early:** Apply filters in the Power Query Editor or at the report/page/visual level to reduce the amount of data processed.
    * **Use `STAR SCHEMA` principles:** This is inherently what dbt helps create.

6. **Report Design:**
    * Keep reports clean and uncluttered.
    * Use appropriate visuals for the type of data and analysis.
    * Provide clear titles and labels.
    * Consider user experience and navigation.

## Example Analysis Scenarios

Once connected, you can build visuals for:

* **Transaction Volume Over Time:** Line chart with `dim_date.full_date` on the axis and a measure for `COUNTROWS(fct_transactions)` or `SUM(fct_transactions[output_total_usd])` as values, sliced by `dim_cryptocurrency.symbol`.
* **Average Transaction Fee by Cryptocurrency:** Bar chart with `dim_cryptocurrency.symbol` on the axis and a measure for `AVERAGE(fct_transactions[fee_usd])` as values.
* **Price Trends:** Line chart with `dim_date.full_date` on the axis and `AVERAGE(fct_daily_market_summary[price_usd])` as values, sliced by `dim_cryptocurrency.symbol`.
* **Number of Blocks Mined Per Day:** Using `dim_block` joined with `dim_date`.

By following these guidelines, you can effectively leverage the data prepared by the ELT pipeline to gain valuable insights into cryptocurrency activity and market trends using Power BI.
