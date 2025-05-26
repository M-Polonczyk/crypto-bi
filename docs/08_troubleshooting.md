# Troubleshooting Guide

This guide provides solutions and debugging tips for common issues encountered while working with the Crypto Analytics BI project.

## Docker Compose Issues

1. **Services Fail to Start / `docker-compose up` Errors:**
    * **Check Docker Desktop/Engine:** Ensure Docker is running and has sufficient resources (CPU, memory, disk space) allocated.
    * **Port Conflicts:** If a port defined in `docker-compose.yaml` (e.g., `8080` for Airflow, `5432` for PostgreSQL) is already in use on your host machine, the service will fail to start.
        * **Solution:** Stop the conflicting service on your host or change the host-side port mapping in `docker-compose.yaml` (e.g., `ports: - "8081:8080"`).
    * **Volume Mount Issues:**
        * Ensure the local directories you are mounting as volumes (e.g., `./dags`, `./dbt_project`) exist and have correct permissions.
        * On Windows, file path issues with Docker Desktop can sometimes occur. Ensure paths are correctly specified.
    * **Insufficient Disk Space:** Docker images, volumes, and logs can consume significant disk space. Clean up unused Docker resources: `docker system prune -a --volumes`.
    * **`.env` File Missing or Incorrect:** Ensure the `.env` file exists in the project root and contains all necessary variables with correct values.
    * **Inspect Logs:** Use `docker-compose logs <service_name>` (e.g., `docker-compose logs airflow-scheduler`) to see detailed error messages from a specific service.

