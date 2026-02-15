"""
python -m ml_analysis.src.model_trainer
"""


# src/model_trainer.py
import pandas as pd
import os
import joblib
from datetime import date
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import warnings
warnings.filterwarnings("ignore")

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
today_str = date.today().isoformat()

MODEL_SAVE_DIR = os.path.join("ml_analysis", "data", "models")
PROCESSED_DATA_DIR = os.path.join("ml_analysis", "data", "processed_data", "tech_analysis_train")
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

def load_training_data():
    dfs = []
    if not os.path.exists(PROCESSED_DATA_DIR):
        raise FileNotFoundError(f"No data at {PROCESSED_DATA_DIR}")
    for file in os.listdir(PROCESSED_DATA_DIR):
        if file.endswith("_indicators.csv"):
            df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, file))
            df["Ticker"] = file.split("_")[0]
            dfs.append(df)
    if not dfs:
        raise ValueError("No *_indicators.csv files found.")
    return pd.concat(dfs, ignore_index=True)

def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred)
    }

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
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    model_defs = {
        "randomforest": (
            RandomForestClassifier(random_state=42),
            {
                "n_estimators": [100, 150],
                "max_depth": [5, 10, None]
            }
        ),
        "xgboost": (
            XGBClassifier(eval_metric="logloss", use_label_encoder=False, random_state=42),
            {
                "n_estimators": [100],
                "max_depth": [3, 5],
                "learning_rate": [0.05, 0.1]
            }
        ),
        "lightgbm": (
            LGBMClassifier(random_state=42),
            {
                "n_estimators": [100],
                "num_leaves": [15, 31],
                "learning_rate": [0.05, 0.1]
            }
        )
    }

    best_model = None
    best_model_name = None
    best_f1 = 0.0

    for name, (model, param_grid) in model_defs.items():
        print(f"\n🔍 Tuning {name.upper()} with GridSearchCV...")
        clf = GridSearchCV(model, param_grid, cv=5, scoring="f1", n_jobs=-1)
        clf.fit(X_train, y_train)
        best_estimator = clf.best_estimator_
        scores = evaluate_model(best_estimator, X_test, y_test)

        print(f"📊 {name.upper()} Metrics:")
        for metric, value in scores.items():
            print(f"   {metric.capitalize()}: {value:.4f}")

        model_path = os.path.join(MODEL_SAVE_DIR, f"{name}_model.pkl")
        joblib.dump(best_estimator, model_path)

        if scores["f1"] > best_f1:
            best_f1 = scores["f1"]
            best_model = best_estimator
            best_model_name = name

    print(f"\n🏆 Best Model: {best_model_name.upper()} with F1 score: {best_f1:.4f}")
    with open(os.path.join(MODEL_SAVE_DIR, "best_model.txt"), "w") as f:
        f.write(best_model_name)

if __name__ == "__main__":
    train_model()
