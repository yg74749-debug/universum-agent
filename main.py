import os
import datetime
from zoneinfo import ZoneInfo

from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram

TZ = ZoneInfo("Europe/Belgrade")  # Prishtina ile aynı

def format_ums(res: dict) -> list[str]:
    lines = []
    lines.append("📌 UMS RAPORU")
    if res.get("ok"):
        lines.append("✅ UMS RAPORU açıldı.")
    else:
        lines.append(f"❌ UMS RAPORU hata: {res.get('error')}")
    lines.append(f"• 'Mali Yükümlülük' yakalandı mı? {'EVET' if res.get('financial_block') else 'HAYIR'}")
    lines.append(f"• Sınav kaydı bulundu mu? {'EVET' if res.get('exam_found') else 'HAYIR'}")
    if res.get("details"):
        lines.append("🧾 Detaylar:")
        for d in res["details"]:
            lines.append(f"  - {d}")
    return lines

def format_canvas(res: dict) -> list[str]:
    lines = []
    lines.append("📌 CANVAS RAPORU")
    if res.get("ok"):
        lines.append("✅ CANVAS RAPORU açıldı.")
    else:
        lines.append(f"❌ CANVAS RAPORU hata: {res.get('error')}")
    lines.append(f"• Quiz/Survey bulundu mu? {'EVET' if res.get('quiz_found') else 'HAYIR'}")
    lines.append(f"• Survey otomatik dolduruldu mu? {'EVET' if res.get('survey_filled') else 'HAYIR'}")
    lines.append(f"• PDF indirme denendi mi? {'EVET' if res.get('pdf_download') else 'HAYIR'}")
    if res.get("details"):
        lines.append("🧾 Detaylar:")
        for d in res["details"]:
            lines.append(f"  - {d}")
    return lines

def main():
    run_no = os.getenv("GITHUB_RUN_NUMBER") or "?"
    now = datetime.datetime.now(TZ)

    print(f"\n[MAIN] BOT RUN #{run_no} | {now.isoformat()}")

    report_lines = []
    report_lines.append(f"📊 BOT RUN #{run_no}")
    report_lines.append(f"🕒 Saat: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # UMS
    ums_res = run_ums()
    report_lines.append("")  # boş satır
    report_lines += format_ums(ums_res)

    # CANVAS
    canvas_res = run_canvas()
    report_lines.append("")
    report_lines += format_canvas(canvas_res)

    msg = "\n".join(report_lines)

    print("\n===== TELEGRAM RAPOR =====")
    print(msg)
    print("==========================\n")

    send_telegram(msg)

if __name__ == "__main__":
    main()
