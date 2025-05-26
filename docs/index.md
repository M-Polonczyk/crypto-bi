# Project Documentation: Crypto Analytics BI

Welcome to the detailed documentation for the Crypto Analytics BI On-Premise ELT Pipeline.

This documentation provides in-depth information about the project's architecture, data pipeline, data modeling strategy, and development guidelines.

## Navigation

- **[Architecture Overview](./01_architecture.md):** Understand the overall system design and component interactions.
- **[Data Sources](./02_data_sources.md):** Learn about the external APIs used and the data they provide.
- **[Ingestion Pipeline](./03_ingestion_pipeline.md):** Details on how data is extracted and loaded into PostgreSQL using Airflow.
- **[dbt Data Modeling](./04_dbt_data_modeling/index.md):** Explore how raw data is transformed into an analytical model.
  - [Dimensional Model](./04_dbt_data_modeling/04_01_dimensional_model.md)
  - [Sources](./04_dbt_data_modeling/04_02_sources.md)
  - [Staging Layer](./04_dbt_data_modeling/04_03_staging_layer.md)
  - [Marts Layer](./04_dbt_data_modeling/04_04_marts_layer.md)
  - [Testing and Quality](./04_dbt_data_modeling/04_05_testing_and_quality.md)
- **[Airflow Orchestration](./05_airflow_orchestration.md):** Specifics of DAG design and pipeline scheduling.
- **[Power BI Integration](./06_powerbi_integration.md):** Guidelines for connecting and visualizing data.
- **[Development Guide](./07_development_guide.md):** Information for developers contributing to the project.
- **[Troubleshooting](./08_troubleshooting.md):** Solutions for common problems.

## Getting Started

If you haven't already, please review the main [Project README.md](../README.md) for setup and installation instructions.
