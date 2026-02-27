from playwright.sync_api import sync_playwright

def get_context(storage_state_path):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(storage_state=storage_state_path)
    context._pw = pw
    context._browser = browser
    return context

def close_context(context):
    browser = getattr(context, "_browser", None)
    pw = getattr(context, "_pw", None)
    context.close()
    if browser:
        browser.close()
    if pw:
        pw.stop()
