"""
python -m stock_news_analysis.notification.twilio_reply_webhook
"""

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/demo-reply", methods=["POST"])
def demo_reply():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From', '')
    
    print(f"📩 Reply from {from_number}: {incoming_msg}")
    
    response = MessagingResponse()
    
    if incoming_msg == "yes":
        reply = "✅ Thank you! Proceeding with the trade."
    elif incoming_msg == "no":
        reply = "❌ Okay, trade canceled."
    else:
        reply = "❓ Please reply with 'Yes' or 'No'."

    response.message(reply)
    return str(response)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
