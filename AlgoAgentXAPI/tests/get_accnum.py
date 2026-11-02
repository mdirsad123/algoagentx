
import requests
import getpass

base = "https://demo.tradelocker.com/backend-api"

email = input("TradeLocker Email: ")
password = getpass.getpass("TradeLocker Password: ")
server = input("Server [GFTTL]: ") or "GFTTL"

# Step 1: Get token
response = requests.post(
    f"{base}/auth/jwt/token",
    json={
        "email": email,
        "password": password,
        "server": server
    },
    timeout=20
)
response.raise_for_status()

token = response.json()["accessToken"]

# Step 2: Fetch all accounts
response = requests.get(
    f"{base}/auth/jwt/all-accounts",
    headers={"Authorization": f"Bearer {token}"},
    timeout=20
)
response.raise_for_status()

# Step 3: Print account IDs and accNum
for account in response.json().get("accounts", []):
    print(
        "Account ID:", account.get("id"),
        "| accNum:", account.get("accNum"),
        "| Name:", account.get("name")
    )
