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
        context, page = get_context("ums_state.json")

        print("[UMS] Login sayfası açılıyor...")
        page.goto("https://ums-student-portal.universum-ks.org/")
        page.wait_for_timeout(3000)

        print("[UMS] Login başarılı mı kontrol ediliyor...")
        if "login" not in page.url:
            print("[UMS] ✅ Login OK")
            result["ok"] = True
            result["details"].append("UMS login başarılı")
        else:
            print("[UMS] ❌ Login başarısız")

        print("[UMS] Exam sayfasına gidiliyor...")
        page.goto("https://ums-student-portal.universum-ks.org/student/exams")
        page.wait_for_timeout(4000)

        page_text = page.content()

        print("[UMS] 'Mali Yükümlülük' aranıyor...")
        if "Mali Yükümlülük" in page_text:
            print("[UMS] ⚠️ Mali Yükümlülük bulundu!")
            result["financial_block"] = True
        else:
            print("[UMS] Mali Yükümlülük yok")

        print("[UMS] 'Exam Registration' aranıyor...")
        if "Exam Registration" in page_text or "Sınav Kaydı" in page_text:
            print("[UMS] 📌 Sınav kaydı bulundu")
            result["exam_found"] = True
        else:
            print("[UMS] Sınav kaydı yok")

        close_context(context)

        print("[UMS] ===== END =====\n")
        return result

    except Exception as e:
        print("[UMS] ❌ CRASH:", str(e))
        result["error"] = str(e)
        return result
