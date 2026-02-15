# src/technical_analysis.py
"""
python -m ml_analysis.src.technical_analysis
"""

import pandas as pd
import ta
import os
from datetime import date

today_str = date.today().isoformat()

RAW_DATA_PATH = os.path.join("ml_analysis", "data", "raw_data")
PROCESSED_DATA_PATH = os.path.join("ml_analysis", "data", "processed_data", f"tech_analysis_{today_str}")
os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)

def calculate_indicators(ticker: str):
    """Load CSV and calculate technical indicators"""
    print(f"⏳ Processing {ticker}...")

    file_path = os.path.join(RAW_DATA_PATH, f"{ticker}.csv")
    if not os.path.exists(file_path):
        print(f"❌ Skipping {ticker} — raw file not found.")
        return

    df = pd.read_csv(file_path)

    # Safety checks
    if df.shape[0] < 20:
        print(f"⚠️ Skipping {ticker} — not enough rows ({df.shape[0]}) to calculate indicators.")
        return

    if df[["High", "Low", "Close"]].isnull().sum().sum() > 0:
        print(f"⚠️ Skipping {ticker} — missing High/Low/Close values.")
        return

    # Technical indicators
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["EMA_20"] = df["Close"].ewm(span=20).mean()
    df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"]).rsi()

    macd = ta.trend.MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    try:
        adx = ta.trend.ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"])
        df["ADX"] = adx.adx()
    except Exception as e:
        print(f"❌ ADX calculation failed for {ticker}: {e}")
        df["ADX"] = None

    try:
        cmf = ta.volume.ChaikinMoneyFlowIndicator(high=df["High"], low=df["Low"], close=df["Close"], volume=df["Volume"])
        df["CMF"] = cmf.chaikin_money_flow()
    except Exception as e:
        print(f"❌ CMF calculation failed for {ticker}: {e}")
        df["CMF"] = None

    # Supertrend
    def supertrend(df, period=10, multiplier=3):
        atr = ta.volatility.AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=period).average_true_range()
        hl2 = (df["High"] + df["Low"]) / 2
        upperband = hl2 + multiplier * atr
        lowerband = hl2 - multiplier * atr

        supertrend = [True] * len(df)
        for i in range(1, len(df)):
            if df["Close"][i] > upperband[i - 1]:
                supertrend[i] = True
            elif df["Close"][i] < lowerband[i - 1]:
                supertrend[i] = False
            else:
                supertrend[i] = supertrend[i - 1]
                if supertrend[i] and lowerband[i] < lowerband[i - 1]:
                    lowerband[i] = lowerband[i - 1]
                if not supertrend[i] and upperband[i] > upperband[i - 1]:
                    upperband[i] = upperband[i - 1]
        df["Supertrend"] = supertrend
        return df

    df = supertrend(df)

    # Save output
    out_path = os.path.join(PROCESSED_DATA_PATH, f"{ticker}_indicators.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Indicators saved for {ticker} at {out_path}")

def calculate_indicators_batch(tickers: list):
    for ticker in tickers:
        calculate_indicators(ticker)

if __name__ == "__main__":
    # Replace this list with dynamic news-based tickers
    new_stock_list = ["CREDITACC.NS", "BORANA.NS"]
    calculate_indicators_batch(new_stock_list)
