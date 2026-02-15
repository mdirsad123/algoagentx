"""
python -m ml_analysis.src.model_predictor
"""

import pandas as pd
import os
import joblib
from datetime import date

today_str = date.today().isoformat()

MODEL_DIR = os.path.join("ml_analysis", "data", "models")
PROCESSED_DATA_DIR = os.path.join("ml_analysis", "data", "processed_data", f"tech_analysis_{today_str}")
SIGNAL_DIR = os.path.join("ml_analysis", "data", "processed_data", "ml_signal")
SIGNAL_OUTPUT_PATH = os.path.join(SIGNAL_DIR, f"ml_signals_{today_str}.csv")

# Ensure output directory exists
os.makedirs(SIGNAL_DIR, exist_ok=True)

FEATURE_COLS = [
    "SMA_20", "EMA_20", "RSI", "MACD", "MACD_signal",
    "ADX", "CMF", "Supertrend", "Volume"
]

def load_best_model():
    best_model_file = os.path.join(MODEL_DIR, "best_model.txt")
    if not os.path.exists(best_model_file):
        raise FileNotFoundError("Missing best_model.txt. Run model_trainer.py first.")

    with open(best_model_file, "r") as f:
        model_name = f.read().strip()

    model_path = os.path.join(MODEL_DIR, f"{model_name}_model.pkl")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Expected model file not found: {model_path}")

    print(f"✅ Loaded best model: {model_name}")
    return joblib.load(model_path)

def predict_today_signals():
    model = load_best_model()
    results = []

    for file in os.listdir(PROCESSED_DATA_DIR):
        if file.endswith("_indicators.csv"):
            ticker = file.split("_")[0]
            df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, file))
            df = df.dropna(subset=FEATURE_COLS)

            if df.empty:
                continue

            latest = df.iloc[-1]
            if isinstance(latest["Supertrend"], bool):
                latest["Supertrend"] = int(latest["Supertrend"])

            X = pd.DataFrame([latest[FEATURE_COLS]])
            pred = model.predict(X)[0]
            proba = model.predict_proba(X)[0][1]  # Confidence for class "1" (STRONG BUY)

            results.append({
                "Ticker": ticker,
                "ML_Prediction": "STRONG BUY" if pred else "HOLD / SELL",
                "ML_Confidence": round(proba, 4)
            })

    pd.DataFrame(results).to_csv(SIGNAL_OUTPUT_PATH, index=False)
    print(f"📈 Signals saved to: {SIGNAL_OUTPUT_PATH}")

if __name__ == "__main__":
    predict_today_signals()
