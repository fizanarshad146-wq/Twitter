import os
import sys
import time
import threading
import subprocess
import urllib.request

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import app

def start_flask_server():
    """Runs Flask server quietly on port 5000"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def wait_for_server():
    url = "http://127.0.0.1:5000/api/stats"
    for _ in range(30):
        try:
            res = urllib.request.urlopen(url)
            if res.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def open_standalone_app_window():
    # Attempt 1: PyWebView Desktop Window
    try:
        import webview
        print("🚀 Launching Native Desktop GUI Window...")
        webview.create_window(
            title="X Auto Poster - Multi-Account Desktop Manager",
            url="http://127.0.0.1:5000",
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
                cmd = [ep, "--app=http://127.0.0.1:5000", "--start-maximized"]
                subprocess.Popen(cmd)
                print(f"✅ Launched Desktop App Window using: {ep}")
                return
            except Exception as b_err:
                print(f"Failed to launch app with {ep}: {b_err}")

    # Fallback 3: Default system browser
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")

def main():
    print("==================================================")
    print("   ⚡ X AUTO POSTER - DESKTOP APPLICATION ⚡   ")
    print("==================================================")

    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()

    if wait_for_server():
        print("🟢 Backend Engine Running at http://127.0.0.1:5000")
        open_standalone_app_window()
    else:
        print("❌ Server failed to start on port 5000")

if __name__ == "__main__":
    main()
