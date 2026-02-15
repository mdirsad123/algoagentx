"""
python -m stock_news_analysis.algo_trading.download_instrument
"""

import requests
import pandas as pd
import json

# Step 1: Download instruments
url = "https://api.upstox.com/v2/instruments"
response = requests.get(url)

if response.status_code == 200:
    # Step 2: Parse and filter only NSE EQ (equity) instruments
    all_data = response.json()
    df = pd.DataFrame(all_data)

    filtered_df = df[
        (df['exchange'] == 'NSE') &
        (df['instrument_type'] == 'EQ') &
        (df['segment'] == 'NSE_EQ')
    ].copy()

    # Step 3: Save to JSON only
    with open("upstox_instruments_nse.json", "w") as f:
        json.dump(filtered_df.to_dict(orient="records"), f, indent=2)

    print(f"✅ Saved {len(filtered_df)} NSE equity instruments to 'upstox_instruments_nse.json'.")

else:
    print("❌ Failed to fetch instruments list:", response.status_code, response.text)
