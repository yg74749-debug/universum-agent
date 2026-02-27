from .browser import get_context, close_context

def run_canvas():
    result = {
        "ok": False,
        "error": None,
        "quiz_found": False,
        "survey_filled": False,
        "pdf_download": False,
        "details": []
    }

    print("\n[CANVAS] ===== START =====")

    try:
        pw, browser, context, page = get_context("canvas_state.json")
...
close_context(pw, browser, context)

        print("[CANVAS] Dashboard açılıyor...")
        page.goto("https://canvas.universum-ks.org/")
        page.wait_for_timeout(3000)

        if "login" not in page.url:
            print("[CANVAS] ✅ Login OK")
            result["ok"] = True
            result["details"].append("Canvas login başarılı")
        else:
            print("[CANVAS] ❌ Login başarısız")

        page_text = page.content()

        print("[CANVAS] Quiz aranıyor...")
        if "Take the Quiz" in page_text or "Quiz" in page_text:
            print("[CANVAS] 📌 Quiz bulundu")
            result["quiz_found"] = True
        else:
            print("[CANVAS] Quiz yok")

        print("[CANVAS] Survey aranıyor...")
        if "Survey" in page_text:
            print("[CANVAS] 📌 Survey bulundu (otomatik doldurma eklenebilir)")
        else:
            print("[CANVAS] Survey yok")

        print("[CANVAS] PDF link aranıyor...")
        if ".pdf" in page_text:
            print("[CANVAS] 📥 PDF link bulundu")
            result["pdf_download"] = True
        else:
            print("[CANVAS] PDF yok")

        close_context(context)

        print("[CANVAS] ===== END =====\n")
        return result

    except Exception as e:
        print("[CANVAS] ❌ CRASH:", str(e))
        result["error"] = str(e)
        return result
