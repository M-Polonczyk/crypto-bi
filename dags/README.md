# Cryptocurrency Data Pipeline - Airflow DAGs

This directory contains Airflow DAGs for the enhanced cryptocurrency data pipeline using SQLAlchemy and Pydantic.

## DAGs Overview

### 1. `crypto_pipeline_sqlalchemy_dag.py` (Main Pipeline)
The primary production DAG that runs daily to ingest cryptocurrency data from multiple sources.

**Schedule**: Daily at 1 AM UTC (`0 1 * * *`)

**Tasks**:
1. **initialize_database** - Verify database connectivity and create tables
2. **ingest_coingecko_data** - Ingest market data from CoinGecko API
3. **ingest_blockchair_data** - Ingest blockchain data from Blockchair API
4. **generate_report** - Create ingestion summary report
5. **cleanup_old_logs** - Remove old ingestion logs (30+ days)
6. **system_health_check** - Monitor system resources

**Features**:
- Timezone-aware UTC timestamps
- Comprehensive error handling and logging
- Batch processing for performance
- Pydantic validation for data integrity
- SQLAlchemy ORM for type-safe database operations

### 2. `crypto_pipeline_utilities_dag.py` (Utilities)
Manual utility DAG for testing, debugging, and maintenance operations.

**Schedule**: Manual trigger only

**Tasks**:
- **display_settings** - Show current pipeline configuration
- **test_database** - Test database connectivity
- **test_coingecko_api** - Test CoinGecko API access
- **test_blockchair_api** - Test Blockchair API access
- **backfill_single_date** - Backfill data for specific date
- **cleanup_test_data** - Clean up test data
- **system_info** - Display system information

## Configuration

The DAGs use the `CryptoSettings` class for configuration, which supports environment variables:

```bash
# Database configuration
DATABASE_URL=postgresql://user:pass@localhost/dbname

# API rate limits (requests per minute)
COINGECKO_RATE_LIMIT=50
BLOCKCHAIR_RATE_LIMIT=1440

# Processing configuration
BATCH_SIZE=1000
```

## Data Sources

### CoinGecko API
- **Coin metadata**: Names, symbols, descriptions
- **Market prices**: Daily OHLCV data
- **Rate limit**: 50 requests/minute (demo tier)

### Blockchair API
- **Blocks**: Block headers and metadata
- **Transactions**: Transaction details and amounts
- **Addresses**: Address statistics and balances
- **Rate limit**: 1440 requests/minute (free tier)

## Database Schema

The pipeline uses SQLAlchemy ORM models:

- **blocks** - Blockchain block data
- **transactions** - Transaction records
- **addresses** - Address statistics
- **market_prices** - Daily OHLCV market data
- **coin_metadata** - Coin information
- **ingestion_logs** - Processing audit trail

## Monitoring

### Ingestion Logs
All data processing is tracked in the `ingestion_logs` table:
- Source (coingecko, blockchair)
- Data type (blocks, transactions, prices)
- Status (success, failed, partial)
- Records processed
- Start/end timestamps
- Error messages

### System Health
The pipeline includes health checks for:
- Database connectivity
- API accessibility
- System resources (disk, memory)
- Required Python packages

## Deployment

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost/crypto_db"
   export COINGECKO_RATE_LIMIT=50
   export BLOCKCHAIR_RATE_LIMIT=1440
   ```

3. **Initialize database**:
   ```bash
   python scripts/test_sqlalchemy_pipeline.py
   ```

4. **Deploy DAGs**:
   Copy DAG files to your Airflow DAGs directory and ensure the `src/` directory is in the Python path.

## Testing

Use the test script to validate the pipeline:

```bash
python scripts/test_sqlalchemy_pipeline.py
```

This script tests:
- Settings configuration
- Database connectivity
- API access (CoinGecko and Blockchair)
- Data ingestion functionality
- DAG integration

## Troubleshooting

### Common Issues

1. **Import errors in Airflow**:
   - Ensure the project root is in `PYTHONPATH`
   - Check that all dependencies are installed in the Airflow environment

2. **Database connection failures**:
   - Verify `DATABASE_URL` environment variable
   - Check database server accessibility
   - Ensure required database exists

3. **API rate limit errors**:
   - Reduce `COINGECKO_RATE_LIMIT` and `BLOCKCHAIR_RATE_LIMIT`
   - Implement delays between requests
   - Consider upgrading API plans

4. **Memory issues with large datasets**:
   - Reduce `BATCH_SIZE` in settings
   - Implement date-based chunking
   - Monitor system resources

### Logging

All DAG tasks include comprehensive logging. Check:
- Airflow task logs in the web UI
- Application logs in the configured log directory
- Database ingestion logs for processing history

## Maintenance

### Regular Tasks
- Monitor ingestion logs for failures
- Clean up old logs (automated in main DAG)
- Update API credentials as needed
- Monitor database storage usage

### Backfill Operations
Use the utilities DAG to backfill historical data:

1. Trigger `crypto_pipeline_utilities` DAG
2. Configure `target_date` parameter
3. Run `backfill_single_date` task

## Next Steps

1. **dbt Integration**: Add dbt transformations for dimensional modeling
2. **PowerBI Connection**: Create views and stored procedures for BI tools
3. **Data Quality**: Implement data quality checks and alerts
4. **Performance**: Add database indexing and query optimization
5. **Monitoring**: Integrate with monitoring systems (Prometheus, Grafana)
