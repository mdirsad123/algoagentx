"""
python -m ml_analysis.src.main
"""

import os
from datetime import datetime
from .data_fetcher import sync_stock_data
from .bse_data_fetcher import sync_stock_from_bhavcopy
from .technical_analysis import calculate_indicators_batch
from .model_trainer import train_model
from .model_predictor import predict_today_signals
# from ml_analysis.data.training_data.stokcs_name import news_stock


def main(nifty_stocks, flag= False):

    if not nifty_stocks:  # catches both [] and None
        print("⚠️ No stocks to process. Exiting pipeline.\n")
        return
    
    today = datetime.now().strftime("%d-%m-%Y")
    print(f"\n🚀 Stock Screener Pipeline Starting ({today})\n")

    # 1. Define tickers
    tickers = nifty_stocks

    # 2. Fetch & update stock data
    if flag:
        for code in tickers:
            if code.endswith(".NS"):
                sync_stock_data(code)  # NSE stocks
            else:
                sync_stock_from_bhavcopy(code)  # BSE stocks
    else:
        for ticker in tickers:
            sync_stock_data(ticker)
    

    # 3. Generate technical indicators
    calculate_indicators_batch(tickers)

    # 5. Train model on indicators
    # train_model()
    predict_today_signals()

    print("\n✅ Full pipeline complete.")

if __name__ == "__main__":

    new_stock_list = ["541154"]
    
    main(new_stock_list)

