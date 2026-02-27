import os
import datetime

from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram


def _now_str():
    # GitHub runner UTC kullanır; saat göstermek için yeterli
    return str(datetime.datetime.now())


def _run_no():
    # GitHub Actions her run’a otomatik bir numara verir (en sağlam çözüm)
    return os.getenv("GITHUB_RUN_NUMBER", "?")


def _format_portal_report(title: str, r):
    """
    r: dict bekliyoruz.
    Örnek:
      {
        "ok": True/False,
        "error": None/"...",
        "details": ["...", "..."],
        "quiz_found": bool,
        ...
      }
    """
    lines = []
    lines.append(f"📌 {title}")

    if not isinstance(r, dict):
        # Beklenmeyen dönüş tipi
        lines.append(f"❌ {title} crash: Unexpected return type: {type(r).__name__}")
        return lines

    ok = bool(r.get("ok", False))
    err = r.get("error")

    if ok:
        lines.append(f"✅ {title} açıldı.")
    else:
        # Hata varsa sebebiyle göster
        if err:
            lines.append(f"❌ {title} hata: {err}")
        else:
            lines.append(f"❌ {title} başarısız (sebep belirtilmedi).")

    # Özel sinyaller (senin istediğin log/analiz maddeleri)
    # Canvas tarafı
    if title.upper() == "CANVAS RAPORU":
        if "quiz_found" in r:
            lines.append(f"• Quiz/Survey bulundu mu? {'EVET' if r.get('quiz_found') else 'HAYIR'}")
        if "survey_filled" in r:
            lines.append(f"• Survey otomatik dolduruldu mu? {'EVET' if r.get('survey_filled') else 'HAYIR'}")
        if "pdf_download" in r:
            lines.append(f"• PDF indirme denendi mi? {'EVET' if r.get('pdf_download') else 'HAYIR'}")

    # UMS tarafı
    if title.upper() == "UMS RAPORU":
        if "financial_block" in r:
            lines.append(f"• 'Mali Yükümlülük' yakalandı mı? {'EVET' if r.get('financial_block') else 'HAYIR'}")
        if "exam_found" in r:
            lines.append(f"• Sınav kaydı bulundu mu? {'EVET' if r.get('exam_found') else 'HAYIR'}")

    # Detaylar (varsa)
    details = r.get("details", [])
    if isinstance(details, list) and details:
        lines.append("🧾 Detaylar:")
        for d in details[:10]:  # spam olmasın diye 10 satır limit
            lines.append(f"  - {d}")

    return lines


def main():
    msg_lines = []
    msg_lines.append(f"📊 BOT RUN #{_run_no()}")
    msg_lines.append(f"🕒 Saat: {_now_str()}")
    msg_lines.append("")  # boş satır

    # UMS
    try:
        ums_r = run_ums()
    except Exception as e:
        ums_r = {"ok": False, "error": f"UMS crash: {e}", "details": []}
    msg_lines += _format_portal_report("UMS RAPORU", ums_r)

    msg_lines.append("")  # boş satır

    # Canvas
    try:
        canvas_r = run_canvas()
    except Exception as e:
        canvas_r = {"ok": False, "error": f"Canvas crash: {e}", "details": []}
    msg_lines += _format_portal_report("CANVAS RAPORU", canvas_r)

    # Telegram gönder
    send_telegram("\n".join(msg_lines))


if __name__ == "__main__":
    main()
