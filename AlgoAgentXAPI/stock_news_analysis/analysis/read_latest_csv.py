"""
python stock_news_analysis/analysis/read_latest_csv.py
"""

import pandas as pd
import os
from datetime import date

def load_latest_data():
    """Load the latest CSV file from the output directory and filter by datetime range."""
    # output_dir = os.path.join("stock_news_analysis", "output", "chart_pattern_detect")
    output_dir = os.path.join("stock_news_analysis", "input")
    if not os.path.exists(output_dir):
        return None

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        return None

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    df = pd.read_csv(os.path.join(output_dir, latest_file))

    return df

def load_latest_positive_data():
    """Load latest input sentiment file and return only new, positive rows not yet saved in today's chart_pattern file."""
    
    input_dir = os.path.join("stock_news_analysis", "output")  # input is from output sentiment file
    output_dir = os.path.join("stock_news_analysis", "output", "chart_pattern_detect")

    if not os.path.exists(input_dir):
        return None

    # Get latest sentiment file
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    if not input_files:
        return None

    latest_input_file = max(input_files, key=lambda x: os.path.getctime(os.path.join(input_dir, x)))
    input_path = os.path.join(input_dir, latest_input_file)
    input_df = pd.read_csv(input_path)

    # Filter positive sentiment rows first
    input_df = input_df[input_df["final_sentiment"].isin(["Positive", "Very Positive"])]

    if input_df.empty:
        return None

    # Normalize date field for consistent comparison
    input_df['Time'] = input_df['Time'].astype(str)

    # Columns to compare
    compare_columns = ["Company", "Headline", "Description", "Time", "pdf_link"]

    # Today's chart pattern file
    today_str = date.today().isoformat()
    output_file = os.path.join(output_dir, f"chart_pattern_{today_str}.csv")

    # If output doesn't exist yet, return all input_df
    if not os.path.exists(output_file):
        return input_df

    output_df = pd.read_csv(output_file)
    output_df['Time'] = output_df['Time'].astype(str)

    # Merge input vs output to detect unprocessed rows
    merged_df = pd.merge(
        input_df,
        output_df[compare_columns],
        how="left",
        on=compare_columns,
        indicator=True
    )

    new_positive_df = merged_df[merged_df["_merge"] == "left_only"].drop(columns=["_merge"])

    return new_positive_df

def load_latest_data_output_sentiment():
    """Load the latest CSV file from the output directory and filter by datetime range."""
    # output_dir = os.path.join("stock_news_analysis", "output", "chart_pattern_detect")
    output_dir = os.path.join("stock_news_analysis", "output")
    if not os.path.exists(output_dir):
        return None

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        return None

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    df = pd.read_csv(os.path.join(output_dir, latest_file))

    return df

def load_latest_data_output_chart_ind():
    """Load the latest CSV file from the output directory and filter by datetime range."""
    output_dir = os.path.join("stock_news_analysis", "output", "chart_pattern_detect")
    if not os.path.exists(output_dir):
        return None

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        return None

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    file_path = os.path.join(output_dir, latest_file)
    
    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        return None
        
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return None
        return df
    except pd.errors.EmptyDataError:
        return None
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def load_new_data_to_process(flag: bool):
    # Choose correct input directory based on flag
    if flag:
        input_dir = os.path.join("stock_news_analysis", "output", "get_data_bse_scrap") # for bse scrap data
    else:
        input_dir = os.path.join("stock_news_analysis", "input") # for nse scrap data

    output_dir = os.path.join("stock_news_analysis", "output")

    if not os.path.exists(input_dir):
        return None

    # Find latest input CSV
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    if not input_files:
        return None

    latest_input_file = max(input_files, key=lambda x: os.path.getctime(os.path.join(input_dir, x)))
    input_path = os.path.join(input_dir, latest_input_file)
    input_df = pd.read_csv(input_path)

    # Normalize column names
    input_df.columns = [col.strip().upper() for col in input_df.columns]

    # Convert date column
    input_df['BROADCAST DATE/TIME'] = input_df['BROADCAST DATE/TIME'].astype(str)

    # Prepare today’s output file
    today_str = date.today().isoformat()
    output_file = os.path.join(output_dir, f"process_sentiment_anaylsis_{today_str}.csv")

    if not os.path.exists(output_file):
        return input_df  # No output yet, return all

    # Read existing output and normalize
    output_df = pd.read_csv(output_file)
    output_df.columns = [col.strip().upper() for col in output_df.columns]

    # Rename columns to match input_df structure
    output_df.rename(columns={
        "COMPANY": "SYMBOL",  # in case of old format
        "COMPANY NAME": "SYMBOL",
        "HEADLINE": "SUBJECT",
        "DESCRIPTION": "DETAILS",
        "TIME": "BROADCAST DATE/TIME",
        "PDF_LINK": "ATTACHMENT"
    }, inplace=True)

    output_df['BROADCAST DATE/TIME'] = output_df['BROADCAST DATE/TIME'].astype(str)

    # Define compare columns
    compare_columns = ["SYMBOL", "SUBJECT", "DETAILS", "BROADCAST DATE/TIME", "ATTACHMENT"]

    # Merge to get only new rows
    merged_df = pd.merge(
        input_df,
        output_df[compare_columns],
        on=compare_columns,
        how='left',
        indicator=True
    )

    new_data_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    return new_data_df

def read_final_result_to_trade_execute():
    output_dir = os.path.join("stock_news_analysis", "output", "fianl_result_stock")
    if not os.path.exists(output_dir):
        return None

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        return None

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    df = pd.read_csv(os.path.join(output_dir, latest_file))

    return df

def read_ml_signal_data():
    output_dir = os.path.join("ml_analysis", "data", "processed_data", "ml_signal")
    if not os.path.exists(output_dir):
        return None

    files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    if not files:
        return None

    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    df = pd.read_csv(os.path.join(output_dir, latest_file))

    return df

if __name__ == "__main__":
    data_df = load_latest_positive_data()
    print("Latest Data Loaded:", data_df)