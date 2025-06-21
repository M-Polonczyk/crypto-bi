import psycopg2
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST_APP", "localhost"),
            port=os.getenv("DB_PORT_APP", "5432"),
            dbname=os.getenv("DB_NAME_APP", "app_db"),
            user=os.getenv("DB_USER_APP", "airflow_user"),
            password=os.getenv("DB_PASSWORD_APP", "airflow_pass")
        )
        logging.info("Successfully connected to the database.")
        return conn
    except psycopg2.Error as e:
        logging.error("Error connecting to PostgreSQL Database: %s", e)
        raise

def execute_query(conn, query, params=None, fetch_one=False, fetch_all=False):
    """Executes a given SQL query."""
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            logging.info("Query executed successfully: %s...", query[:100])
            if fetch_one:
                return cur.fetchone()
            if fetch_all:
                return cur.fetchall()
    except psycopg2.Error as e:
        logging.error("Error executing query: %s\nQuery: %s...", e, query[:200])
        conn.rollback()
        raise

def execute_many(conn, query, data_list):
    """Executes a SQL query for many rows of data (e.g., INSERT)."""
    try:
        with conn.cursor() as cur:
            cur.executemany(query, data_list)
            conn.commit()
            logging.info("Batch query executed successfully for %s records.", len(data_list))
    except psycopg2.Error as e:
        logging.error("Error executing batch query: %s\nQuery: %s...", e, query[:200])
        conn.rollback()
        raise