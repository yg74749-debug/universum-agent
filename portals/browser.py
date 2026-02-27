# portals/browser.py
from playwright.sync_api import sync_playwright


def get_context(storage_file=None):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)

    if storage_file:
        ctx = browser.new_context(storage_state=storage_file)
    else:
        ctx = browser.new_context()

    return ctx


def close_context(ctx):
    try:
        browser = ctx.browser
        ctx.close()
        browser.close()
    except Exception:
        pass


def debug_page(page, name="PAGE"):
    """
    Sayfanın URL, title ve kısa text snippetini loga basar
    """
    try:
        print(f"[{name}] URL:", page.url)
        print(f"[{name}] TITLE:", page.title())

        body = page.inner_text("body")[:400].replace("\n", " ")
        print(f"[{name}] SNIPPET:", body)

    except Exception as e:
        print(f"[{name}] DEBUG ERROR:", str(e))
