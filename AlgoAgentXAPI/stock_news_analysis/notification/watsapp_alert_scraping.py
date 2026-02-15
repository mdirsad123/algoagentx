"""
python -m stock_news_analysis.notification.watsapp_alert_scraping
"""

import pywhatkit as kit
import time
from datetime import datetime

# List of contacts
data = ["+918692031866"]

def send_watsapp_trade_signal(messages_str):
    print("📤 Sending WhatsApp messages...\n")
    today = datetime.now().strftime("%Y-%m-%d")

    for contact in data:
        try:
            kit.sendwhatmsg_instantly(contact, messages_str, tab_close=True)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Message sent to {contact}")
            time.sleep(10)  # wait before next message to avoid overlap
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error sending to {contact}: {e}")

if __name__ == "__main__":
    start_time = time.time()
    messages_str = "📿 Assalamu Alaikum! Here's your daily Islamic reminder. Stay blessed! ☪️"
    send_watsapp_trade_signal(messages_str)
    end_time = time.time()
    print(f"\n⏱️ Total execution time: {end_time - start_time:.2f} seconds")
