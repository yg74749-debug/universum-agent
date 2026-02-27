import os
import requests

def send_telegram(message: str) -> None:
    token = os.environ["TG_BOT_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]

    while message:
        part, message = message[:3500], message[3500:]
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": part},
            timeout=30,
        )
        r.raise_for_status()
