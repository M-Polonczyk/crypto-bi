"""
Pydantic models for data validation and serialization.
Used for API request/response validation and data transformation.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from enum import Enum


class CoinSymbol(str, Enum):
    """Supported cryptocurrency symbols."""
    BITCOIN = "BTC"
    ETHEREUM = "ETH"
    DOGECOIN = "DOGE"


class IngestionStatus(str, Enum):
    """Data ingestion status options."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    RUNNING = "running"


class BlockchainBlockRequest(BaseModel):
    """Request model for blockchain block data."""
    coin_symbol: str = Field(..., min_length=2, max_length=10)
    date_str: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_height: Optional[int] = Field(None, ge=0)
    end_height: Optional[int] = Field(None, ge=0)
    limit: Optional[int] = Field(1000, ge=1, le=10000)

    @model_validator(mode='after')
    def validate_height_range(self):
        if self.end_height is not None and self.start_height is not None:
            if self.end_height < self.start_height:
                raise ValueError('end_height must be greater than or equal to start_height')
        return self


class BlockchainBlockData(BaseModel):
    """Validated blockchain block data."""
    block_id: int = Field(..., ge=0)
    coin_symbol: str = Field(..., min_length=2, max_length=10)
    block_hash: str = Field(..., min_length=64, max_length=255)
    block_time: Optional[datetime] = None
    transaction_count: Optional[int] = Field(None, ge=0)
    size_bytes: Optional[int] = Field(None, ge=0)
    difficulty: Optional[Decimal] = Field(None, ge=0)

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockchainTransactionData(BaseModel):
    """Validated blockchain transaction data."""
    tx_hash: str = Field(..., min_length=64, max_length=255)
    coin_symbol: str = Field(..., min_length=2, max_length=10)
    block_id: Optional[int] = Field(None, ge=0)
    tx_time: Optional[datetime] = None
    fee_usd: Optional[Decimal] = Field(None, ge=0)
    output_total_usd: Optional[Decimal] = Field(None, ge=0)
    input_count: Optional[int] = Field(None, ge=0)
    output_count: Optional[int] = Field(None, ge=0)
    size_bytes: Optional[int] = Field(None, ge=0)
    is_coinbase: bool = False

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockchainAddressData(BaseModel):
    """Validated blockchain address data."""
    address: str = Field(..., min_length=20, max_length=255)
    coin_symbol: str = Field(..., min_length=2, max_length=10)
    first_seen_time: Optional[datetime] = None
    last_seen_time: Optional[datetime] = None
    transaction_count: Optional[int] = Field(None, ge=0)
    received_total_usd: Optional[Decimal] = Field(None, ge=0)
    spent_total_usd: Optional[Decimal] = Field(None, ge=0)
    balance_usd: Optional[Decimal] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }


class MarketPriceData(BaseModel):
    """Validated market price data from CoinGecko."""
    coin_id: str = Field(..., min_length=1, max_length=50)
    price_date: date
    price_usd: Optional[Decimal] = Field(None, ge=0)
    volume_usd: Optional[Decimal] = Field(None, ge=0)
    market_cap_usd: Optional[Decimal] = Field(None, ge=0)

    @field_validator('price_date')
    def validate_price_date(cls, v):
        if v > date.today():
            raise ValueError('price_date cannot be in the future')
        return v

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            date: lambda v: v.isoformat()
        }


class DataIngestionLogData(BaseModel):
    """Data ingestion log entry."""
    source: str = Field(..., min_length=1, max_length=50)
    data_type: str = Field(..., min_length=1, max_length=50)
    coin_symbol: Optional[str] = Field(None, min_length=2, max_length=10)
    target_date: Optional[date] = None
    status: IngestionStatus
    records_processed: int = Field(0, ge=0)
    records_inserted: int = Field(0, ge=0)
    records_updated: int = Field(0, ge=0)
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @model_validator(mode='after')
    def validate_completion_time(self):
        if self.completed_at is not None and self.started_at is not None:
            if self.completed_at < self.started_at:
                raise ValueError('completed_at must be after started_at')
        return self

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }


class CoinMetadataData(BaseModel):
    """Coin metadata configuration."""
    symbol: str = Field(..., min_length=2, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    coingecko_id: Optional[str] = Field(None, max_length=50)
    blockchair_id: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    ingestion_enabled: bool = True
    last_ingested_date: Optional[date] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }


class IngestionRequest(BaseModel):
    """Request model for data ingestion operations."""
    source: str = Field(..., pattern=r'^(blockchair|coingecko)$')
    data_types: List[str] = Field(...)
    coin_symbols: Optional[List[str]] = Field(None)

    target_date: Optional[date] = None
    force_refresh: bool = False

    @field_validator('coin_symbols')
    def validate_coin_symbols(cls, v):
        if v is not None:
            if len(v) < 1:
                raise ValueError('coin_symbols must contain at least 1 item')
            if len(v) > 10:
                raise ValueError('coin_symbols must contain at most 10 items')
        return v

    @model_validator(mode='after')
    def validate_data_types(self):
        valid_types = {
            'blockchair': ['blocks', 'transactions', 'addresses'],
            'coingecko': ['prices', 'market_data']
        }
        
        if self.source and self.source in valid_types:
            invalid_types = [dt for dt in self.data_types if dt not in valid_types[self.source]]
            if invalid_types:
                raise ValueError(f'Invalid data types for {self.source}: {invalid_types}')
        return self


class IngestionResponse(BaseModel):
    """Response model for data ingestion operations."""
    request_id: str
    status: IngestionStatus
    message: str
    details: Dict[str, Any] = {}
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: Dict[str, int] = {}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockchairAPIResponse(BaseModel):
    """Model for raw Blockchair API responses."""
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class CoinGeckoAPIResponse(BaseModel):
    """Model for raw CoinGecko API responses."""
    market_data: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    symbol: Optional[str] = None

    class Config:
        extra = "allow"


class DatabaseStats(BaseModel):
    """Database statistics and health metrics."""
    total_blocks: int = 0
    total_transactions: int = 0
    total_addresses: int = 0
    total_price_records: int = 0
    latest_block_by_coin: Dict[str, int] = {}
    latest_price_by_coin: Dict[str, date] = {}
    last_updated: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class ValidationError(BaseModel):
    """Standard validation error response."""
    field: str
    message: str
    invalid_value: Any


class APIErrorResponse(BaseModel):
    """Standard API error response."""
    error: str
    message: str
    details: Optional[List[ValidationError]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
