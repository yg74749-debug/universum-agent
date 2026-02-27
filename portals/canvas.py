from .browser import get_context, close_context

def run_canvas():
    lines = ["📌 CANVAS RAPORU"]

    try:
        ctx = get_context("canvas_state.json")
        page = ctx.new_page()
        page.goto("https://canvas.universum-ks.org/")
        page.wait_for_timeout(3000)
        lines.append("✅ Canvas açıldı.")

    except Exception as e:
        lines.append(f"❌ Canvas hata: {type(e).__name__}")

    finally:
        try:
            close_context(ctx)
        except:
            pass

    return lines
