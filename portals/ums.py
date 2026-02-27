from .browser import get_context, close_context

def run_ums():
    lines = ["📌 UMS RAPORU"]

    try:
        ctx = get_context("ums_state.json")
        page = ctx.new_page()
        page.goto("https://ums-student-portal.universum-ks.org/")
        page.wait_for_timeout(3000)
        lines.append("✅ UMS açıldı.")

    except Exception as e:
        lines.append(f"❌ UMS hata: {type(e).__name__}")

    finally:
        try:
            close_context(ctx)
        except:
            pass

    return lines
