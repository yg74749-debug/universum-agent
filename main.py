import datetime
import json
import os
from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram

RUN_FILE = "run_count.json"
DAILY_FILE = "daily_report.json"


# ---------- RUN COUNT ----------
def get_run_count():
    if not os.path.exists(RUN_FILE):
        return 0
    with open(RUN_FILE, "r") as f:
        return json.load(f).get("count", 0)


def save_run_count(c):
    with open(RUN_FILE, "w") as f:
        json.dump({"count": c}, f)


# ---------- DAILY REPORT ----------
def load_daily():
    today = datetime.date.today().isoformat()
    if not os.path.exists(DAILY_FILE):
        return {"date": today, "done": [], "fail": []}

    data = json.load(open(DAILY_FILE))
    if data["date"] != today:
        return {"date": today, "done": [], "fail": []}

    return data


def save_daily(data):
    json.dump(data, open(DAILY_FILE, "w"))


# ---------- MAIN ----------
def main():
    run = get_run_count() + 1
    save_run_count(run)

    now = datetime.datetime.now()
    msg = []
    msg.append(f"📊 BOT RUN #{run}")
    msg.append(f"🕒 Saat: {now}")

    daily = load_daily()

    # ---------- UMS ----------
    try:
        ums_result = run_ums()
        msg.append("\n📌 UMS RAPORU")

        if ums_result["ok"]:
            msg.append("✅ UMS açıldı")
            daily["done"].append("UMS Login")

            if ums_result.get("financial_block"):
                msg.append("⚠️ Mali Yükümlülük tespit edildi")
                daily["fail"].append("UMS Mali Borç")

            if ums_result.get("exam_found"):
                msg.append("📚 Yeni sınav kaydı bulundu")

        else:
            msg.append(f"❌ UMS hata: {ums_result['error']}")
            daily["fail"].append("UMS Error")

    except Exception as e:
        msg.append(f"❌ UMS crash: {str(e)}")
        daily["fail"].append("UMS Crash")

    # ---------- CANVAS ----------
    try:
        canvas_result = run_canvas()
        msg.append("\n📌 CANVAS RAPORU")

        if canvas_result["ok"]:
            msg.append("✅ Canvas açıldı")
            daily["done"].append("Canvas Login")

            if canvas_result.get("quiz_found"):
                msg.append("📝 Quiz bulundu")

            if canvas_result.get("survey_filled"):
                msg.append("🧾 Survey otomatik dolduruldu")

            if canvas_result.get("pdf_download"):
                msg.append("📄 PDF indirildi")

        else:
            msg.append(f"❌ Canvas hata: {canvas_result['error']}")
            daily["fail"].append("Canvas Error")

    except Exception as e:
        msg.append(f"❌ Canvas crash: {str(e)}")
        daily["fail"].append("Canvas Crash")

    save_daily(daily)

    # ---------- GÜNLÜK RAPOR ----------
    if now.hour == 0:
        msg.append("\n📅 GÜNLÜK RAPOR")
        msg.append("✅ Yapılanlar:")
        msg += ["- " + x for x in set(daily["done"])]

        msg.append("\n⚠️ Yapılamayanlar:")
        msg += ["- " + x for x in set(daily["fail"])]

        save_daily({"date": datetime.date.today().isoformat(),
                    "done": [], "fail": []})

    send_telegram("\n".join(msg))


if __name__ == "__main__":
    main()
