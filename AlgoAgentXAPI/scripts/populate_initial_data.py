#!/usr/bin/env python3
"""
Initial Data Population Script for AlgoAgentX

This script populates the database with:
1. All trading strategies from the strategies directory
2. All instruments (BTCUSD, NIFTY, XAUUSD)
3. All market data from CSV files

USAGE:
    python scripts/populate_initial_data.py --help

EXAMPLE:
    python scripts/populate_initial_data.py --execute
"""

import argparse
import logging
import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, insert
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.models import Strategy, Instrument, MarketData
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('populate_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InitialDataPopulator:
    """Populate initial data for AlgoAgentX"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.database_url
        self.engine = create_async_engine(self.db_url)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.project_root = Path(__file__).parent.parent

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

    async def populate_strategies(self) -> Dict[str, int]:
        """Populate all trading strategies from strategies directory"""
        strategies_dir = self.project_root / "strategies"
        strategy_mappings = {
            "ema_crossover.py": "EMA Crossover",
            "rsi_strategy.py": "RSI Strategy",
            "smc_strategy.py": "SMC Strategy",
            "stock_burner_ema_9_20.py": "Stock Burner EMA 9-20",
            "trend_continuation_tce_adam.py": "Trend Continuation TCE",
        }

        results = {}

        async with self.async_session() as session:
            for filename, strategy_name in strategy_mappings.items():
                file_path = strategies_dir / filename
                if not file_path.exists():
                    logger.warning(f"Strategy file not found: {filename}")
                    continue

                # Check if strategy already exists
                result = await session.execute(
                    select(Strategy).where(Strategy.name == strategy_name)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(f"Strategy already exists: {strategy_name} (ID: {existing.id})")
                    results[strategy_name] = existing.id
                    continue

                # Create new strategy
                # Read strategy parameters from file (simplified - you might want to parse the actual parameters)
                parameters = {
                    "description": f"{strategy_name} trading strategy",
                    "risk_per_trade": 0.01,
                    "max_positions": 5
                }

                new_strategy = Strategy(
                    name=strategy_name,
                    description=f"{strategy_name} trading strategy implementation",
                    parameters=parameters,
                    created_by=1  # Use dummy user ID 1
                )

                session.add(new_strategy)
                await session.commit()
                await session.refresh(new_strategy)

                logger.info(f"Created strategy: {strategy_name} (ID: {new_strategy.id})")
                results[strategy_name] = new_strategy.id

        return results

    async def populate_instruments(self) -> Dict[str, int]:
        """Populate all instruments"""
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

        results = {}

        async with self.async_session() as session:
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
                    logger.info(f"Instrument already exists: {instrument_data['symbol']} (ID: {existing.id})")
                    results[instrument_data["symbol"]] = existing.id
                    continue

                # Create new instrument
                new_instrument = Instrument(**instrument_data)
                session.add(new_instrument)
                await session.commit()
                await session.refresh(new_instrument)

                logger.info(f"Created instrument: {instrument_data['symbol']} (ID: {new_instrument.id})")
                results[instrument_data["symbol"]] = new_instrument.id

        return results

    async def populate_market_data(self, instruments: Dict[str, int]) -> Dict[str, int]:
        """Populate all market data from CSV files"""
        import pandas as pd
        from datetime import datetime

        data_dir = self.project_root / "data" / "raw"
        results = {"total_files": 0, "successful": 0, "failed": 0}

        # Define CSV file patterns
        csv_patterns = [
            ("BTCUSD_5M_1Year.csv", "BTCUSD", "5m"),
            ("BTCUSD_15M_1Year.csv", "BTCUSD", "15m"),
            ("BTCUSD_H1_1Year.csv", "BTCUSD", "1h"),
            ("BTCUSD_D1_1Year.csv", "BTCUSD", "1d"),
            ("NIFTY_5M_1Year.csv", "NIFTY", "5m"),
            ("NIFTY_15M_1Year.csv", "NIFTY", "15m"),
            ("NIFTY_H1_1Year.csv", "NIFTY", "1h"),
            ("NIFTY_D1_1Year.csv", "NIFTY", "1d"),
            ("NIFTY_5m_5Year.csv", "NIFTY", "5m"),  # Additional NIFTY 5m data
            ("XAUUSD_5M_1Year.csv", "XAUUSD", "5m"),
            ("XAUUSD_15M_1Year.csv", "XAUUSD", "15m"),
            ("XAUUSD_H1_1Year.csv", "XAUUSD", "1h"),
            ("XAUUSD_D1_1Year.csv", "XAUUSD", "1d"),
        ]

        async with self.async_session() as session:
            for filename, symbol, timeframe in csv_patterns:
                results["total_files"] += 1
                csv_path = data_dir / filename

                if not csv_path.exists():
                    logger.warning(f"CSV file not found: {filename}")
                    results["failed"] += 1
                    continue

                if symbol not in instruments:
                    logger.error(f"Instrument not found: {symbol}")
                    results["failed"] += 1
                    continue

                instrument_id = instruments[symbol]

                try:
                    # Read CSV
                    logger.info(f"Processing: {filename}")
                    df = pd.read_csv(csv_path)

                    # Validate columns
                    required_cols = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
                    if not required_cols.issubset(set(df.columns)):
                        logger.error(f"Invalid CSV structure: {filename}")
                        results["failed"] += 1
                        continue

                    # Clean data
                    df['Date'] = pd.to_datetime(df['Date'])
                    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    for col in numeric_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    df = df.dropna().sort_values('Date')

                    # Check if data already exists
                    start_date = df['Date'].min()
                    end_date = df['Date'].max()

                    existing_check = await session.execute(
                        select(MarketData).where(
                            MarketData.instrument_id == instrument_id,
                            MarketData.timeframe == timeframe,
                            MarketData.timestamp >= start_date,
                            MarketData.timestamp <= end_date
                        ).limit(1)
                    )

                    if existing_check.scalar_one_or_none():
                        logger.info(f"Data already exists for {symbol}/{timeframe}")
                        results["successful"] += 1
                        continue

                    # Insert data in chunks
                    chunk_size = 1000
                    total_inserted = 0

                    for i in range(0, len(df), chunk_size):
                        chunk = df.iloc[i:i + chunk_size]

                        records = []
                        for _, row in chunk.iterrows():
                            records.append({
                                'instrument_id': instrument_id,
                                'timeframe': timeframe,
                                'timestamp': row['Date'],
                                'open': float(row['Open']),
                                'high': float(row['High']),
                                'low': float(row['Low']),
                                'close': float(row['Close']),
                                'volume': float(row['Volume']) if pd.notna(row['Volume']) else 0.0
                            })

                        await session.execute(insert(MarketData), records)
                        total_inserted += len(records)

                    await session.commit()
                    logger.info(f"Inserted {total_inserted} records for {symbol}/{timeframe}")
                    results["successful"] += 1

                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to process {filename}: {e}")
                    results["failed"] += 1

        return results

    async def run_full_population(self, dry_run: bool = False) -> Dict:
        """Run complete initial data population"""
        logger.info("Starting initial data population...")

        if dry_run:
            logger.info("DRY RUN MODE - No data will be inserted")

        results = {
            "strategies": {},
            "instruments": {},
            "market_data": {},
            "status": "success"
        }

        try:
            # 1. Populate strategies
            logger.info("Populating strategies...")
            if not dry_run:
                results["strategies"] = await self.populate_strategies()

            # 2. Populate instruments
            logger.info("Populating instruments...")
            if not dry_run:
                results["instruments"] = await self.populate_instruments()

            # 3. Populate market data
            logger.info("Populating market data...")
            if not dry_run:
                results["market_data"] = await self.populate_market_data(results["instruments"])

            logger.info("Initial data population completed successfully!")

        except Exception as e:
            logger.error(f"Initial data population failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)

        return results

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Initial Data Population for AlgoAgentX"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - validate but do not insert data'
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the population (default is dry run)'
    )

    args = parser.parse_args()

    # Determine execution mode
    if args.execute:
        dry_run = False
        logger.info("EXECUTION MODE: Data will be inserted into database")
    else:
        dry_run = True
        logger.info("DRY RUN MODE: Data will be validated but not inserted")

    # Initialize populator
    populator = InitialDataPopulator()

    try:
        # Run population
        results = await populator.run_full_population(dry_run=dry_run)

        # Print results
        logger.info("\n" + "="*60)
        logger.info("INITIAL DATA POPULATION RESULTS")
        logger.info("="*60)

        if results["status"] == "success":
            logger.info("✅ Population completed successfully!")
            if not dry_run:
                logger.info(f"Strategies created: {len(results['strategies'])}")
                logger.info(f"Instruments created: {len(results['instruments'])}")
                logger.info(f"Market data files processed: {results['market_data'].get('total_files', 0)}")
                logger.info(f"Successful: {results['market_data'].get('successful', 0)}")
                logger.info(f"Failed: {results['market_data'].get('failed', 0)}")
        else:
            logger.error("❌ Population failed")
            if "error" in results:
                logger.error(f"Error: {results['error']}")

        logger.info("="*60)

    finally:
        await populator.close()

if __name__ == "__main__":
    asyncio.run(main())