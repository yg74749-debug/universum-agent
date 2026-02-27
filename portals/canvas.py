from .browser import get_context, close_context

def run_canvas():
    result = {
        "ok": False,
        "error": None,
        "quiz_found": False,
        "survey_filled": False,
        "pdf_download": False,
        "details": []
    }

    try:
        # ... burada login + gezme kodun var ...

        result["ok"] = True
        result["details"].append("Canvas login başarılı")

        # quiz bulduysan:
        # result["quiz_found"] = True

        # survey doldurduysan:
        # result["survey_filled"] = True

        # pdf indirdiyse:
        # result["pdf_download"] = True

        return result

    except Exception as e:
        result["error"] = str(e)
        return result

    return lines
