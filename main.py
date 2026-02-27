import os
import datetime

from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram


def main():
    report = []

    # ✅ Kaçıncı run (GitHub Actions otomatik verir)
    run_number = os.getenv("GITHUB_RUN_NUMBER", "local")

    now = datetime.datetime.now()
    header = [
        f"📊 BOT RUN #{run_number}",
        f"🕒 Saat: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    # =========================
    # UMS
    # =========================
    try:
        report.append("📌 UMS RAPORU")
        ums_result = run_ums()

        if ums_result:
            report += ums_result
        else:
            report.append("⚠️ UMS veri bulunamadı.")

    except Exception as e:
        report.append(f"❌ UMS hata: {type(e).__name__} - {e}")

    report.append("")

    # =========================
    # CANVAS
    # =========================
    try:
        report.append("📌 CANVAS RAPORU")
        canvas_result = run_canvas()

        if canvas_result:
            report += canvas_result
        else:
            report.append("⚠️ Canvas veri bulunamadı.")

    except Exception as e:
        report.append(f"❌ Canvas hata: {type(e).__name__} - {e}")

    # =========================
    # TELEGRAM
    # =========================
    final_message = "\n".join(header + report)
    send_telegram(final_message)


if __name__ == "__main__":
    main()
