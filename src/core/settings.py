"""
Settings and configuration module for the cryptocurrency data pipeline.
Manages environment variables, database connections, and application settings.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class DatabaseSettings:
    """Database connection settings."""

    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = "password"
    database: str = "crypto_data"
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 3600
    echo: bool = False

    @property
    def url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        """Create database settings from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            username=os.getenv("DB_USER_APP", "postgres"),
            password=os.getenv("DB_PASSWORD_APP", "password"),
            database=os.getenv("DB_NAME_APP", "crypto_data"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )


@dataclass
class APISettings:
    """External API settings and rate limits."""

    # CoinGecko settings
    coingecko_api_key: Optional[str] = None
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_pro_url: str = "https://pro-api.coingecko.com/api/v3"
    coingecko_rate_limit: int = 3  # seconds between requests
    coingecko_timeout: int = 30

    # Blockchair settings
    blockchair_base_url: str = "https://api.blockchair.com"
    blockchair_rate_limit: int = 1  # seconds between requests
    blockchair_timeout: int = 30
    blockchair_batch_size: int = 10

    @classmethod
    def from_env(cls) -> "APISettings":
        """Create API settings from environment variables."""
        return cls(
            coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
            coingecko_rate_limit=int(os.getenv("COINGECKO_RATE_LIMIT", "3")),
            coingecko_timeout=int(os.getenv("COINGECKO_TIMEOUT", "30")),
            blockchair_rate_limit=int(os.getenv("BLOCKCHAIR_RATE_LIMIT", "1")),
            blockchair_timeout=int(os.getenv("BLOCKCHAIR_TIMEOUT", "30")),
            blockchair_batch_size=int(os.getenv("BLOCKCHAIR_BATCH_SIZE", "10")),
        )


@dataclass
class IngestionSettings:
    """Data ingestion configuration."""

    # General settings
    default_coins: List[str] = field(
        default_factory=lambda: ["bitcoin", "ethereum", "dogecoin"]
    )
    max_retries: int = 3
    retry_delay: int = 60  # seconds

    # Blockchair specific
    blockchair_block_limit: int = 1000
    blockchair_tx_limit: int = 10000
    blockchair_address_batch_size: int = 10

    # CoinGecko specific
    coingecko_backfill_days: int = 30

    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "IngestionSettings":
        """Create ingestion settings from environment variables."""
        default_coins = os.getenv("DEFAULT_COINS", "bitcoin,ethereum,dogecoin").split(
            ","
        )

        return cls(
            default_coins=[coin.strip() for coin in default_coins],
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "60")),
            blockchair_block_limit=int(os.getenv("BLOCKCHAIR_BLOCK_LIMIT", "1000")),
            blockchair_tx_limit=int(os.getenv("BLOCKCHAIR_TX_LIMIT", "10000")),
            blockchair_address_batch_size=int(
                os.getenv("BLOCKCHAIR_ADDRESS_BATCH_SIZE", "10")
            ),
            coingecko_backfill_days=int(os.getenv("COINGECKO_BACKFILL_DAYS", "30")),
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


@dataclass
class AirflowSettings:
    """Airflow-specific settings."""

    # DAG settings
    schedule_interval: str = "@daily"
    start_date_days_ago: int = 1
    catchup: bool = False
    max_active_runs: int = 1

    # Task settings
    task_retries: int = 2
    retry_delay_minutes: int = 5
    task_timeout_minutes: int = 30

    # Email settings
    email_on_failure: bool = True
    email_on_retry: bool = False
    email_recipients: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "AirflowSettings":
        """Create Airflow settings from environment variables."""
        email_recipients = []
        if os.getenv("AIRFLOW_EMAIL_RECIPIENTS"):
            email_recipients = [
                email.strip()
                for email in os.getenv("AIRFLOW_EMAIL_RECIPIENTS", "").split(",")
            ]

        return cls(
            schedule_interval=os.getenv("AIRFLOW_SCHEDULE_INTERVAL", "@daily"),
            start_date_days_ago=int(os.getenv("AIRFLOW_START_DATE_DAYS_AGO", "1")),
            catchup=os.getenv("AIRFLOW_CATCHUP", "false").lower() == "true",
            max_active_runs=int(os.getenv("AIRFLOW_MAX_ACTIVE_RUNS", "1")),
            task_retries=int(os.getenv("AIRFLOW_TASK_RETRIES", "2")),
            retry_delay_minutes=int(os.getenv("AIRFLOW_RETRY_DELAY_MINUTES", "5")),
            task_timeout_minutes=int(os.getenv("AIRFLOW_TASK_TIMEOUT_MINUTES", "30")),
            email_on_failure=os.getenv("AIRFLOW_EMAIL_ON_FAILURE", "true").lower()
            == "true",
            email_on_retry=os.getenv("AIRFLOW_EMAIL_ON_RETRY", "false").lower()
            == "true",
            email_recipients=email_recipients,
        )


