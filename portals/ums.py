# portals/ums.py
import json
from .browser import get_context, close_context, debug_page

UMS_URL = "https://ums-student-portal.universum-ks.org/"
API_DOMAIN = "ums-university-api.universum-ks.org"

# UMS sayfalarında borç uyarısı bazen TR bazen AL gelir
FINANCIAL_MARKERS = [
    "Mali Yükümlülük", "Mali Yukumluluk",
    "Detyrim Financiar", "detyrim financiar",
    "borxh", "Keni një detyrim financiar",
    "Disa funksione janë të kufizuara",
]

def _safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None

def _flatten_strings(obj, out, limit=8000):
    """JSON içindeki tüm stringleri toplar (endpoint bağımsız tarama için)."""
    if len(out) >= limit:
        return
    if obj is None:
        return
    if isinstance(obj, str):
        s = obj.strip()
        if s:
            out.append(s)
        return
    if isinstance(obj, (int, float, bool)):
        return
    if isinstance(obj, list):
        for x in obj[:300]:
            _flatten_strings(x, out, limit=limit)
        return
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:500]:
            if isinstance(k, str) and k.strip():
                out.append(k.strip())
            _flatten_strings(v, out, limit=limit)

def _score_exam_json(j):
    """Bu JSON sınav/registration ile alakalı mı? Basit skor."""
    strings = []
    _flatten_strings(j, strings, limit=4000)
    blob = " | ".join(strings).lower()

    keywords = [
        "exam", "exams", "provim", "provimet",
        "registration", "regjistrim", "regjistrimi",
        "studentexam", "examregistration",
        "date", "data", "ora", "time",
        "course", "lënda", "lenda",
    ]
    score = 0
    for k in keywords:
        if k in blob:
            score += 1

    # Eğer JSON’da “list” gibi çok büyük ve alakasız şey varsa skor kırabiliriz (opsiyonel)
    return score, blob

def _extract_exam_items(j):
    """
    Çok esnek: JSON neresinde list varsa onu yakalayıp
    1-2 satırlık okunabilir stringler üretmeye çalışır.
    """
    items = []

    def walk(o):
        if o is None:
            return
        if isinstance(o, list):
            # list of dicts -> candidate
            if o and all(isinstance(x, dict) for x in o[:20]):
                for d in o[:50]:
                    # olası alan adları (tam bilmesek de)
                    fields = []
                    for key in ["courseName", "course", "subject", "lenda", "lënda",
                                "examDate", "date", "data", "time", "ora",
                                "room", "salla", "location",
                                "status", "state"]:
                        if key in d and d[key] not in (None, "", []):
                            fields.append(f"{key}={d[key]}")
                    if fields:
                        items.append(" | ".join(fields))
                    else:
                        # fallback: kısa json
                        try:
                            items.append(json.dumps(d, ensure_ascii=False)[:220])
                        except Exception:
                            pass
            else:
                for x in o[:200]:
                    walk(x)
            return
        if isinstance(o, dict):
            for v in list(o.values())[:500]:
                walk(v)

    walk(j)

    # unique + temiz
    uniq = []
    seen = set()
    for it in items:
        it = (it or "").strip().replace("\n", " ")
        if not it:
            continue
        if it not in seen:
            seen.add(it)
            uniq.append(it)

    return uniq[:10]

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

        api_json_hits = []   # (url, status, json_obj)
        api_nonjson_hits = []  # (url, status, ct)

        ctx = get_context("ums_state.json")
        page = ctx.new_page()

        # API cevaplarını yakala
        def on_response(resp):
            try:
                url = resp.url or ""
                if API_DOMAIN not in url:
                    return

                status = resp.status
                ct = (resp.headers or {}).get("content-type", "")

                # JSON içerik yakala
                if "application/json" in ct.lower():
                    txt = resp.text()
                    j = _safe_json_loads(txt)
                    if j is not None:
                        api_json_hits.append((url, status, j))
                    else:
                        api_nonjson_hits.append((url, status, ct + " (json parse failed)"))
                else:
                    api_nonjson_hits.append((url, status, ct))
            except Exception:
                pass

        page.on("response", on_response)

        page.goto(UMS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")
        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # Menüde link var mı (route tahmini değil; sadece ek trafik yaratıp API çağrısı tetiklemek için)
        # UMS SPA bazen route değişince API çağırıyor.
        candidates = [
            UMS_URL + "ExamRegistration",
            UMS_URL + "StudentExamRegistration",
            UMS_URL + "StudentExamRegistration/List",
            UMS_URL + "MyExams",
            UMS_URL + "Payments",
            UMS_URL + "StudentPayments",
        ]
        for url in candidates:
            try:
                print(f"[UMS] Visiting route: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
            except Exception:
                continue

        # Finansal blok: sayfa textinden yakala (TR + AL)
        body_text = ""
        try:
            body_text = page.inner_text("body")
        except Exception:
            body_text = page.content()

        for marker in FINANCIAL_MARKERS:
            if marker.lower() in (body_text or "").lower():
                result["financial_block"] = True
                result["details"].append("Detyrim Financiar / Mali Yükümlülük uyarısı tespit edildi.")
                print("[UMS] ⚠️ Financial block detected from page text")
                break

        # API özet
        print(f"[UMS] JSON hits: {len(api_json_hits)}")
        result["details"].append(f"JSON hit sayısı: {len(api_json_hits)}")

        # JSON’lar içinde sınavla en alakalı olanı seç
        best = None
        best_score = -1
        best_url = None
        for (url, status, j) in api_json_hits:
            score, _ = _score_exam_json(j)
            if score > best_score:
                best_score = score
                best = j
                best_url = url

        if best is not None and best_score >= 2:
            items = _extract_exam_items(best)
            if items:
                result["exam_found"] = True
                result["exam_items"] = items
                result["details"].append(f"Sınav JSON bulundu (score={best_score})")
                result["details"].append(f"Kaynak API: {best_url}")
                print(f"[UMS] ✅ Exam JSON selected score={best_score}")
            else:
                result["details"].append(f"Exam JSON adayı var ama satır çıkarılamadı (score={best_score})")
                result["details"].append(f"Kaynak API: {best_url}")
        else:
            # En azından debug: hangi API’ler vurulmuş?
            # (Telegram raporun aşırı uzamasın diye ilk 3)
            for (url, status, j) in api_json_hits[:3]:
                result["details"].append(f"API JSON: {status} {url}")
            if not api_json_hits:
                result["details"].append("UMS API JSON yakalanamadı (state/cookie eksik olabilir).")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
