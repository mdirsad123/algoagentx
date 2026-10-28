from datetime import datetime, timedelta, timezone
import pandas as pd
from app.services.dynamic_strategy_loader import load_dynamic_strategy_class
from app.tools.check_live_incremental_parity import verify

SOURCE = '''
class Strategy:
    LIVE_INCREMENTAL_VERSION = 1
    def __init__(self, df):
        self.df = df.copy()
        self.closes = []
    def generate(self):
        df = self.df.copy()
        df["signal"] = (df["Close"] > df["Close"].rolling(3).mean()).astype(int)
        df["strategy_stop_loss"] = df["Low"] - 1
        df["strategy_target"] = df["High"] + 2
        return df
    def start_live_incremental(self, generated):
        self.closes = list(self.df["Close"].astype(float))
        return True
    def on_closed_candle(self, candle):
        self.closes.append(float(candle["Close"]))
        row = dict(candle)
        row["signal"] = int(len(self.closes) >= 3 and self.closes[-1] > sum(self.closes[-3:]) / 3)
        row["strategy_stop_loss"] = float(candle["Low"]) - 1
        row["strategy_target"] = float(candle["High"]) + 2
        return pd.DataFrame([row])
'''


def test_dynamic_strategy_parity_checker_uses_platform_loader():
    cls = load_dynamic_strategy_class(SOURCE)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    df = pd.DataFrame([dict(Date=start+timedelta(minutes=i*5), Open=100+i, High=102+i,
                            Low=99+i, Close=100+i+(i % 3), Volume=100) for i in range(24)])
    result = verify(cls, df, history_bars=10, checks=12, params={})
    assert result['pass'], result['checks']
