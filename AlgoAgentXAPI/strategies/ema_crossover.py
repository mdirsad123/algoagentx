import pandas as pd
import numpy as np


class EMACrossover:
    def __init__(self, df, rr_ratio=2.0):
        self.df = df.copy()
        self.rr_ratio = rr_ratio

    def generate(self):
        df = self.df.copy()

        # Calculate EMAs
        df['ema_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()

        # Generate signals
        df['Position'] = 0

        # Long signal: EMA 9 crosses above EMA 20
        long_condition = (df['ema_9'] > df['ema_20']) & (df['ema_9'].shift(1) <= df['ema_20'].shift(1))
        df.loc[long_condition, 'Position'] = 1

        # Short signal: EMA 9 crosses below EMA 20
        short_condition = (df['ema_9'] < df['ema_20']) & (df['ema_9'].shift(1) >= df['ema_20'].shift(1))
        df.loc[short_condition, 'Position'] = -1

        return df