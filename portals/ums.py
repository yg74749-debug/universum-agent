# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _is_404(page) -> bool:
    try:
        h = _norm(page.content())
        return ("404" in h and "not found" in h) or "page not found" in h
    except Exception:
        return False

def _has_financial_block(html: str) -> bool:
    html_l = (html or "").lower()
    keys = [
        "mali yükümlülük", "mali yukumluluk",
        "financial obligation", "financial obligations",
        "detyrim financiar", "detyrime financiare",
        "borxh",
        "disa funksione janë të kufizuara",
        "keni një detyrim financiar"
    ]
    return any(k in html_l for k in keys)

def _extract_exam_items(page):
    # Menü/nav spamını kes
    bad_contains = [
        "portali", "paneli", "profili", "ndihmë", "help",
        "plani i orarit", "vlerësimet", "transkripta",
        "regjistrimi i semestrit", "lista e pagesave", "tema e diplomës",
        "© 2024", "të gjitha të drejtat",
        "go back", "page not found"
    ]

    items = []

    def ok_line(t: str) -> bool:
        tl = _norm(t)
        if len(t.strip()) < 12:
            return False
        if any(b in tl for b in bad_contains):
            return False
        # sınav satırı ipuçları
        if any(k in tl for k in ["provim", "exam", "regjistr", "data", "date", "ora", "salla", "room", "kurs", "course"]):
            return True
        # tarihe benzer bir şey varsa da kabul et (2026 / 27.02 vb)
        if "202" in tl or "." in tl:
            return True
        return False

    # Önce tablo
    for sel in ["table tbody tr", "table tr"]:
        try:
            rows = page.query_selector_all(sel)
            for r in rows[:80]:
                t = (r.inner_text() or "").strip()
                if t and ok_line(t):
                    items.append(t.replace("\n", " | "))
        except Exception:
            pass

    # Olmazsa list/kart
    if not items:
        for sel in [".card", ".list-group-item", "li", "div"]:
            try:
                els = page.query_selector_all(sel)
                for e in els[:120]:
                    t = (e.inner_text() or "").strip()
                    if t and ok_line(t):
                        items.append(t.replace("\n", " | "))
            except Exception:
                pass

    # uniq
    uniq = []
    seen = set()
    for it in items:
        if it not in seen:
            seen.add(it)
            uniq.append(it)

    return uniq

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

        # login başlangıcı
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        # DEBUG
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # --- 1) FINANCIAL CHECK (özellikle borç uyarısının çıktığı sayfa) ---
        financial_urls = [
            urljoin(UMS_BASE, "ExamRegistration"),
            urljoin(UMS_BASE, "ExamRegistration/List"),
        ]

        print("[UMS] Financial check sayfaları deneniyor...")
        for url in financial_urls:
            try:
                print(f"[UMS] Trying financial URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2200)
                if _is_404(page):
                    print("[UMS] -> 404, skip")
                    continue
                html = page.content() or ""
                if _has_financial_block(html):
                    result["financial_block"] = True
                    result["details"].append(f"Detyrim Financiar tespit edildi: {url}")
                    print("[UMS] ⚠️ Financial block FOUND")
                    # blok varsa exam kayıtlarını yine deneyebiliriz ama çoğu zaman görünmez
                    break
            except Exception as e:
                print(f"[UMS] financial URL failed: {url} | {str(e)[:120]}")
                continue

        # --- 2) EXAM LIST CHECK (kayıt/list sayfaları) ---
        exam_urls = [
            urljoin(UMS_BASE, "StudentExamRegistration/List"),
            urljoin(UMS_BASE, "StudentExamRegistration"),
            urljoin(UMS_BASE, "MyExams"),
        ]

        # Menüden de exam linkleri topla (Provimet e Mia / Regjistrimi i Provimit)
        try:
            print("[UMS] Menüden exam linkleri çekiliyor...")
            page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            anchors = page.query_selector_all("a[href]")
            for a in anchors:
                href = (a.get_attribute("href") or "").strip()
                txt = (a.inner_text() or "").strip()
                if not href:
                    continue
                full = href if href.startswith("http") else urljoin(UMS_BASE, href)
                key = (txt + " " + href).lower()
                if any(k in key for k in ["provim", "exam", "regjistr", "registration"]):
                    if full not in exam_urls:
                        exam_urls.append(full)
        except Exception:
            pass

        result["details"].append(f"Exam URL aday sayısı: {len(exam_urls)}")

        print("[UMS] Exam sayfaları deneniyor...")
        all_items = []
        for url in exam_urls[:20]:
            try:
                print(f"[UMS] Trying exam URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                if _is_404(page):
                    print("[UMS] -> 404, skip")
                    continue

                # burada da financial block çıkabilir
                html = page.content() or ""
                if (not result["financial_block"]) and _has_financial_block(html):
                    result["financial_block"] = True
                    result["details"].append(f"Detyrim Financiar tespit edildi (exam sayfasında): {url}")

                items = _extract_exam_items(page)
                if items:
                    result["details"].append(f"Exam sayfasından satır alındı: {url} ({len(items)})")
                    all_items.extend(items)

                # debug sadece ilk işe yarayan sayfada
                if items:
                    print("[UMS] DEBUG after exam items found")
                    debug_page(page, "UMS")
                    break

            except Exception as e:
                result["details"].append(f"Exam URL hata: {url} -> {str(e)[:90]}")

        # uniq birleşik
        uniq = []
        seen = set()
        for it in all_items:
            if it not in seen:
                seen.add(it)
                uniq.append(it)

        if uniq:
            result["exam_found"] = True
            result["exam_items"] = uniq[:10]
            result["details"].append(f"Toplam sınav satırı: {len(uniq)}")
        else:
            result["exam_found"] = False
            result["details"].append("Sınav satırı bulunamadı (sayfa boş / JS ile doluyor olabilir).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
