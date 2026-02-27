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

        print("[CANVAS] Canvas açılıyor...")
        page.goto("https://canvas.universum-ks.org/")
        page.wait_for_timeout(4000)

        if "login" not in page.url:
            print("[CANVAS] ✅ Login OK")
            result["ok"] = True
            result["details"].append("Canvas login başarılı")
        else:
            print("[CANVAS] ❌ Login başarısız")

        # Quiz arama örneği
        html = page.content()
        if "Take the Quiz" in html or "Survey" in html:
            print("[CANVAS] Quiz/Survey bulundu")
            result["quiz_found"] = True

        close_context(pw, browser, context)
        print("[CANVAS] ===== END =====\n")
        return result

    except Exception as e:
        print("[CANVAS] ❌ CRASH:", str(e))
        result["error"] = str(e)
        return result
