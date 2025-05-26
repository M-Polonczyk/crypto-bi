# Data Sources

This project relies on external APIs to gather blockchain activity and cryptocurrency market data. The primary sources are the Blockchair API and the CoinGecko API.

## 1. Blockchair API

- **Website:** [https://blockchair.com/api/docs](https://blockchair.com/api/docs)
- **Purpose:** Provides comprehensive data for various blockchains. In this project, it's used for Bitcoin (BTC), Ethereum (ETH), and Dogecoin (DOGE).
- **Data Points Extracted (Examples):**
  - **Blocks:**
    - Block ID / Height
    - Block Hash
    - Timestamp
    - Transaction Count
    - Block Size
    - Difficulty
    - Miner information (if available)
  - **Transactions:**
    - Transaction Hash (ID)
    - Block ID (confirming block)
    - Timestamp
    - Fees (in native currency and USD)
    - Input Count & Output Count
    - Total Input Value & Total Output Value (in native currency and USD)
    - Transaction Size
    - Coinbase status
    - Input addresses and values (potentially, for more detailed analysis)
    - Output addresses and values (potentially, for more detailed analysis)
  - **Addresses (Potential Future Enhancement):**
    - Address balance
    - Transaction count associated with an address
    - First seen / Last seen timestamps
- **Endpoints Used (Examples):**
  - `/<coin>/blocks?date=<YYYY-MM-DD>&limit=<N>`: To fetch blocks mined on a specific date.
  - `/<coin>/transactions?date=<YYYY-MM-DD>&limit=<N>`: To fetch transactions confirmed on a specific date.
  - More specific endpoints might be used for fetching details of a single block or transaction if needed.
- **Authentication:** Blockchair offers a generous free tier. For higher rate limits or more features, an API key might be required and can be configured via environment variables.
- **Rate Limits:** The free tier has rate limits (e.g., requests per minute/hour). Ingestion scripts include basic delays (`time.sleep()`) to respect these limits. For high-volume backfills, more sophisticated rate limiting and retry logic might be necessary.
- **Data Format:** JSON.
- **Ingestion Script:** `src/ingestion/blockchair_ingestor.py`

## 2. CoinGecko API

- **Website:** [https://www.coingecko.com/en/api/documentation](https://www.coingecko.com/en/api/documentation)
- **Purpose:** Provides cryptocurrency market data, including prices, trading volumes, market capitalization, and historical data.
- **Data Points Extracted (Examples for BTC, ETH, DOGE):**
  - **Historical Price:** Daily closing price in USD.
  - **Total Volume:** Daily total trading volume in USD across tracked exchanges.
  - **Market Capitalization:** Daily market cap in USD.
- **Endpoints Used (Examples):**
  - `/coins/{id}/history?date={dd-mm-yyyy}&localization=false`: To fetch historical market data (price, volume, market cap) for a specific coin on a specific date. The `id` corresponds to CoinGecko's unique identifier for the coin (e.g., "bitcoin", "ethereum", "dogecoin").
- **Authentication:**
  - **Public API:** Available without an API key, but with stricter rate limits.
  - **Pro API:** Requires an API key (configured via `COINGECKO_API_KEY` environment variable) for higher rate limits and additional features. The ingestion script supports using the Pro API if an key is provided.
- **Rate Limits:** The public API has rate limits (e.g., 10-30 calls per minute). The Pro API offers significantly higher limits. Ingestion scripts include basic delays (`time.sleep()`) between calls.
- **Data Format:** JSON.
- **Ingestion Script:** `src/ingestion/coingecko_ingestor.py`

## Data Granularity and Update Frequency

- **Blockchain Data (Blockchair):** Aiming for daily granularity, fetching all blocks and transactions confirmed on the previous day.
- **Market Data (CoinGecko):** Daily granularity, fetching the previous day's closing price, total volume, and market cap.

The Airflow pipeline is typically scheduled to run once daily to update the data warehouse with the previous day's information.

```
