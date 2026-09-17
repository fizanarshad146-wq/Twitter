import os
import sys
import json
import time
import hashlib
import threading
import glob
import subprocess
import shutil

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from services.browser_poster import MultiAccountBrowserPoster

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
PROJECTS_FILE = os.path.join(DATA_DIR, 'projects.json')
GUIDE_FILE = os.path.join(DATA_DIR, 'guide.json')
PROJECTS_DIR = os.path.join(UPLOAD_DIR, 'projects')
os.makedirs(PROJECTS_DIR, exist_ok=True)

DEFAULT_GUIDE_STEPS = [
    {
        "num": 1,
        "title": "Add Twitter/X Accounts (1-Click Interactive Login)",
        "content": "Go to <strong>Multi-Account Manager</strong>, click <strong>🌐 1-Click Login to Twitter / X</strong>. A visible Chrome window will open on screen. Simply log into your Twitter account. The system automatically saves session cookies!"
    },
    {
        "num": 2,
        "title": "Create Account Projects & Assign Folders",
        "content": "Go to <strong>Account Projects & Folders</strong> tab to link dedicated media folders to specific accounts. Choose whether to watch uploading live in <strong>👁️ Manual Mode</strong> or run <strong>🙈 Silently</strong> in the background."
    },
    {
        "num": 3,
        "title": "Set Min/Max Delays (Seconds or Minutes)",
        "content": "Configure posting interval delays between posts. Select unit as <strong>Seconds (s)</strong> or <strong>Minutes (m)</strong> for exact timing control."
    },
    {
        "num": 4,
        "title": "Max Posts Limit per 24 Hours",
        "content": "Prevent account rate limits by setting a maximum number of posts allowed per 24 hours (e.g. 20 posts/day). The engine automatically pauses when the daily limit is hit!"
    },
    {
        "num": 5,
        "title": "Automatic Post Archiving (.posted subfolder)",
        "content": "When a post successfully publishes, it automatically moves to a <code>.posted</code> archive subfolder inside the project folder so it is never double-posted!"
    },
    {
        "num": 6,
        "title": "🌐 Deploy 24/7 to Online Cloud Server (GitHub + Free Hosting)",
        "content": "To keep auto-posting running 24 hours a day without keeping your home PC turned on:<br><ol style='margin-left:20px; line-height:1.8; color:var(--text-muted); font-size:0.88rem;'><li><strong>Step 1: Push Code to GitHub</strong> - Create a private repository on GitHub.com and push this project folder.</li><li><strong>Step 2: Sign Up on Free Host</strong> - Go to Render.com or Railway.app or a Linux VPS.</li><li><strong>Step 3: Build & Launch Command</strong> - Set Build Command to: <code>pip install -r requirements.txt && playwright install chromium --with-deps</code> and Start Command to: <code>python app.py</code>.</li><li><strong>Step 4: Persistence</strong> - Upload your account cookie JSON files to the server's data/ directory.</li></ol>"
    }
]

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    return default

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

def add_log(message, level="info", category="system"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "category": category, # posting, account, system, error
        "message": message,
        "level": level
    }
    campaign_state["logs"].insert(0, log_entry)
    if len(campaign_state["logs"]) > 500:
        campaign_state["logs"] = campaign_state["logs"][:500]
    print(f"[{timestamp}] [{category.upper()}] [{level.upper()}] {message}")

browser_poster = MultiAccountBrowserPoster(log_callback=add_log)

# Global campaign state
campaign_state = {
    "is_running": False,
    "is_paused": False,
    "target_account_id": "all", # "all" or specific account ID
    "active_project_id": None,
    "custom_folder_path": None,
    "delay_min": 30,
    "delay_max": 60,
    "delay_unit": "sec",
    "caption_mode": "auto_filename", # "auto_filename", "custom", "none", "txt_file"
    "custom_caption": "",
    "max_posts_per_day": 0, # 0 = unlimited
    "dry_run": False,
    "headless": True,
    "total_files": 0,
    "completed": 0,
    "remaining": 0,
    "skipped_duplicates": 0,
    "failed": 0,
    "current_file": None,
    "current_account": None,
    "next_post_time": None,
    "logs": []
}

