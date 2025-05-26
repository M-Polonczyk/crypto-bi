# Crypto Analytics BI Project (On-Premise ELT Pipeline)

This project implements an on-premise Extract, Load, Transform (ELT) pipeline for analyzing cryptocurrency market data and blockchain activity. It leverages Apache Airflow for orchestration, dbt for data transformation, PostgreSQL as the data warehouse, and is designed to feed data into Power BI for visualization and business intelligence.

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Initializing Airflow (First Time)](#initializing-airflow-first-time)
- [Data Pipeline Workflow](#data-pipeline-workflow)
- [dbt Project](#dbt-project)
- [Connecting Power BI](#connecting-power-bi)
- [Development](#development)
  - [Running dbt Commands Manually](#running-dbt-commands-manually)
  - [Accessing Services](#accessing-services)
- [Further Documentation](#further-documentation)
- [Contributing](#contributing)
- [License](#license)

## Project Overview

The goal of this project is to:

1. **Ingest** raw data from cryptocurrency APIs (Blockchair for blockchain data, CoinGecko for market prices/volumes).
2. **Load** this raw data into a PostgreSQL database.
3. **Transform** the raw data into a clean, structured dimensional model suitable for analytics using dbt.
4. **Orchestrate** the entire pipeline using Apache Airflow.
5. Enable **analysis and visualization** using Power BI connected to the transformed data in PostgreSQL.

The primary cryptocurrencies targeted for analysis are Bitcoin (BTC), Ethereum (ETH), and Dogecoin (DOGE).

## Tech Stack

- **Orchestration:** Apache Airflow
- **Data Transformation:** dbt (Data Build Tool) with `dbt-postgres`
- **Data Warehouse:** PostgreSQL
- **Data Ingestion:** Python (`requests`, `psycopg2`)
- **Containerization:** Docker & Docker Compose
- **Business Intelligence:** Power BI Desktop (connecting to PostgreSQL)
- **Version Control:** Git

## Project Structure

```
.
├── dags/                  # Airflow DAG definitions
├── dbt_project/           # dbt models, tests, seeds, etc.
├── docker/                # Docker related files (e.g., custom Airflow Dockerfile)
│   └── airflow/
│       ├── Dockerfile
│       └── requirements_airflow.txt
├── docs/                  # Project documentation
├── logs/                  # (Mounted by Docker) Airflow & application logs
├── plugins/               # (Mounted by Docker) Airflow plugins (if any)
├── src/                   # Python source code for data ingestion
│   ├── ingestion/
│   └── common/
├── .env                   # Environment variables for Docker Compose (GITIGNORED)
├── .gitignore
├── docker-compose.yaml    # Docker Compose configuration
├── README.md              # This file
└── ... (other project files)
```

For detailed information on the `dbt_project` structure, refer to `dbt_project/README.md` (you should create this or link to dbt docs).

## Setup and Installation

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose) installed and running.
- Git installed.
- A text editor or IDE (e.g., VS Code).
- (Optional, for local Python dev outside Docker) Python 3.8+ and pip.

### Environment Configuration

1. **Clone the repository:**

    ```bash
    git clone <your-repository-url>
    cd <your-project-directory>
    ```

2. **Create the `.env` file:**
    Copy the provided `.env.example` (if you have one) to `.env` or create it manually in the project root. This file contains crucial credentials and configurations for Docker Compose.

    ```bash
    cp .env.example .env # If you have an example
    # --- OR ---
    # Create .env and populate with values like:
    # POSTGRES_USER=airflow_user
    # POSTGRES_PASSWORD=airflow_pass
    # ... (refer to the docker-compose section in previous responses for full list)
    ```

    **Important:** Ensure the database credentials in `.env` (especially `DB_USER_APP`, `DB_PASSWORD_APP`, `DB_NAME_APP`) are consistent with what your dbt `profiles.yml` expects (when configured to use environment variables).

3. **dbt `profiles.yml`:**
    Your dbt `profiles.yml` (typically located at `~/.dbt/profiles.yml` or specified by the `DBT_PROFILES_DIR` environment variable) needs to be configured to connect to the `postgres_app_db` service defined in `docker-compose.yaml`.
    The Airflow Docker image is configured to look for dbt profiles using environment variables passed from the `.env` file (e.g., `DB_HOST=postgres_app_db`). If you mount a `profiles.yml` into the Airflow container, ensure its `host` setting points to `postgres_app_db`.

    Example snippet for `profiles.yml` using environment variables:

    ```yaml
    # In your ~/.dbt/profiles.yml or the one mounted to Airflow
    crypto_analytics_onprem:
      target: dev
      outputs:
        dev:
          type: postgres
          host: "{{ env_var('DB_HOST') }}"       # Will be 'postgres_app_db' inside Docker
          port: "{{ env_var('DB_PORT', 5432) | int }}"
          user: "{{ env_var('DB_USER_DBT') }}"
          pass: "{{ env_var('DB_PASSWORD_DBT') }}"
          dbname: "{{ env_var('DB_NAME') }}"
          schema: "{{ env_var('DBT_DEFAULT_SCHEMA', 'public') }}" # Or your target schema for dbt
          threads: 4
    ```

### Running with Docker Compose

1. **Build the custom Airflow image (if changes were made to `docker/airflow/Dockerfile` or `requirements_airflow.txt`):**

    ```bash
    docker-compose build
    ```

2. **Start all services in detached mode:**

    ```bash
    docker-compose up -d
    ```

    This will start:
    - `postgres_airflow_meta`: PostgreSQL database for Airflow metadata.
    - `postgres_app_db`: PostgreSQL database for your application data (dbt target).
    - `airflow-scheduler`: Airflow scheduler.
    - `airflow-webserver`: Airflow web UI.

### Initializing Airflow (First Time)

After the containers are up and running for the first time, you need to initialize the Airflow database and create an admin user.

1. **Initialize the Airflow metadata database:**

    ```bash
    docker-compose run --rm airflow-webserver airflow db init
    ```

    *(If you see errors about migrations, try `airflow db migrate` first, then `airflow db init` if it's an older setup)*

2. **Create an Airflow admin user:**

    ```bash
    docker-compose run --rm airflow-webserver airflow users create \
        --username admin \
        --firstname YourFirstName \
        --lastname YourLastName \
        --role Admin \
        --email admin@example.com \
        --password yoursecurepassword
    ```

    *(Replace placeholders with your desired credentials)*

    Alternatively, check the `.env` file for `_AIRFLOW_WWW_USER_USERNAME` and `_AIRFLOW_WWW_USER_PASSWORD` if your Airflow image's entrypoint script handles user creation automatically (the provided `apache/airflow` base image usually requires manual creation or a custom entrypoint).

## Data Pipeline Workflow

1. **Ingestion (Airflow DAGs):**
    - Python scripts located in `src/ingestion/` are triggered by Airflow DAGs (defined in `dags/`).
    - These scripts fetch data from Blockchair and CoinGecko APIs.
    - Raw data is loaded into staging tables in the `postgres_app_db` (e.g., into the `public` schema or a dedicated `raw_data` schema).
2. **Transformation (dbt orchestrated by Airflow):**
    - An Airflow DAG triggers dbt commands (`dbt deps`, `dbt seed`, `dbt run`, `dbt test`).
    - dbt reads from the raw/staging tables and materializes transformed models (dimensions and facts) into analytical schemas (e.g., `analytics`, `marts`) within `postgres_app_db`.
    - The dbt models are defined in `dbt_project/models/`.
3. **Scheduling:**
    - Airflow DAGs are scheduled to run periodically (e.g., daily) to keep the data warehouse updated.

## dbt Project

The `dbt_project/` directory contains all dbt-related files:

- `dbt_project.yml`: Main project configuration.
- `profiles.yml` (Configuration): Defines database connection profiles. **Managed outside this project's Git history for security, typically `~/.dbt/profiles.yml` or via environment variables.**
- `models/`: SQL and YAML files defining data sources, staging models, intermediate transformations, and final mart tables (facts and dimensions).
- `seeds/`: CSV files for static lookup data.
- `tests/`: Custom data quality tests.
- `macros/`: Reusable SQL snippets.

Refer to the dbt documentation and files within `dbt_project/` for more details.

## Connecting Power BI

1. Ensure the Docker Compose services are running, especially `postgres_app_db`.
2. Open Power BI Desktop.
3. Click "Get Data" -> "Database" -> "PostgreSQL database".
4. **Server:** `localhost` (since port 5432 of `postgres_app_db` is mapped to `localhost:5432`).
5. **Database:** The name of your application database (e.g., `crypto_raw_db` or as defined by `DB_NAME_APP` in your `.env`).
6. **Credentials:** Use the database user and password defined for `DB_USER_APP` and `DB_PASSWORD_APP` in your `.env` file.
7. Connect and select the tables/views from your dbt mart schemas (e.g., `analytics.fct_transactions`, `analytics.dim_date`).

## Development

### Running dbt Commands Manually

You can execute dbt commands directly within the running Airflow worker/scheduler container (as it has dbt installed) or set up a local Python virtual environment with `dbt-postgres` pointing to the Dockerized PostgreSQL.

**Inside the Airflow container:**

1. Find the container ID: `docker ps` (look for `airflow-scheduler` or `airflow-webserver`).
2. Exec into the container:

    ```bash
    docker exec -it <airflow_container_id_or_name> bash
    ```

3. Navigate to the mounted dbt project:

    ```bash
    cd /opt/airflow/dbt_project_for_airflow
    ```

4. Run dbt commands (ensure `DBT_PROFILES_DIR` is set correctly if your `profiles.yml` is not in the default dbt location within the container, or that the environment variables used by `profiles.yml` are available):

    ```bash
    # Example:
    # Assuming profiles.yml is configured to use env_vars set in docker-compose
    dbt run --select staging.stg_blockchair_blocks
    dbt test
    ```

### Accessing Services

- **Airflow Web UI:** `http://localhost:8080`
- **PostgreSQL (App DB):** `localhost:5432` (Connect with any SQL client like pgAdmin, DBeaver, or psql). User/Pass/DB from `.env` (`DB_USER_APP`, etc.).
- **PostgreSQL (Airflow Meta DB):** `localhost:5433`. User/Pass/DB from `.env` (`POSTGRES_USER`, etc.). Generally, you won't need to interact with this directly.

## Further Documentation

- **[Project Specific Docs](./docs/index.md):** More detailed documentation on data models, pipeline specifics, and design decisions.
- **[dbt Documentation](https://docs.getdbt.com/)**
- **[Apache Airflow Documentation](https://airflow.apache.org/docs/)**
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/)**
- **[Power BI Documentation](https://docs.microsoft.com/en-us/power-bi/)**

## Contributing

Please refer to `CONTRIBUTING.md` for guidelines (if you create one).

## License

Specify your project's license here (e.g., MIT, Apache 2.0, or proprietary).

```

---

## `docs/` Directory Structure and Content Ideas

This directory is for more in-depth documentation that doesn't fit neatly into the main `README.md`. You can use Markdown files and potentially a static site generator like MkDocs, Docsify, or Sphinx if the documentation becomes extensive.

**Proposed Structure:**

```

docs/
├── index.md                     # Landing page for documentation (can be a copy of README or a summary)
├── 01_architecture.md           # Overview of the system architecture
├── 02_data_sources.md           # Details about APIs used, data points extracted
├── 03_ingestion_pipeline.md     # Deep dive into the Airflow ingestion DAGs and Python scripts
├── 04_dbt_data_modeling.md      #
│   ├── 04_01_dimensional_model.md # Explanation of the star/snowflake schema
│   ├── 04_02_sources.md           # Details on dbt sources
│   ├── 04_03_staging_layer.md     # Purpose and examples of staging models
│   ├── 04_04_marts_layer.md       # Details on fact and dimension tables
│   └── 04_05_testing_and_quality.md # dbt testing strategy
├── 05_airflow_orchestration.md  # Specifics on DAG design, scheduling, monitoring
├── 06_powerbi_integration.md    # Tips for connecting Power BI, common DAX patterns
├── 07_development_guide.md      # How to contribute, coding standards, local setup variations
├── 08_troubleshooting.md        # Common issues and solutions
└── images/                      # For diagrams and screenshots
    └── architecture_diagram.png

```

**Example Content for `docs/index.md`:**

```markdown
# Project Documentation: Crypto Analytics BI

Welcome to the detailed documentation for the Crypto Analytics BI On-Premise ELT Pipeline.

This documentation provides in-depth information about the project's architecture, data pipeline, data modeling strategy, and development guidelines.

## Navigation

-   **[Architecture Overview](./01_architecture.md):** Understand the overall system design and component interactions.
-   **[Data Sources](./02_data_sources.md):** Learn about the external APIs used and the data they provide.
-   **[Ingestion Pipeline](./03_ingestion_pipeline.md):** Details on how data is extracted and loaded into PostgreSQL using Airflow.
-   **[dbt Data Modeling](./04_dbt_data_modeling.md):** Explore how raw data is transformed into an analytical model.
    -   [Dimensional Model](./04_dbt_data_modeling/04_01_dimensional_model.md)
    -   [Sources](./04_dbt_data_modeling/04_02_sources.md)
    -   [Staging Layer](./04_dbt_data_modeling/04_03_staging_layer.md)
    -   [Marts Layer](./04_dbt_data_modeling/04_04_marts_layer.md)
    -   [Testing and Quality](./04_dbt_data_modeling/04_05_testing_and_quality.md)
-   **[Airflow Orchestration](./05_airflow_orchestration.md):** Specifics of DAG design and pipeline scheduling.
-   **[Power BI Integration](./06_powerbi_integration.md):** Guidelines for connecting and visualizing data.
-   **[Development Guide](./07_development_guide.md):** Information for developers contributing to the project.
-   **[Troubleshooting](./08_troubleshooting.md):** Solutions for common problems.

## Getting Started

If you haven't already, please review the main [Project README.md](../README.md) for setup and installation instructions.
```

**Content for `docs/01_architecture.md` (High-Level):**

```markdown
# System Architecture

This project implements an on-premise Extract, Load, Transform (ELT) pipeline. The major components and data flow are as follows:

1.  **External Data Sources:**
    *   **Blockchair API:** Provides blockchain data (blocks, transactions) for Bitcoin, Ethereum, and Dogecoin.
    *   **CoinGecko API:** Provides market data (prices, volumes, market caps).

2.  **Data Ingestion (Python Scripts):**
    *   Python scripts located in the `src/ingestion/` directory are responsible for making API calls to Blockchair and CoinGecko.
    *   These scripts handle basic parsing and formatting of the API responses.

3.  **Apache Airflow (Orchestration):**
    *   Airflow DAGs (Direct Acyclic Graphs) define the workflow, dependencies, and scheduling of tasks.
    *   **Ingestion Tasks:** Airflow triggers the Python ingestion scripts.
    *   **Loading Tasks:** Ingested data is loaded into "raw" or "staging" tables in the PostgreSQL Application Database.
    *   **Transformation Tasks:** Airflow triggers `dbt` commands (`dbt run`, `dbt test`, etc.) to perform data transformations.

4.  **PostgreSQL (Data Warehouse):**
    *   **`postgres_airflow_meta`:** A dedicated PostgreSQL instance (or database) to store Airflow's operational metadata.
    *   **`postgres_app_db`:** The primary PostgreSQL instance (or database) serving as the data warehouse.
        *   **Raw/Staging Schemas (e.g., `public`, `raw_data`):** Stores data directly ingested from APIs before transformation.
        *   **Analytical Schemas (e.g., `staging`, `analytics`, `marts`):** Stores tables and views created by dbt transformations, forming the dimensional model.

5.  **dbt (Data Build Tool):**
    *   Manages all SQL-based data transformations.
    *   Reads from raw/staging tables in `postgres_app_db`.
    *   Materializes cleaned, transformed, and modeled data (facts and dimensions) back into analytical schemas in `postgres_app_db`.
    *   Handles data quality testing.

6.  **Power BI Desktop (Business Intelligence & Visualization):**
    *   Connects directly to the analytical schemas (e.g., `analytics.fct_transactions`) in the `postgres_app_db`.
    *   Allows users to create reports, dashboards, and perform ad-hoc analysis.

## Data Flow Diagram

```mermaid
graph LR
    A[External APIs <br>(Blockchair, CoinGecko)] --> B(Python Ingestion Scripts <br> in src/ingestion);
    C(Apache Airflow <br> DAGs in dags/) -- Manages --> B;
    B -- Loads Raw Data --> D_RAW[PostgreSQL App DB <br> (Raw/Staging Schemas)];
    C -- Triggers dbt --> E(dbt Transformation <br> Models in dbt_project/);
    E -- Reads From --> D_RAW;
    E -- Writes Transformed Data --> D_ANALYTICS[PostgreSQL App DB <br> (Analytical Schemas: staging, marts)];
    D_ANALYTICS --> F(Power BI Desktop <br> Reports & Dashboards);
    C -- Uses --> G[PostgreSQL Airflow Meta DB];

    subgraph "Dockerized Environment"
        direction LR
        C
        D_RAW
        D_ANALYTICS
        E
        G
    end
```

*(You can generate an actual image from this Mermaid syntax if your Markdown renderer supports it, or create a PNG/SVG and link it from `docs/images/`)*

## Containerization (Docker Compose)

All core backend services (Airflow, PostgreSQL) are containerized using Docker Compose for ease of setup, portability, and consistent development environments. Refer to `docker-compose.yaml` for the service definitions.
