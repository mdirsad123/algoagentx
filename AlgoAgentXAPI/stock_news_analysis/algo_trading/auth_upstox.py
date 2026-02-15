"""
python -m stock_news_analysis.algo_trading.auth_upstox
"""

import requests
import webbrowser
import json
import os
from urllib.parse import urlencode

# ---------- CONFIG SECTION ----------
client_id = '8c5684de-a579-4126-b7b6-ebd86a450c30'
client_secret = '1etgbwkquc'
redirect_uri = 'http://localhost:8000/callback'
token_file = 'upstox_token.json'
# ------------------------------------

def save_token(token_data):
    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=4)
    print("✅ Access token saved to", token_file)

def load_token():
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return json.load(f)
    return None

def get_login_url():
    base_url = "https://api.upstox.com/v2/login/authorization/dialog"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
    }
    return f"{base_url}?{urlencode(params)}"

def get_access_token(auth_code):
    url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        save_token(data)
        return data
    else:
        print("❌ Failed to get access token:", response.text)
        return None

# --------------------- MAIN FLOW ---------------------

# Try loading existing token
token_data = load_token()

if token_data and token_data.get("access_token"):
    print("✅ Token loaded from file.")
else:
    # Step 1: Open login URL for user authentication
    login_url = get_login_url()
    print("👉 Open this URL and login:", login_url)
    webbrowser.open(login_url)

    # Step 2: Enter auth code from redirect
    auth_code = input("🔑 Enter the code from the URL after login (parameter ?code=...): ").strip()

    # Step 3: Exchange code for token
    token_data = get_access_token(auth_code)

if token_data:
    print("🎯 Your Access Token is:", token_data["access_token"])
else:
    print("❌ Could not get token.")
