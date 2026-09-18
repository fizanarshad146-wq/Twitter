import os
import time
import json
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

class MultiAccountBrowserPoster:
    def __init__(self, log_callback=None):
        self.data_dir = DATA_DIR
        self.log_callback = log_callback

    def log(self, message, level="info", category="account"):
        print(f"[{category.upper()}] [{level.upper()}] {message}")
        if self.log_callback:
            try:
                self.log_callback(message, level, category)
            except Exception:
                pass

    def get_account_cookie_path(self, account_id):
        return os.path.join(self.data_dir, f"cookies_{account_id}.json")

    def has_saved_session(self, account_id):
        cpath = self.get_account_cookie_path(account_id)
        if not os.path.exists(cpath) or os.path.getsize(cpath) < 10:
            return False
        try:
            with open(cpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cookies = data.get("cookies", [])
                return any(c.get("name") == "auth_token" for c in cookies)
        except Exception:
            return False

    def launch_interactive_login(self, account_id):
        """
        Launches a visible Chromium window directed to x.com/i/flow/login.
        The user logs in manually on screen. Automatically detects when auth_token cookie or x.com/home is reached,
        extracts the Twitter @username, saves session cookies, and closes cleanly!
        """
        cpath = self.get_account_cookie_path(account_id)
        self.log(f"🌐 Launching visible login window for account ID {account_id}...", "info", "account")
        
        detected_username = None

        with sync_playwright() as p:
            browser = None
            exec_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            
            # Try system executables first
            for ep in exec_paths:
                if os.path.exists(ep):
                    try:
                        kwargs = {
                            "headless": False,
                            "executable_path": ep,
                            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
                        }
                        browser = p.chromium.launch(**kwargs)
                        self.log(f"Launched visible browser with Chrome/Edge: {ep}", "info", "account")
                        break
                    except Exception as ep_err:
                        self.log(f"Launch with {ep} failed: {ep_err}", "warning", "account")

            if not browser:
                for channel_option in ["chrome", "msedge", None]:
                    try:
                        kwargs = {
                            "headless": False,
                            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
                        }
                        if channel_option:
                            kwargs["channel"] = channel_option
                        browser = p.chromium.launch(**kwargs)
                        self.log(f"Launched browser with channel: {channel_option}", "info", "account")
                        break
                    except Exception as b_err:
                        self.log(f"Launch attempt failed ({channel_option}): {b_err}", "warning", "account")

            if not browser:
                return False, "Failed to launch browser process.", None

            context = browser.new_context(viewport=None)
            page = context.new_page()
            
            self.log("Opening https://x.com/i/flow/login for user login...", "info", "account")
            try:
                page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                self.log(f"Initial navigation warning: {nav_err}", "warning", "account")

            self.log("Login window open. Waiting for user to complete login on screen...", "info", "account")

            # Wait loop: poll for auth_token cookie or login completion (up to 5 minutes)
            for _ in range(150):
                time.sleep(2)
                if page.is_closed():
                    self.log("Window closed by user.", "warning", "account")
                    break

                try:
                    cookies = context.cookies()
                    has_auth = any(c.get("name") == "auth_token" and c.get("value") for c in cookies)
                    current_url = page.url

                    if has_auth or "x.com/home" in current_url or "twitter.com/home" in current_url:
                        self.log("🟢 Login detected! Saving session cookies...", "success", "account")
                        
                        time.sleep(2)
                        context.storage_state(path=cpath)
                        
                        try:
                            # Primary method: Profile link href
                            profile_link = page.locator('a[data-testid="AppTabBar_Profile_Link"]').first
                            if profile_link.is_visible(timeout=3000):
                                href = profile_link.get_attribute('href')
                                if href and href.startswith('/') and len(href) > 1:
                                    detected_username = href.strip('/')
                            
                            # Secondary fallback: Account switcher button text
                            if not detected_username:
                                handle_el = page.locator('div[data-testid="SideNav_AccountSwitcher_Button"] span').first
                                if handle_el.is_visible(timeout=3000):
                                    text = handle_el.inner_text()
                                    if "@" in text:
                                        detected_username = text.replace("@", "").strip()
                        except Exception as h_err:
                            print(f"[MultiBrowser] Handle extraction info: {h_err}")

                        break
                except Exception as e:
                    print(f"[MultiBrowser] Polling loop exception: {e}")
                    break

            try:
                context.storage_state(path=cpath)
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass

        if self.has_saved_session(account_id):
            return True, "Login completed and session saved successfully!", detected_username
        else:
            return False, "Login window closed before login was completed.", None

    def save_manual_cookies(self, account_id, raw_input):
        cpath = self.get_account_cookie_path(account_id)
        raw_input = raw_input.strip()
        cookies_list = []

        if raw_input.startswith('[') or raw_input.startswith('{'):
            try:
                parsed = json.loads(raw_input)
                if isinstance(parsed, dict) and "cookies" in parsed:
                    cookies_list = parsed["cookies"]
                elif isinstance(parsed, list):
                    cookies_list = parsed
            except Exception:
                pass

        if not cookies_list:
            auth_token_val = None
            ct0_val = None

            if '=' in raw_input:
                parts = raw_input.split(';')
                for part in parts:
                    if '=' in part:
                        k, v = part.strip().split('=', 1)
                        if k.strip() == 'auth_token':
                            auth_token_val = v.strip()
                        elif k.strip() == 'ct0':
                            ct0_val = v.strip()
            else:
                auth_token_val = raw_input

            if auth_token_val:
                cookies_list.append({
                    "name": "auth_token",
                    "value": auth_token_val,
                    "domain": ".x.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax"
                })
                cookies_list.append({
                    "name": "auth_token",
                    "value": auth_token_val,
                    "domain": ".twitter.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax"
                })

            if ct0_val:
                cookies_list.append({
                    "name": "ct0",
                    "value": ct0_val,
                    "domain": ".x.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                })

        if not cookies_list:
            return False, "Invalid cookie format! Please enter auth_token string or JSON."

        storage_state = {
            "cookies": cookies_list,
            "origins": []
        }

        with open(cpath, 'w', encoding='utf-8') as f:
            json.dump(storage_state, f, indent=2)

        return True, f"Successfully saved session cookies for account ID {account_id}!"

    def post_tweet_with_account(self, account_id, text_content, media_filepath=None, headless=True):
        """
        Automates creating a tweet on x.com using saved storage_state cookies for a specific account.
        """
        cpath = self.get_account_cookie_path(account_id)
        if not self.has_saved_session(account_id):
            return False, f"❌ No valid session cookies found for account ID {account_id}."

        self.log(f"🌐 Launching automated tweet process (Headless={headless})...", "info", "posting")
        with sync_playwright() as p:
            browser = None
            args_list = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ]
            if not headless:
                args_list.append("--start-maximized")

            last_err = ""
            channels_to_try = [None] if sys.platform != "win32" else [None, "chrome", "msedge"]

            for channel_option in channels_to_try:
                try:
                    kwargs = {
                        "headless": headless,
                        "args": args_list
                    }
                    if channel_option:
                        kwargs["channel"] = channel_option
                    browser = p.chromium.launch(**kwargs)
                    break
                except Exception as b_err:
                    last_err = str(b_err)

            if not browser:
                try:
                    import subprocess
                    self.log("⚙️ Chromium binary missing on server. Running playwright install chromium --with-deps...", "warning", "posting")
                    subprocess.run(["playwright", "install", "--with-deps", "chromium"], check=True, timeout=300)
                    browser = p.chromium.launch(headless=headless, args=args_list)
                except Exception as install_err:
                    self.log(f"⚠️ Auto-install chromium attempt failed: {install_err}", "error", "posting")

            if not browser:
                return False, f"❌ Failed to launch browser process for automated posting: {last_err}"

            try:
                viewport_setting = None if not headless else {"width": 1280, "height": 800}
                context = browser.new_context(storage_state=cpath, viewport=viewport_setting)
                # Set hard timeouts to prevent infinite hanging
                context.set_default_timeout(15000)
                context.set_default_navigation_timeout(25000)

                page = context.new_page()

                def _dismiss_overlays():
                    try:
                        selectors = [
                            'div[role="button"]:has-text("Refuse non-essential cookies")',
                            'div[role="button"]:has-text("Accept all cookies")',
                            'div[role="button"]:has-text("Got it")',
                            'div[role="button"]:has-text("Not now")',
                            'div[data-testid="app-bar-close"]',
                            'div[role="button"]:has-text("Dismiss")'
                        ]
                        for sel in selectors:
                            btn = page.locator(sel).first
                            if btn.count() > 0 and btn.is_visible():
                                btn.click(timeout=2000, force=True)
                                time.sleep(0.5)
                    except Exception:
                        pass

                # Step 1: Visit home to establish CSRF token and verify login context
                self.log("Navigating to x.com/home to verify login context...", "info", "posting")
                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
                time.sleep(3 if headless else 5)
                _dismiss_overlays()

                # Check if home feed loaded or redirected to login/verification
                curr_url = page.url
                if any(k in curr_url for k in ["x.com/login", "x.com/i/flow/login", "account/access", "challenge", "verify"]):
                    browser.close()
                    reason = "Security verification/challenge prompt detected on X" if "challenge" in curr_url or "access" in curr_url else "Session expired or logged out"
                    return False, f"❌ {reason} for account {account_id} (URL: {curr_url}). Please re-login in Account Manager."

                # Step 2: Locate tweet composer
                self.log("Opening compose post editor...", "info", "posting")
                
                # First try navigating to compose/post
                try:
                    page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=20000)
                    time.sleep(2)
                    _dismiss_overlays()
                except Exception as nav_e:
                    self.log(f"Direct compose page navigation notice: {nav_e}", "info", "posting")

                textbox_selector = 'div[data-testid="tweetTextarea_0"], div[role="textbox"][contenteditable="true"], div[aria-label*="Post text"], div[aria-label*="Tweet text"], div[aria-label*="What is happening"]'
                textbox = None

                try:
                    elem = page.locator(textbox_selector).first
                    if elem.count() > 0 and elem.is_visible():
                        textbox = elem
                except Exception:
                    pass

                if not textbox:
                    self.log("Trying fallback inline compose box on home page...", "info", "posting")
                    try:
                        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
                        time.sleep(2)
                        _dismiss_overlays()

                        # Try clicking floating compose button if visible
                        side_compose = page.locator('a[data-testid="SideNav_NewTweet_Button"]').first
                        if side_compose.count() > 0 and side_compose.is_visible():
                            side_compose.click(force=True, timeout=3000)
                            time.sleep(2)

                        elem = page.locator(textbox_selector).first
                        if elem.count() > 0 and elem.is_visible():
                            textbox = elem
                    except Exception as fb_err:
                        self.log(f"Fallback inline check info: {fb_err}", "warning", "posting")

                if not textbox:
                    curr_url_after = page.url
                    self.log(f"Session invalid or compose textbox not found for account {account_id}. Current URL: {curr_url_after}", "error", "error")
                    browser.close()
                    return False, f"❌ Saved session expired or compose textbox not found for account {account_id} (Current URL: {curr_url_after}). Please re-login."

                textbox.click(force=True, timeout=5000)
                time.sleep(0.5)

                if text_content:
                    try:
                        textbox.fill(text_content, timeout=5000)
                    except Exception:
                        page.keyboard.insert_text(text_content)
                    self.log(f"Entered tweet text ({len(text_content)} chars)", "info", "posting")
                    time.sleep(1.5 if headless else 2)

                if media_filepath:
                    if not os.path.exists(media_filepath):
                        self.log(f"❌ Specified media file path does not exist: {media_filepath}", "error", "posting")
                    else:
                        file_input = page.locator('input[data-testid="fileInput"], input[type="file"]').first
                        if file_input.count() > 0:
                            file_input.set_input_files(media_filepath, timeout=10000)
                            self.log(f"📎 Attached media file: {os.path.basename(media_filepath)} ({round(os.path.getsize(media_filepath)/1024, 1)} KB)", "info", "posting")
                            time.sleep(4 if headless else 6)
                        else:
                            self.log("⚠️ File input element not found for media attachment.", "warning", "posting")

                post_btn = page.locator('button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"], div[data-testid="tweetButton"], div[data-testid="tweetButtonInline"], div[role="button"]:has-text("Post")').first
                
                if post_btn.count() > 0:
                    try:
                        post_btn.wait_for(state="visible", timeout=8000)
                        if post_btn.is_enabled():
                            post_btn.click(force=True, timeout=5000)
                            self.log("🚀 Clicked 'Post' button! Waiting for confirmation...", "success", "posting")
                            time.sleep(4 if headless else 6)
                            
                            try:
                                context.storage_state(path=cpath)
                            except Exception:
                                pass

                            browser.close()
                            return True, "Successfully published tweet directly on X.com!"
                        else:
                            self.log(f"⚠️ Post button found but remained disabled. Text len: {len(text_content)} chars.", "warning", "posting")
                    except Exception as btn_err:
                        self.log(f"Post button interaction warning: {btn_err}", "warning", "posting")

                browser.close()
                media_info = f", Media: {os.path.basename(media_filepath)}" if media_filepath else ""
                return False, f"❌ Post button remained disabled or non-clickable (Tweet length: {len(text_content)} chars{media_info})."

            except Exception as e:
                err_type = type(e).__name__
                err_detail = str(e)
                self.log(f"Tweet automation exception [{err_type}]: {err_detail}", "error", "error")
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
                return False, f"❌ Playwright Automation Error [{err_type}]: {err_detail}"
