import psycopg2
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "crypto_db"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password")
        )
        logging.info("Successfully connected to the database.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"Error connecting to PostgreSQL Database: {e}")
        raise

def execute_query(conn, query, params=None, fetch_one=False, fetch_all=False):
    """Executes a given SQL query."""
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            logging.info(f"Query executed successfully: {query[:100]}...") # Log snippet
            if fetch_one:
                return cur.fetchone()
            if fetch_all:
                return cur.fetchall()
    except psycopg2.Error as e:
        logging.error(f"Error executing query: {e}\nQuery: {query[:200]}...")
        conn.rollback() # Rollback in case of error
        raise

def execute_many(conn, query, data_list):
    """Executes a SQL query for many rows of data (e.g., INSERT)."""
    try:
        with conn.cursor() as cur:
            cur.executemany(query, data_list)
            conn.commit()
            logging.info(f"Batch query executed successfully for {len(data_list)} records.")
    except psycopg2.Error as e:
        logging.error(f"Error executing batch query: {e}\nQuery: {query[:200]}...")
        conn.rollback()
        raise