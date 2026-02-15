"""
python -m stock_news_analysis.notification.telegram_alert
"""

import requests
from stock_news_analysis.config.alert_auth import telegram_auth


def send_telegram_alert(message: str):
    bot_token = telegram_auth.get("bot_token")
    channel_username = telegram_auth.get("channel_username")
    
    bot_token = bot_token  # Replace with your actual bot token
    channel_username = channel_username  # Replace with your channel username

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': channel_username,
        'text': message
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raise error for bad response
        result = response.json()

        if result.get("ok"):
            print("✅ Alert sent successfully.")
        else:
            print(f"⚠️ Failed to send alert: {result}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending alert: {e}")

if __name__ == "__main__":
    # Example usage
    test_message = "📊 *Stock Alert*\n\n🏢 *Company:* ABC Corp\n💡 *Signal:* Buy\n📈 *Current Price:* ₹1000\n🎯 *Confidence:* 85%\n📊 *Pattern:* Bullish\n🧠 *Sentiment:* Positive\n🏦 *Fii_Dii_buying:* High"
    send_telegram_alert(test_message)
