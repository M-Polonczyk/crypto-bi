# Development Guide

This guide provides instructions and best practices for developers contributing to the Crypto Analytics BI project.

## Local Development Setup

Refer to the main `README.md` for detailed instructions on setting up the Dockerized environment using `docker-compose`. Key aspects include:

- Cloning the repository.
- Creating and configuring the `.env` file.
- Ensuring Docker Desktop (or Docker Engine + Compose) is running.
- Building the Docker images (`docker-compose build`).
- Starting the services (`docker-compose up -d`).
- Initializing Airflow (database and user creation) on the first run.

## Working with Apache Airflow DAGs

- **Location:** DAG files are located in the `./dags/` directory, which is mounted into the Airflow scheduler and webserver containers.
- **Creating/Modifying DAGs:**
  - Edit Python files in the `./dags/` directory on your host machine.
  - Airflow's scheduler will automatically pick up changes to DAG files (usually within a few minutes, configurable in `airflow.cfg`).
  - New DAGs will appear in the Airflow UI.
- **Testing DAGs:**
  - **Airflow UI:** Trigger DAGs manually, clear task states, and inspect logs.
  - **Airflow CLI:** You can `exec` into the `airflow-scheduler` or `airflow-webserver` container and use the Airflow CLI for more advanced testing (e.g., `airflow dags test <dag_id> <execution_date>`).
- **PYTHONPATH:** The `src/` directory is mounted into Airflow containers and added to `PYTHONPATH` (often done in the DAG file itself or via Dockerfile configuration) so that DAGs can import custom Python modules from `src.ingestion` or `src.common`.

## Working with Python Ingestion Scripts

- **Location:** Ingestion logic resides in `./src/ingestion/`. Common utilities are in `./src/common/`.
- **Development:**
  - You can develop and test these scripts locally on your host machine if you have Python and the necessary libraries (`requests`, `psycopg2-binary`) installed, and can connect to the Dockerized PostgreSQL (`postgres_app_db` on `localhost:5432`).
  - Alternatively, make changes and test by triggering the corresponding Airflow tasks, then inspecting logs via the Airflow UI.
- **Dependencies:** Python dependencies for Airflow (and thus for the environment where ingestion scripts run within Docker) are managed in `docker/airflow/requirements_airflow.txt`. If you add new dependencies for your ingestion scripts, update this file and rebuild the Airflow Docker image (`docker-compose build airflow-scheduler`).

## Working with dbt

- **Location:** The dbt project is in `./dbt_project/`. This directory is mounted into the Airflow containers.
- **dbt `profiles.yml`:**
  - For Airflow to run `dbt` commands, it needs a `profiles.yml` that can connect to the `postgres_app_db` service.
  - The recommended approach is to use environment variables within `profiles.yml` (e.g., `host: "{{ env_var('DB_HOST') }}"`). These environment variables (`DB_HOST`, `DB_USER_DBT`, etc.) are passed from the project's root `.env` file to the Airflow containers via `docker-compose.yaml`.
  - If running dbt commands locally on your host machine (outside Docker, but connecting to the Dockerized DB), your local `~/.dbt/profiles.yml` should point to `host: localhost`, `port: 5432`, and use the `DB_USER_APP`, `DB_PASSWORD_APP`, `DB_NAME_APP` credentials from the root `.env` file.
- **Running dbt Commands:**
  - **Via Airflow:** Airflow DAGs use `BashOperator` to execute `dbt` commands. This is the standard way transformations are run in the orchestrated pipeline.

        ```bash
        # Example command in Airflow DAG's BashOperator
        dbt run --project-dir /opt/airflow/dbt_project_for_airflow --profiles-dir /opt/airflow/dbt_project_for_airflow 
        # (if profiles.yml is also mounted there, or relies purely on env_vars)
        ```

  - **Manually within Docker:**
        1. `docker exec -it <airflow_container_name_or_id> bash`
        2. `cd /opt/airflow/dbt_project_for_airflow`
        3. `dbt run --select my_model`
  - **Locally on Host (if dbt installed):**
        1. Ensure your local `~/.dbt/profiles.yml` is configured for `localhost:5432`.
        2. `cd dbt_project/`
        3. `dbt run --select my_model`
- **Developing dbt Models:**
  - Edit SQL files in `./dbt_project/models/`.
  - Follow dbt best practices: use staging layers, create modular models, write tests, and document your models in `.yml` files.
  - Run `dbt compile` to see the compiled SQL.
  - Run `dbt run` and `dbt test` frequently during development.
- **dbt Dependencies:** If you add packages to `dbt_project/packages.yml`, run `dbt deps` (locally or via an Airflow task) to install them. The `target/` and `dbt_packages/` directories are gitignored.

## Coding Standards and Conventions

- **Python:** Follow PEP 8 guidelines. Use a linter like Flake8 or Black for code formatting.
- **SQL (dbt):**
  - Use consistent formatting (e.g., [SQLFluff](https://sqlfluff.com/) can be integrated with dbt).
  - Use CTEs for readability in complex models.
  - Clearly name models, columns, and CTEs.
  - Comment your code where necessary.
- **Airflow DAGs:**
  - Use clear task names.
  - Define explicit dependencies.
  - Keep DAG definitions concise; move complex Python logic into separate modules in `src/`.
- **Commit Messages:** Follow conventional commit message formats (e.g., `feat: add new transaction fact model`, `fix: correct coingecko api date formatting`).

## Branching Strategy (Example)

- `main` (or `master`): Represents the stable, production-ready state.
- `develop`: Integration branch for features.
- Feature branches: `feature/<ticket_id>-<short-description>` (e.g., `feature/CRYPTO-123-add-doge-market-data`).
- Bugfix branches: `fix/<ticket_id>-<short-description>`.
- Pull Requests (PRs) should be used to merge feature/fix branches into `develop`, and `develop` into `main`. PRs should be reviewed.

## Environment Variables

- All sensitive credentials (API keys, database passwords) and environment-specific configurations should be managed via the root `.env` file and accessed as environment variables within the Docker containers.
- **DO NOT commit the `.env` file to Git.** A `.env.example` file should be provided.

## Updating Dependencies

- **Python (Airflow/Ingestion):** Update versions in `docker/airflow/requirements_airflow.txt`, then rebuild the Docker image: `docker-compose build airflow-scheduler` (or relevant service).
- **dbt Packages:** Update versions in `dbt_project/packages.yml`, then run `dbt deps` (either locally, within the container, or via an Airflow task).

This guide provides a starting point for development. Adapt and expand it as your team and project grow.
