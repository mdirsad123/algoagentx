"""
python -m stock_news_analysis.scraping_data_screener.csv_data_nse_annoucement_scrap
"""

import os
import time
import pyautogui
from datetime import date
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utility.debbuger_port_driver import get_driver
from utility.my_automation_logger import get_logger

logger = get_logger('download_nse_announcements')
today_str = date.today().isoformat()

# Set correct normalized path
module_dir = os.path.dirname(__file__)
base_dir = os.path.dirname(os.path.dirname(module_dir))  # Go up two levels

# Generate final path for saving CSV
download_dir = os.path.normpath(os.path.join(base_dir, "stock_news_analysis", "input"))
download_filename = f"nse_csv_data_{today_str}.csv"
download_path = os.path.join(download_dir, download_filename)

# Ensure directory exists
os.makedirs(download_dir, exist_ok=True)
logger.info(f"📁 Ensured download directory exists: {download_dir}")

def get_nse_annoucement_data(driver):
    URL = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
    wait = WebDriverWait(driver, 30)
    driver.get(URL)
    logger.info("🚀 Opened NSE India announcement page")

    display_date = date.today().strftime("%d-%m-%Y")

    # STEP 1: Click "Custom" filter
    custom_button_xpath = "//li[@class='customFilter']/a[@data-val='Custom']"
    custom_button = wait.until(EC.presence_of_element_located((By.XPATH, custom_button_xpath)))
    driver.execute_script("arguments[0].click();", custom_button)
    logger.info("📆 Clicked on Custom Date Filter via JS")

    # STEP 2: Set FROM and TO dates
    from_date_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='anncEqFmDate']")))
    to_date_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='anncToFmDate']")))

    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'))", from_date_input, display_date)
    time.sleep(0.5)  # Let change event settle
    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'))", to_date_input, display_date)
    logger.info(f"🗓️ Date set to {display_date}")

    time.sleep(2)
    # STEP 3: Click "GO" button
    go_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@id='Announcements_equity']//button[@type='submit'][normalize-space()='GO']")))
    time.sleep(0.5)
    go_button.click()
    logger.info("🟢 Clicked on GO button to fetch data")
    time.sleep(2)

    # STEP 4: Click Download CSV button
    download_button_xpath = "//a[@id='CFanncEquity-download']"
    download_button = wait.until(EC.presence_of_element_located((By.XPATH, download_button_xpath)))

    # Scroll to download button and click it using JavaScript
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
    time.sleep(0.5)  # Let scroll settle
    driver.execute_script("arguments[0].click();", download_button)
    logger.info("⬇️ Clicked on Download CSV button via JS")

    # STEP 5: Save using pyautogui
    time.sleep(3)
    pyautogui.write(download_path)
    logger.info(f"💾 Entered download path: {download_path}")
    time.sleep(1.8)
    pyautogui.press('enter')

    time.sleep(1.5)  # Wait for dialog to appear
    pyautogui.press('left')   # Move from 'No' to 'Yes'
    time.sleep(0.3)
    pyautogui.press('enter')  # Confirm overwrite
    logger.info("🟢 Pressed Left + Enter to confirm overwrite (Yes)")

    return

if __name__ == "__main__":
    start = time.time()
    driver = get_driver()
    get_nse_annoucement_data(driver)
    end = time.time()
    logger.info(f"✅ All New Data Get in {end - start:.2f} seconds")
