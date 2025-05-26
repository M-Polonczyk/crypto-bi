# Apache Airflow Orchestration

Apache Airflow is the backbone of this ELT pipeline, responsible for scheduling, executing, monitoring, and managing dependencies between all data processing tasks. This document outlines how Airflow is used in this project.

## Core Airflow Concepts Utilized

1. **DAGs (Directed Acyclic Graphs):**
    * The primary way workflows are defined in Airflow. Each DAG represents a sequence of tasks with defined dependencies.
    * Our main DAG (e.g., `crypto_data_ingestion_pipeline_vX.py` in the `dags/` folder) orchestrates the entire daily ELT process.
    * **Definition:** Written in Python.
    * **Scheduling:** Uses cron expressions or timedelta objects to define how often the DAG should run (e.g., daily at 1 AM UTC).

2. **Operators:**
    * Building blocks of DAGs; they define a single unit of work.
    * **`PythonOperator`:** Used to execute Python callable functions. This is how our custom ingestion scripts (`src/ingestion/*.py`) are invoked.
    * **`BashOperator`:** Used to execute shell commands. This is the primary way `dbt` commands (`dbt run`, `dbt test`, `dbt seed`, `dbt deps`) are executed.
    * **`PostgresOperator` (Potentially):** Could be used to execute specific SQL statements directly against PostgreSQL if needed, though most SQL transformations are handled by dbt.

3. **Tasks:**
    * An instantiated Operator within a DAG becomes a Task.
    * Tasks have upstream and downstream dependencies, defining the order of execution.

4. **Scheduler:**
    * The Airflow component that monitors all DAGs and Triggers Task Instances whose dependencies have been met and schedule has been reached.

5. **Webserver (UI):**
    * Provides a user interface for monitoring DAG runs, task statuses, logs, and managing Airflow configurations.
    * Accessible at `http://localhost:8080` in our Dockerized setup.

6. **Connections & Variables (Managed by Airflow):**
    * While our current setup primarily uses environment variables (passed via Docker Compose) for database credentials needed by dbt and Python scripts, Airflow has its own system for managing connections (e.g., to PostgreSQL) and variables. For more complex setups, these could be utilized.

## Main ELT DAG Structure (`crypto_data_ingestion_pipeline_vX.py`)

The primary DAG typically has the following structure and flow:

1. **DAG Definition:**
    * `dag_id`, `start_date`, `schedule_interval` (e.g., `'@daily'`), `catchup=False` (usually for production), default arguments (retries, email on failure, etc.).

2. **Task Definitions:**

    * **Start Task (Optional `DummyOperator`):** Marks the beginning of the DAG.

    * **Ingestion Tasks (Parallel):**
        * A `PythonOperator` task for CoinGecko data ingestion (e.g., `task_ingest_coingecko`).
            * Calls a Python function like `ingest_all_coingecko_data_callable()` which in turn calls the core logic in `src/ingestion/coingecko_ingestor.py`.
        * A `PythonOperator` task for Blockchair data ingestion (e.g., `task_ingest_blockchair`).
            * Calls a Python function like `ingest_all_blockchair_data_callable()` which then calls functions in `src/ingestion/blockchair_ingestor.py` for blocks and transactions.
        * These two main ingestion tasks can often run in parallel as they deal with different data sources.

    * **dbt Pre-Transformation Tasks (Sequential):**
        * `task_dbt_deps` (`BashOperator`): Executes `dbt deps --project-dir ...` to install any dbt package dependencies. This should run before any other dbt command if packages are used.
        * `task_dbt_seed` (`BashOperator`): Executes `dbt seed --project-dir ...` to load static data from CSV files in the `seeds/` directory.

    * **dbt Transformation Task:**
        * `task_dbt_run` (`BashOperator`): Executes `dbt run --project-dir ...` to materialize all dbt models (staging, intermediate, marts). This is the core transformation step.

    * **dbt Testing Task:**
        * `task_dbt_test` (`BashOperator`): Executes `dbt test --project-dir ...` to run all defined data quality tests on the transformed models.

    * **End Task (Optional `DummyOperator`):** Marks the successful completion of the DAG.

3. **Task Dependencies (Defining the Flow):**
    Using `>>` (set downstream) and `<<` (set upstream) operators or lists for parallel execution.

    ```python
    # Example Dependency Flow
    start_task = DummyOperator(task_id='start', dag=dag)
    end_task = DummyOperator(task_id='end', dag=dag)

    # Ingestion tasks can run in parallel
    ingestion_tasks = [task_ingest_coingecko, task_ingest_blockchair]

    start_task >> ingestion_tasks # Both ingestion tasks depend on start

    # dbt tasks run sequentially after ingestion
    # Ensure all ingestion tasks are complete before starting dbt sequence
    for task in ingestion_tasks:
        task >> task_dbt_deps 

    task_dbt_deps >> task_dbt_seed >> task_dbt_run >> task_dbt_test >> end_task
    ```

## Configuration and Environment

* **PYTHONPATH:** The Airflow workers/scheduler need access to the `src/` directory to import Python ingestion modules. The Docker setup mounts `src/` and the DAG file often includes logic to add the project root to `sys.path`.
* **DBT_PROJECT_DIR & DBT_PROFILES_DIR:** The `BashOperator` tasks executing `dbt` commands need to specify the `--project-dir` to point to the mounted `dbt_project/` directory. `DBT_PROFILES_DIR` (or the default `~/.dbt/`) must contain a `profiles.yml` configured to connect to the `postgres_app_db` service, using environment variables for credentials.
* **Environment Variables for dbt:** The `BashOperator` tasks for dbt pass necessary database connection environment variables (`DB_HOST`, `DB_USER_DBT`, `DB_PASSWORD_DBT`, etc.) which are then used by the `profiles.yml` `env_var()` function. These are sourced from the `.env` file by Docker Compose.

## Logging and Monitoring

* **Task Logs:** All `stdout` and `stderr` from Python scripts and dbt commands are captured by Airflow and accessible per task instance in the Airflow UI. This is crucial for debugging.
* **DAG Runs View:** Shows the status of all DAG runs (success, running, failed).
* **Graph View / Gantt Chart:** Visualize task dependencies and execution times.
* **Alerting (Optional):** Airflow can be configured to send email alerts on task failures or SLA misses (though not implemented in the basic setup).

## Idempotency

* **DAGs:** Airflow DAGs themselves are generally idempotent in terms of definition.
* **Tasks:**
  * Ingestion scripts aim for idempotency (e.g., `ON CONFLICT DO NOTHING` or `ON CONFLICT DO UPDATE`).
  * `dbt run` is generally idempotent for `view` and `table` materializations (it recreates or replaces them). For `incremental` models, dbt handles idempotency based on the incremental strategy and unique keys.
  * `dbt seed` can be made idempotent using flags like `--full-refresh` or by designing seeds to handle existing data.

By leveraging Airflow, the project achieves a robust, automated, and monitorable ELT pipeline.
