"""
Docstring for strategies.stock_burner_ema_9_20

✅ Strategy Logic (Codable & Realistic)
🔹 Trend Filter (200 EMA)

LONG only if Close > EMA200

SHORT only if Close < EMA200

🔹 Setup (EMA 9 / EMA 20 Crossover)

Bullish

EMA 9 crosses above EMA 20

Bearish

EMA 9 crosses below EMA 20

🔹 Entry Confirmation (Stock Burner style)

Entry candle must close in crossover direction

Candle body ≥ 50% of full candle (strong momentum)

Optional: Volume > 20-period average (optional toggle)

🔹 Stop Loss (Clean & Logical)

LONG → SL = recent swing low (last N candles)

SHORT → SL = recent swing high

🔹 Target

Fixed Risk : Reward (already supported by your engine)

Default: 1:2
"""
import pandas as pd
import numpy as np

class StockBurnerEMA920:
    """
    Stock Burner Influencer EMA Strategy
    Engine-compatible version
    """

    def __init__(self, df: pd.DataFrame, rr_ratio=2):
        self.df = df.copy()
        self.rr_ratio = rr_ratio

    def generate(self):
        df = self.df

        # -----------------------------
        # Indicators
        # -----------------------------
        df["ema_9"] = df["Close"].ewm(span=9, adjust=False).mean()
        df["ema_20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["ema_200"] = df["Close"].ewm(span=200, adjust=False).mean()

        # Candle strength
        df["body"] = abs(df["Close"] - df["Open"])
        df["range"] = df["High"] - df["Low"]
        df["body_ratio"] = df["body"] / df["range"]

        # -----------------------------
        # REQUIRED BY ENGINE
        # -----------------------------
        df["Position"] = 0   # 🔥 THIS FIXES YOUR ERROR

        for i in range(201, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]

            # -------- LONG --------
            if (
                prev["ema_9"] < prev["ema_20"]
                and curr["ema_9"] > curr["ema_20"]
                and curr["Close"] > curr["ema_200"]
                and curr["Close"] > curr["Open"]
                and curr["body_ratio"] >= 0.5
            ):
                df.at[df.index[i], "Position"] = 1

            # -------- SHORT --------
            elif (
                prev["ema_9"] > prev["ema_20"]
                and curr["ema_9"] < curr["ema_20"]
                and curr["Close"] < curr["ema_200"]
                and curr["Close"] < curr["Open"]
                and curr["body_ratio"] >= 0.5
            ):
                df.at[df.index[i], "Position"] = -1

        return df
