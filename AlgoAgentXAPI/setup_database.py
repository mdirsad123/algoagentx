#!/usr/bin/env python3
"""
Complete Database Setup Script for AlgoAgentX

This script populates the database with:
1. All trading strategies from the strategies directory
2. All instruments (BTCUSD, NIFTY, XAUUSD)
3. All market data from CSV files

USAGE:
    python setup_database.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from scripts.csv_to_postgres_migration import CSVMarketDataIngestor
from app.db.models import Strategy, Instrument
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def populate_strategies():
    """Populate all trading strategies"""
    logger.info("Populating strategies...")

    strategies_data = [
        {
            "name": "EMA Crossover",
            "description": "EMA Crossover trading strategy implementation",
            "parameters": {
                "description": "EMA Crossover trading strategy",
                "risk_per_trade": 0.01,
                "max_positions": 5
            }
        },
        {
            "name": "RSI Strategy",
            "description": "RSI Strategy trading strategy implementation",
            "parameters": {
                "description": "RSI Strategy trading strategy",
                "risk_per_trade": 0.01,
                "max_positions": 5
            }
        },
        {
            "name": "SMC Strategy",
            "description": "SMC Strategy trading strategy implementation",
            "parameters": {
                "description": "SMC Strategy trading strategy",
                "risk_per_trade": 0.01,
                "max_positions": 5
            }
        },
        {
            "name": "Stock Burner EMA 9-20",
            "description": "Stock Burner EMA 9-20 trading strategy implementation",
            "parameters": {
                "description": "Stock Burner EMA 9-20 trading strategy",
                "risk_per_trade": 0.01,
                "max_positions": 5
            }
        },
        {
            "name": "Trend Continuation TCE",
            "description": "Trend Continuation TCE trading strategy implementation",
            "parameters": {
                "description": "Trend Continuation TCE trading strategy",
                "risk_per_trade": 0.01,
                "max_positions": 5
            }
        }
    ]

    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        for strategy_data in strategies_data:
            # Check if strategy already exists
            result = await session.execute(
                select(Strategy).where(Strategy.name == strategy_data["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Strategy already exists: {strategy_data['name']}")
                continue

            # Create new strategy
            new_strategy = Strategy(
                name=strategy_data["name"],
                description=strategy_data["description"],
                parameters=strategy_data["parameters"],
                created_by=1  # Use dummy user ID 1
            )

            session.add(new_strategy)
            await session.commit()
            await session.refresh(new_strategy)

            logger.info(f"Created strategy: {strategy_data['name']} (ID: {new_strategy.id})")

    await engine.dispose()

async def populate_instruments():
    """Populate all instruments"""
    logger.info("Populating instruments...")

    instruments_data = [
        {
            "symbol": "BTCUSD",
            "exchange": "BINANCE",
            "market": "CRYPTO",
            "instrument_type": "CRYPTO",
            "tick_size": 0.01,
            "lot_size": 1
        },
        {
            "symbol": "NIFTY",
            "exchange": "NSE",
            "market": "INDIA",
            "instrument_type": "INDEX",
            "tick_size": 0.01,
            "lot_size": 1
        },
        {
            "symbol": "XAUUSD",
            "exchange": "FX",
            "market": "FOREX",
            "instrument_type": "COMMODITY",
            "tick_size": 0.01,
            "lot_size": 1
        }
    ]

    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        for instrument_data in instruments_data:
            # Check if instrument already exists
            result = await session.execute(
                select(Instrument).where(
                    Instrument.symbol == instrument_data["symbol"],
                    Instrument.exchange == instrument_data["exchange"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Instrument already exists: {instrument_data['symbol']}")
                continue

            # Create new instrument
            new_instrument = Instrument(**instrument_data)
            session.add(new_instrument)
            await session.commit()
            await session.refresh(new_instrument)

            logger.info(f"Created instrument: {instrument_data['symbol']} (ID: {new_instrument.id})")

    await engine.dispose()

async def populate_market_data():
    """Populate all market data from CSV files"""
    logger.info("Populating market data...")

    # Define CSV file patterns (relative to the project root)
    csv_patterns = [
        ("AlgoAgentXAPI/data/raw/BTCUSD_5M_1Year.csv", "BTCUSD", "BINANCE", "CRYPTO", "5m"),
        ("AlgoAgentXAPI/data/raw/BTCUSD_15M_1Year.csv", "BTCUSD", "BINANCE", "CRYPTO", "15m"),
        ("AlgoAgentXAPI/data/raw/BTCUSD_H1_1Year.csv", "BTCUSD", "BINANCE", "CRYPTO", "1h"),
        ("AlgoAgentXAPI/data/raw/BTCUSD_D1_1Year.csv", "BTCUSD", "BINANCE", "CRYPTO", "1d"),
        ("AlgoAgentXAPI/data/raw/NIFTY_5M_1Year.csv", "NIFTY", "NSE", "INDIA", "5m"),
        ("AlgoAgentXAPI/data/raw/NIFTY_15M_1Year.csv", "NIFTY", "NSE", "INDIA", "15m"),
        ("AlgoAgentXAPI/data/raw/NIFTY_H1_1Year.csv", "NIFTY", "NSE", "INDIA", "1h"),
        ("AlgoAgentXAPI/data/raw/NIFTY_D1_1Year.csv", "NIFTY", "NSE", "INDIA", "1d"),
        ("AlgoAgentXAPI/data/raw/NIFTY_5m_5Year.csv", "NIFTY", "NSE", "INDIA", "5m"),
        ("AlgoAgentXAPI/data/raw/XAUUSD_5M_1Year.csv", "XAUUSD", "FX", "FOREX", "5m"),
        ("AlgoAgentXAPI/data/raw/XAUUSD_15M_1Year.csv", "XAUUSD", "FX", "FOREX", "15m"),
        ("AlgoAgentXAPI/data/raw/XAUUSD_H1_1Year.csv", "XAUUSD", "FX", "FOREX", "1h"),
        ("AlgoAgentXAPI/data/raw/XAUUSD_D1_1Year.csv", "XAUUSD", "FX", "FOREX", "1d"),
    ]

    ingestor = CSVMarketDataIngestor()

    try:
        for csv_path, symbol, exchange, market, timeframe in csv_patterns:
            logger.info(f"Processing: {symbol} {timeframe}")
            result = await ingestor.auto_detect_and_ingest(
                csv_path=csv_path,
                instrument_symbol=symbol,
                exchange=exchange,
                market=market,
                timeframe=timeframe,
                dry_run=False
            )

            if result['status'] == 'success':
                logger.info(f"SUCCESS {symbol} {timeframe}: {result['success_count']} records")
            else:
                logger.warning(f"FAILED {symbol} {timeframe}: {result.get('error', 'Unknown error')}")

    finally:
        await ingestor.close()

async def main():
    """Main setup function"""
    logger.info("Starting AlgoAgentX Database Setup")
    logger.info("=" * 50)

    try:
        # 1. Populate strategies
        await populate_strategies()

        # 2. Populate instruments
        await populate_instruments()

        # 3. Populate market data
        await populate_market_data()

        logger.info("=" * 50)
        logger.info("Database setup completed successfully!")
        logger.info("You can now test the backtest functionality.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start the API server: python main.py")
        logger.info("2. Start the frontend: cd ../AlgoAgentXApp && npm run dev")
        logger.info("3. Navigate to /backtest to test the functionality")

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
