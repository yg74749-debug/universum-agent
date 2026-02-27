# portals/canvas.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

CANVAS_BASE = "https://canvas.universum-ks.org/"

KEYWORDS = [
    "Quiz",
    "Survey",
    "Anket",
    "Sınav",
    "Assignment",
    "Ödev"
]

def _contains_any(text):
    t = text or ""
    return any(k.lower() in t.lower() for k in KEYWORDS)


def run_canvas():
    result = {
        "ok": False,
        "error": None,
        "quiz_found": False,
        "survey_filled": False,
        "pdf_download": False,
        "found_links": [],
        "details": []
    }

    ctx = None

    try:
        print("[CANVAS] ===== START =====")
        print("[CANVAS] Canvas açılıyor...")

        ctx = get_context("canvas_state.json")
        page = ctx.new_page()
        page.goto(CANVAS_BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)

        result["ok"] = True
        result["details"].append("Canvas login başarılı")
        print("[CANVAS] ✅ Login OK")

        print("[CANVAS] DEBUG after login")
        debug_page(page, "CANVAS")

        links = page.query_selector_all("a[href*='/courses/']")
        course_urls = []

        for a in links:
            href = a.get_attribute("href") or ""
            if "/courses/" in href:
                full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                if full not in course_urls:
                    course_urls.append(full)

        print(f"[CANVAS] Found courses: {len(course_urls)}")
        print(f"[CANVAS] First course sample: {course_urls[0] if course_urls else 'NONE'}")

        for cu in course_urls[:5]:
            for sub in ["/quizzes", "/assignments"]:
                target = cu.rstrip("/") + sub

                try:
                    print(f"[CANVAS] Visiting: {target}")
                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)

                    debug_page(page, "CANVAS")

                    body = page.inner_text("body")

                    if _contains_any(body):
                        result["quiz_found"] = True
                        result["found_links"].append(target)

                except Exception as e:
                    print("[CANVAS] ERROR:", str(e)[:120])

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    finally:
        if ctx:
            close_context(ctx)

        print("[CANVAS] ===== END =====\n")
