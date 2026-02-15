"""
python -m stock_news_analysis.main
"""

import os
import pandas as pd
from datetime import date
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from stock_news_analysis.analysis.extract_text_from_pdf import extract_text_from_bse_pdf, extract_text_from_nse_xml
from stock_news_analysis.analysis.clean_extracted_text import advanced_clean_extracted_text
# from stock_news_analysis.analysis.text_summarization import summarize_text
from stock_news_analysis.analysis.sentiment_analysis import analyze_sentiment
from stock_news_analysis.analysis.read_latest_csv import load_latest_data, load_new_data_to_process
from stock_news_analysis.analysis.data_save_csv import save_to_csv_after_sentiment
from utility.my_automation_logger import get_logger
from utility.debbuger_port_driver import get_driver
from stock_news_analysis.scraping_data_screener.csv_data_nse_annoucement_scrap import get_nse_annoucement_data
from stock_news_analysis.scraping_data_screener.full_day_nseindia_annoucement_stock import fetch_announcements, save_bse_scrap_data_to_csv
from stock_news_analysis.scraping_data_screener.chart_pattern_scrap import fetch_all_patterns_and_indicators
from stock_news_analysis.analysis.data_save_csv import save_to_csv_chart_ind
from ml_analysis.src.main import main as ml_analysis_main
from stock_news_analysis.analysis.read_latest_csv import load_latest_positive_data

logger = get_logger('screener_announcements')

def process_row(index, total, row):
    pdf_link = row.get("ATTACHMENT")
    company = row.get("SYMBOL", "Unknown")
    companyname = row.get("COMPANY NAME", "Unknown")
    headline = row.get("SUBJECT", "") or ""
    description = row.get("DETAILS", "") or ""
    time_str = row.get("BROADCAST DATE/TIME", "") or ""

    logger.info(f"📄 [{index}/{total}] Processing for company: {company}")

    combined_text = headline.strip()

    # Append description if it's present
    if description.strip():
        combined_text += " " + description.strip()

    # Try PDF extraction if link is available and it's a .pdf
    if pdf_link and pdf_link.lower().endswith(".pdf"):
        try:
            # logger.info(f"📥 Attempting PDF extraction from: {pdf_link}")
            pdf_text = extract_text_from_bse_pdf(pdf_link)

            if pdf_text and pdf_text.strip():
                clean_text = advanced_clean_extracted_text(pdf_text[400:5000])
                combined_text += " " + clean_text
            else:
                logger.warning(f"⚠️ PDF text empty or whitespace for: {pdf_link}")
        except Exception as e:
            logger.warning(f"⚠️ Error extracting from PDF {pdf_link}: {e}")

    try:
        if not combined_text.strip():
            logger.warning(f"⚠️ No usable text for sentiment for: {company}")
            return None
        
        sentiment_data = analyze_sentiment(combined_text)

        sentiment_scores = sentiment_data[0]
        final_sentiment = sentiment_data[1]

        vader_score = sentiment_scores.get('vader')
        textblob_score = sentiment_scores.get('textblob')
        bert_sentiment = sentiment_scores.get('transformer')
        confidence = sentiment_scores.get('confidence')

        if bert_sentiment is None:
            logger.warning(f"⚠️ Missing 'transformer' sentiment for {pdf_link}")
            return None

        return {
            "Company": company,
            "companyname": companyname,
            "Headline": headline,
            "Description": description,
            "Time": time_str,
            "pdf_link": pdf_link,
            "vader_score": vader_score,
            "textblob_score": textblob_score,
            "bert_sentiment": bert_sentiment,
            "confidence": confidence,
            "final_sentiment": final_sentiment
        }

    except Exception as e:
        logger.error(f"❌ Error processing combined sentiment for {company}: {e}")
        return None

def main(flag):
    try:
        df = load_new_data_to_process(flag)
        processed_rows = []
        failed_links = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            total = len(df)
            futures = {
                executor.submit(process_row, idx + 1, total, row): row
                for idx, (_, row) in enumerate(df.iterrows())
            }
            for future in as_completed(futures):
                result = future.result()
                row = futures[future]
                if result:
                    processed_rows.append(result)
                else:
                    failed_links.append(row.get("ATTACHMENT"))

        if processed_rows:
            save_to_csv_after_sentiment(processed_rows)
        else:
            logger.info("No valid PDFs were processed.")

    except Exception as e:
        logger.error(f"❌ Failed to read CSV or process data: {e}")

if __name__ == "__main__":
    start = time.time()
    flag = False
    driver = get_driver()
    # get_nse_annoucement_data(driver)

    # if flag:
    #     seen = set()
    #     data = fetch_announcements(driver, seen)
    #     save_bse_scrap_data_to_csv(data)
    # else:
    #     get_nse_annoucement_data(driver)

    time.sleep(3)  # Ensure data is downloaded before processing
    # import pdb; pdb.set_trace()  # Debugging breakpoint
    # main(flag)
    # time.sleep(1)

    df = load_latest_positive_data()
    time.sleep(0.5)
    data = fetch_all_patterns_and_indicators(driver, df, flag)

    save_to_csv_chart_ind(data)

    time.sleep(2)

    if flag:
        new_stock = df['Company'].astype(str).str.upper().str.strip()
        new_stock_list = new_stock.unique().tolist()  # Remove duplicates if any
    else:
        new_stock = df['Company'].astype(str).str.upper().str.strip() + ".NS"
        new_stock_list = new_stock.unique().tolist()  # Remove duplicates if any
        # new_stock_list = ["CREDITACC.NS", "BORANA.NS"]

    # ml_analysis_main(new_stock_list, flag)

    end = time.time()
    logger.info(f"✅ All New Data Processed in {end - start:.2f} seconds")
