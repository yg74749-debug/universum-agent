# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _is_404(page) -> bool:
    try:
        t = _norm(page.inner_text("body"))
        return ("404" in t and "page" in t and "not found" in t) or "doesn't exist" in t
    except Exception:
        try:
            h = _norm(page.content())
            return "404" in h and "not found" in h
        except Exception:
            return False

def _has_financial_block_text(text: str) -> bool:
    tl = (text or "").lower()
    keys = [
        "mali yükümlülük", "mali yukumluluk",
        "financial obligation", "financial obligations",
        "detyrim financiar", "detyrime financiare",
        "borxh",
        "disa funksione janë të kufizuara",
        "keni një detyrim financiar",
        "detyrim financiar"
    ]
    return any(k in tl for k in keys)

def _extract_exam_items(page):
    bad_contains = [
        "portali", "paneli", "profili", "ndihmë", "help",
        "plani i orarit", "vlerësimet", "transkripta",
        "regjistrimi i semestrit", "lista e pagesave", "tema e diplomës",
        "© 2024", "të gjitha të drejtat",
        "go back", "page not found",
        "shko te profili", "shiko detajet e pagesës",
        "duke ngarkuar", "loading"
    ]

    def ok_line(t: str) -> bool:
        t = (t or "").strip()
        tl = _norm(t)
        if len(t) < 12:
            return False
        if any(b in tl for b in bad_contains):
            return False
        # sınav/register ipuçları
        if any(k in tl for k in ["provim", "exam", "regjistr", "registration", "data", "date", "ora", "salla", "room", "kurs", "course"]):
            return True
        # tarih benzeri
        if any(x in tl for x in ["202", ".", ":", "/"]):
            return True
        return False

    items = []

    # Önce tablo
    for sel in ["table tbody tr", "table tr"]:
        try:
            rows = page.query_selector_all(sel)
            for r in rows[:120]:
                t = (r.inner_text() or "").strip()
                if t and ok_line(t):
                    items.append(t.replace("\n", " | "))
        except Exception:
            pass

    # sonra kart/list fallback
    if not items:
        for sel in [".card", ".list-group-item", "li", "div"]:
            try:
                els = page.query_selector_all(sel)
                for e in els[:220]:
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

def _wait_spa_data(page, label: str, max_seconds: int = 12):
    """
    React/SPA sayfalarında veri geç geliyorsa:
    - networkidle dene
    - body text uzunluğu artıyor mu polling
    """
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    prev_len = 0
    stable = 0
    for i in range(max_seconds):
        try:
            t = page.inner_text("body")
        except Exception:
            t = page.content() or ""

        cur = len(t or "")
        print(f"[UMS] {label} wait tick {i+1}/{max_seconds} | body_len={cur}")
        if cur > prev_len + 50:
            stable = 0
            prev_len = cur
        else:
            stable += 1

        # 3 tick stabil kaldıysa yeter
        if stable >= 3 and cur > 400:
            break

        page.wait_for_timeout(1000)

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

        # profile sayfası genelde login sonrası dolu menü verir
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        _wait_spa_data(page, "after login")
        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # menü linkleri
        menu_links = []
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
                # exam/registration/payment odaklı linkler
                if any(k in key for k in ["provim", "exam", "regjistr", "registration", "pagesa", "payment"]):
                    if full not in menu_links:
                        menu_links.append(full)
        except Exception as e:
            result["details"].append(f"Menü link okuma hatası: {str(e)[:90]}")

        # bilinen + menüden gelen exam url adayları
        exam_urls = []
        base_candidates = [
            "StudentExamRegistration/List",
            "StudentExamRegistration",
            "ExamRegistration",
            "ExamRegistration/List",
            "MyExams",
            "Payments",
            "Payment",
            "StudentPayments",
            "Payment/List",
        ]
        for p in base_candidates:
            u = urljoin(UMS_BASE, p)
            if u not in exam_urls:
                exam_urls.append(u)
        for u in menu_links:
            if u not in exam_urls:
                exam_urls.append(u)

        result["details"].append(f"Exam URL aday sayısı: {len(exam_urls)}")
        print(f"[UMS] Exam URL aday sayısı: {len(exam_urls)}")

        # sayfaları dolaş
        all_items = []
        for url in exam_urls[:25]:
            try:
                print(f"[UMS] Trying URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                _wait_spa_data(page, "after goto", max_seconds=10)

                if _is_404(page):
                    print("[UMS] -> 404, skip")
                    continue

                # financial block check (HTML + visible text)
                try:
                    body_text = page.inner_text("body")
                except Exception:
                    body_text = ""
                html = ""
                try:
                    html = page.content() or ""
                except Exception:
                    html = ""

                if _has_financial_block_text(body_text) or _has_financial_block_text(html):
                    result["financial_block"] = True
                    result["details"].append(f"Detyrim Financiar tespit edildi: {url}")
                    print("[UMS] ⚠️ Financial block FOUND")
                    print("[UMS] DEBUG financial page")
                    debug_page(page, "UMS")
                    # finansal blok varsa sınav listesi zaten kısıtlı olabilir; yine de item dene
                    # break etmiyorum; bazen aynı sayfa içinde tablo da gösteriyor

                items = _extract_exam_items(page)
                if items:
                    all_items.extend(items)
                    result["details"].append(f"Sınav satırı bulundu: {len(items)} | Kaynak: {url}")
                    print("[UMS] ✅ Exam items found")
                    print("[UMS] DEBUG after items")
                    debug_page(page, "UMS")
                    # ilk anlamlı sayfada dur
                    break
                else:
                    result["details"].append(f"Bu sayfada sınav satırı yok: {url}")

            except Exception as e:
                result["details"].append(f"URL hata: {url} -> {str(e)[:90]}")

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
