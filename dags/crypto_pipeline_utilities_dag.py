"""
Cryptocurrency Pipeline Utilities DAG

This DAG provides utility tasks for manual operations, testing, and maintenance
of the cryptocurrency data pipeline.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
import logging
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.settings import settings, get_active_coins, get_coin_symbol_mapping
from src.database import DatabaseService

logger = logging.getLogger(__name__)


def test_database_connection(**context):
    """Test database connectivity and display basic information."""
    try:
        db = DatabaseService(settings.database.url)
        logger.info("✓ Database connection successful")
        
        # Test table creation
        db.create_tables()
        logger.info("✓ Database tables verified")
        
        # Test a simple query
        with db.get_session() as session:
            result = session.execute(text("SELECT 1 as test")).fetchone()
            logger.info(f"✓ Database query test: {result}")
        
        return {"status": "success", "database": settings.database.database}
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        raise


def test_coingecko_api(**context):
    """Test CoinGecko API connectivity and sample data retrieval."""
    try:
        import requests
        
        # Simple API test without ingestor
        api_key = os.getenv("COINGECKO_API_KEY")
        if api_key:
            base_url = "https://pro-api.coingecko.com/api/v3"
            headers = {"x_cg_pro_api_key": api_key}
        else:
            base_url = "https://api.coingecko.com/api/v3"
            headers = {}
        
        # Test with a simple ping
        url = f"{base_url}/ping"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info("✓ CoinGecko API test successful")
        return {"status": "success", "api_url": base_url}
                
    except Exception as e:
        logger.error(f"✗ CoinGecko API test failed: {e}")
        raise


def test_blockchair_api(**context):
    """Test Blockchair API connectivity and sample data retrieval."""
    try:
        import requests
        
        # Test with Bitcoin stats (lightweight)
        url = "https://api.blockchair.com/bitcoin/stats"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data and 'data' in data:
            logger.info(f"✓ Blockchair API test successful. Bitcoin blocks: {data['data'].get('blocks', 'unknown')}")
            return {"status": "success", "stats": data['data']}
        else:
            raise ValueError("No stats retrieved from Blockchair API")
                
    except Exception as e:
        logger.error(f"✗ Blockchair API test failed: {e}")
        raise


def backfill_single_date(**context):
    """Backfill data for a specific date (useful for manual operations)."""
    # Get date from DAG run configuration or use yesterday
    dag_run = context.get('dag_run')
    if dag_run and dag_run.conf and 'target_date' in dag_run.conf:
        target_date_str = dag_run.conf['target_date']
        target_date = datetime.fromisoformat(target_date_str).date()
    else:
        # Default to yesterday
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    
    logger.info(f"Starting backfill for date: {target_date}")
    
    try:
        # This would normally use the actual ingestors
        # For now, just log the intent
        logger.info(f"Would backfill CoinGecko data for {target_date}")
        logger.info(f"Would backfill Blockchair data for {target_date}")
        
        # Test database connectivity during backfill
        db = DatabaseService(settings.database.url)
        db.create_tables()
        
        return {
            'target_date': target_date.isoformat(),
            'status': 'simulated',
            'message': 'Backfill simulation completed - real implementation would use ingestors'
        }
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise


def cleanup_test_data(**context):
    """Clean up test data and ingestion logs (use with caution)."""
    logger.warning("Starting cleanup of test data - this will remove ingestion logs!")
    
    try:
        db = DatabaseService(settings.database.url)
        
        with db.get_session() as session:
            # Only clean up logs from the last hour (safety measure)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            
            # This would normally clean up logs, but we need to check the actual table structure
            logger.info(f"Would clean up logs older than {cutoff_time}")
            logger.info("Cleanup simulation completed")
            
            return {'deleted_logs': 0, 'status': 'simulated'}
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


def display_settings(**context):
    """Display current pipeline settings for debugging."""
    logger.info("Current pipeline settings:")
    logger.info(f"Database URL: {settings.database.url[:30]}...")  # Don't log full URL
    logger.info(f"Database host: {settings.database.host}")
    logger.info(f"Database name: {settings.database.database}")
    logger.info(f"Default coins: {settings.ingestion.default_coins}")
    logger.info(f"Environment: {settings.environment}")
    
    active_coins = get_active_coins()
    coin_mapping = get_coin_symbol_mapping()
    
    logger.info(f"Active coins: {[coin['symbol'] for coin in active_coins]}")
    logger.info(f"CoinGecko mapping: {coin_mapping}")
    
    return {
        "database_host": settings.database.host,
        "database_name": settings.database.database,
        "default_coins": settings.ingestion.default_coins,
        "active_coins": [coin['symbol'] for coin in active_coins],
        "environment": settings.environment
    }


# Default arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the utilities DAG
with DAG(
    dag_id='crypto_pipeline_utilities',
    description='Utilities and manual operations for cryptocurrency data pipeline',
    schedule=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=3,  # Allow multiple utility runs
    tags=['crypto', 'utilities', 'testing', 'manual'],
    default_args=default_args,
    doc_md=__doc__,
    params={
        "target_date": "2024-01-01",  # Default parameter for backfill
    }
) as dag:
    
    # Display current settings
    settings_task = PythonOperator(
        task_id='display_settings',
        python_callable=display_settings,
    )
    
    # Test database connectivity
    test_db_task = PythonOperator(
        task_id='test_database',
        python_callable=test_database_connection,
    )
    
    # Test CoinGecko API
    test_coingecko_task = PythonOperator(
        task_id='test_coingecko_api',
        python_callable=test_coingecko_api,
    )
    
    # Test Blockchair API
    test_blockchair_task = PythonOperator(
        task_id='test_blockchair_api',
        python_callable=test_blockchair_api,
    )
    
    # Backfill single date
    backfill_task = PythonOperator(
        task_id='backfill_single_date',
        python_callable=backfill_single_date,
    )
    
    # Cleanup test data
    cleanup_task = PythonOperator(
        task_id='cleanup_test_data',
        python_callable=cleanup_test_data,
    )
    
    # System info
    system_info_task = BashOperator(
        task_id='system_info',
        bash_command="""
        echo "=== System Information ==="
        echo "Date: $(date)"
        echo "Python version: $(python3 --version)"
        echo "Disk space:"
        df -h /
        echo "Memory:"
        free -h
        echo "Environment variables:"
        env | grep -E "(POSTGRES|DATABASE|CRYPTO)" | sort
        """,
    )
    
    # Set up dependencies - most tasks can run independently
    settings_task >> [test_db_task, test_coingecko_task, test_blockchair_task]
    [test_db_task, test_coingecko_task, test_blockchair_task] >> system_info_task
