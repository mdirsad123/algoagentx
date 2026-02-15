#!/usr/bin/env python3
"""
CSV to PostgreSQL Migration Script for AlgoAgentX

This script provides a safe, idempotent way to ingest historical market data
from CSV files into the PostgreSQL database.

USAGE:
    python scripts/csv_to_postgres_migration.py --help

FEATURES:
- Manual trigger only (not part of API)
- Chunked inserts for large files
- Validation checks
- Idempotent operations (no duplicates)
- Logging without frontend exposure
- Instrument and timeframe auto-detection

EXAMPLE:
    python scripts/csv_to_postgres_migration.py \
        --csv-path "data/raw/BTCUSD_5M_1Year.csv" \
        --instrument-symbol "BTCUSD" \
        --exchange "BINANCE" \
        --market "CRYPTO" \
        --timeframe "5m" \
        --dry-run

    python scripts/csv_to_postgres_migration.py \
        --csv-path "data/raw/NIFTY_5M_1Year.csv" \
        --instrument-symbol "NIFTY" \
        --exchange "NSE" \
        --market "INDIA" \
        --timeframe "5m" \
        --execute
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.models import Instrument, MarketData
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CSVMarketDataIngestor:
    """Safe CSV to PostgreSQL market data ingestion"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.database_url
        self.engine = create_async_engine(self.db_url)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

    async def get_or_create_instrument(
        self, symbol: str, exchange: str, market: str,
        instrument_type: str = "INDEX", tick_size: float = 0.01,
        lot_size: int = 1
    ) -> Instrument:
        """
        Get existing instrument or create new one.
        Idempotent operation - won't create duplicates.
        """
        async with self.async_session() as session:
            # Check if instrument already exists
            result = await session.execute(
                select(Instrument).where(
                    Instrument.symbol == symbol,
                    Instrument.exchange == exchange
                )
            )
            instrument = result.scalar_one_or_none()

            if instrument:
                logger.info(f"Instrument found: {symbol} ({instrument.id})")
                return instrument

            # Create new instrument
            logger.info(f"Creating new instrument: {symbol}")
            new_instrument = Instrument(
                symbol=symbol,
                exchange=exchange,
                market=market,
                instrument_type=instrument_type,
                tick_size=tick_size,
                lot_size=lot_size
            )

            session.add(new_instrument)
            await session.commit()
            await session.refresh(new_instrument)

            logger.info(f"Created instrument: {symbol} (ID: {new_instrument.id})")
            return new_instrument

    def _validate_csv_structure(self, df: pd.DataFrame) -> bool:
        """Validate CSV has required columns"""
        required_columns = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
        actual_columns = set(df.columns)

        if not required_columns.issubset(actual_columns):
            missing = required_columns - actual_columns
            logger.error(f"CSV missing required columns: {missing}")
            return False

        return True

    def _clean_and_prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare CSV data for database insertion"""
        # Make a copy to avoid modifying original
        df = df.copy()

        # Convert Date to datetime and make timezone-aware
        df['Date'] = pd.to_datetime(df['Date'], utc=True)

        # Ensure numeric columns
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Drop rows with NaN values
        df = df.dropna()

        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)

        return df

    async def _check_existing_data(
        self, session: AsyncSession, instrument_id: int,
        timeframe: str, start_date: datetime, end_date: datetime
    ) -> bool:
        """Check if data already exists for this instrument/timeframe/period"""
        result = await session.execute(
            select(MarketData).where(
                MarketData.instrument_id == instrument_id,
                MarketData.timeframe == timeframe,
                MarketData.timestamp >= start_date,
                MarketData.timestamp <= end_date
            ).limit(1)
        )

        return result.scalar_one_or_none() is not None

    async def ingest_csv_data(
        self, csv_path: str, instrument_id: int,
        timeframe: str, chunk_size: int = 1000,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """
        Ingest CSV data into PostgreSQL with chunked inserts

        Returns:
            (success_count, total_records)
        """
        try:
            # Read CSV
            logger.info(f"Reading CSV: {csv_path}")
            df = pd.read_csv(csv_path)

            if not self._validate_csv_structure(df):
                return 0, 0

            # Clean and prepare data
            df = self._clean_and_prepare_data(df)

            if df.empty:
                logger.warning("No valid data after cleaning")
                return 0, 0

            total_records = len(df)
            logger.info(f"Processing {total_records} records")

            if dry_run:
                logger.info("DRY RUN: Would process data but not insert")
                return 0, total_records

            # Check if data already exists
            start_date = df['Date'].min()
            end_date = df['Date'].max()

            async with self.async_session() as session:
                if await self._check_existing_data(session, instrument_id, timeframe, start_date, end_date):
                    logger.warning(f"Data already exists for {instrument_id}/{timeframe} from {start_date} to {end_date}")
                    return 0, total_records

                # Process in chunks
                success_count = 0
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i + chunk_size]

                    # Prepare data for insertion
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

                    try:
                        # Use bulk insert
                        await session.execute(insert(MarketData), records)
                        success_count += len(records)
                        logger.info(f"Inserted chunk {i//chunk_size + 1}: {len(records)} records")

                    except IntegrityError as e:
                        await session.rollback()
                        logger.error(f"Integrity error in chunk {i//chunk_size + 1}: {e}")
                        continue
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Error in chunk {i//chunk_size + 1}: {e}")
                        continue

                await session.commit()
                logger.info(f"Successfully inserted {success_count}/{total_records} records")
                return success_count, total_records

        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            return 0, 0

    async def auto_detect_and_ingest(
        self, csv_path: str, instrument_symbol: str,
        exchange: str, market: str, timeframe: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Auto-detect instrument and ingest data

        Returns:
            {
                'instrument_id': int,
                'total_records': int,
                'success_count': int,
                'status': 'success'|'partial'|'failed'
            }
        """
        try:
            # Get or create instrument
            instrument = await self.get_or_create_instrument(
                symbol=instrument_symbol,
                exchange=exchange,
                market=market
            )

            # Ingest CSV data
            success_count, total_records = await self.ingest_csv_data(
                csv_path=csv_path,
                instrument_id=instrument.id,
                timeframe=timeframe,
                dry_run=dry_run
            )

            if success_count == total_records:
                status = 'success'
            elif success_count > 0:
                status = 'partial'
            else:
                status = 'failed'

            return {
                'instrument_id': instrument.id,
                'instrument_symbol': instrument_symbol,
                'total_records': total_records,
                'success_count': success_count,
                'status': status,
                'timeframe': timeframe
            }

        except Exception as e:
            logger.error(f"Auto ingestion failed: {e}")
            return {
                'instrument_id': None,
                'instrument_symbol': instrument_symbol,
                'total_records': 0,
                'success_count': 0,
                'status': 'failed',
                'timeframe': timeframe,
                'error': str(e)
            }

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="CSV to PostgreSQL Market Data Migration for AlgoAgentX"
    )

    parser.add_argument(
        '--csv-path',
        type=str,
        required=True,
        help='Path to CSV file containing market data'
    )

    parser.add_argument(
        '--instrument-symbol',
        type=str,
        required=True,
        help='Instrument symbol (e.g., BTCUSD, NIFTY)'
    )

    parser.add_argument(
        '--exchange',
        type=str,
        required=True,
        help='Exchange name (e.g., BINANCE, NSE)'
    )

    parser.add_argument(
        '--market',
        type=str,
        required=True,
        choices=['INDIA', 'CRYPTO', 'FOREX'],
        help='Market type'
    )

    parser.add_argument(
        '--timeframe',
        type=str,
        required=True,
        choices=['5m', '15m', '1h', '1d'],
        help='Timeframe of the data'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - validate but do not insert data'
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the migration (default is dry run)'
    )

    args = parser.parse_args()

    # Validate CSV path
    if not os.path.exists(args.csv_path):
        logger.error(f"CSV file not found: {args.csv_path}")
        sys.exit(1)

    # Determine execution mode
    if args.execute:
        dry_run = False
        logger.info("EXECUTION MODE: Data will be inserted into database")
    else:
        dry_run = True
        logger.info("DRY RUN MODE: Data will be validated but not inserted")

    # Initialize ingestor
    ingestor = CSVMarketDataIngestor()

    try:
        # Run migration
        result = await ingestor.auto_detect_and_ingest(
            csv_path=args.csv_path,
            instrument_symbol=args.instrument_symbol,
            exchange=args.exchange,
            market=args.market,
            timeframe=args.timeframe,
            dry_run=dry_run
        )

        # Print results
        logger.info("\n" + "="*50)
        logger.info("MIGRATION RESULTS")
        logger.info("="*50)
        logger.info(f"Instrument: {result['instrument_symbol']}")
        logger.info(f"Timeframe: {result['timeframe']}")
        logger.info(f"Total Records: {result['total_records']}")
        logger.info(f"Success Count: {result['success_count']}")
        logger.info(f"Status: {result['status']}")
        logger.info("="*50)

        if result['status'] == 'success':
            logger.info("✅ Migration completed successfully!")
        elif result['status'] == 'partial':
            logger.warning("⚠️  Partial migration - some records may have failed")
        else:
            logger.error("❌ Migration failed")

        if 'error' in result:
            logger.error(f"Error: {result['error']}")

    finally:
        await ingestor.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())