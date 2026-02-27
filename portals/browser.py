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
