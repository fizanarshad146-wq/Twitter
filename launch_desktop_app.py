import os
import sys
import time
import json
import threading
import subprocess
import urllib.request

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import app

def get_target_server_url():
    """Check data/server_config.json or environment variable for Remote Cloud URL (e.g., Render)"""
    config_file = os.path.join(BASE_DIR, 'data', 'server_config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                remote_url = cfg.get("remote_url", "").strip()
                if remote_url and remote_url.startswith("http"):
                    return remote_url
        except Exception:
            pass
    return os.environ.get("REMOTE_SERVER_URL", "http://127.0.0.1:5000").strip()

def start_flask_server():
    """Runs Flask server quietly on port 5000"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def wait_for_server(target_url):
    check_url = f"{target_url.rstrip('/')}/api/stats"
    print(f"📡 Checking backend status at: {check_url}...")
    for _ in range(30):
        try:
            res = urllib.request.urlopen(check_url, timeout=5)
            if res.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def open_standalone_app_window(target_url):
    # Attempt 1: PyWebView Desktop Window
    try:
        import webview
        print(f"🚀 Launching Native Desktop GUI Window -> {target_url}")
        webview.create_window(
            title="X Auto Poster - Multi-Account Desktop Manager",
            url=target_url,
            width=1400,
            height=900,
            resizable=True,
            min_size=(1024, 700)
        )
        webview.start()
        return
    except Exception as e:
        print(f"PyWebView window notice: {e}. Falling back to Browser App Window...")

    # Attempt 2: Standalone Browser App Window (--app mode)
    exec_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]

    for ep in exec_paths:
        if os.path.exists(ep):
            try:
                cmd = [ep, f"--app={target_url}", "--start-maximized"]
                subprocess.Popen(cmd)
                print(f"✅ Launched Desktop App Window using: {ep}")
                return
            except Exception as b_err:
                print(f"Failed to launch app with {ep}: {b_err}")

    # Fallback 3: Default system browser
    import webbrowser
    webbrowser.open(target_url)

def main():
    print("==================================================")
    print("   ⚡ X AUTO POSTER - DESKTOP APPLICATION ⚡   ")
    print("==================================================")

    target_url = get_target_server_url()
    is_remote = target_url != "http://127.0.0.1:5000"

    if is_remote:
        print(f"🌐 Cloud Mode Active! Target Server: {target_url}")
        if wait_for_server(target_url):
            print(f"🟢 Remote Cloud Backend Connected: {target_url}")
            open_standalone_app_window(target_url)
        else:
            print(f"⚠️ Remote server ({target_url}) did not respond in time. Opening app anyway...")
            open_standalone_app_window(target_url)
    else:
        print("💻 Local Engine Mode Active (127.0.0.1:5000)")
        server_thread = threading.Thread(target=start_flask_server, daemon=True)
        server_thread.start()

        if wait_for_server(target_url):
            print(f"🟢 Local Backend Engine Running at {target_url}")
            open_standalone_app_window(target_url)
        else:
            print("❌ Local server failed to start on port 5000")

if __name__ == "__main__":
    main()
