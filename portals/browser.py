from playwright.sync_api import sync_playwright

def get_context(storage_state_path: str):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(storage_state=storage_state_path)
    page = context.new_page()
    return pw, browser, context, page

def close_context(pw, browser, context):
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
        def debug_page(page, tag=""):
    try:
        url = page.url
    except Exception:
        url = "?"
    try:
        title = page.title()
    except Exception:
        title = "?"
    try:
        text = page.inner_text("body") or ""
        text_len = len(text)
        snippet = text[:400].replace("\n", " ").replace("\r", " ")
    except Exception:
        text_len = -1
        snippet = "?"
    print(f"[{tag}] URL: {url}")
    print(f"[{tag}] TITLE: {title}")
    print(f"[{tag}] BODY_LEN: {text_len}")
    print(f"[{tag}] SNIP: {snippet}")