def get_file_hash(filepath_or_content):
    if os.path.exists(filepath_or_content):
        hasher = hashlib.md5()
        with open(filepath_or_content, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    else:
        return hashlib.md5(filepath_or_content.encode('utf-8')).hexdigest()

poster_thread = None

def posting_worker():
    global campaign_state
    add_log("⚡ Auto Posting Engine Started (Multi-Account Browser Automation)", "success", "posting")
    
    account_index = 0

    while campaign_state["is_running"]:
        if campaign_state["is_paused"]:
            time.sleep(2)
            continue
            
        history = load_json(HISTORY_FILE, [])
        posted_hashes = set(item.get("hash") for item in history if item.get("status") == "posted")

        # Calculate 24-hour daily posting limit
        current_time_sec = time.time()
        posts_last_24h = 0
        for item in history:
            if item.get("status") == "posted" and "timestamp" in item:
                try:
                    struct_time = time.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S")
                    post_sec = time.mktime(struct_time)
                    if current_time_sec - post_sec <= 86400:
                        posts_last_24h += 1
                except Exception:
                    pass

        max_daily = int(campaign_state.get("max_posts_per_day", 0))
        if max_daily > 0 and posts_last_24h >= max_daily:
            add_log(f"🛑 Daily limit reached ({posts_last_24h}/{max_daily} posts in last 24h). Engine paused.", "warning", "posting")
            campaign_state["is_paused"] = True
            time.sleep(5)
            continue
        
        target_dir = campaign_state.get("custom_folder_path")
        if not target_dir or not os.path.exists(target_dir):
            target_dir = UPLOAD_DIR

        files = glob.glob(os.path.join(target_dir, "*"))
        files = [f for f in files if os.path.isfile(f)]
        
        campaign_state["total_files"] = len(files)
        
        target_file = None
        target_hash = None
        
        for file_path in sorted(files):
            file_hash = get_file_hash(file_path)
            if file_hash not in posted_hashes:
                target_file = file_path
                target_hash = file_hash
                break
                
        unposted_count = sum(1 for f in files if get_file_hash(f) not in posted_hashes)
        campaign_state["remaining"] = unposted_count
        campaign_state["skipped_duplicates"] = max(0, len(files) - unposted_count - campaign_state["completed"] - campaign_state["failed"])
            
        if not target_file:
            add_log("🎉 All posts in folder completed! No new unposted files found.", "success", "posting")
            campaign_state["is_running"] = False
            campaign_state["current_file"] = None
            break
            
        filename = os.path.basename(target_file)
        campaign_state["current_file"] = filename
        
        accounts = load_json(ACCOUNTS_FILE, [])
        active_accounts = [a for a in accounts if a.get("status") == "active" and browser_poster.has_saved_session(a.get("id"))]

        if campaign_state["target_account_id"] != "all":
            active_accounts = [a for a in accounts if a.get("id") == campaign_state["target_account_id"] and browser_poster.has_saved_session(a.get("id"))]

        if not active_accounts and not campaign_state["dry_run"]:
            add_log("⚠️ No active Twitter account with valid session found! Please add an account session in Account Manager.", "warning", "account")
            campaign_state["is_running"] = False
            break

        if active_accounts:
            current_acc = active_accounts[account_index % len(active_accounts)]
            account_index += 1
        else:
            current_acc = {"id": "demo", "username": "DemoUser (Dry-Run)"}

        campaign_state["current_account"] = current_acc.get("username")
        add_log(f"Processing post '{filename}' for account @{current_acc.get('username')}...", "info", "posting")
        
        ext = os.path.splitext(filename)[1].lower()
        base_name = os.path.splitext(filename)[0]
        tweet_text = ""
        media_path = None

        caption_mode = campaign_state.get("caption_mode", "auto_filename")
        custom_caption = campaign_state.get("custom_caption", "")

        if ext == '.txt':
            try:
                with open(target_file, 'r', encoding='utf-8') as tf:
                    tweet_text = tf.read().strip()
            except Exception:
                tweet_text = base_name
        else:
            media_path = target_file
            matching_txt = os.path.join(target_dir, f"{base_name}.txt")

            if os.path.exists(matching_txt):
                try:
                    with open(matching_txt, 'r', encoding='utf-8') as tf:
                        tweet_text = tf.read().strip()
                except Exception:
                    tweet_text = ""
            elif caption_mode == "none":
                tweet_text = ""
            elif caption_mode == "custom":
                tweet_text = custom_caption
            elif caption_mode == "auto_filename":
                import re
                clean_name = base_name.replace('_', ' ').replace('-', ' ').strip()
                clean_name = re.sub(r'^\d+[\s\-_]*', '', clean_name)
                tweet_text = clean_name.capitalize() if clean_name else base_name
            else:
                tweet_text = base_name

        if campaign_state["dry_run"]:
            time.sleep(2)
            success, tweet_id, msg = True, f"sim_{int(time.time())}", "Posted successfully (Simulation Test Mode)"
        else:
            success, msg = browser_poster.post_tweet_with_account(
                current_acc.get("id"),
                tweet_text,
                media_path,
                headless=campaign_state.get("headless", True)
            )
            tweet_id = f"web_{int(time.time())}" if success else None
        
        record = {
            "filename": filename,
            "hash": target_hash,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "account": f"@{current_acc.get('username')}",
            "status": "posted" if success else "failed",
            "tweet_id": tweet_id,
            "tweet_text": tweet_text[:100],
            "message": msg
        }
        
        history.append(record)
        save_json(HISTORY_FILE, history)
        
        if success:
            campaign_state["completed"] += 1
            add_log(f"✅ Successfully posted '{filename}' on @{current_acc.get('username')}!", "success", "posting")

            # Move file to .posted subfolder to guarantee no duplicates
            try:
                posted_archive = os.path.join(target_dir, '.posted')
                os.makedirs(posted_archive, exist_ok=True)
                dest_path = os.path.join(posted_archive, filename)
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                shutil.move(target_file, dest_path)
                add_log(f"📁 Moved '{filename}' to .posted archive subfolder.", "info", "posting")
            except Exception as move_err:
                print(f"[Archive Error] {move_err}")
        else:
            campaign_state["failed"] += 1
            add_log(f"❌ Failed to post '{filename}': {msg}", "danger", "error")
            
        import random
        delay_sec = random.randint(int(campaign_state["delay_min"]), int(campaign_state["delay_max"]))
        campaign_state["next_post_time"] = time.time() + delay_sec
        
        add_log(f"⏳ Waiting {delay_sec} seconds interval delay before next post...", "info", "posting")
        
        elapsed = 0
        while elapsed < delay_sec and campaign_state["is_running"]:
            if campaign_state["is_paused"]:
                time.sleep(1)
                continue
            time.sleep(1)
            elapsed += 1
            
    campaign_state["is_running"] = False
    campaign_state["current_file"] = None
    campaign_state["next_post_time"] = None
    add_log("⏹️ Auto Posting Engine Stopped.", "info", "system")

# REST API Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    history = load_json(HISTORY_FILE, [])
    accounts = load_json(ACCOUNTS_FILE, [])
    files = glob.glob(os.path.join(UPLOAD_DIR, "*"))
    files = [f for f in files if os.path.isfile(f)]
    
    # Attach session status to accounts
    for a in accounts:
        a["has_cookies"] = browser_poster.has_saved_session(a.get("id"))

    posted_hashes = set(item.get("hash") for item in history if item.get("status") == "posted")
    unposted_count = sum(1 for f in files if get_file_hash(f) not in posted_hashes)
    
    # Calculate continuous hourly counts for past 12 hours
    import datetime
    now = datetime.datetime.now()
    hourly_counts = {}
    for item in history:
        if item.get("status") == "posted" and "timestamp" in item:
            ts = item["timestamp"]
            hour_key = ts[:13]
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1

    graph_labels = []
    graph_values = []
    for i in range(11, -1, -1):
        dt = now - datetime.timedelta(hours=i)
        hour_key = dt.strftime("%Y-%m-%d %H")
        label = dt.strftime("%H:00")
        graph_labels.append(label)
        graph_values.append(hourly_counts.get(hour_key, 0))

    # Calculate posts in last 24h
    current_time_sec = time.time()
    posts_last_24h = 0
    for item in history:
        if item.get("status") == "posted" and "timestamp" in item:
            try:
                struct_time = time.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S")
                if current_time_sec - time.mktime(struct_time) <= 86400:
                    posts_last_24h += 1
            except Exception:
                pass

    return jsonify({
        "campaign": campaign_state,
        "total_in_folder": len(files),
        "posted_total": len(posted_hashes),
        "posts_last_24h": posts_last_24h,
        "unposted_remaining": unposted_count,
        "accounts": accounts,
        "accounts_count": len(accounts),
        "graph_data": {
            "labels": graph_labels,
            "data": graph_values
        }
    })

@app.route('/api/accounts', methods=['GET', 'POST'])
def manage_accounts():
    accounts = load_json(ACCOUNTS_FILE, [])
    if request.method == 'GET':
        updated = False
        for a in accounts:
            has_c = browser_poster.has_saved_session(a.get("id"))
            a["has_cookies"] = has_c
            if has_c and a.get("status") != "active":
                a["status"] = "active"
                updated = True
        if updated:
            save_json(ACCOUNTS_FILE, accounts)
        return jsonify(accounts)
        
    elif request.method == 'POST':
        data = request.json
        username = data.get("username", "").strip().replace("@", "")
        raw_cookie = data.get("cookies", "").strip()

        if not username:
            username = f"Account_{int(time.time())}"
            
        acc_id = f"acc_{int(time.time())}"
        new_acc = {
            "id": acc_id,
            "username": username,
            "status": "active",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if raw_cookie:
            success, msg = browser_poster.save_manual_cookies(acc_id, raw_cookie)
            if not success:
                return jsonify({"error": msg}), 400

        accounts.append(new_acc)
        save_json(ACCOUNTS_FILE, accounts)
        add_log(f"🔑 Account @{username} added successfully!", "success")
        return jsonify({"message": "Account added", "account": new_acc})

@app.route('/api/accounts/add_and_launch_login', methods=['POST'])
def add_and_launch_login():
    data = request.json
    label = data.get("username", "").strip() or f"Account_{int(time.time())}"
    acc_id = f"acc_{int(time.time())}"

    # Pre-save account entry
    accounts = load_json(ACCOUNTS_FILE, [])
    new_acc = {
        "id": acc_id,
        "username": label.replace("@", ""),
        "status": "pending_login",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    accounts.append(new_acc)
    save_json(ACCOUNTS_FILE, accounts)

    def run_interactive():
        add_log(f"🌐 Opening visible Twitter login browser window for '{label}'...", "info", "account")
        success, msg, detected_username = browser_poster.launch_interactive_login(acc_id)
        if success:
            accs = load_json(ACCOUNTS_FILE, [])
            for a in accs:
                if a.get("id") == acc_id:
                    if detected_username:
                        a["username"] = detected_username
                    a["status"] = "active"
                    break
            save_json(ACCOUNTS_FILE, accs)
            add_log(f"🟢 Successfully logged in and activated account @{detected_username or label}!", "success", "account")
        else:
            add_log(f"⚠️ Interactive login window closed before login was completed: {msg}", "warning", "account")

    t = threading.Thread(target=run_interactive, daemon=True)
    t.start()
    return jsonify({"message": "Interactive browser login window launched.", "account_id": acc_id})

@app.route('/api/accounts/relogin/<acc_id>', methods=['POST'])
def relogin_account(acc_id):
    """Spawns Playwright interactive login for a specific existing account"""
    def run_login():
        add_log(f"🌐 Opening visible Twitter login browser window for account ID {acc_id}...", "info", "account")
        success, msg, detected_username = browser_poster.launch_interactive_login(acc_id)
        if success:
            accounts = load_json(ACCOUNTS_FILE, [])
            for a in accounts:
                if a.get("id") == acc_id:
                    if detected_username:
                        a["username"] = detected_username
                    a["status"] = "active"
                    break
            save_json(ACCOUNTS_FILE, accounts)
            add_log(f"🟢 Login completed & session saved for account @{detected_username or acc_id}!", "success", "account")
        else:
            add_log(f"❌ Login window closed before completion for account ID {acc_id}: {msg}", "warning", "account")

    t = threading.Thread(target=run_login, daemon=True)
    t.start()
    return jsonify({"message": "Interactive browser login launched."})

@app.route('/api/accounts/activate/<acc_id>', methods=['POST'])
def activate_account(acc_id):
    accounts = load_json(ACCOUNTS_FILE, [])
    for a in accounts:
        if a.get("id") == acc_id:
            a["status"] = "active"
            add_log(f"Activated account @{a.get('username')}", "info")
    save_json(ACCOUNTS_FILE, accounts)
    return jsonify({"message": "Account activated"})

@app.route('/api/accounts/<acc_id>', methods=['DELETE'])
def delete_account(acc_id):
    accounts = load_json(ACCOUNTS_FILE, [])
    accounts = [a for a in accounts if a.get("id") != acc_id]
    save_json(ACCOUNTS_FILE, accounts)
    
    # Remove cookie file if exists
    cpath = browser_poster.get_account_cookie_path(acc_id)
    if os.path.exists(cpath):
        try:
            os.remove(cpath)
        except Exception:
            pass
            
    add_log(f"Deleted account ID {acc_id}", "warning")
    return jsonify({"message": "Account deleted"})

@app.route('/api/upload_folder', methods=['POST'])
def upload_folder():
    if 'files[]' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
        
    uploaded_files = request.files.getlist('files[]')
    saved_count = 0
    duplicate_count = 0
    
    history = load_json(HISTORY_FILE, [])
    posted_hashes = set(item.get("hash") for item in history)

    for file in uploaded_files:
        if file.filename:
            filename = secure_filename(os.path.basename(file.filename))
            save_path = os.path.join(UPLOAD_DIR, filename)
            file.save(save_path)
            
            fhash = get_file_hash(save_path)
            if fhash in posted_hashes:
                duplicate_count += 1
            else:
                saved_count += 1
                
    add_log(f"📁 Batch Upload Complete: {saved_count} new posts imported, {duplicate_count} previously posted duplicates detected.", "success")
    return jsonify({
        "message": f"Successfully processed {len(uploaded_files)} files.",
        "imported": saved_count,
        "duplicates": duplicate_count
    })

@app.route('/api/upload_text', methods=['POST'])
def upload_text():
    data = request.json
    text_content = data.get("text", "").strip()
    filename_prefix = data.get("filename", "tweet").strip()
    
    if not text_content:
        return jsonify({"error": "Text content cannot be empty"}), 400
        
    filename = f"{secure_filename(filename_prefix)}_{int(time.time())}.txt"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text_content)
        
    add_log(f"📝 Text post created: '{filename}'", "success")
    return jsonify({"message": "Text post saved", "filename": filename})

@app.route('/api/browse_folder', methods=['POST'])
def browse_folder():
    """Launches native OS folder browser dialog to pick a directory path on desktop"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_selected = filedialog.askdirectory(master=root, title="Select Posts Media Folder")
        root.destroy()
        if folder_selected:
            return jsonify({"folder_path": os.path.abspath(folder_selected)})
        else:
            return jsonify({"error": "No folder selected"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to open native folder dialog: {e}"}), 500

@app.route('/api/open_folder', methods=['POST'])
def open_folder():
    """Opens File Explorer directly to the attached folder on Windows/Mac/Linux"""
    data = request.json or {}
    folder_path = data.get("folder_path", "").strip()
    proj_id = data.get("proj_id")

    if proj_id:
        projects = load_json(PROJECTS_FILE, [])
        proj = next((p for p in projects if p.get("id") == proj_id), None)
        if proj and proj.get("folder_path"):
            folder_path = proj.get("folder_path")

    if not folder_path or not os.path.exists(folder_path):
        folder_path = campaign_state.get("custom_folder_path") or UPLOAD_DIR

    try:
        os.makedirs(folder_path, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(folder_path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder_path])
        else:
            subprocess.Popen(['xdg-open', folder_path])
        add_log(f"📂 Opened File Explorer for folder: {folder_path}", "info")
        return jsonify({"message": f"Opened folder {folder_path}", "folder_path": folder_path})
    except Exception as e:
        return jsonify({"error": f"Failed to open folder: {e}"}), 500

@app.route('/api/campaign/control', methods=['POST'])
def campaign_control():
    global campaign_state, poster_thread
    data = request.json
    action = data.get("action")
    
    if action == "start":
        if campaign_state["is_running"]:
            campaign_state["is_paused"] = False
            add_log("▶️ Campaign Resumed", "info")
            return jsonify({"message": "Campaign resumed"})
            
        delay_unit = data.get("delay_unit", "sec")
        d_min = int(data.get("delay_min", 30))
        d_max = int(data.get("delay_max", 60))
        if delay_unit == "min":
            d_min *= 60
            d_max *= 60

        campaign_state["delay_min"] = d_min
        campaign_state["delay_max"] = d_max
        campaign_state["delay_unit"] = delay_unit
        campaign_state["caption_mode"] = data.get("caption_mode", "auto_filename")
        campaign_state["custom_caption"] = data.get("custom_caption", "").strip()
        campaign_state["max_posts_per_day"] = int(data.get("max_posts_per_day", 0))
        campaign_state["dry_run"] = bool(data.get("dry_run", False))
        campaign_state["headless"] = bool(data.get("headless", True))
        campaign_state["target_account_id"] = data.get("target_account_id", "all")
        campaign_state["is_running"] = True
        campaign_state["is_paused"] = False
        campaign_state["completed"] = 0
        campaign_state["failed"] = 0
        
        poster_thread = threading.Thread(target=posting_worker, daemon=True)
        poster_thread.start()
        return jsonify({"message": "Campaign started"})
        
    elif action == "pause":
        campaign_state["is_paused"] = True
        add_log("⏸️ Campaign Paused", "warning")
        return jsonify({"message": "Campaign paused"})
        
    elif action == "stop":
        campaign_state["is_running"] = False
        campaign_state["is_paused"] = False
        add_log("⏹️ Campaign Stop Requested", "warning")
        return jsonify({"message": "Campaign stopped"})
        
    return jsonify({"error": "Invalid action"}), 400

@app.route('/api/queue/<path:filename>', methods=['DELETE'])
def delete_queue_file(filename):
    target_dir = campaign_state.get("custom_folder_path") or UPLOAD_DIR
    fpath = os.path.join(target_dir, filename)
    if os.path.exists(fpath) and os.path.isfile(fpath):
        try:
            os.remove(fpath)
            add_log(f"🗑️ Removed '{filename}' from queue.", "warning")
            return jsonify({"message": f"Removed {filename} from queue"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404

@app.route('/api/history', methods=['GET', 'DELETE'])
def get_history():
    if request.method == 'GET':
        history = load_json(HISTORY_FILE, [])
        target_dir = campaign_state.get("custom_folder_path")
        if not target_dir or not os.path.exists(target_dir):
            target_dir = UPLOAD_DIR

        files = glob.glob(os.path.join(target_dir, "*"))
        files = [f for f in files if os.path.isfile(f)]
        posted_hashes = set(item.get("hash") for item in history if item.get("status") == "posted")

        queue = []
        for fpath in sorted(files):
            fname = os.path.basename(fpath)
            fhash = get_file_hash(fpath)
            if fhash not in posted_hashes:
                size_kb = round(os.path.getsize(fpath) / 1024, 1)
                mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fpath)))
                queue.append({
                    "filename": fname,
                    "size_kb": size_kb,
                    "timestamp": mtime,
                    "account": f"@{campaign_state.get('current_account') or 'Pending Rotation'}",
                    "status": "queued",
                    "message": f"Waiting in queue ({size_kb} KB)"
                })

        return jsonify({
            "history": history,
            "queue": queue
        })
    elif request.method == 'DELETE':
        save_json(HISTORY_FILE, [])
        add_log("🧹 Posting History Log Cleared!", "warning")
        return jsonify({"message": "Posting history cleared successfully"})

@app.route('/api/clear_folder', methods=['DELETE'])
def clear_folder():
    files = glob.glob(os.path.join(UPLOAD_DIR, "*"))
    removed = 0
    for f in files:
        if os.path.isfile(f):
            try:
                os.remove(f)
                removed += 1
            except Exception:
                pass
    add_log(f"🗑️ Cleared {removed} files from post folder.", "warning")
    return jsonify({"message": f"Cleared {removed} files"})

@app.route('/api/projects', methods=['GET', 'POST'])
def manage_projects():
    projects = load_json(PROJECTS_FILE, [])
    accounts = load_json(ACCOUNTS_FILE, [])
    acc_map = {a.get("id"): a.get("username") for a in accounts}
    history = load_json(HISTORY_FILE, [])
    posted_hashes = set(item.get("hash") for item in history if item.get("status") == "posted")

    if request.method == 'GET':
        for proj in projects:
            fpath = proj.get("folder_path")
            if not fpath or not os.path.exists(fpath):
                fpath = os.path.join(PROJECTS_DIR, proj.get("id"))
                os.makedirs(fpath, exist_ok=True)
                proj["folder_path"] = fpath

            files = [f for f in glob.glob(os.path.join(fpath, "*")) if os.path.isfile(f)]
            unposted = sum(1 for f in files if get_file_hash(f) not in posted_hashes)
            
            proj["account_username"] = acc_map.get(proj.get("account_id"), "All Accounts") if proj.get("account_id") != "all" else "All Accounts"
            proj["total_files"] = len(files)
            proj["remaining_files"] = unposted
            proj["posted_files"] = len(files) - unposted

        save_json(PROJECTS_FILE, projects)
        return jsonify(projects)

    elif request.method == 'POST':
        data = request.json
        proj_id = data.get("id") or f"proj_{int(time.time())}"
        name = data.get("name", "").strip() or f"Project_{proj_id}"
        account_id = data.get("account_id", "all")
        posting_mode = data.get("posting_mode", "manual") # "manual" (visible) or "silent" (headless)
        delay_min = int(data.get("delay_min", 30))
        delay_max = int(data.get("delay_max", 60))
        delay_unit = data.get("delay_unit", "sec")
        caption_mode = data.get("caption_mode", "auto_filename")
        custom_caption = data.get("custom_caption", "").strip()
        custom_path = data.get("folder_path", "").strip()

        max_posts_per_day = int(data.get("max_posts_per_day", 0))

        if custom_path and os.path.exists(custom_path):
            folder_path = custom_path
        else:
            folder_path = os.path.join(PROJECTS_DIR, proj_id)
            os.makedirs(folder_path, exist_ok=True)

        existing = next((p for p in projects if p.get("id") == proj_id), None)
        if existing:
            existing.update({
                "name": name,
                "account_id": account_id,
                "folder_path": folder_path,
                "posting_mode": posting_mode,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "delay_unit": delay_unit,
                "caption_mode": caption_mode,
                "custom_caption": custom_caption,
                "max_posts_per_day": max_posts_per_day
            })
            proj_data = existing
        else:
            proj_data = {
                "id": proj_id,
                "name": name,
                "account_id": account_id,
                "folder_path": folder_path,
                "posting_mode": posting_mode,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "delay_unit": delay_unit,
                "caption_mode": caption_mode,
                "custom_caption": custom_caption,
                "max_posts_per_day": max_posts_per_day,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            projects.append(proj_data)

        save_json(PROJECTS_FILE, projects)
        add_log(f"📁 Project '{name}' saved & assigned to account @{acc_map.get(account_id, 'All')} (Max 24h Posts: {max_posts_per_day or 'Unlimited'})", "success")
        return jsonify({"message": "Project saved successfully", "project": proj_data})

@app.route('/api/projects/<proj_id>/files', methods=['GET'])
def get_project_files(proj_id):
    projects = load_json(PROJECTS_FILE, [])
    proj = next((p for p in projects if p.get("id") == proj_id), None)
    if not proj:
        return jsonify({"error": "Project not found"}), 404

    target_dir = proj.get("folder_path")
    if not target_dir or not os.path.exists(target_dir):
        return jsonify({"project_id": proj_id, "project_name": proj.get("name"), "folder_path": target_dir, "files": []})

    history = load_json(HISTORY_FILE, [])
    posted_hashes = set(item.get("hash") for item in history if item.get("status") == "posted")

    all_paths = glob.glob(os.path.join(target_dir, "*"))
    file_list = []
    for fpath in sorted(all_paths):
        if os.path.isfile(fpath):
            fname = os.path.basename(fpath)
            fhash = get_file_hash(fpath)
            ext = os.path.splitext(fname)[1].lower()
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fpath)))
            is_posted = fhash in posted_hashes

            ftype = "image"
            if ext in ['.mp4', '.mov', '.avi', '.mkv']:
                ftype = "video"
            elif ext in ['.txt']:
                ftype = "text"

            file_list.append({
                "filename": fname,
                "filepath": fpath,
                "size_kb": size_kb,
                "ftype": ftype,
                "mtime": mtime,
                "is_posted": is_posted,
                "status": "✅ Posted" if is_posted else "⏳ Queued"
            })

    return jsonify({
        "project_id": proj_id,
        "project_name": proj.get("name"),
        "folder_path": target_dir,
        "files": file_list
    })

@app.route('/api/projects/<proj_id>/files/<path:filename>', methods=['DELETE'])
def delete_project_file(proj_id, filename):
    projects = load_json(PROJECTS_FILE, [])
    proj = next((p for p in projects if p.get("id") == proj_id), None)
    if not proj:
        return jsonify({"error": "Project not found"}), 404

    target_dir = proj.get("folder_path")
    fpath = os.path.join(target_dir, filename)
    if os.path.exists(fpath) and os.path.isfile(fpath):
        try:
            os.remove(fpath)
            add_log(f"🗑️ Deleted file '{filename}' from project '{proj.get('name')}'", "warning")
            return jsonify({"message": f"Deleted {filename}"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404

@app.route('/api/projects/<proj_id>', methods=['DELETE'])
def delete_project(proj_id):
    projects = load_json(PROJECTS_FILE, [])
    projects = [p for p in projects if p.get("id") != proj_id]
    save_json(PROJECTS_FILE, projects)
    add_log(f"Deleted Project ID {proj_id}", "warning")
    return jsonify({"message": "Project deleted"})

@app.route('/api/projects/<proj_id>/upload', methods=['POST'])
def upload_project_folder(proj_id):
    projects = load_json(PROJECTS_FILE, [])
    proj = next((p for p in projects if p.get("id") == proj_id), None)
    if not proj:
        return jsonify({"error": "Project not found"}), 404

    target_dir = proj.get("folder_path")
    os.makedirs(target_dir, exist_ok=True)

    if 'files[]' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded_files = request.files.getlist('files[]')
    saved_count = 0
    duplicate_count = 0
    history = load_json(HISTORY_FILE, [])
    posted_hashes = set(item.get("hash") for item in history)

    for file in uploaded_files:
        if file.filename:
            filename = secure_filename(os.path.basename(file.filename))
            save_path = os.path.join(target_dir, filename)
            file.save(save_path)

            fhash = get_file_hash(save_path)
            if fhash in posted_hashes:
                duplicate_count += 1
            else:
                saved_count += 1

    add_log(f"📁 Project '{proj.get('name')}' Uploaded: {saved_count} new posts imported to {target_dir}", "success")
    return jsonify({"message": "Upload complete", "imported": saved_count, "duplicates": duplicate_count})

@app.route('/api/projects/<proj_id>/run', methods=['POST'])
def run_project_campaign(proj_id):
    global campaign_state, poster_thread
    projects = load_json(PROJECTS_FILE, [])
    proj = next((p for p in projects if p.get("id") == proj_id), None)
    if not proj:
        return jsonify({"error": "Project not found"}), 404

    if campaign_state["is_running"]:
        return jsonify({"error": "A campaign is already running! Please stop it first."}), 400

    target_dir = proj.get("folder_path")
    if not target_dir or not os.path.exists(target_dir):
        return jsonify({"error": f"Project folder path '{target_dir}' does not exist."}), 400

    is_manual = (proj.get("posting_mode") == "manual")
    delay_unit = proj.get("delay_unit", "sec")
    d_min = int(proj.get("delay_min", 30))
    d_max = int(proj.get("delay_max", 60))
    if delay_unit == "min":
        d_min *= 60
        d_max *= 60

    campaign_state["active_project_id"] = proj.get("id")
    campaign_state["custom_folder_path"] = target_dir
    campaign_state["target_account_id"] = proj.get("account_id", "all")
    campaign_state["delay_min"] = d_min
    campaign_state["delay_max"] = d_max
    campaign_state["delay_unit"] = delay_unit
    campaign_state["caption_mode"] = proj.get("caption_mode", "auto_filename")
    campaign_state["custom_caption"] = proj.get("custom_caption", "")
    campaign_state["headless"] = not is_manual
    campaign_state["dry_run"] = False
    campaign_state["is_running"] = True
    campaign_state["is_paused"] = False
    campaign_state["completed"] = 0
    campaign_state["failed"] = 0

    add_log(f"🚀 Launching Campaign for Project '{proj.get('name')}' (Mode: {'👁️ VISIBLE BROWSER' if is_manual else '🙈 SILENT BACKGROUND'})", "success")

    poster_thread = threading.Thread(target=posting_worker, daemon=True)
    poster_thread.start()
    return jsonify({"message": f"Campaign started for project '{proj.get('name')}'", "project": proj})

@app.route('/api/guide', methods=['GET', 'POST'])
def manage_guide():
    if request.method == 'GET':
        guide_data = load_json(GUIDE_FILE, DEFAULT_GUIDE_STEPS)
        return jsonify(guide_data)
    elif request.method == 'POST':
        data = request.json
        if isinstance(data, list):
            save_json(GUIDE_FILE, data)
            add_log("📝 User Guide instructions updated.", "info")
            return jsonify({"message": "Guide saved successfully", "guide": data})
        return jsonify({"error": "Invalid guide format"}), 400

@app.route('/api/guide/reset', methods=['POST'])
def reset_guide():
    save_json(GUIDE_FILE, DEFAULT_GUIDE_STEPS)
    add_log("🔄 User Guide reset to default instructions.", "warning")
    return jsonify({"message": "Guide reset to default", "guide": DEFAULT_GUIDE_STEPS})

if __name__ == '__main__':
    print("⚡ Starting Twitter Auto Posting Server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
