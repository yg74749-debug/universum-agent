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

        # login kontrol (çok genel)
        page.wait_for_timeout(1500)
        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        # DEBUG: Login sonrası neredeyiz?
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # Sınav sayfasını yakalamak için birkaç olası path dene
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
                page.wait_for_timeout(2000)  # 1.2 yerine 2.0
                print("[UMS] DEBUG after exam goto")
                debug_page(page, "UMS")

                exam_page_opened = True
                result["details"].append(f"Exam sayfası denendi: {url}")
                break
            except Exception as e:
                print(f"[UMS] Exam URL failed: {url} | {str(e)[:120]}")
                continue

        if not exam_page_opened:
            # En azından ana sayfada text arayalım
            result["details"].append("Exam URL bulunamadı, ana sayfada kontrol edildi.")

        # DEBUG: Mali yükümlülük kontrolünden hemen önce sayfanın durumu
        print("[UMS] DEBUG before financial check")
        debug_page(page, "UMS")

        # Mali yükümlülük tespiti (sayfa içeriğinde string arama)
        print("[UMS] 'Mali Yükümlülük' aranıyor...")
        html = page.content()
        if "Mali Yükümlülük" in html or "Mali Yükumluluk" in html:
            result["financial_block"] = True
            result["details"].append("Mali Yükümlülük uyarısı tespit edildi (erişim kısıtlı olabilir).")
            print("[UMS] ⚠️ Mali Yükümlülük VAR")
            return result
        else:
            print("[UMS] Mali Yükümlülük yok")

        # Sınav listesini arama (çok genel selector yaklaşımı)
        text = page.inner_text("body")
        if ("Sınav" in text) and ("Kayıt" in text or "Kayıtlar" in text):
            result["details"].append("Sınav sayfasında 'Sınav/Kayıt' metni görüldü.")

        # olası liste elemanlarını çek (li, tr)
        items = []
        for sel in ["table tr", "ul li", ".card", ".list-group-item"]:
            try:
                els = page.query_selector_all(sel)
                for e in els[:30]:
                    t = (e.inner_text() or "").strip()
                    if t and ("202" in t or "Sınav" in t or "Exam" in t):
                        items.append(t.replace("\n", " | "))
            except Exception:
                pass

        # temizle
        uniq = []
        seen = set()
        for it in items:
            if it not in seen:
                seen.add(it)
                uniq.append(it)

        if uniq:
            result["exam_found"] = True
            result["exam_items"] = uniq[:10]
            result["details"].append(f"Sınav listesi bulundu: {len(uniq)} satır.")
        else:
            result["details"].append("Sınav listesi bulunamadı (sayfa boş/format farklı olabilir).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
