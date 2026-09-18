import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from services.browser_poster import MultiAccountBrowserPoster

def emit_log(message, level="info", category="posting"):
    print(f"[TELEMETRY:{level}:{category}] {message}", flush=True)

def main():
    if len(sys.argv) < 5:
        print(f"[RESULT_JSON] {json.dumps({'success': False, 'message': 'Invalid CLI arguments.'})}", flush=True)
        sys.exit(1)

    account_id = sys.argv[1]
    temp_text_file = sys.argv[2]
    media_path_raw = sys.argv[3]
    headless_str = sys.argv[4].lower()

    media_filepath = None if media_path_raw == "NONE" else media_path_raw
    headless = (headless_str == "true")

    text_content = ""
    if os.path.exists(temp_text_file):
        try:
            with open(temp_text_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except Exception as e:
            emit_log(f"Warning reading temp text file: {e}", "warning")

    poster = MultiAccountBrowserPoster(log_callback=emit_log)
    success, message = poster._post_tweet_direct(account_id, text_content, media_filepath=media_filepath, headless=headless)

    res = {
        "success": success,
        "message": message
    }
    print(f"[RESULT_JSON] {json.dumps(res)}", flush=True)

if __name__ == "__main__":
    main()
