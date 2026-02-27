# main.py
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram_notify import send_telegram
from portals.ums import run_ums
from portals.canvas import run_canvas

TZ = ZoneInfo("Europe/Belgrade")  # Prishtina/Belgrade aynı saat

def slot_of_day(dt: datetime) -> int:
    return (dt.hour // 3) + 1  # 0-2 =>1, 3-5=>2 ... 21-23=>8

def format_report(now: datetime, ums: dict, canvas: dict) -> str:
    slot = slot_of_day(now)

    lines = []
    lines.append(f"📊 RUN SLOT {slot}/8")
    lines.append(f"🕒 Saat: {now.strftime('%Y-%m-%d %H:%M:%S')} (Prishtina)")
    lines.append("")
    lines.append("📌 UMS RAPORU")
    if ums.get("error"):
        lines.append(f"❌ UMS hata: {ums['error']}")
    else:
        lines.append("✅ UMS açıldı." if ums.get("ok") else "❌ UMS açılamadı.")
    lines.append(f"• 'Mali Yükümlülük' yakalandı mı? {'EVET' if ums.get('financial_block') else 'HAYIR'}")
    lines.append(f"• Sınav kaydı bulundu mu? {'EVET' if ums.get('exam_found') else 'HAYIR'}")

    if ums.get("exam_items"):
        lines.append("🧾 Sınavlar (ilk 5):")
        for it in ums["exam_items"][:5]:
            lines.append(f"  - {it}")

    if ums.get("details"):
        lines.append("🧾 Detaylar:")
        for d in ums["details"][:8]:
            lines.append(f"  - {d}")

    lines.append("")
    lines.append("📌 CANVAS RAPORU")
    if canvas.get("error"):
        lines.append(f"❌ Canvas hata: {canvas['error']}")
    else:
        lines.append("✅ Canvas açıldı." if canvas.get("ok") else "❌ Canvas açılamadı.")
    lines.append(f"• Quiz/Survey bulundu mu? {'EVET' if canvas.get('quiz_found') else 'HAYIR'}")
    lines.append(f"• Survey otomatik dolduruldu mu? {'EVET' if canvas.get('survey_filled') else 'HAYIR'}")
    lines.append(f"• PDF indirme denendi mi? {'EVET' if canvas.get('pdf_download') else 'HAYIR'}")

    if canvas.get("found_links"):
        lines.append("🔗 Bulunan linkler (ilk 5):")
        for u in canvas["found_links"][:5]:
            lines.append(f"  - {u}")

    if canvas.get("details"):
        lines.append("🧾 Detaylar:")
        for d in canvas["details"][:8]:
            lines.append(f"  - {d}")

    return "\n".join(lines)

def main():
    now = datetime.now(TZ)
    print(f"[MAIN] RUN SLOT {slot_of_day(now)}/8 | {now.isoformat()}")

    # UMS
    ums = {}
    try:
        ums = run_ums()
    except Exception as e:
        ums = {"ok": False, "error": f"UMS crash: {str(e)}"}

    # CANVAS
    canvas = {}
    try:
        canvas = run_canvas()
    except Exception as e:
        canvas = {"ok": False, "error": f"Canvas crash: {str(e)}"}

    report = format_report(now, ums, canvas)

    print("\n===== TELEGRAM RAPOR =====")
    print(report)
    print("==========================\n")

    send_telegram(report)

if __name__ == "__main__":
    main()
