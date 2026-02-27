# portals/browser.py
from pathlib import Path
from playwright.sync_api import sync_playwright

def get_context(storage_state_path: str):
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    state_file = Path(storage_state_path)

    if state_file.exists():
        ctx = browser.new_context(storage_state=str(state_file))
    else:
        ctx = browser.new_context()

    ctx._pw = p
    ctx._browser = browser
    return ctx


def close_context(ctx):
    try:
        ctx.close()
    except Exception:
        pass

    try:
        ctx._browser.close()
    except Exception:
        pass

    try:
        ctx._pw.stop()
    except Exception:
        pass


def debug_page(page, tag="DEBUG"):
    try:
        print(f"[{tag}] URL:", page.url)
    except:
        pass

    try:
        print(f"[{tag}] TITLE:", page.title())
    except:
        pass

    try:
        html = page.content()
        print(f"[{tag}] HTML PREVIEW:", html[:600])
    except Exception as e:
        print(f"[{tag}] HTML ERROR:", str(e)[:120])
