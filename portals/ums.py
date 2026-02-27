# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _is_404(page) -> bool:
    try:
        h = _norm(page.content())
        return ("404" in h and "not found" in h) or "page you are looking for doesn't exist" in h
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
    bad_contains = [
        "portali", "paneli", "profili", "ndihmë", "help",
        "plani i orarit", "vlerësimet", "transkripta",
        "regjistrimi i semestrit", "lista e pagesave", "tema e diplomës",
        "© 2024", "të gjitha të drejtat",
        "go back", "page not found",
        "shko te profili", "shiko detajet e pagesës",
    ]

    items = []

    def ok_line(t: str) -> bool:
        t = (t or "").strip()
        tl = _norm(t)
        if len(t) < 10:
            return False
        if any(b in tl for b in bad_contains):
            return False
        # sınav satırı ipuçları
        if any(k in tl for k in ["provim", "exam", "regjistr", "data", "date", "ora", "salla", "room", "kurs", "course"]):
            return True
        # tarihe benzer bir pattern
        if "202" in tl or "." in tl:
            return True
        return False

    # Tablo satırları
    for sel in ["table tbody tr", "table tr"]:
        try:
            rows = page.query_selector_all(sel)
            for r in rows[:100]:
                t = (r.inner_text() or "").strip()
                if t and ok_line(t):
                    items.append(t.replace("\n", " | "))
        except Exception:
            pass

    # Kart/list fallback
    if not items:
        for sel in [".card", ".list-group-item", "li", "div"]:
            try:
                els = page.query_selector_all(sel)
                for e in els[:160]:
                    t = (e.inner_text() or "").strip()
                    if t and ok_line(t):
                        items.append(t.replace("\n", " | "))
            except Exception:
                pass

    # uniq
    uniq, seen = [], set()
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

        # SPA: profile'a git ve networkidle bekle
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(2000)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # --- Menü linklerini JS yüklendikten sonra gerçekten çek ---
        print("[UMS] Menü linkleri toplanıyor (SPA)...")
        menu_links = []
        try:
            # sayfada menü metinlerinin görünmesini bekle (yoksa anchors boş kalıyor)
            page.wait_for_selector("text=PORTALI", timeout=15000)
        except Exception:
            pass

        try:
            raw = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({href: e.getAttribute('href') || '', text: (e.innerText || '').trim()}))"
            )
            for it in raw or []:
                href = (it.get("href") or "").strip()
                txt = (it.get("text") or "").strip()
                if not href:
                    continue
                full = href if href.startswith("http") else urljoin(UMS_BASE, href)
                key = (txt + " " + href).lower()
                if any(k in key for k in ["provim", "exam", "regjistr", "registration", "pagesa", "payment"]):
                    if full not in menu_links:
                        menu_links.append(full)
        except Exception as e:
            result["details"].append(f"Menü link okuma hatası: {str(e)[:90]}")

        # --- Financial check: bu sayfalar borç uyarısını genelde veriyor ---
        financial_urls = [
            urljoin(UMS_BASE, "ExamRegistration"),
            urljoin(UMS_BASE, "ExamRegistration/List"),
            urljoin(UMS_BASE, "StudentExamRegistration"),
            urljoin(UMS_BASE, "StudentExamRegistration/List"),
        ]

        print("[UMS] Financial check URL'leri:")
        for u in financial_urls:
            print(f"[UMS]  - {u}")

        for url in financial_urls:
            try:
                print(f"[UMS] Trying financial URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)

                if _is_404(page):
                    print("[UMS] -> 404, skip")
                    continue

                html = page.content() or ""
                if _has_financial_block(html):
                    result["financial_block"] = True
                    result["details"].append(f"Detyrim Financiar tespit edildi: {url}")
                    print("[UMS] ⚠️ Financial block FOUND")
                    print("[UMS] DEBUG financial page")
                    debug_page(page, "UMS")
                    break
            except Exception as e:
                print(f"[UMS] financial URL failed: {url} | {str(e)[:120]}")
                continue

        # --- Exam sayfaları: menüden gelenleri + bilinenleri birleştir ---
        exam_urls = []
        # bilinenler
        for u in [
            urljoin(UMS_BASE, "StudentExamRegistration/List"),
            urljoin(UMS_BASE, "StudentExamRegistration"),
            urljoin(UMS_BASE, "MyExams"),
            urljoin(UMS_BASE, "ExamRegistration"),
            urljoin(UMS_BASE, "ExamRegistration/List"),
        ]:
            if u not in exam_urls:
                exam_urls.append(u)

        # menü linkleri ekle
        for u in menu_links:
            if u not in exam_urls:
                exam_urls.append(u)

        result["details"].append(f"Exam URL aday sayısı: {len(exam_urls)}")
        print(f"[UMS] Exam URL aday sayısı: {len(exam_urls)}")
        for u in exam_urls[:25]:
            print(f"[UMS] Candidate: {u}")

        print("[UMS] Exam sayfaları deneniyor...")
        all_items = []
        for url in exam_urls[:25]:
            try:
                print(f"[UMS] Trying exam URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)

                if _is_404(page):
                    print("[UMS] -> 404, skip")
                    continue

                html = page.content() or ""
                if (not result["financial_block"]) and _has_financial_block(html):
                    result["financial_block"] = True
                    result["details"].append(f"Detyrim Financiar tespit edildi (exam sayfasında): {url}")
                    print("[UMS] ⚠️ Financial block FOUND on exam page")

                items = _extract_exam_items(page)
                if items:
                    result["details"].append(f"Exam sayfasından satır alındı: {url} ({len(items)})")
                    all_items.extend(items)
                    print("[UMS] ✅ Exam items found")
                    print("[UMS] DEBUG after exam items found")
                    debug_page(page, "UMS")
                    break

            except Exception as e:
                result["details"].append(f"Exam URL hata: {url} -> {str(e)[:90]}")

        # uniq
        uniq, seen = [], set()
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
