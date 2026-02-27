# portals/ums.py
from .browser import get_context, close_context, debug_page

UMS_URL = "https://ums-student-portal.universum-ks.org/"

def run_ums():
    result = {
        "ok": False,
        "error": None,
        "financial_block": False,
        "exam_found": False,
        "exam_items": [],
        "details": []
    }

    ctx = None

    try:
        print("[UMS] ===== START =====")
        print("[UMS] Portal açılıyor...")

        ctx = get_context("ums_state.json")
        page = ctx.new_page()
        page.goto(UMS_URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(1500)
        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        print("[UMS] Exam sayfasına gidiliyor...")
        candidates = [
            UMS_URL + "exams",
            UMS_URL + "student/exams",
            UMS_URL + "my-exams",
        ]

        exam_page_opened = False

        for url in candidates:
            try:
                print(f"[UMS] Trying exam URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)

                print("[UMS] DEBUG after exam goto")
                debug_page(page, "UMS")

                exam_page_opened = True
                result["details"].append(f"Exam sayfası denendi: {url}")
                break
            except Exception as e:
                print(f"[UMS] Exam URL failed: {url} | {str(e)[:120]}")
                continue

        html = page.content()

        print("[UMS] 'Mali Yükümlülük' aranıyor...")
        if "Mali Yükümlülük" in html:
            result["financial_block"] = True
            result["details"].append("Mali Yükümlülük bulundu")
            return result

        text = page.inner_text("body")

        if "Sınav" in text or "Exam" in text:
            result["exam_found"] = True
            result["exam_items"].append("Sayfada sınav kelimesi bulundu")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    finally:
        if ctx:
            close_context(ctx)

        print("[UMS] ===== END =====\n")
