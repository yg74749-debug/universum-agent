from .browser import get_context, close_context

def run_ums():
    result = {
        "ok": False,
        "error": None,
        "financial_block": False,
        "exam_found": False,
        "details": []
    }

    print("\n[UMS] ===== START =====")

    try:
        pw, browser, context, page = get_context("ums_state.json")

        print("[UMS] Portal açılıyor...")
        page.goto("https://ums-student-portal.universum-ks.org/")
        page.wait_for_timeout(3000)

        if "login" not in page.url:
            print("[UMS] ✅ Login OK")
            result["ok"] = True
            result["details"].append("UMS login başarılı")
        else:
            print("[UMS] ❌ Login başarısız")

        print("[UMS] Exam sayfasına gidiliyor...")
        page.goto("https://ums-student-portal.universum-ks.org/student/exams")
        page.wait_for_timeout(4000)

        html = page.content()

        print("[UMS] 'Mali Yükümlülük' aranıyor...")
        if "Mali Yükümlülük" in html:
            print("[UMS] ⚠️ Mali Yükümlülük bulundu!")
            result["financial_block"] = True
        else:
            print("[UMS] Mali Yükümlülük yok")

        close_context(pw, browser, context)
        print("[UMS] ===== END =====\n")
        return result

    except Exception as e:
        print("[UMS] ❌ CRASH:", str(e))
        result["error"] = str(e)
        return result
