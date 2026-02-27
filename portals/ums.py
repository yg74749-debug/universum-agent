# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _norm(s: str) -> str:
    return (s or "").strip().lower()

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
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # Menüden sınav sayfası linkini yakala
        print("[UMS] Menü linkleri taranıyor...")
        candidates = []
        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            href = (a.get_attribute("href") or "").strip()
            txt = (a.inner_text() or "").strip()
            if not href:
                continue

            full = href if href.startswith("http") else urljoin(UMS_BASE, href)

            key = (txt + " " + href).lower()
            if any(k in key for k in ["provim", "exam", "regjistr", "registration"]):
                if full not in candidates:
                    candidates.append(full)

        # Fallback olası route’lar
        for extra in [
            urljoin(UMS_BASE, "StudentExamRegistration/List"),
            urljoin(UMS_BASE, "StudentExamRegistration"),
            urljoin(UMS_BASE, "ExamRegistration/List"),
            urljoin(UMS_BASE, "ExamRegistration"),
            urljoin(UMS_BASE, "MyExams"),
            urljoin(UMS_BASE, "Provimet"),
        ]:
            if extra not in candidates:
                candidates.append(extra)

        result["details"].append(f"Aday sınav linki sayısı: {len(candidates)}")

        # Exam sayfasını bul
        chosen = None
        print("[UMS] Exam sayfası aranıyor...")
        for url in candidates[:25]:
            try:
                print(f"[UMS] Trying exam URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2200)

                html_low = _norm(page.content())
                if "404" in html_low and "not found" in html_low:
                    print("[UMS] -> 404, skip")
                    continue

                chosen = url
                result["details"].append(f"Exam sayfası seçildi: {url}")
                print("[UMS] ✅ Exam page OK")
                print("[UMS] DEBUG after exam goto")
                debug_page(page, "UMS")
                break
            except Exception as e:
                print(f"[UMS] Exam URL failed: {url} | {str(e)[:120]}")
                continue

        if not chosen:
            result["details"].append("Sınav sayfası bulunamadı (menü/route farklı olabilir).")
            return result

        # ✅ Financial block tespiti (senin sayfandaki tam kelimeler dahil)
        print("[UMS] Financial block aranıyor...")
        html = page.content() or ""
        financial_keys = [
            "Mali Yükümlülük", "Mali Yukumluluk",
            "financial obligation", "financial obligations",
            "detyrim financiar", "detyrime financiare",  # AL
            "borxh",  # debt kelimesi
            "Disa funksione janë të kufizuara",  # uyarı cümlesi
        ]
        if any(k.lower() in html.lower() for k in financial_keys):
            result["financial_block"] = True
            result["details"].append("Detyrim Financiar / borç uyarısı tespit edildi (fonksiyonlar kısıtlı olabilir).")
            print("[UMS] ⚠️ Financial block FOUND")
            # blok varsa sınav listelemeyi denesek bile genelde boş olur
            return result
        else:
            print("[UMS] Financial block yok")

        # ✅ Sınav satırlarını daha temiz çıkar (navbar/menü spamını kes)
        bad_contains = [
            "portali", "paneli", "profili", "ndihmë", "help",
            "plani i orarit", "vlerësimet", "transkripta",
            "regjistrimi i semestrit", "lista e pagesave", "tema e diplomës",
            "© 2024", "të gjitha të drejtat",
        ]

        items = []

        # Önce tablo satırları (en doğru yer genelde burası)
        for sel in ["table tbody tr", "table tr"]:
            try:
                rows = page.query_selector_all(sel)
                for r in rows[:60]:
                    t = (r.inner_text() or "").strip()
                    if not t:
                        continue
                    tl = _norm(t)
                    if any(b in tl for b in bad_contains):
                        continue
                    if len(t) < 12:
                        continue
                    # sınav satırına benzer ipuçları
                    if any(k in tl for k in ["provim", "exam", "regjistr", "data", "date", "ora", "salla", "room", "kurs", "course"]):
                        items.append(t.replace("\n", " | "))
            except Exception:
                pass

        # Tablo yoksa kart/list dene (ama filtreli)
        if not items:
            for sel in [".card", ".list-group-item", "li"]:
                try:
                    els = page.query_selector_all(sel)
                    for e in els[:80]:
                        t = (e.inner_text() or "").strip()
                        if not t:
                            continue
                        tl = _norm(t)
                        if any(b in tl for b in bad_contains):
                            continue
                        if len(t) < 12:
                            continue
                        if any(k in tl for k in ["provim", "exam", "regjistr", "data", "date", "ora", "salla", "room"]):
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

        if uniq:
            result["exam_found"] = True
            result["exam_items"] = uniq[:10]
            result["details"].append(f"Sınav satırı bulundu: {len(uniq)}")
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
