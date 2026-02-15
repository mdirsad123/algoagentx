"""
python -m ml_analysis.src.train_main
"""

from ml_analysis.data.training_data.stokcs_name import nse_stock, bse_stock
from .data_fetcher import sync_stock_data
from .bse_data_fetcher import sync_stock_from_bhavcopy
from .train_technical_analysis import calculate_indicators_batch
from .model_trainer import train_model

def main():
    """
    Main function to run the stock screener pipeline.
    Fetches stock data, calculates technical indicators, and trains the model.
    """
    if not nse_stock and not bse_stock:
        print("⚠️ No stocks to process. Exiting pipeline.\n")
        return

    print("\n🚀 Stock Screener Pipeline Starting\n")

    # 1. Fetch & update NSE stock data
    for ticker in nse_stock:
        sync_stock_data(ticker)

    # 2. Fetch & update BSE stock data
    for ticker in bse_stock:
        sync_stock_from_bhavcopy(ticker)

    # 3. Combine all stock symbols for technical indicator calculation
    tickers = nse_stock + bse_stock  # Combine both lists

    # 4. Generate technical indicators
    calculate_indicators_batch(tickers)

    # 5. Train model
    train_model()

    print("\n✅ Full pipeline complete.")

if __name__ == "__main__":
    main()
