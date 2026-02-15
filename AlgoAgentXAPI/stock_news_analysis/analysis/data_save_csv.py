"""
python -m stock_news_analysis.analysis.data_save_csv
"""

import os
import sys
import pandas as pd
from datetime import date
from pathlib import Path
from utility.my_automation_logger import get_logger

logger = get_logger('Saved_csv_of_after_sentiment_analysis')

today_str = date.today().isoformat()
CSV_FILE = Path(__file__).resolve().parent.parent / "output" / f"process_sentiment_anaylsis_{today_str}.csv"
CSV_FILE_CHART_IND = Path(__file__).resolve().parent.parent / "output" / "chart_pattern_detect" / f"chart_pattern_{today_str}.csv"
FINAL_EXECUTED_STOCK = Path(__file__).resolve().parent.parent / "output" / "fianl_result_stock" / f"fianl_recomendation_stock_{today_str}.csv"


def save_to_csv_after_sentiment(new_data):
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    columns = ["Company", "companyname", "Headline", "Description", "Time", "pdf_link", "vader_score", "textblob_score", "bert_sentiment", "confidence", "final_sentiment"]

    if CSV_FILE.exists() and CSV_FILE.stat().st_size > 0:
        try:
            old_df = pd.read_csv(CSV_FILE)
            old_links = set(old_df["pdf_link"])
        except Exception as e:
            logger.warning(f"⚠️ Failed to read existing CSV: {e}")
            old_links = set()
            old_df = pd.DataFrame(columns=columns)

        new_entries = [row for row in new_data if row["pdf_link"] not in old_links]
        if new_entries:
            pd.DataFrame(new_entries).to_csv(CSV_FILE, mode='a', header=False, index=False)
            logger.info(f"✅ Appended {len(new_entries)} new rows.")
        else:
            logger.info("ℹ️ No new announcements.")
    else:
        pd.DataFrame(new_data, columns=columns).to_csv(CSV_FILE, index=False)
        logger.info(f"✅ Created new CSV with {len(new_data)} entries: {CSV_FILE.name}")

def save_to_csv_chart_ind(df):
    CSV_FILE_CHART_IND.parent.mkdir(parents=True, exist_ok=True)

    try:
        if CSV_FILE_CHART_IND.exists() and CSV_FILE_CHART_IND.stat().st_size > 0:
            df_existing = pd.read_csv(CSV_FILE_CHART_IND)
            df_combined = pd.concat([df_existing, df], ignore_index=True)
            df_combined.drop_duplicates(subset=["Company", "Headline", "Chart_Pattern", "Fii_Dii_BUYING"], keep="last", inplace=True)
            df_combined.to_csv(CSV_FILE_CHART_IND, index=False)
            logger.info(f"✅ Updated existing CSV with {len(df)} new/updated rows: {CSV_FILE_CHART_IND.name}")
        else:
            df.to_csv(CSV_FILE_CHART_IND, index=False)
            logger.info(f"✅ Created new CSV with {len(df)} rows: {CSV_FILE_CHART_IND.name}")
    except Exception as e:
        logger.error(f"❌ Error saving CSV: {e}")

def save_to_csv_final_result(df):
    FINAL_EXECUTED_STOCK.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "Company", "Annoucement_Time", "Final_Sentiment",
        "Chart_Pattern", "ML_Prediction", "ML_Confidence", "Success_Chance", "Trade_Execute_Or_Not", "Fii_Dii_BUYING"
    ]

    try:
        # Filter to only required columns in case df has extra
        df = df[columns]

        if FINAL_EXECUTED_STOCK.exists() and FINAL_EXECUTED_STOCK.stat().st_size > 0:
            df_existing = pd.read_csv(FINAL_EXECUTED_STOCK)
            df_combined = pd.concat([df_existing, df], ignore_index=True)
            df_combined.drop_duplicates(
                subset=["Company", "Annoucement_Time", "Chart_Pattern"],
                keep="last",
                inplace=True
            )
            df_combined.to_csv(FINAL_EXECUTED_STOCK, index=False)
            logger.info(f"✅ Updated final result CSV with {len(df)} new/updated rows: {FINAL_EXECUTED_STOCK.name}")
        else:
            df.to_csv(FINAL_EXECUTED_STOCK, index=False)
            logger.info(f"✅ Created new final result CSV with {len(df)} rows: {FINAL_EXECUTED_STOCK.name}")
    except Exception as e:
        logger.error(f"❌ Error saving final result CSV: {e}")

def update_trade_execution_status(company_name):
    output_dir = os.path.join("stock_news_analysis", "output", "fianl_result_stock")
    if not os.path.exists(output_dir):
        print("❌ Output folder not found.")
        return False

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        print("❌ No CSV files found.")
        return False

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    full_path = os.path.join(output_dir, latest_file)

    try:
        df = pd.read_csv(full_path)

        # Normalize
        df['Company'] = df['Company'].astype(str).str.strip()
        df['Trade_Execute_Or_Not'] = df['Trade_Execute_Or_Not'].astype(str).str.strip().str.lower()

        # Find company where not yet executed
        mask = (df['Company'] == company_name.strip()) & (df['Trade_Execute_Or_Not'] == "no")

        if df[mask].empty:
            print(f"⚠️ Already executed or company not found: {company_name}")
            return False

        # Update status to 'yes'
        df.loc[mask, 'Trade_Execute_Or_Not'] = "yes"
        df.to_csv(full_path, index=False)

        print(f"✅ Trade marked as executed for: {company_name}")
        return True

    except Exception as e:
        print(f"❌ Failed to update execution status: {e}")
        return False
    
if __name__ == "__main__":
    company_name = 'ICICIGI'
    # save_to_csv_after_sentiment(data)
    print(update_trade_execution_status(company_name))