#!/usr/bin/env python3
"""
Test script for the SQLAlchemy-based cryptocurrency data pipeline.

This script validates that all components work together correctly,
including database connectivity, API access, and data ingestion.
"""

import sys
import os
from datetime import datetime, timezone, timedelta
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.settings import CryptoSettings
from database import DatabaseService
from ingestion.blockchair_ingestor_sqlalchemy import BlockchairIngestor
from ingestion.coingecko_ingestor_sqlalchemy import CoinGeckoIngestor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_settings():
    """Test settings configuration."""
    logger.info("Testing settings configuration...")
    
    try:
        settings = CryptoSettings()
        logger.info(f"✓ Settings loaded successfully")
        logger.info(f"  - Database URL: {settings.database_url[:20]}...")
        logger.info(f"  - Blockchains: {settings.blockchains}")
        logger.info(f"  - CoinGecko coins: {list(settings.coingecko_coins.keys())}")
        logger.info(f"  - Batch size: {settings.batch_size}")
        return settings
    except Exception as e:
        logger.error(f"✗ Settings test failed: {e}")
        raise


def test_database_connectivity(settings):
    """Test database connectivity and table creation."""
    logger.info("Testing database connectivity...")
    
    try:
        with DatabaseService(settings.database_url) as db:
            logger.info("✓ Database connection successful")
            
            # Create tables
            db.create_tables()
            logger.info("✓ Database tables created/verified")
            
            # Get stats
            stats = db.get_ingestion_stats()
            logger.info(f"✓ Current database stats: {stats}")
            
            return db
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        raise


def test_coingecko_integration(settings):
    """Test CoinGecko API integration."""
    logger.info("Testing CoinGecko integration...")
    
    try:
        with DatabaseService(settings.database_url) as db:
            ingestor = CoinGeckoIngestor(db, settings)
            
            # Test metadata ingestion (small dataset)
            logger.info("Testing coin metadata ingestion...")
            metadata_results = ingestor.ingest_coin_metadata()
            logger.info(f"✓ Metadata ingestion: {metadata_results}")
            
            # Test price ingestion for yesterday
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            logger.info(f"Testing price ingestion for {yesterday}...")
            price_results = ingestor.ingest_market_prices(yesterday)
            logger.info(f"✓ Price ingestion: {price_results}")
            
            return True
    except Exception as e:
        logger.error(f"✗ CoinGecko test failed: {e}")
        return False


def test_blockchair_integration(settings):
    """Test Blockchair API integration."""
    logger.info("Testing Blockchair integration...")
    
    try:
        with DatabaseService(settings.database_url) as db:
            ingestor = BlockchairIngestor(db, settings)
            
            # Test with Bitcoin only (most reliable)
            test_blockchain = "bitcoin"
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            
            logger.info(f"Testing {test_blockchain} blocks ingestion for {yesterday}...")
            block_results = ingestor.ingest_recent_blocks(test_blockchain, yesterday, limit=5)
            logger.info(f"✓ Blocks ingestion: {block_results}")
            
            # Only test transactions if blocks were successful
            if block_results.get('inserted', 0) > 0 or block_results.get('updated', 0) > 0:
                logger.info(f"Testing {test_blockchain} transactions ingestion...")
                tx_results = ingestor.ingest_transactions_for_date(test_blockchain, yesterday, limit=10)
                logger.info(f"✓ Transactions ingestion: {tx_results}")
            
            return True
    except Exception as e:
        logger.error(f"✗ Blockchair test failed: {e}")
        return False


def test_dag_functions():
    """Test the functions that would be called by Airflow DAGs."""
    logger.info("Testing DAG integration functions...")
    
    try:
        settings = CryptoSettings()
        
        # Simulate DAG context
        execution_date = datetime.now(timezone.utc) - timedelta(days=1)
        context = {
            'execution_date': execution_date,
            'dag_run': None
        }
        
        # Test database initialization (like the DAG task)
        logger.info("Testing database initialization task...")
        with DatabaseService(settings.database_url) as db:
            db.create_tables()
            stats = db.get_ingestion_stats()
            logger.info(f"✓ Database initialization: {stats}")
        
        # Test CoinGecko task simulation
        logger.info("Testing CoinGecko ingestion task...")
        target_date = execution_date.date()
        
        with DatabaseService(settings.database_url) as db:
            ingestor = CoinGeckoIngestor(db, settings)
            
            # Simulate the DAG task logic
            metadata_results = ingestor.ingest_coin_metadata()
            price_results = ingestor.ingest_market_prices(target_date)
            
            task_result = {
                'metadata_results': metadata_results,
                'price_results': price_results,
                'execution_date': target_date.isoformat()
            }
            logger.info(f"✓ CoinGecko task simulation: {task_result}")
        
        logger.info("✓ DAG integration tests completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ DAG integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("="*60)
    logger.info("Starting SQLAlchemy Cryptocurrency Pipeline Tests")
    logger.info("="*60)
    
    try:
        # Test 1: Settings
        settings = test_settings()
        logger.info("")
        
        # Test 2: Database
        test_database_connectivity(settings)
        logger.info("")
        
        # Test 3: CoinGecko (optional - may fail due to rate limits)
        logger.info("Testing CoinGecko integration (optional)...")
        coingecko_success = test_coingecko_integration(settings)
        logger.info("")
        
        # Test 4: Blockchair (optional - may fail due to rate limits)
        logger.info("Testing Blockchair integration (optional)...")
        blockchair_success = test_blockchair_integration(settings)
        logger.info("")
        
        # Test 5: DAG functions
        dag_success = test_dag_functions()
        logger.info("")
        
        # Summary
        logger.info("="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info("✓ Settings configuration: PASSED")
        logger.info("✓ Database connectivity: PASSED")
        logger.info(f"{'✓' if coingecko_success else '⚠'} CoinGecko integration: {'PASSED' if coingecko_success else 'SKIPPED/FAILED'}")
        logger.info(f"{'✓' if blockchair_success else '⚠'} Blockchair integration: {'PASSED' if blockchair_success else 'SKIPPED/FAILED'}")
        logger.info(f"{'✓' if dag_success else '✗'} DAG integration: {'PASSED' if dag_success else 'FAILED'}")
        
        if dag_success:
            logger.info("")
            logger.info("🎉 Pipeline is ready for Airflow deployment!")
            logger.info("   You can now use the DAGs in the dags/ directory:")
            logger.info("   - crypto_pipeline_sqlalchemy_dag.py (main pipeline)")
            logger.info("   - crypto_pipeline_utilities_dag.py (utilities)")
        else:
            logger.error("❌ Pipeline has issues that need to be resolved")
            return 1
            
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
