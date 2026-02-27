# telegram_notify.py
import os
import requests

def send_telegram(text: str):
    token = os.environ.get("TG_BOT_TOKEN", "")
    chat_id = os.environ.get("TG_CHAT_ID", "")

    if not token or not chat_id:
        print("[TG] Missing TG_BOT_TOKEN or TG_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": chat_id, "text": text})
        print("[TG] sendMessage status:", r.status_code)
    except Exception as e:
        print("[TG] sendMessage error:", str(e)[:160])
