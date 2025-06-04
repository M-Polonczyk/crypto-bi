-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

GRANT ALL PRIVILEGES ON DATABASE app_db TO airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
