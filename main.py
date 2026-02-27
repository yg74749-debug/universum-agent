# main.py
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram

TZ = ZoneInfo("Europe/Belgrade")  # Prishtina ile aynı saat dilimi

def now_local() -> datetime:
    return datetime.now(tz=TZ)

def run_slot(dt: datetime) -> int:
    # 00-02 => 1, 03-05 => 2, ... 21-23 => 8
    return (dt.hour // 3) + 1

def is_daily_report(dt: datetime) -> bool:
    # Daily workflow ile env üzerinden kontrol edeceğiz
    return os.getenv("DAILY_REPORT", "0") == "1"

def main():
    dt = now_local()
    slot = run_slot(dt)
    daily = is_daily_report(dt)

    header = f"[MAIN] RUN SLOT {slot}/8 | {dt.isoformat()}"
    print(header)

    report_lines = []
    report_lines.append(f"📊 RUN SLOT {slot}/8" + (" (GÜNLÜK RAPOR)" if daily else ""))
    report_lines.append(f"🕒 Saat: {dt.strftime('%Y-%m-%d %H:%M:%S')} (Prishtina)")

    ums = run_ums()
    canvas = run_canvas()

    # --- UMS rapor formatı ---
    report_lines.append("\n📌 UMS RAPORU")
    if ums["ok"]:
        report_lines.append("✅ UMS açıldı.")
    else:
        report_lines.append(f"❌ UMS hata: {ums['error']}")

    report_lines.append(f"• 'Mali Yükümlülük' yakalandı mı? {'EVET' if ums.get('financial_block') else 'HAYIR'}")
    report_lines.append(f"• Sınav kaydı bulundu mu? {'EVET' if ums.get('exam_found') else 'HAYIR'}")
    if ums.get("exam_items"):
        # spam olmasın: en fazla 5 satır
        report_lines.append("🧾 Sınavlar (ilk 5):")
        for x in ums["exam_items"][:5]:
            report_lines.append(f"  - {x}")
    if ums.get("details"):
        report_lines.append("🧾 Detaylar:")
        for d in ums["details"][:8]:
            report_lines.append(f"  - {d}")

    # --- Canvas rapor formatı ---
    report_lines.append("\n📌 CANVAS RAPORU")
    if canvas["ok"]:
        report_lines.append("✅ Canvas açıldı.")
    else:
        report_lines.append(f"❌ Canvas hata: {canvas['error']}")

    report_lines.append(f"• Quiz/Survey bulundu mu? {'EVET' if canvas.get('quiz_found') else 'HAYIR'}")
    report_lines.append(f"• Survey otomatik dolduruldu mu? {'EVET' if canvas.get('survey_filled') else 'HAYIR'}")
    report_lines.append(f"• PDF indirme denendi mi? {'EVET' if canvas.get('pdf_download') else 'HAYIR'}")

    if canvas.get("found_links"):
        report_lines.append("🔗 Bulunanlar (ilk 5):")
        for u in canvas["found_links"][:5]:
            report_lines.append(f"  - {u}")

    if canvas.get("details"):
        report_lines.append("🧾 Detaylar:")
        for d in canvas["details"][:10]:
            report_lines.append(f"  - {d}")

    msg = "\n".join(report_lines)
    print("\n===== TELEGRAM RAPOR =====")
    print(msg)
    print("==========================")

    send_telegram(msg)

if __name__ == "__main__":
    main()
