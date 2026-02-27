# portals/ums.py
import json
from urllib.parse import urljoin
from .browser import get_context, close_context, debug_page

UMS_BASE = "https://ums-student-portal.universum-ks.org/"

def _clip(s: str, n: int = 140) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[:n] + ("..." if len(s) > n else "")

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

        # ---- NETWORK CAPTURE (AGGRESSIVE) ----
        net = {
            "req_total": 0,
            "resp_total": 0,
            "by_type": {},           # resourceType -> count
            "xhr_fetch": [],         # last 30
            "other": [],             # last 30
            "json_hits": [],         # last 30 (url,status,ctype)
            "domains": {},           # domain -> count
        }

        def _domain(url: str) -> str:
            try:
                return url.split("/")[2]
            except Exception:
                return "unknown"

        def on_request(req):
            try:
                net["req_total"] += 1
                rtype = req.resource_type or "unknown"
                net["by_type"][rtype] = net["by_type"].get(rtype, 0) + 1

                u = req.url or ""
                d = _domain(u)
                net["domains"][d] = net["domains"].get(d, 0) + 1

                item = f"{rtype} | {req.method} | {u}"
                if rtype in ("xhr", "fetch"):
                    net["xhr_fetch"].append(item)
                    net["xhr_fetch"] = net["xhr_fetch"][-30:]
                else:
                    net["other"].append(item)
                    net["other"] = net["other"][-30:]
            except Exception:
                pass

        def on_response(resp):
            try:
                net["resp_total"] += 1
                u = resp.url or ""
                status = resp.status
                ctype = (resp.headers.get("content-type", "") or "").lower()
                if "json" in ctype:
                    net["json_hits"].append((u, status, ctype))
                    net["json_hits"] = net["json_hits"][-30:]
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)

        # ---- GO LOGIN LANDING ----
        page.goto(urljoin(UMS_BASE, "Profile"), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)

        result["ok"] = True
        result["details"].append("UMS login başarılı")
        print("[UMS] ✅ Login OK")

        print("[UMS] DEBUG after login")
        debug_page(page, "UMS")

        # ---- STORAGE DUMP (IMPORTANT) ----
        try:
            storage = page.evaluate("""
            () => {
              const ls = {};
              const ss = {};
              try { for (let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); ls[k]=localStorage.getItem(k); } } catch(e){}
              try { for (let i=0;i<sessionStorage.length;i++){ const k=sessionStorage.key(i); ss[k]=sessionStorage.getItem(k); } } catch(e){}
              return { localStorage: ls, sessionStorage: ss, href: location.href };
            }
            """)
            # çok uzamasın diye sadece key listesi yaz
            ls_keys = list((storage.get("localStorage") or {}).keys())
            ss_keys = list((storage.get("sessionStorage") or {}).keys())
            print(f"[UMS] localStorage keys ({len(ls_keys)}): {ls_keys[:30]}")
            print(f"[UMS] sessionStorage keys ({len(ss_keys)}): {ss_keys[:30]}")
            result["details"].append(f"localStorage key sayısı: {len(ls_keys)}")
            result["details"].append(f"sessionStorage key sayısı: {len(ss_keys)}")
        except Exception as e:
            result["details"].append(f"Storage dump hata: {str(e)[:80]}")

        # ---- TRIGGER SOME ROUTES (to force API calls) ----
        routes = [
            "StudentExamRegistration/List",
            "StudentExamRegistration",
            "ExamRegistration",
            "ExamRegistration/List",
            "MyExams",
            "Payments",
            "StudentPayments",
            "Payment",
            "Payment/List",
        ]

        for r in routes:
            url = urljoin(UMS_BASE, r)
            print(f"[UMS] Visiting route: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)
            except Exception as e:
                result["details"].append(f"Route hata: {url} -> {str(e)[:80]}")

        # ---- PRINT NETWORK SUMMARY ----
        top_domains = sorted(net["domains"].items(), key=lambda x: x[1], reverse=True)[:8]
        top_types = sorted(net["by_type"].items(), key=lambda x: x[1], reverse=True)

        print(f"[UMS] REQ total: {net['req_total']} | RESP total: {net['resp_total']}")
        print(f"[UMS] Types: {top_types}")
        print(f"[UMS] Top domains: {top_domains}")

        print(f"[UMS] XHR/FETCH last {len(net['xhr_fetch'])}:")
        for line in net["xhr_fetch"]:
            print("[UMS]   " + _clip(line, 220))

        print(f"[UMS] JSON hits last {len(net['json_hits'])}:")
        for (u, st, ct) in net["json_hits"]:
            print("[UMS]   " + _clip(f"{st} | {u} | {ct}", 220))

        # telegrama da özet düş
        result["details"].append(f"REQ total: {net['req_total']} / RESP total: {net['resp_total']}")
        result["details"].append(f"JSON hit sayısı: {len(net['json_hits'])}")
        result["details"].append(f"Top domains: {top_domains}")

        # şimdilik sadece debug topluyoruz
        return result

    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if ctx:
            close_context(ctx)
        print("[UMS] ===== END =====\n")
