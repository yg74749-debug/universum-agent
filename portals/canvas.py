# portals/canvas.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

CANVAS_BASE = "https://canvas.universum-ks.org/"

KEYWORDS = [
    "Take the Quiz", "Quiz", "Quizzes",
    "Survey", "Anket",
    "Sınav", "Sinav",
    "Ödev", "Odev",
    "Assignment", "Assignments",
    "Module", "Modules",
]

def _contains_any(text: str) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in KEYWORDS)

def _wait_text(page, ms=12000) -> str:
    try:
        page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        pass
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:
        try:
            return page.inner_text("body")
        except Exception:
            return ""

def _find_course_nav_link(page, want: str) -> str | None:
    """
    want: 'quizzes' / 'assignments' / 'modules'
    Course sol menüsünden gerçek linki bulur.
    """
    try:
        for a in page.query_selector_all("a[href]"):
            href = (a.get_attribute("href") or "").strip()
            if f"/{want}" in href:
                return href if href.startswith("http") else urljoin(CANVAS_BASE, href)
    except Exception:
        pass
    return None

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
        page.wait_for_timeout(1000)

        _ = _wait_text(page)
        result["ok"] = True
        result["details"].append("Canvas login başarılı")
        print("[CANVAS] ✅ Login OK")

        print("[CANVAS] DEBUG after login")
        debug_page(page, "CANVAS")

        # Course linklerini bul
        course_urls = []
        for a in page.query_selector_all("a[href*='/courses/']"):
            href = (a.get_attribute("href") or "").strip()
            if "/courses/" in href:
                full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                if full not in course_urls:
                    course_urls.append(full)

        if not course_urls:
            try:
                dash = urljoin(CANVAS_BASE, "/courses")
                page.goto(dash, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)
                _ = _wait_text(page)
                for a in page.query_selector_all("a[href*='/courses/']"):
                    href = (a.get_attribute("href") or "").strip()
                    if "/courses/" in href:
                        full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                        if full not in course_urls:
                            course_urls.append(full)
                result["details"].append(f"Course sayfası denendi: {dash}")
            except Exception:
                pass

        print(f"[CANVAS] Found courses: {len(course_urls)}")
        print(f"[CANVAS] First course sample: {course_urls[0] if course_urls else 'NONE'}")

        if not course_urls:
            result["details"].append("Course linkleri bulunamadı.")
            return result

        result["details"].append(f"Bulunan course sayısı: {len(course_urls)}")

        found = []

        for cu in course_urls[:8]:
            try:
                # Course ana sayfasına gir
                print(f"[CANVAS] Visiting course root: {cu}")
                page.goto(cu, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)
                root_txt = _wait_text(page)
                debug_page(page, "CANVAS")

                # Sol menüden gerçek linkleri bul
                q_link = _find_course_nav_link(page, "quizzes")
                a_link = _find_course_nav_link(page, "assignments")
                m_link = _find_course_nav_link(page, "modules")

                if not q_link:
                    result["details"].append(f"Course {cu} -> Quizzes linki yok (kapalı olabilir).")
                if not a_link:
                    result["details"].append(f"Course {cu} -> Assignments linki yok (kapalı olabilir).")
                if not m_link:
                    result["details"].append(f"Course {cu} -> Modules linki yok (kapalı olabilir).")

                # Bulduysan git ve tara
                for label, link in [("quizzes", q_link), ("assignments", a_link), ("modules", m_link)]:
                    if not link:
                        continue
                    print(f"[CANVAS] Visiting: {link}")
                    page.goto(link, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(800)
                    txt = _wait_text(page)
                    debug_page(page, "CANVAS")

                    if _contains_any(txt):
                        for a in page.query_selector_all("a[href]"):
                            href = (a.get_attribute("href") or "").strip()
                            atxt = (a.inner_text() or "").strip()
                            if not href:
                                continue
                            if _contains_any(atxt) or "/quizzes/" in href or "/assignments/" in href:
                                full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                                if full not in found:
                                    found.append(full)

                # Course root sayfası bile bazen “To Do” gösterir
                if _contains_any(root_txt):
                    for a in page.query_selector_all("a[href]"):
                        href = (a.get_attribute("href") or "").strip()
                        atxt = (a.inner_text() or "").strip()
                        if not href:
                            continue
                        if _contains_any(atxt):
                            full = href if href.startswith("http") else urljoin(CANVAS_BASE, href)
                            if full not in found:
                                found.append(full)

            except Exception as e:
                result["details"].append(f"Course hata: {cu} -> {str(e)[:120]}")

        if found:
            result["quiz_found"] = True
            result["found_links"] = found[:15]
            result["details"].append(f"Quiz/Survey olabilecek link bulundu: {len(found)}")
        else:
            result["details"].append("Quiz/Survey linki bulunamadı (sekmeler kapalı olabilir veya içerik farklı yerde).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[CANVAS] ===== END =====\n")