@dataclass
class AppSettings:
    """Main application settings container."""

    database: DatabaseSettings = field(default_factory=DatabaseSettings.from_env)
    api: APISettings = field(default_factory=APISettings.from_env)
    ingestion: IngestionSettings = field(default_factory=IngestionSettings.from_env)
    airflow: AirflowSettings = field(default_factory=AirflowSettings.from_env)

    # Application metadata
    app_name: str = "crypto-data-pipeline"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Create complete application settings from environment."""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )


# Coin configuration mapping
SUPPORTED_COINS = {
    "bitcoin": {
        "symbol": "BTC",
        "name": "Bitcoin",
        "coingecko_id": "bitcoin",
        "blockchair_id": "bitcoin",
        "is_active": True,
        "ingestion_enabled": True,
    },
    "ethereum": {
        "symbol": "ETH",
        "name": "Ethereum",
        "coingecko_id": "ethereum",
        "blockchair_id": "ethereum",
        "is_active": True,
        "ingestion_enabled": True,
    },
    "dogecoin": {
        "symbol": "DOGE",
        "name": "Dogecoin",
        "coingecko_id": "dogecoin",
        "blockchair_id": "dogecoin",
        "is_active": True,
        "ingestion_enabled": True,
    },
    "litecoin": {
        "symbol": "LTC",
        "name": "Litecoin",
        "coingecko_id": "litecoin",
        "blockchair_id": "litecoin",
        "is_active": True,
        "ingestion_enabled": False,  # Can be enabled later
    },
    "bitcoin-cash": {
        "symbol": "BCH",
        "name": "Bitcoin Cash",
        "coingecko_id": "bitcoin-cash",
        "blockchair_id": "bitcoin-cash",
        "is_active": True,
        "ingestion_enabled": False,
    },
}

settings = AppSettings.from_env()


def get_coin_config(coin_key: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific coin."""
    return SUPPORTED_COINS.get(coin_key)


def get_active_coins() -> List[Dict[str, Any]]:
    """Get list of active coins for ingestion."""
    return [
        config
        for config in SUPPORTED_COINS.values()
        if config.get("is_active", False) and config.get("ingestion_enabled", False)
    ]


def get_coin_symbol_mapping() -> Dict[str, str]:
    """Get mapping from coin keys to CoinGecko IDs."""
    return {
        coin_key: config["coingecko_id"]
        for coin_key, config in SUPPORTED_COINS.items()
        if config.get("is_active", False) and config.get("coingecko_id")
    }


def validate_settings() -> List[str]:
    """Validate settings and return list of any issues found."""
    issues = []

    # Database validation
    if not settings.database.username:
        issues.append("Database username is required")
    if not settings.database.password:
        issues.append("Database password is required")
    if not settings.database.database:
        issues.append("Database name is required")

    # API validation
    if not settings.api.coingecko_api_key:
        issues.append("CoinGecko API key is recommended for higher rate limits")

    # Ingestion validation
    if not settings.ingestion.default_coins:
        issues.append("At least one default coin should be configured")

    return issues


def print_settings_summary():
    """Print a summary of current settings (excluding sensitive data)."""
    print(f"=== {settings.app_name} v{settings.version} Settings ===")
    print(f"Environment: {settings.environment}")
    print(f"Debug Mode: {settings.debug}")
    print(
        f"Database: {settings.database.host}:{settings.database.port}/{settings.database.database}"
    )
    print(f"Default Coins: {settings.ingestion.default_coins}")
    print(f"Active Coins: {[coin['symbol'] for coin in get_active_coins()]}")
    print(f"Log Level: {settings.ingestion.log_level}")

    # Validation
    issues = validate_settings()
    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration is valid")


if __name__ == "__main__":
    print_settings_summary()
