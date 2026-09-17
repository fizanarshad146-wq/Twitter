import os
import sys
import time
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
COOKIES_FILE = os.path.join(DATA_DIR, 'auth_cookies.json')
LOG_FILE = os.path.join(DATA_DIR, 'browser_launch.log')
os.makedirs(DATA_DIR, exist_ok=True)

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def main():
    log("=== Starting Standalone Browser Login Window ===")
    try:
        from playwright.sync_api import sync_playwright
        log("Playwright imported successfully.")

        with sync_playwright() as p:
            browser = None
            # Try launching standard Playwright Chromium, then Chrome/Edge fallbacks
            for channel_option in [None, "chrome", "msedge"]:
                try:
                    log(f"Attempting browser launch (channel={channel_option})...")
                    kwargs = {
                        "headless": False,
                        "args": [
                            "--start-maximized",
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox"
                        ]
                    }
                    if channel_option:
                        kwargs["channel"] = channel_option

                    browser = p.chromium.launch(**kwargs)
                    log(f"✅ Browser launched successfully (channel={channel_option})!")
                    break
                except Exception as b_err:
                    log(f"Launch attempt failed for channel={channel_option}: {b_err}")

            if not browser:
                log("CRITICAL: Failed to launch browser on all channel options!")
                return

            context = browser.new_context(viewport=None)
            page = context.new_page()
            log("Navigating to https://x.com/login ...")
            page.goto("https://x.com/login", wait_until="domcontentloaded")
            log("Window open. Waiting for user login...")

            # Poll for login completion
            for _ in range(300):
                time.sleep(2)
                if page.is_closed():
                    log("User closed browser window.")
                    break
                    
                try:
                    cookies = context.cookies()
                    has_auth = any(c.get("name") == "auth_token" and c.get("value") for c in cookies)
                    current_url = page.url

                    if has_auth or "x.com/home" in current_url or "twitter.com/home" in current_url:
                        log("✅ LOGIN DETECTED! Saving session cookies...")
                        time.sleep(2)
                        context.storage_state(path=COOKIES_FILE)
                        log(f"Cookies saved to {COOKIES_FILE}")
                        break
                except Exception as e:
                    log(f"Polling loop exception: {e}")
                    break

            try:
                context.storage_state(path=COOKIES_FILE)
                log(f"Final session cookies saved to {COOKIES_FILE}")
            except Exception as e:
                log(f"Error saving final cookies: {e}")

            try:
                browser.close()
            except Exception:
                pass
            log("Browser window closed cleanly.")

    except Exception as e:
        err_msg = f"CRITICAL ERROR in launch_browser.py: {e}\n{traceback.format_exc()}"
        log(err_msg)

if __name__ == "__main__":
    main()
