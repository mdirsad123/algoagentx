import os

settings = {
    "COHERE_API_KEY": os.getenv("COHERE_API_KEY"),
    "EMAIL_ADDRESS": os.getenv("EMAIL_ADDRESS"),
    "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
    "LINKEDIN_EMAIL": os.getenv("LINKEDIN_EMAIL"),
    "LINKEDIN_PASSWORD": os.getenv("LINKEDIN_PASSWORD")
}

twilio_auth = {
    "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
    "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
    "content_sid": os.getenv("TWILIO_CONTENT_SID"),
    "from_whatsapp_number": os.getenv("TWILIO_FROM_WHATSAPP_NUMBER"),
    "to_whatsapp_number": os.getenv("TWILIO_TO_WHATSAPP_NUMBER")
}
telegram_auth = {
    "bot_name": os.getenv("TELEGRAM_BOT_NAME"),
    "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "channel_username": os.getenv("TELEGRAM_CHANNEL_USERNAME")
}
