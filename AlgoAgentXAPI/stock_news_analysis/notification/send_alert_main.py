"""
python -m stock_news_analysis.notification.send_alert_main
"""
import yfinance as yf
from .watsapp_alert_scraping import send_watsapp_trade_signal
from .telegram_alert import send_telegram_alert
from investing_risk_management.risk_management import get_live_risk_config

def send_alert_msg(row):
    try:
        symbol = row['Company']
        confidence = float(row['Success_Chance'])
        pattern = row['Chart_Pattern']
        sentiment = row['Final_Sentiment']
        signal = row['ML_Prediction']
        Fii_Dii_BUYING = row['Fii_Dii_BUYING']

        # Inputs for risk config
        budget = 100000
        risk_per_trade = 1000

        # Fetch price and company info
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info
            current_price = info.get("currentPrice", "N/A")
            company_name = info.get("longName", symbol)
        except:
            current_price = "N/A"
            company_name = symbol

        # Risk/Reward Calculation
        try:
            rr = get_live_risk_config(
                symbol=f"{symbol}.NS",
                budget=budget,
                risk_per_trade=risk_per_trade,
                stop_loss_manual=None,
                entry_manual=None
            )
        except Exception as e:
            rr = {"error": str(e)}

        # Format Risk Info
        if "error" not in rr:
            risk_info = f"""
💵 Buy Price: ₹{rr.get('Buy Price')}
📉 Stop Loss: ₹{rr.get('Stop Loss')} (-{rr.get('Stop Loss %')}%)
🎯 Target Price: ₹{rr.get('Target Price')} (+{rr.get('Profit %')}%)
📊 Risk:Reward: {rr.get('RR Ratio', 'N/A')}
💰 Quantity: {rr.get('Quantity')} units
💼 Investment: ₹{rr.get('Investment')}
⚠️ Total Risk: ₹{rr.get('Total Risk')}
📈 Total Profit: ₹{rr.get('Total Profit')}
""".strip()
        else:
            risk_info = f"⚠️ Risk config error: {rr['error']}"

        # Final message
        message = f"""
📊 Stock Alert

🏢 {company_name} ({symbol})
💡 Signal: {signal}
📈 Current Price: ₹{current_price}
🎯 Confidence: {confidence:.1f}%
📊 Pattern: {pattern}
🧠 Sentiment: {sentiment}
🏦 Fii_Dii_buying: {Fii_Dii_BUYING}

🛡️ Risk/Reward Plan
{risk_info}

🕋 Bismillah! May your trades be profitable and wise. 📈
💼 Smart moves today lead to strong gains tomorrow.
""".strip()

        # Send alert
        # send_watsapp_trade_signal(message)
        send_telegram_alert(message)  # optional

    except Exception as e:
        print(f"❌ Error sending alert for {row.get('Company', 'Unknown')}: {e}")
