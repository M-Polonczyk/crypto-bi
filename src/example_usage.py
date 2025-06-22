"""
Example usage of the enhanced cryptocurrency data pipeline
with SQLAlchemy ORM and Pydantic models.
"""

import logging
from datetime import datetime, date, timedelta
from src.database import db_service
from src.ingestion.blockchair_ingestor_sqlalchemy import blockchair_ingestor
from src.ingestion.coingecko_ingestor_sqlalchemy import coingecko_ingestor
from src.schemas import CoinMetadataData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_coin_metadata():
    """Initialize coin metadata for supported cryptocurrencies."""
    coins = [
        CoinMetadataData(
            symbol="BTC",
            name="Bitcoin",
            coingecko_id="bitcoin",
            blockchair_id="bitcoin",
            is_active=True,
            ingestion_enabled=True
        ),
        CoinMetadataData(
            symbol="ETH", 
            name="Ethereum",
            coingecko_id="ethereum",
            blockchair_id="ethereum",
            is_active=True,
            ingestion_enabled=True
        ),
        CoinMetadataData(
            symbol="DOGE",
            name="Dogecoin", 
            coingecko_id="dogecoin",
            blockchair_id="dogecoin",
            is_active=True,
            ingestion_enabled=True
        )
    ]
    
    for coin in coins:
        coin_id = db_service.insert_coin_metadata(coin)
        logging.info(f"Setup coin metadata for {coin.symbol} (ID: {coin_id})")


def run_daily_pipeline():
    """Run the complete daily data ingestion pipeline."""
    logging.info("Starting daily cryptocurrency data pipeline")
    
    # 1. Setup database and metadata
    db_service.create_tables()
    setup_coin_metadata()
    
    # 2. Get active coins for ingestion
    active_coins = db_service.get_active_coins()
    coin_symbols = [coin.symbol.lower() for coin in active_coins]
    coin_map = {coin.symbol: coin.coingecko_id for coin in active_coins if coin.coingecko_id}
    
    logging.info(f"Active coins for ingestion: {coin_symbols}")
    
    # 3. Run Blockchair ingestion (blocks and transactions)
    try:
        logging.info("Starting Blockchair data ingestion...")
        blockchair_results = blockchair_ingestor.run_daily_ingestion(coin_symbols)
        
        for coin, result in blockchair_results.items():
            if "error" in result:
                logging.error(f"Blockchair ingestion failed for {coin}: {result['error']}")
            else:
                logging.info(f"Blockchair ingestion completed for {coin}")
                if "blocks" in result:
                    logging.info(f"  Blocks: {result['blocks']['result'] if result['blocks']['success'] else result['blocks']['error']}")
                if "transactions" in result:
                    logging.info(f"  Transactions: {result['transactions']['result'] if result['transactions']['success'] else result['transactions']['error']}")
                    
    except Exception as e:
        logging.error(f"Blockchair ingestion failed: {e}")
    
    # 4. Run CoinGecko ingestion (market prices)
    try:
        logging.info("Starting CoinGecko data ingestion...")
        coingecko_result = coingecko_ingestor.ingest_coingecko_data_for_date(coin_map)
        
        if coingecko_result["success"]:
            logging.info(f"CoinGecko ingestion completed: {coingecko_result['result']}")
        else:
            logging.error(f"CoinGecko ingestion failed: {coingecko_result['error']}")
            
    except Exception as e:
        logging.error(f"CoinGecko ingestion failed: {e}")
    
    # 5. Generate and log database statistics
    try:
        stats = db_service.get_database_stats()
        logging.info("=== Database Statistics ===")
        logging.info(f"Total blocks: {stats.total_blocks}")
        logging.info(f"Total transactions: {stats.total_transactions}")
        logging.info(f"Total addresses: {stats.total_addresses}")
        logging.info(f"Total price records: {stats.total_price_records}")
        logging.info(f"Latest blocks by coin: {stats.latest_block_by_coin}")
        logging.info(f"Latest prices by coin: {stats.latest_price_by_coin}")
        
    except Exception as e:
        logging.error(f"Failed to generate database stats: {e}")
    
    logging.info("Daily cryptocurrency data pipeline completed")


def run_backfill_example():
    """Example of running a backfill operation."""
    logging.info("Starting backfill example...")
    
    # Setup
    db_service.create_tables()
    setup_coin_metadata()
    
    # Get coin mapping
    active_coins = db_service.get_active_coins()
    coin_map = {coin.symbol: coin.coingecko_id for coin in active_coins if coin.coingecko_id}
    
    # Backfill last 7 days of price data
    try:
        result = coingecko_ingestor.backfill_missing_data(coin_map, days_back=7)
        logging.info(f"Backfill completed: {len(result)} dates processed")
        
        success_count = sum(1 for r in result.values() if r.get("success", False))
        logging.info(f"Successful ingestions: {success_count}/{len(result)}")
        
    except Exception as e:
        logging.error(f"Backfill failed: {e}")


def query_data_examples():
    """Examples of querying data using the database service."""
    logging.info("Running data query examples...")
    
    try:
        # Get recent blocks for Bitcoin
        btc_blocks = db_service.get_blocks(
            coin_symbol="BTC",
            limit=10
        )
        logging.info(f"Found {len(btc_blocks)} recent Bitcoin blocks")
        
        # Get recent transactions
        btc_transactions = db_service.get_transactions(
            coin_symbol="BTC",
            limit=10
        )
        logging.info(f"Found {len(btc_transactions)} recent Bitcoin transactions")
        
        # Get recent price data
        yesterday = date.today() - timedelta(days=1)
        recent_prices = db_service.get_market_prices(
            start_date=yesterday,
            limit=10
        )
        logging.info(f"Found {len(recent_prices)} recent price records")
        
        # Get ingestion logs
        recent_logs = db_service.get_ingestion_logs(limit=10)
        logging.info(f"Found {len(recent_logs)} recent ingestion logs")
        
    except Exception as e:
        logging.error(f"Query examples failed: {e}")


if __name__ == "__main__":
    # Run the complete pipeline
    run_daily_pipeline()
    
    # Example queries
    query_data_examples()
    
    # Uncomment to run backfill example
    # run_backfill_example()
