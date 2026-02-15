"""
python -m ml_analysis.src.bse_data_fetcher
"""

import os
import io
import requests
import pandas as pd
from datetime import datetime, timedelta

# Folder paths
RAW_DATA_DIR = os.path.join("ml_analysis", "data", "raw_data")
BHAVCOPY_DIR = os.path.join("ml_analysis", "data", "bhavcopy_store")
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(BHAVCOPY_DIR, exist_ok=True)

# Cache bhavcopies only once per session
bhavcopy_cache = {}

def get_bhavcopy_path(date: datetime) -> str:
    date_str = date.strftime("%Y-%m-%d")
    return os.path.join(BHAVCOPY_DIR, f"bhavcopy_{date_str}.csv")

def download_bhavcopy_if_needed(date: datetime) -> pd.DataFrame:
    """Download bhavcopy once and cache"""
    date_str = date.strftime("%Y-%m-%d")

    # 1. Check memory cache
    if date_str in bhavcopy_cache:
        return bhavcopy_cache[date_str]

    # 2. Check file cache
    file_path = get_bhavcopy_path(date)
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            bhavcopy_cache[date_str] = df
            print(f"✅ Bhavcopy loaded from disk: {file_path}")
            return df
        except Exception as e:
            print(f"⚠️ Failed to load bhavcopy from disk for {date_str}: {e}")
            return pd.DataFrame()

    # 3. Download
    date_url_str = date.strftime("%Y%m%d")
    url = f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{date_url_str}_F_0000.CSV"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx"
    }

    try:
        print(f"📥 Downloading bhavcopy for {date_str}")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.BytesIO(response.content))
            df["DATE"] = date_str
            df.to_csv(file_path, index=False)
            bhavcopy_cache[date_str] = df
            print(f"✅ Saved bhavcopy to disk: {file_path}")
            return df
        else:
            print(f"❌ Failed to download bhavcopy {date_str} (HTTP {response.status_code})")
    except Exception as e:
        print(f"⚠️ Error downloading bhavcopy for {date_str}: {e}")

    # Save empty in cache to avoid retrying in same run
    bhavcopy_cache[date_str] = pd.DataFrame()
    return pd.DataFrame()

def sync_stock_from_bhavcopy(stock_code: str, days: int = 90):
    """Update a single stock’s CSV from bhavcopies"""
    stock_path = os.path.join(RAW_DATA_DIR, f"{stock_code}.csv")

    if os.path.exists(stock_path) and os.path.getsize(stock_path) > 0:
        try:
            df_existing = pd.read_csv(stock_path)
            df_existing.columns = df_existing.columns.str.strip().str.replace('\ufeff', '')

            # Debug: Print column names
            print(f"📌 Columns in {stock_code}.csv: {df_existing.columns.tolist()}")

            if "Date" not in df_existing.columns:
                print(f"⚠️ Skipping {stock_code} – 'Date' column not found after header cleanup.")
                return

            df_existing["Date"] = pd.to_datetime(df_existing["Date"], errors="coerce")
            df_existing = df_existing.dropna(subset=["Date"])  # Ensure no NaT dates
            existing_dates = set(df_existing["Date"].dt.strftime("%Y-%m-%d"))

        except Exception as e:
            print(f"⚠️ Skipping {stock_code} due to read error: {e}")
            return
    else:
        df_existing = pd.DataFrame()
        existing_dates = set()

    new_rows = []

    for i in range(days):
        date = datetime.today() - timedelta(days=i)
        if date.weekday() >= 5:
            continue  # Skip weekends

        date_str = date.strftime("%Y-%m-%d")
        if date_str in existing_dates:
            print(f"⏩ Already have data for {stock_code} on {date_str}")
            continue

        df_bhav = download_bhavcopy_if_needed(date)
        if df_bhav.empty:
            continue

        # Detect format
        if "SC_CODE" in df_bhav.columns:
            df_filtered = df_bhav[df_bhav["SC_CODE"].astype(str) == stock_code]
            if df_filtered.empty:
                continue
            df_filtered = df_filtered.rename(columns={
                "SC_CODE": "Code",
                "SC_NAME": "Name",
                "OPEN": "Open",
                "HIGH": "High",
                "LOW": "Low",
                "CLOSE": "Close",
                "NO_OF_SHRS": "Volume",
                "NET_TURNOV": "Turnover",
                "DATE": "Date"
            })

        elif "FinInstrmId" in df_bhav.columns:
            df_filtered = df_bhav[df_bhav["FinInstrmId"].astype(str) == stock_code]
            if df_filtered.empty:
                continue
            df_filtered = df_filtered.rename(columns={
                "FinInstrmId": "Code",
                "FinInstrmNm": "Name",
                "OpnPric": "Open",
                "HghPric": "High",
                "LwPric": "Low",
                "ClsPric": "Close",
                "TtlTradgVol": "Volume",
                "TtlTrfVal": "Turnover",
                "DATE": "Date"
            })
        else:
            print(f"❌ Unknown bhavcopy format for {date_str}")
            continue

        # Final cleanup
        df_filtered = df_filtered[["Date", "Code", "Name", "Open", "High", "Low", "Close", "Volume", "Turnover"]]
        df_filtered["Date"] = pd.to_datetime(df_filtered["Date"], errors="coerce")
        df_filtered = df_filtered.dropna(subset=["Date"])
        new_rows.append(df_filtered)

    if new_rows:
        df_new = pd.concat(new_rows, ignore_index=True)
        if not df_existing.empty:
            df_existing["Date"] = pd.to_datetime(df_existing["Date"], errors="coerce")
            df_existing = df_existing.dropna(subset=["Date"])
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
        df_final.drop_duplicates(subset=["Date", "Code"], inplace=True)
        df_final.sort_values("Date", inplace=True)
        df_final.to_csv(stock_path, index=False)
        print(f"✅ Updated {stock_code}.csv with {len(df_new)} new rows")
    else:
        print(f"📌 No new data to update for {stock_code}")
        
if __name__ == "__main__":
    
    test_bse_stock = ["506734", "506808"]

    for ticker in test_bse_stock:
        sync_stock_from_bhavcopy(ticker)
