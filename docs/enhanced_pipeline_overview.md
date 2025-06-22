# Enhanced Cryptocurrency Data Pipeline

## Overview

This enhanced data pipeline uses **SQLAlchemy ORM** and **Pydantic models** to provide a robust, type-safe, and maintainable system for cryptocurrency data ingestion and management.

## Key Components

### 1. SQLAlchemy Models (`src/models.py`)

**Database Tables:**
- `BlockchainBlock` - Blockchain block data with indexes for performance
- `BlockchainTransaction` - Transaction data with relationships to blocks
- `BlockchainAddress` - Address/wallet data for tracking
- `MarketPrice` - Historical price, volume, and market cap data
- `DataIngestionLog` - Comprehensive logging of all ingestion operations
- `CoinMetadata` - Configuration and metadata for supported coins

**Features:**
- Composite primary keys for multi-coin support
- Proper relationships between tables
- Optimized indexes for common queries
- Automatic timestamps for audit trails
- Conflict resolution with ON CONFLICT DO UPDATE

### 2. Pydantic Schemas (`src/schemas.py`)

**Data Validation Models:**
- `BlockchainBlockData` - Validated block data with type checking
- `BlockchainTransactionData` - Transaction validation with decimal precision
- `BlockchainAddressData` - Address data with balance validation
- `MarketPriceData` - Price data with date validation
- `DataIngestionLogData` - Ingestion tracking with status enums
- Request/Response models for API operations

**Features:**
- Automatic type conversion and validation
- Custom validators for business rules
- JSON serialization with proper encoding
- Error handling with detailed validation messages

### 3. Database Service (`src/database.py`)

**High-Level Operations:**
- `insert_blocks()` - Batch insert/update blocks with conflict resolution
- `insert_transactions()` - Transaction batch processing
- `insert_addresses()` - Address data management
- `insert_market_prices()` - Price data with deduplication
- `get_database_stats()` - Comprehensive statistics and health metrics

**Features:**
- Connection pooling and automatic retry
- Context managers for session management
- Bulk operations for performance
- Comprehensive error handling and logging
- Health checks and monitoring

### 4. Enhanced Ingestors

**Blockchair Ingestor (`src/ingestion/blockchair_ingestor_sqlalchemy.py`):**
- Type-safe data processing with Pydantic validation
- Comprehensive error handling and recovery
- Detailed ingestion logging for monitoring
- Batch processing for API efficiency
- Support for blocks, transactions, and addresses

**CoinGecko Ingestor (`src/ingestion/coingecko_ingestor_sqlalchemy.py`):**
- Historical price data ingestion
- Backfill operations for missing data
- API rate limiting and error handling
- Multi-date processing capabilities

## Usage Examples

### Basic Daily Pipeline

```python
from src.database import db_service
from src.ingestion.blockchair_ingestor_sqlalchemy import blockchair_ingestor
from src.ingestion.coingecko_ingestor_sqlalchemy import coingecko_ingestor

# Initialize database
db_service.create_tables()

# Run daily ingestion
coin_symbols = ["bitcoin", "ethereum", "dogecoin"]
blockchair_results = blockchair_ingestor.run_daily_ingestion(coin_symbols)

coin_map = {"BTC": "bitcoin", "ETH": "ethereum", "DOGE": "dogecoin"}
coingecko_result = coingecko_ingestor.ingest_coingecko_data_for_date(coin_map)
```

### Data Queries

```python
# Get recent blocks
blocks = db_service.get_blocks(coin_symbol="BTC", limit=100)

# Get transactions for a specific block
transactions = db_service.get_transactions(block_id=850000, limit=1000)

# Get price history
from datetime import date, timedelta
yesterday = date.today() - timedelta(days=1)
prices = db_service.get_market_prices(
    coin_id="bitcoin", 
    start_date=yesterday,
    limit=30
)

# Get database statistics
stats = db_service.get_database_stats()
print(f"Total blocks: {stats.total_blocks}")
print(f"Latest blocks: {stats.latest_block_by_coin}")
```

### Monitoring and Logging

```python
# Get ingestion logs
logs = db_service.get_ingestion_logs(source="blockchair", limit=50)

# Check recent failures
failed_logs = db_service.get_ingestion_logs(
    status=IngestionStatus.FAILED, 
    limit=10
)
```

## Benefits of This Approach

### 1. **Type Safety**
- Pydantic models ensure data validation at runtime
- SQLAlchemy provides compile-time type checking
- Prevents data corruption and API integration issues

### 2. **Performance**
- Bulk insert operations with conflict resolution
- Optimized database indexes for common queries
- Connection pooling and session management
- Batch processing of API requests

### 3. **Reliability**
- Comprehensive error handling at every level
- Detailed logging for debugging and monitoring
- Automatic retry mechanisms and graceful degradation
- Data integrity constraints and validation

### 4. **Maintainability**
- Clean separation of concerns (models, services, ingestors)
- Consistent patterns across all components
- Easy to extend for new data sources or cryptocurrencies
- Comprehensive documentation and examples

### 5. **Monitoring**
- Built-in ingestion logging with status tracking
- Database health checks and statistics
- Performance metrics and error tracking
- Audit trails for all data modifications

## Integration with Airflow

The enhanced ingestors can be easily integrated into Airflow DAGs:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from src.ingestion.blockchair_ingestor_sqlalchemy import blockchair_ingestor

def run_blockchair_ingestion(**context):
    result = blockchair_ingestor.run_daily_ingestion(
        coin_symbols=["bitcoin", "ethereum", "dogecoin"]
    )
    return result

dag = DAG('crypto_ingestion', schedule_interval='@daily')

blockchair_task = PythonOperator(
    task_id='ingest_blockchair_data',
    python_callable=run_blockchair_ingestion,
    dag=dag
)
```

## Next Steps

1. **Extend coin support** by adding more entries to `CoinMetadata`
2. **Add API endpoints** using FastAPI for external access
3. **Implement data transformations** for analytics and reporting
4. **Add monitoring dashboards** using the built-in statistics
5. **Scale horizontally** with multiple worker processes
6. **Add data quality checks** and automated validation rules

This enhanced system provides a solid foundation for a production-ready cryptocurrency data pipeline with excellent maintainability, performance, and reliability characteristics.
