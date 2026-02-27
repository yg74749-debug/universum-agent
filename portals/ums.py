# portals/ums.py
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

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

        # Eğer menüden çıkmadıysa fallback birkaç olası route daha
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

        exam_page_opened = False
        chosen = None

        print("[UMS] Exam sayfası aranıyor...")
        for url in candidates[:25]:
            try:
                print(f"[UMS] Trying exam URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)

                html = (page.content() or "").lower()
                if "404" in html and "not found" in html:
                    print("[UMS] -> 404, skip")
                    continue

                # sayfa boş yükleniyorsa React “loading” gösterebilir, yine de kabul et
                chosen = url
                exam_page_opened = True
                result["details"].append(f"Exam sayfası seçildi: {url}")
                print("[UMS] ✅ Exam page OK")
                print("[UMS] DEBUG after exam goto")
                debug_page(page, "UMS")
                break
            except Exception as e:
                print(f"[UMS] Exam URL failed: {url} | {str(e)[:120]}")
                continue

        if not exam_page_opened:
            result["details"].append("Sınav sayfası bulunamadı (menü/route farklı olabilir).")
            return result

        # Mali yükümlülük kontrolü (TR + EN + AL ipuçları)
        print("[UMS] 'Mali Yükümlülük' aranıyor...")
        html = page.content() or ""
        financial_keys = [
            "Mali Yükümlülük", "Mali Yukumluluk",
            "financial obligation", "financial obligations",
            "detyrime financiare", "obligime financiare"
        ]
        if any(k.lower() in html.lower() for k in financial_keys):
            result["financial_block"] = True
            result["details"].append("Mali/Finansal yükümlülük uyarısı tespit edildi.")
            print("[UMS] ⚠️ Financial block FOUND")
            return result
        else:
            print("[UMS] Mali Yükümlülük yok")

        # Sınav satırlarını çekmeye çalış
        bad_lines = ["hyrja e fundit", "last login", "go back", "page not found", "duke ngarkuar"]
        items = []

        for sel in ["table tr", "tbody tr", "ul li", ".card", ".list-group-item", "div"]:
            try:
                els = page.query_selector_all(sel)
                for e in els[:80]:
                    t = (e.inner_text() or "").strip()
                    if not t:
                        continue
                    tl = t.lower()

                    if any(b in tl for b in bad_lines):
                        continue

                    # çok kısa ve alakasız olanları ele
                    if len(t) < 10:
                        continue

                    # sınav kaydına benzer ipuçları
                    if any(k in tl for k in ["provim", "exam", "data", "date", "ora", "salla", "room", "kurs", "course"]):
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
            result["details"].append("Sınav satırı bulunamadı (sayfa JS ile sonradan doluyor olabilir).")
            result["exam_found"] = False

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
