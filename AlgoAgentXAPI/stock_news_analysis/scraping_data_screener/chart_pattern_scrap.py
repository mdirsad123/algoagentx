"""
python -m stock_news_analysis.scraping_data_screener.chart_pattern_scrap
"""

import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from collections import defaultdict
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utility.debbuger_port_driver import get_driver
from utility.my_automation_logger import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from stock_news_analysis.analysis.read_latest_csv import load_latest_positive_data
from stock_news_analysis.analysis.data_save_csv import save_to_csv_chart_ind

# Configuration
logger = get_logger('screener_announcements')

# Common fetch function
def fetch_single_url(driver, companies, url, label):
    results = defaultdict(list)
    wait = WebDriverWait(driver, 10)
    short_wait = WebDriverWait(driver, 1)
    
    try:
        driver.get(url)
        print(f"Opened: {label} -> {url}")
        time.sleep(2)
        
        for company in companies:
            try:
                search_word = " ".join(company.split()[:2])
                # import pdb; pdb.set_trace()  # Debugging breakpoint
                search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search stocks here...']")))
                search_box.clear()
                search_box.send_keys(search_word)
                time.sleep(1)

                xpath_company = f"//a[starts-with(normalize-space(), '{search_word}')]"
                short_wait.until(EC.presence_of_element_located((By.XPATH, xpath_company)))
                results[company].append(label)
                print(f"✅ {company} -> {label}")
            except TimeoutException:
                continue
            except Exception as e:
                print(f"⚠️ {company} -> {label} ERROR: {e}")
                continue
    except Exception as e:
        print(f"❌ Error in {label} scraping: {e}")
    
    return results

def fetch_parallel_chartink(driver, companies, url_label_dict):
    all_results = defaultdict(list)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fetch_single_url, driver, companies, url, label): label
            for url, label in url_label_dict.items()
        }
        for future in as_completed(futures):
            result = future.result()
            for k, v in result.items():
                all_results[k].extend(v)
    return all_results

def fetch_all_patterns_and_indicators(driver, df, flag=False):
    # df = load_latest_positive_data()

    if df is None or df.empty:
        print("✅ No new positive sentiment data to process.")
        return pd.DataFrame()

    if 'Company' not in df.columns:
        print("❌ 'Company' column missing in the data.")
        return pd.DataFrame()

    if flag:
        if df['Company'].str.endswith(".NS").any():
            df['Company'] = df['Company'].str.replace('.NS', '', regex=False)
            companies = df['Company'].dropna().unique().tolist()
        else:
            companies = df['companyname'].dropna().unique().tolist()
    else:
        if df['Company'].str.endswith(".NS").any():
            df['Company'] = df['Company'].str.replace('.NS', '', regex=False)
            companies = df['Company'].dropna().unique().tolist()
        else:
            companies = df['Company'].dropna().unique().tolist()

    pattern_urls = {
        "https://chartink.com/screener/copy-cup-handle-breakout-pattern-with-high-volume": "Cup and Handle",
        "https://chartink.com/screener/daily-double-bottom": "Double Bottom",
        "https://chartink.com/screener/falling-wedge-pattern": "Falling Wedge",
        "https://chartink.com/screener/bull-flag-scanner": "Bull Flag",
        "https://chartink.com/screener/resistance-breakout-with-high-volume": "Resistance Breakout",
        "https://chartink.com/screener/volume-spike-daily": "Volume Spike",
        "https://chartink.com/screener/inverse-head-and-shoulders-6": "Inverse Head and Shoulders"
    }

    indicator_urls = {
        "https://chartink.com/screener/fii-dii-229": "Fill Dii buy >30cr",
        "https://chartink.com/screener/rsi-indicator": "RSI Signal",
        "https://chartink.com/screener/supertrend-screener": "Supertrend",
        "https://chartink.com/screener/adx-indicator": "ADX Signal",
        "https://chartink.com/screener/cmf-68": "CMF Signal",
        "https://chartink.com/screener/golden-cross-scan":"Golden Cross"
    }

    pattern_results = fetch_parallel_chartink(driver, companies, pattern_urls)
    indicator_results = fetch_parallel_chartink(driver, companies, indicator_urls)

    df['Chart_Pattern'] = df['Company'].apply(lambda x: ', '.join(pattern_results.get(x, [])))
    df['Fii_Dii_BUYING'] = df['Company'].apply(lambda x: ', '.join(indicator_results.get(x, [])))
    return df

if __name__ == "__main__":
    driver = get_driver()
    start = time.time()
    data = fetch_all_patterns_and_indicators(driver)
    # print(data)
    save_to_csv_chart_ind(data)
    end = time.time()
    logger.info(f"✅ All New Data Processed in {end - start:.2f} seconds")

    driver.quit()
