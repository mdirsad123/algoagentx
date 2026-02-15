"""
python -m stock_news_analysis.notification.watsapp_alert_Twilio
"""

import json
from twilio.rest import Client
from stock_news_analysis.config.alert_auth import twilio_auth
# from config.alert_auth import twilio_auth


account_sid = twilio_auth['account_sid']
auth_token = twilio_auth['auth_token']
from_whatsapp_number = twilio_auth['from_whatsapp_number']
to_whatsapp_number = twilio_auth['to_whatsapp_number']
content_sid = twilio_auth['content_sid']

def send_whatsapp_alert(stock, confidence, pattern, price):
    

    # Format template variables for Twilio
    content_variables = json.dumps({
        "1": stock,
        "2": str(confidence),
        "3": pattern,
        "4": price,
    })

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        from_=from_whatsapp_number,
        to=to_whatsapp_number,
        content_sid=content_sid,
        content_variables=content_variables
    )

    print(f"✅ WhatsApp alert sent! SID: {message.sid}")

def send_whatsapp_alert_trade_executed(stock, confidence, pattern, price, executed_msg):
    
    # Format template variables for Twilio
    content_variables = json.dumps({
        "1": stock,
        "2": str(confidence),
        "3": pattern,
        "4": price,
        "5": executed_msg,
    })

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        from_=from_whatsapp_number,
        to=to_whatsapp_number,
        content_sid=content_sid,
        content_variables=content_variables
    )

    print(f"✅ WhatsApp alert sent! SID: {message.sid}")

if __name__ == "__main__":
    # Example usage
    # send_whatsapp_alert(
    #     stock="NTPC",
    #     confidence=80,
    #     pattern="Hammer, Double Top",
    #     price="XXX"
    # )
    send_whatsapp_alert_trade_executed(
        stock="NTPC",
        confidence=80,
        pattern="Hammer, Double Top",
        price="XXX",
        executed_msg=" Entry price: ₹XXX, Quantity: 1"
    )
