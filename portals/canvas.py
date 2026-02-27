# portals/canvas.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

CANVAS_BASE = "https://canvas.universum-ks.org/"

KEYWORDS = [
    "Take the Quiz",
    "Quiz",
    "Quizzes",
    "Survey",
    "Anket",
    "Sınav",
    "Ödev"
]

def _contains_any(text: str) -> bool:
    t = (text or "")
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

        # 🔍 DEBUG LOGIN SONRASI
        print("[CANVAS] DEBUG after login")
        debug_page(page, "CANVAS")

        # Course linklerini bul
        links = page.query_selector_all("a[href*='/courses/']")
        course_urls = []

        for a in links:
            href = a.get_attribute("href") or ""
            if "/courses/" in href:
                full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                if full not in course_urls:
                    course_urls.append(full)

        # Eğer dashboard'ta course yoksa alternatif sayfa
        if not course_urls:
            try:
                dash = urljoin(CANVAS_BASE, "/courses")
                page.goto(dash, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)

                print("[CANVAS] DEBUG after /courses page")
                debug_page(page, "CANVAS")

                links = page.query_selector_all("a[href*='/courses/']")
                for a in links:
                    href = a.get_attribute("href") or ""
                    if "/courses/" in href:
                        full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                        if full not in course_urls:
                            course_urls.append(full)

                result["details"].append(f"Course sayfası denendi: {dash}")
            except Exception as e:
                result["details"].append(f"/courses sayfası açılamadı: {str(e)[:80]}")

        print(f"[CANVAS] Found courses: {len(course_urls)}")
        print(f"[CANVAS] First course sample: {course_urls[0] if course_urls else 'NONE'}")

        if not course_urls:
            result["details"].append("Course linkleri bulunamadı.")
            return result

        result["details"].append(f"Bulunan course sayısı: {len(course_urls)}")

        found = []

        # Her course'ta quizzes + assignments gez
        for cu in course_urls[:8]:
            for sub in ["/quizzes", "/assignments"]:
                target = cu.rstrip("/") + sub
                try:
                    print(f"[CANVAS] Visiting: {target}")
                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)

                    debug_page(page, "CANVAS")

                    body = page.inner_text("body")

                    if _contains_any(body):
                        for a in page.query_selector_all("a"):
                            href = a.get_attribute("href") or ""
                            txt = (a.inner_text() or "").strip()

                            if not href:
                                continue

                            if _contains_any(txt) or "/quizzes/" in href or "/assignments/" in href:
                                full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                                if full not in found:
                                    found.append(full)

                except Exception as e:
                    result["details"].append(f"Hata: {target} -> {str(e)[:80]}")

        if found:
            result["quiz_found"] = True
            result["found_links"] = found[:15]
            result["details"].append(f"Quiz/Survey olabilecek link bulundu: {len(found)}")
        else:
            result["details"].append("Quiz/Survey linki bulunamadı.")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    finally:
        if ctx:
            close_context(ctx)
        print("[CANVAS] ===== END =====\n")
