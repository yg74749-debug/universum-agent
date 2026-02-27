# portals/ums.py
import json
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _has_financial_block_text(text: str) -> bool:
    tl = (text or "").lower()
    keys = [
        "mali yükümlülük", "mali yukumluluk",
        "detyrim financiar", "keni një detyrim financiar",
        "borxh", "financial obligation"
    ]
    return any(k in tl for k in keys)

def _safe_preview(obj, maxlen=240):
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return (s[:maxlen] + "...") if len(s) > maxlen else s

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

        # --- NETWORK CAPTURE ---
        captured = {
            "json_hits": [],      # (url, status)
            "candidates": [],     # urls that look like endpoints we care about
            "parsed": []          # small previews
        }

        def on_response(resp):
            try:
                url = resp.url or ""
                status = resp.status
                ctype = (resp.headers.get("content-type", "") or "").lower()

                # sadece universum alanı + json/ api tipleri
                if "ums-student-portal.universum-ks.org" not in url:
                    return

                # aday endpoint: exam/provim/registration/payment
                key = url.lower()
                if any(k in key for k in ["exam", "provim", "registration", "regjistr", "payment", "pagesa", "invoice", "fee", "finance", "obligation"]):
                    if url not in captured["candidates"]:
                        captured["candidates"].append(url)

                if "application/json" in ctype:
                    captured["json_hits"].append((url, status))
            except Exception:
                pass

        page.on("response", on_response)

        # Login sonrası menü renderını tetiklemek için profile aç
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # Birkaç kritik route gez (network endpointleri tetiklemek için)
        routes = [
            "StudentExamRegistration/List",
            "ExamRegistration",
            "MyExams",
            "Payments",
            "StudentPayments",
            "ExamRegistration/List",
        ]
        for r in routes:
            url = urljoin(UMS_BASE, r)
            print(f"[UMS] Visiting route: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                # finansal blok metnini UI text'ten yakala
                try:
                    body = page.inner_text("body")
                    if _has_financial_block_text(body):
                        result["financial_block"] = True
                except Exception:
                    pass
            except Exception as e:
                result["details"].append(f"Route hata: {url} -> {str(e)[:80]}")

        # --- JSON endpointleri listele (debug için) ---
        result["details"].append(f"JSON hit sayısı: {len(captured['json_hits'])}")
        result["details"].append(f"Endpoint aday sayısı: {len(captured['candidates'])}")

        print(f"[UMS] JSON hits: {len(captured['json_hits'])}")
        print(f"[UMS] Candidates: {len(captured['candidates'])}")

        # Öncelik: JSON hit'lerden exam/registration geçenleri sırala
        json_urls = [u for (u, s) in captured["json_hits"] if s == 200]
        priority = []
        for u in json_urls:
            k = u.lower()
            if any(x in k for x in ["exam", "provim", "registration", "regjistr"]):
                priority.append(u)
        # fallback: candidates listesinden json olmasa bile dene (bazı api'ler text/json dönebiliyor)
        for u in captured["candidates"]:
            if u not in priority:
                priority.append(u)

        # Çok uzamasın
        priority = priority[:25]

        # --- endpoint parse denemesi ---
        def try_parse_url(api_url: str):
            try:
                # aynı sayfada fetch ile al (cookie taşınır)
                js = """
                async (u) => {
                  try {
                    const r = await fetch(u, { credentials: 'include' });
                    const ct = (r.headers.get('content-type') || '').toLowerCase();
                    const status = r.status;
                    let dataText = await r.text();
                    return { status, ct, dataText };
                  } catch (e) {
                    return { status: -1, ct: '', dataText: String(e) };
                  }
                }
                """
                out = page.evaluate(js, api_url)
                status = out.get("status")
                ct = out.get("ct", "")
                txt = out.get("dataText", "")

                if status != 200:
                    return None

                # json parse
                data = None
                if "application/json" in (ct or "").lower():
                    data = json.loads(txt)
                else:
                    # bazıları json ama content-type yanlış
                    try:
                        data = json.loads(txt)
                    except Exception:
                        return None

                return data
            except Exception:
                return None

        parsed_any = None
        parsed_from = None

        for api_url in priority:
            data = try_parse_url(api_url)
            if data is None:
                continue

            parsed_any = data
            parsed_from = api_url
            captured["parsed"].append((api_url, _safe_preview(data, 260)))

            # data içinde anlamlı “list” arıyoruz
            # çok farklı şekillerde gelebilir: {items:[...]}, {data:[...]}, [...]
            break

        if parsed_any is None:
            result["details"].append("API JSON parse edilemedi (cookie/state eksik veya endpoint yok).")
            return result

        result["details"].append(f"JSON parse OK: {parsed_from}")
        result["details"].append(f"JSON preview: {captured['parsed'][0][1]}")

        # --- exam item çıkarma (genel) ---
        items = []

        def add_item(s: str):
            s = (s or "").strip()
            if not s:
                return
            if len(s) < 6:
                return
            if s not in items:
                items.append(s)

        def walk(obj, depth=0):
            if depth > 5:
                return
            if isinstance(obj, dict):
                # olası alanlar
                for k in ["course", "courseName", "subject", "name", "title"]:
                    if k in obj and isinstance(obj[k], str):
                        add_item(obj[k])
                for k in ["date", "examDate", "startDate", "time", "startTime", "room", "location", "status"]:
                    if k in obj and isinstance(obj[k], (str, int, float)):
                        add_item(f"{k}: {obj[k]}")
                for v in obj.values():
                    walk(v, depth+1)
            elif isinstance(obj, list):
                for v in obj[:50]:
                    walk(v, depth+1)

        walk(parsed_any)

        if items:
            result["exam_found"] = True
            result["exam_items"] = items[:10]
            result["details"].append(f"Exam item çıkarıldı: {len(items)}")
        else:
            result["details"].append("JSON geldi ama exam item çıkarılamadı (format farklı).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
