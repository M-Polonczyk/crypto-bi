-- Create application database
CREATE DATABASE app_db;

-- Create Airflow metadata database
CREATE DATABASE airflow_db;

-- Create users and grant privileges (optional)
CREATE USER IF NOT EXISTS app_user WITH ENCRYPTED PASSWORD 'app_pass';
CREATE USER IF NOT EXISTS airflow_user WITH ENCRYPTED PASSWORD 'airflow_pass';

GRANT ALL PRIVILEGES ON DATABASE app_db TO app_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
