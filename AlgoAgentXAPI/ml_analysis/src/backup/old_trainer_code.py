# src/model_trainer.py
"""
python -m ml_analysis.src.model_trainer
"""

import pandas as pd
import os
import joblib
from datetime import date
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# 🔧 Set CPU fallback
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

# Setup paths
today_str = date.today().isoformat()

# NEW: Save models
MODEL_SAVE_DIR = os.path.join("ml_analysis", "data", "models")
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# NEW: Training data from today
PROCESSED_DATA_DIR = os.path.join("ml_analysis", "data", "processed_data", "tech_analysis_train")

def load_training_data():
    dfs = []
    if not os.path.exists(PROCESSED_DATA_DIR):
        raise FileNotFoundError(f"No technical data found for today: {PROCESSED_DATA_DIR}")

    for file in os.listdir(PROCESSED_DATA_DIR):
        if file.endswith("_indicators.csv"):
            df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, file))
            df["Ticker"] = file.split("_")[0]
            dfs.append(df)

    if not dfs:
        raise ValueError("No training files found in today's processed data folder.")
    
    return pd.concat(dfs, ignore_index=True)

def train_model():
    df = load_training_data()
    df["Target"] = df["Close"].shift(-3) > df["Close"]

    feature_cols = [
        "SMA_20", "EMA_20", "RSI", "MACD", "MACD_signal",
        "ADX", "CMF", "Supertrend", "Volume"
    ]
    df = df.dropna(subset=feature_cols + ["Target"])
    df["Supertrend"] = df["Supertrend"].astype(int)

    X = df[feature_cols]
    y = df["Target"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    models = {
        "randomforest": RandomForestClassifier(n_estimators=100, random_state=42),
        "xgboost": XGBClassifier(eval_metric='logloss', random_state=42, verbosity=0),
        "lightgbm": LGBMClassifier(random_state=42, verbose=-1)
    }

    best_model_name = None
    best_score = 0.0

    for name, model in models.items():
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        print(f"{name.capitalize()} Accuracy: {score:.4f}")

        model_path = os.path.join(MODEL_SAVE_DIR, f"{name}_model.pkl")
        joblib.dump(model, model_path)

        if score > best_score:
            best_score = score
            best_model_name = name

    print(f"🏆 Best Model: {best_model_name.capitalize()} with accuracy {best_score:.4f}")

    # Save the name of the best model in the same folder
    with open(os.path.join(MODEL_SAVE_DIR, "best_model.txt"), "w") as f:
        f.write(best_model_name)

if __name__ == "__main__":
    train_model()
