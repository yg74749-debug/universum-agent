from .browser import get_context, close_context

def run_ums():
    result = {
        "ok": False,
        "error": None,
        "financial_block": False,
        "exam_found": False,
        "details": []
    }

    try:
        # ... burada senin mevcut login + sayfa gezme kodun var ...

        # örnek: login başarılıysa
        result["ok"] = True
        result["details"].append("UMS login başarılı")

        # örnek: mali yükümlülük tespiti yaptıysan
        # result["financial_block"] = True

        # örnek: sınav kaydı gördüysen
        # result["exam_found"] = True

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    return lines
