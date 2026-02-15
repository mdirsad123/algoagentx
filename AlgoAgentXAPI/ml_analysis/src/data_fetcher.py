"""
python -m ml_analysis.src.data_fetcher
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

RAW_DATA_PATH = os.path.join("ml_analysis", "data", "raw_data")
os.makedirs(RAW_DATA_PATH, exist_ok=True)

def sync_stock_data(ticker: str, interval: str = "1d", lookback: str = "3mo"):
    """Fetch or update stock data intelligently"""
    file_path = os.path.join(RAW_DATA_PATH, f"{ticker}.csv")

    try:
        if os.path.exists(file_path):
            df_existing = pd.read_csv(file_path, parse_dates=["Date"])
            df_existing.sort_values("Date", inplace=True)
            last_date = df_existing["Date"].max().date()

            today = datetime.today().date()
            if last_date >= today:
                print(f"✅ {ticker} already up to date.")
                return

            # Fetch from day after last date till today
            start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df_new = yf.Ticker(ticker).history(start=start_date, interval=interval)
            if df_new.empty:
                print(f"⚠️ No new data for {ticker}")
                return

            df_new.reset_index(inplace=True)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.drop_duplicates(subset="Date", inplace=True)
            df_combined.to_csv(file_path, index=False)
            print(f"🔄 Updated data for {ticker} with new rows: {len(df_new)}")

        else:
            df = yf.Ticker(ticker).history(period=lookback, interval=interval)
            df.reset_index(inplace=True)
            df.to_csv(file_path, index=False)
            print(f"📥 Fetched new data for {ticker} over {lookback}")

    except Exception as e:
        print(f"❌ Error syncing {ticker}: {e}")

if __name__ == "__main__":
    # us_stocks = [
    #     "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META"
    # ]
    nifty_stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
    for ticker in nifty_stocks:
        sync_stock_data(ticker)
