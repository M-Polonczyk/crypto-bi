"""
Database service layer using SQLAlchemy ORM.
Provides high-level database operations with Pydantic model integration.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timezone
import logging
import os

from .models import (
    Base, BlockchainBlock, BlockchainTransaction, BlockchainAddress,
    MarketPrice, DataIngestionLog, CoinMetadata
)
from .schemas import (
    BlockchainBlockData, BlockchainTransactionData, BlockchainAddressData,
    MarketPriceData, DataIngestionLogData, CoinMetadataData,
    IngestionStatus, DatabaseStats
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for cryptocurrency data operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database service with connection."""
        if database_url is None:
            # Build database URL from environment variables
            db_user = os.getenv('DB_USER_APP', 'postgres')
            db_password = os.getenv('DB_PASSWORD_APP', 'password')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME_APP', 'crypto_data')
            
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup."""
        session = self.session_local()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # Blockchain Block Operations
    def insert_blocks(self, blocks: List[BlockchainBlockData]) -> Dict[str, int]:
        """Insert or update blockchain blocks."""
        with self.get_session() as session:
            inserted = 0
            updated = 0
            
            for block_data in blocks:
                try:
                    # Check if block exists
                    existing_block = session.query(BlockchainBlock).filter_by(
                        block_id=block_data.block_id,
                        coin_symbol=block_data.coin_symbol
                    ).first()
                    
                    if existing_block:
                        # Update existing block
                        for field, value in block_data.dict(exclude_unset=True).items():
                            setattr(existing_block, field, value)
                        existing_block.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Insert new block
                        new_block = BlockchainBlock(**block_data.dict())
                        session.add(new_block)
                        inserted += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Block integrity error: {e}")
                    session.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing block {block_data.block_id}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Blocks - Inserted: {inserted}, Updated: {updated}")
            return {"inserted": inserted, "updated": updated}
    
    def get_blocks(
        self,
        coin_symbol: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[BlockchainBlock]:
        """Get blockchain blocks with filtering."""
        with self.get_session() as session:
            query = session.query(BlockchainBlock)
            
            if coin_symbol:
                query = query.filter(BlockchainBlock.coin_symbol == coin_symbol)
            if start_date:
                query = query.filter(BlockchainBlock.block_time >= start_date)
            if end_date:
                query = query.filter(BlockchainBlock.block_time <= end_date)
            
            return query.order_by(BlockchainBlock.block_time.desc()).limit(limit).all()
    
    # Blockchain Transaction Operations
    def insert_transactions(self, transactions: List[BlockchainTransactionData]) -> Dict[str, int]:
        """Insert or update blockchain transactions."""
        with self.get_session() as session:
            inserted = 0
            updated = 0
            
            for tx_data in transactions:
                try:
                    # Check if transaction exists
                    existing_tx = session.query(BlockchainTransaction).filter_by(
                        tx_hash=tx_data.tx_hash,
                        coin_symbol=tx_data.coin_symbol
                    ).first()
                    
                    if existing_tx:
                        # Update existing transaction
                        for field, value in tx_data.dict(exclude_unset=True).items():
                            setattr(existing_tx, field, value)
                        existing_tx.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Insert new transaction
                        new_tx = BlockchainTransaction(**tx_data.dict())
                        session.add(new_tx)
                        inserted += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Transaction integrity error: {e}")
                    session.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing transaction {tx_data.tx_hash}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Transactions - Inserted: {inserted}, Updated: {updated}")
            return {"inserted": inserted, "updated": updated}
    
    def get_transactions(
        self,
        coin_symbol: Optional[str] = None,
        block_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[BlockchainTransaction]:
        """Get blockchain transactions with filtering."""
        with self.get_session() as session:
            query = session.query(BlockchainTransaction)
            
            if coin_symbol:
                query = query.filter(BlockchainTransaction.coin_symbol == coin_symbol)
            if block_id:
                query = query.filter(BlockchainTransaction.block_id == block_id)
            if start_date:
                query = query.filter(BlockchainTransaction.tx_time >= start_date)
            if end_date:
                query = query.filter(BlockchainTransaction.tx_time <= end_date)
            
            return query.order_by(BlockchainTransaction.tx_time.desc()).limit(limit).all()
    
    # Address Operations
    def insert_addresses(self, addresses: List[BlockchainAddressData]) -> Dict[str, int]:
        """Insert or update blockchain addresses."""
        with self.get_session() as session:
            inserted = 0
            updated = 0
            
            for addr_data in addresses:
                try:
                    # Check if address exists
                    existing_addr = session.query(BlockchainAddress).filter_by(
                        address=addr_data.address,
                        coin_symbol=addr_data.coin_symbol
                    ).first()
                    
                    if existing_addr:
                        # Update existing address
                        for field, value in addr_data.dict(exclude_unset=True).items():
                            setattr(existing_addr, field, value)
                        existing_addr.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Insert new address
                        new_addr = BlockchainAddress(**addr_data.dict())
                        session.add(new_addr)
                        inserted += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Address integrity error: {e}")
                    session.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing address {addr_data.address}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Addresses - Inserted: {inserted}, Updated: {updated}")
            return {"inserted": inserted, "updated": updated}
    
    # Market Price Operations
    def insert_market_prices(self, prices: List[MarketPriceData]) -> Dict[str, int]:
        """Insert or update market prices."""
        with self.get_session() as session:
            inserted = 0
            updated = 0
            
            for price_data in prices:
                try:
                    # Check if price record exists
                    existing_price = session.query(MarketPrice).filter_by(
                        coin_id=price_data.coin_id,
                        price_date=price_data.price_date
                    ).first()
                    
                    if existing_price:
                        # Update existing price
                        for field, value in price_data.dict(exclude_unset=True).items():
                            setattr(existing_price, field, value)
                        existing_price.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Insert new price
                        new_price = MarketPrice(**price_data.dict())
                        session.add(new_price)
                        inserted += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Price integrity error: {e}")
                    session.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing price for {price_data.coin_id}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Prices - Inserted: {inserted}, Updated: {updated}")
            return {"inserted": inserted, "updated": updated}
    
    def get_market_prices(
        self,
        coin_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[MarketPrice]:
        """Get market prices with filtering."""
        with self.get_session() as session:
            query = session.query(MarketPrice)
            
            if coin_id:
                query = query.filter(MarketPrice.coin_id == coin_id)
            if start_date:
                query = query.filter(MarketPrice.price_date >= start_date)
            if end_date:
                query = query.filter(MarketPrice.price_date <= end_date)
            
            return query.order_by(MarketPrice.price_date.desc()).limit(limit).all()
    
    # Ingestion Log Operations
    def log_ingestion(self, log_data: DataIngestionLogData) -> int:
        """Log data ingestion operation."""
        with self.get_session() as session:
            log_entry = DataIngestionLog(**log_data.dict())
            session.add(log_entry)
            session.commit()
            return log_entry.id
    
    def update_ingestion_log(self, log_id: int, **updates) -> bool:
        """Update ingestion log entry."""
        with self.get_session() as session:
            log_entry = session.query(DataIngestionLog).filter_by(id=log_id).first()
            if log_entry:
                for field, value in updates.items():
                    setattr(log_entry, field, value)
                session.commit()
                return True
            return False
    
    def get_ingestion_logs(
        self,
        source: Optional[str] = None,
        status: Optional[IngestionStatus] = None,
        limit: int = 100
    ) -> List[DataIngestionLog]:
        """Get ingestion logs with filtering."""
        with self.get_session() as session:
            query = session.query(DataIngestionLog)
            
            if source:
                query = query.filter(DataIngestionLog.source == source)
            if status:
                query = query.filter(DataIngestionLog.status == status.value)
            
            return query.order_by(DataIngestionLog.created_at.desc()).limit(limit).all()
    
    # Coin Metadata Operations
    def insert_coin_metadata(self, coin_data: CoinMetadataData) -> int:
        """Insert or update coin metadata."""
        with self.get_session() as session:
            existing_coin = session.query(CoinMetadata).filter_by(
                symbol=coin_data.symbol
            ).first()
            
            if existing_coin:
                # Update existing coin
                for field, value in coin_data.dict(exclude_unset=True).items():
                    setattr(existing_coin, field, value)
                existing_coin.updated_at = datetime.now(timezone.utc)
                session.commit()
                return existing_coin.id
            else:
                # Insert new coin
                new_coin = CoinMetadata(**coin_data.dict())
                session.add(new_coin)
                session.commit()
                return new_coin.id
    
    def get_active_coins(self) -> List[CoinMetadata]:
        """Get all active coins for ingestion."""
        with self.get_session() as session:
            return session.query(CoinMetadata).filter_by(
                is_active=True,
                ingestion_enabled=True
            ).all()
    
    # Statistics and Health Checks
    def get_database_stats(self) -> DatabaseStats:
        """Get comprehensive database statistics."""
        with self.get_session() as session:
            stats = DatabaseStats(last_updated=datetime.now(timezone.utc))
            
            # Count records
            stats.total_blocks = session.query(BlockchainBlock).count()
            stats.total_transactions = session.query(BlockchainTransaction).count()
            stats.total_addresses = session.query(BlockchainAddress).count()
            stats.total_price_records = session.query(MarketPrice).count()
            
            # Latest block by coin
            block_results = session.execute(text("""
                SELECT coin_symbol, MAX(block_id) as max_block
                FROM raw_blockchain_blocks
                GROUP BY coin_symbol
            """)).fetchall()
            
            stats.latest_block_by_coin = {row[0]: row[1] for row in block_results}
            
            # Latest price by coin
            price_results = session.execute(text("""
                SELECT coin_id, MAX(price_date) as max_date
                FROM raw_market_prices_volumes
                GROUP BY coin_id
            """)).fetchall()
            
            stats.latest_price_by_coin = {row[0]: row[1] for row in price_results}
            
            return stats
    
    def health_check(self) -> bool:
        """Perform database health check."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database service instance
db_service = DatabaseService()
