# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_URL = "https://ums-student-portal.universum-ks.org/"

DEBT_KEYWORDS = [
    "Mali Yükümlülük", "Mali Yukumluluk",
    "Detyrim Financiar", "detyrim financiar",
    "borxh", "Keni një detyrim financiar",
    "Disa funksione janë të kufizuara",
]

EXAM_MENU_KEYWORDS = [
    "Regjistrimi i Provimit", "Provimet e Mia", "Provimet",
    "Exam", "Exams", "Sınav", "Sinav",
    "Registration", "List"
]

def _has_any(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords)

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

def _collect_candidate_routes(page) -> list[str]:
    routes = []
    try:
        for a in page.query_selector_all("a[href]"):
            href = (a.get_attribute("href") or "").strip()
            txt = (a.inner_text() or "").strip()
            if not href:
                continue
            full = href if href.startswith("http") else urljoin(UMS_URL, href)
            if _has_any(txt, EXAM_MENU_KEYWORDS) or _has_any(href, EXAM_MENU_KEYWORDS):
                if full not in routes:
                    routes.append(full)
    except Exception:
        pass
    return routes

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
        page.wait_for_timeout(1200)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # Borç kontrolü (ana sayfa)
        txt0 = _wait_text(page)
        if _has_any(txt0, DEBT_KEYWORDS):
            result["financial_block"] = True
            result["details"].append("Finansal blok görüldü (Detyrim Financiar / Mali Yükümlülük).")
            print("[UMS] ⚠️ Financial block detected on landing")

        routes = _collect_candidate_routes(page)
        result["details"].append(f"Aday sınav linki sayısı: {len(routes)}")

        if not routes:
            routes = [
                urljoin(UMS_URL, "ExamRegistration"),
                urljoin(UMS_URL, "StudentExamRegistration"),
                urljoin(UMS_URL, "StudentExamRegistration/List"),
                urljoin(UMS_URL, "MyExams"),
                urljoin(UMS_URL, "Exams"),
            ]
            result["details"].append("Menüden link bulunamadı, fallback rotalar denendi.")

        exam_items = []
        visited = 0

        for r in routes[:10]:
            try:
                print(f"[UMS] Visiting: {r}")
                page.goto(r, wait_until="domcontentloaded", timeout=30000)
                visited += 1
                page.wait_for_timeout(700)
                txt = _wait_text(page)

                if _has_any(txt, DEBT_KEYWORDS):
                    result["financial_block"] = True
                    result["details"].append(f"Finansal blok bu sayfada görüldü: {r}")

                # Satır/öğe yakalama (çoklu selector)
                candidates = []
                for sel in ["table tr", "tbody tr", "ul li", ".card", ".list-group-item", ".row", ".col"]:
                    try:
                        for e in page.query_selector_all(sel)[:60]:
                            t = (e.inner_text() or "").strip()
                            if not t or len(t) < 10:
                                continue
                            if any(k in t for k in ["202", "Prov", "Exam", "Sınav", "Regjistr", "Ora", "Data", "Semestr"]):
                                candidates.append(t.replace("\n", " | "))
                    except Exception:
                        pass

                # uniq
                seen = set()
                uniq = []
                for c in candidates:
                    if c not in seen:
                        seen.add(c)
                        uniq.append(c)

                # navbar spam azalt
                for c in uniq:
                    if "PORTALI PËR STUDENTË" in c and len(c) > 200:
                        continue
                    exam_items.append(c)

            except Exception as e:
                result["details"].append(f"Route hata: {r} -> {str(e)[:100]}")

        result["details"].append(f"Ziyaret edilen route sayısı: {visited}")

        # final uniq
        seen2 = set()
        final = []
        for it in exam_items:
            if it not in seen2:
                seen2.add(it)
                final.append(it)

        if final:
            result["exam_found"] = True
            result["exam_items"] = final[:10]
            result["details"].append(f"Sınav listesi bulundu: {len(final)} satır.")
        else:
            result["details"].append("Sınav satırı bulunamadı (sayfa boş/format farklı/JS ile doluyor olabilir).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