2. **Permission Denied Errors for Mounted Volumes (Especially for Airflow Logs/DAGs):**
    * This often happens because the user inside the Docker container (e.g., `airflow` user with UID 50000) doesn't have write permissions to the directory mounted from the host.
    * **Solution 1 (Recommended in `docker-compose.yaml`):** Set the `user: "${AIRFLOW_UID:-50000}:0"` (or your host user's UID/GID) for Airflow services in `docker-compose.yaml`. You might need to create an `AIRFLOW_UID` variable in your `.env` file with your host user's UID (`id -u` on Linux/macOS).
    * **Solution 2 (Host-side):** Change permissions on the host directories (e.g., `chmod -R 777 ./logs ./dags`), but this is less secure.

## Apache Airflow Issues

1. **DAGs Not Appearing in UI / Not Scheduling:**
    * **Syntax Errors in DAG File:** Check Airflow scheduler logs (`docker-compose logs airflow-scheduler`) for Python import errors or syntax errors in your DAG file. The UI might also show a "Broken DAG" error.
    * **`dags_folder` Configuration:** Ensure the `dags_folder` in `airflow.cfg` (or the volume mount in `docker-compose.yaml`) correctly points to your `dags/` directory.
    * **Scheduler Not Running:** Verify the `airflow-scheduler` container is running (`docker ps`).
    * **`start_date` in the Future:** If a DAG's `start_date` is in the future, it won't be scheduled until that date is reached (unless `catchup=True` and the schedule has passed).
    * **`schedule_interval` is `None` or `@once`:** Such DAGs only run when manually triggered (or once if `catchup=True` for a past `start_date`).

2. **Tasks Failing:**
    * **Inspect Task Logs:** The most crucial step. In the Airflow UI, go to the DAG run, click on the failed task instance, and then "Log". This will show `stdout` and `stderr` from the task's execution.
    * **PYTHONPATH Issues:** If `PythonOperator` tasks fail with `ModuleNotFoundError`, ensure the `src/` directory (or other custom module locations) is correctly added to `PYTHONPATH` for the Airflow workers/scheduler. This is often handled by mounting `src/` and adding to `sys.path` in the DAG file or via Dockerfile.
    * **Environment Variables Missing:** If scripts rely on environment variables (e.g., API keys, database credentials), ensure they are correctly passed to the Airflow execution environment (via `.env` and `docker-compose.yaml`).
    * **Database Connection Errors (from Python scripts):** Verify credentials, host (`postgres_app_db`), port (`5432`), and database name. Ensure the `postgres_app_db` service is healthy.
    * **Rate Limits:** If ingesting from APIs, tasks might fail due to hitting rate limits. Implement delays or more robust retry mechanisms.

3. **Airflow Webserver/Scheduler Fails to Connect to Metadata Database (`postgres_airflow_meta`):**
    * Check logs of `airflow-webserver` and `airflow-scheduler`.
    * Verify the `SQL_ALCHEMY_CONN` string in the Airflow environment configuration (set in `docker-compose.yaml`) is correct and that `postgres_airflow_meta` service is healthy and its credentials match.

## dbt Issues

1. **`dbt run` or `dbt test` Fails (when run by Airflow or manually):**
    * **Connection Errors (Profile Issues):**
        * Ensure `profiles.yml` is correctly configured to connect to `postgres_app_db` (host should be the service name `postgres_app_db` when running inside Docker, or `localhost` if running dbt locally and connecting to the exposed Docker port).
        * Verify database credentials (`DB_USER_DBT`, `DB_PASSWORD_DBT`, `DB_NAME` etc.) are correct and available as environment variables if `profiles.yml` uses `env_var()`.
        * Test the connection using `dbt debug --project-dir ... --profiles-dir ...`.
    * **SQL Errors in Models:** The dbt output will usually show the failing SQL model and the database error message. Copy the compiled SQL (from `target/compiled/`) and run it directly against PostgreSQL using a SQL client for easier debugging.
    * **Model Not Found (`{{ ref('model_name') }}` or `{{ source(...) }}` errors):**
        * Check for typos in model names or source definitions.
        * Ensure the referenced model/source exists and dbt can find it (check paths in `dbt_project.yml`).
        * Run `dbt compile` to see if dbt can resolve references.
    * **Permission Issues in Database:** The dbt database user (`DB_USER_DBT`) must have appropriate permissions (SELECT on source tables/schemas, CREATE/INSERT/SELECT/DROP on target schemas like `staging`, `analytics`).
    * **Test Failures (`dbt test`):** dbt output will indicate which tests failed and often provide sample failing rows. Investigate the data in the relevant tables to understand why the assertion failed.

2. **`dbt deps` Fails:**
    * Check `packages.yml` for correct package names and versions.
    * Ensure you have internet connectivity if fetching packages from dbt Hub.

## PostgreSQL Issues

1. **Cannot Connect to Database (from host SQL client or Power BI):**
    * Ensure the `postgres_app_db` container is running (`docker ps`).
    * Verify the port mapping in `docker-compose.yaml` (e.g., `5432:5432`). You should connect to `localhost:5432` from your host.
    * Check credentials (`DB_USER_APP`, `DB_PASSWORD_APP`, `DB_NAME_APP` from `.env`).
    * Check PostgreSQL logs within the container: `docker logs <postgres_app_db_container_name>`.

2. **Permission Denied in PostgreSQL:**
    * The user connecting to the database (e.g., `DB_USER_APP` for Power BI, `DB_USER_DBT` for dbt) needs appropriate privileges on the schemas and tables they need to access.
    * You might need to `GRANT USAGE ON SCHEMA <schema_name> TO <user_name>;` and `GRANT SELECT ON ALL TABLES IN SCHEMA <schema_name> TO <user_name>;` etc.

## General Debugging Steps

1. **Isolate the Problem:** Try to determine which component is failing (Docker, Airflow, dbt, PostgreSQL, Python script).
2. **Check Logs:** This is almost always the first and most important step.
    * `docker-compose logs <service_name>`
    * Airflow Task Logs (via UI)
    * dbt command line output (and `logs/dbt.log` in your `dbt_project` or the `target` directory if configured)
3. **Simplify:** If a complex DAG or dbt model fails, try running a simpler version or individual parts to pinpoint the error.
4. **Consult Documentation:** Refer to the official documentation for Airflow, dbt, PostgreSQL, and the APIs you are using.
5. **Google the Error Message:** Often, someone else has encountered a similar issue.

Remember to be specific when asking for help (e.g., on Stack Overflow or team channels), providing:
* The exact error message.
* Relevant code snippets.
* Steps to reproduce the issue.
* Your environment details (OS, Docker version, tool versions).
