-- models/marts/core/dim_date.sql
-- This is a simplified date dimension. Consider using dbt-date package for a comprehensive one.
{{ config(materialized='table') }}

SELECT
    datum AS full_date,
    EXTRACT(YEAR FROM datum) AS year,
    EXTRACT(MONTH FROM datum) AS month,
    TO_CHAR(datum, 'Month') AS month_name,
    EXTRACT(DAY FROM datum) AS day_of_month,
    EXTRACT(DOW FROM datum) AS day_of_week_number, -- 0 for Sunday in PostgreSQL
    TO_CHAR(datum, 'Day') AS day_of_week_name,
    EXTRACT(QUARTER FROM datum) AS quarter_of_year,
    EXTRACT(WEEK FROM datum) AS week_of_year,
    EXTRACT(DOY FROM datum) AS day_of_year
FROM generate_series(
    '2010-01-01'::date, -- Adjust start date as needed
    (current_date + interval '5 years'), -- Adjust end date as needed
    '1 day'::interval
) datum
ORDER BY datum