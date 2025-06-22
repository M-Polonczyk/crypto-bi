"""
SQLAlchemy models for cryptocurrency data pipeline.
Defines database table structures and relationships.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Numeric, DateTime, Boolean, Date,
    ForeignKey, Index, UniqueConstraint, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Optional

Base = declarative_base()


class BlockchainBlock(Base):
    """Model for blockchain block data from Blockchair API."""
    __tablename__ = 'raw_blockchain_blocks'
    
    # Composite primary key
    block_id = Column(BigInteger, primary_key=True)
    coin_symbol = Column(String(10), primary_key=True)
    
    # Block details
    block_hash = Column(String(255), unique=True, nullable=False, index=True)
    block_time = Column(DateTime, nullable=True)
    transaction_count = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    difficulty = Column(Numeric(precision=30, scale=6), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    transactions = relationship("BlockchainTransaction", back_populates="block")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_block_time_coin', 'block_time', 'coin_symbol'),
        Index('idx_block_hash', 'block_hash'),
    )

    def __repr__(self):
        return f"<BlockchainBlock(id={self.block_id}, coin={self.coin_symbol}, hash={self.block_hash[:8]}...)>"


class BlockchainTransaction(Base):
    """Model for blockchain transaction data from Blockchair API."""
    __tablename__ = 'raw_blockchain_transactions'
    
    # Composite primary key
    tx_hash = Column(String(255), primary_key=True)
    coin_symbol = Column(String(10), primary_key=True)
    
    # Transaction details
    block_id = Column(BigInteger, nullable=True)
    tx_time = Column(DateTime, nullable=True)
    fee_usd = Column(Numeric(precision=15, scale=8), nullable=True)
    output_total_usd = Column(Numeric(precision=20, scale=8), nullable=True)
    input_count = Column(Integer, nullable=True)
    output_count = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    is_coinbase = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    block = relationship("BlockchainBlock", back_populates="transactions")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_tx_time_coin', 'tx_time', 'coin_symbol'),
        Index('idx_tx_block_id', 'block_id'),
        Index('idx_tx_fee_usd', 'fee_usd'),
        # Note: Foreign key constraint removed to avoid composite key issues
        # Referential integrity maintained at application level
    )

    def __repr__(self):
        return f"<BlockchainTransaction(hash={self.tx_hash[:8]}..., coin={self.coin_symbol}, block={self.block_id})>"


class BlockchainAddress(Base):
    """Model for blockchain address data from Blockchair API."""
    __tablename__ = 'raw_blockchain_addresses'
    
    # Composite primary key
    address = Column(String(255), primary_key=True)
    coin_symbol = Column(String(10), primary_key=True)
    
    # Address details
    first_seen_time = Column(DateTime, nullable=True)
    last_seen_time = Column(DateTime, nullable=True)
    transaction_count = Column(Integer, nullable=True)
    received_total_usd = Column(Numeric(precision=20, scale=8), nullable=True)
    spent_total_usd = Column(Numeric(precision=20, scale=8), nullable=True)
    balance_usd = Column(Numeric(precision=20, scale=8), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_address_balance', 'balance_usd'),
        Index('idx_address_tx_count', 'transaction_count'),
        Index('idx_address_first_seen', 'first_seen_time'),
    )

    def __repr__(self):
        return f"<BlockchainAddress(address={self.address[:8]}..., coin={self.coin_symbol}, balance=${self.balance_usd})>"


class MarketPrice(Base):
    """Model for market price data from CoinGecko API."""
    __tablename__ = 'raw_market_prices_volumes'
    
    # Composite primary key
    coin_id = Column(String(50), primary_key=True)
    price_date = Column(Date, primary_key=True)
    
    # Price data
    price_usd = Column(Numeric(precision=15, scale=8), nullable=True)
    volume_usd = Column(Numeric(precision=20, scale=2), nullable=True)
    market_cap_usd = Column(Numeric(precision=25, scale=2), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_price_date_coin', 'price_date', 'coin_id'),
        Index('idx_price_usd', 'price_usd'),
        Index('idx_market_cap', 'market_cap_usd'),
    )

    def __repr__(self):
        return f"<MarketPrice(coin={self.coin_id}, date={self.price_date}, price=${self.price_usd})>"


class DataIngestionLog(Base):
    """Model to track data ingestion runs and their status."""
    __tablename__ = 'data_ingestion_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Ingestion details
    source = Column(String(50), nullable=False)  # 'blockchair', 'coingecko', etc.
    data_type = Column(String(50), nullable=False)  # 'blocks', 'transactions', 'prices', etc.
    coin_symbol = Column(String(10), nullable=True)
    target_date = Column(Date, nullable=True)
    
    # Status tracking
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'partial'
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    
    # Execution details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_ingestion_source_type', 'source', 'data_type'),
        Index('idx_ingestion_date', 'target_date'),
        Index('idx_ingestion_status', 'status'),
    )

    def __repr__(self):
        return f"<DataIngestionLog(source={self.source}, type={self.data_type}, status={self.status})>"


class CoinMetadata(Base):
    """Model to store coin metadata and configuration."""
    __tablename__ = 'coin_metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Coin identifiers
    symbol = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    coingecko_id = Column(String(50), nullable=True)
    blockchair_id = Column(String(50), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    ingestion_enabled = Column(Boolean, default=True)
    last_ingested_date = Column(Date, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_coin_symbol', 'symbol'),
        Index('idx_coin_active', 'is_active'),
    )

    def __repr__(self):
        return f"<CoinMetadata(symbol={self.symbol}, name={self.name}, active={self.is_active})>"
