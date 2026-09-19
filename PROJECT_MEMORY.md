# 📌 X AUTO POSTING (ELECTRO POSTER) — COMPLETE PROJECT MEMORY & ARCHITECTURE FILE

> **Created:** 2026-09-18
> **Purpose:** Permanent repository memory, technical architecture context, state schemas, bug fixes, and deployment guides across OS reinstalls and environment setups.

---

## 🚀 1. Executive Summary & Core Capabilities
**X AUTO POSTING (X ELECTRO POSTER)** is a full-stack multi-account automated Twitter/X posting platform.
- **Frontend UI:** Futuristic glassmorphism dashboard built with HTML5, Vanilla CSS (`electro.css`), and JavaScript (`app.js`).
- **Backend API:** Flask Python application (`app.py`) with Gunicorn multi-threading support.
- **Automation Engine:** Playwright Python headless/headful multi-account browser poster (`services/browser_poster.py`).
- **Data Persistence:** JSON-based state files in `data/` (`campaign_state.json`, `logs.json`, `accounts.json`, `projects.json`, `history.json`).

---

## 🛠️ 2. Core Architecture & Component Breakdown

### A. Playwright Browser Automation (`services/browser_poster.py`)
- **Session Management:** Saves Twitter/X auth cookies (`auth_token`, `ct0`, etc.) as Playwright `storage_state` JSON files (`data/cookies_<account_id>.json`).
- **Interactive 1-Click Login (`launch_interactive_login`):** Spawns a visible Chrome/Edge window, waits for user login on `x.com/i/flow/login`, auto-detects `auth_token` and Twitter handle (`@username`), saves cookies, and closes cleanly.
- **Automated Tweeting (`post_tweet_with_account`):**
  - **Thread Event Loop:** Auto-initializes `asyncio.set_event_loop(asyncio.new_event_loop())` for Python 3.10+ background thread safety.
  - **Container Ultra-Low Memory Flags:** Includes `--single-process`, `--no-zygote`, `--disable-dev-shm-usage`, `--disable-gpu`, `--disable-software-rasterizer`, and `--js-flags=--max-old-space-size=256` to run within Render's 512MB RAM free tier.
  - **Overlay Auto-Dismissal (`_dismiss_overlays`):** Automatically clicks away Cookie policy banners, "Got it", "Not now", and "Dismiss" popups.
  - **Locator Count Guard:** Uses `file_input.count() > 0` and `post_btn.count() > 0` (preventing Python `Locator` truthiness bugs).
  - **Keyboard Fallback:** Uses `page.keyboard.insert_text()` if `textbox.fill()` fails on React `contenteditable` divs.
  - **Detailed Telemetry:** Logs granular step progress, file sizes, text lengths, current URL, and exact Python/Playwright exception types.

### B. Campaign Execution Engine (`app.py`)
- **Worker Thread (`posting_worker`):** Runs continuously in background to process queue items per campaign configuration.
- **Retry Mechanism (Failure Recovery):**
  - If a post fails, retries up to **3 times** with a 15-second pause between retries.
  - If all 3 attempts fail, triggers a **30-second short failure cooldown** (instead of 1-hour campaign delay).
  - **Full Campaign Delay:** The configured interval delay (`delay_min` to `delay_max`) is **ONLY** applied after a post is **successfully published**!
- **State Persistence (`load_campaign_state` & `save_campaign_state`):**
  - Campaign settings, active project ID, custom folder path, and live telemetry logs are saved to `data/campaign_state.json` and `data/logs.json`.
  - **Page Refresh Safety:** Refreshing the web browser reloading the page reloads state from disk. Engine status, live logs, and project queues never reset on F5!
  - **Auto-Resume:** On server start/reload, if `campaign_state["is_running"]` is `True`, the worker thread auto-resumes posting automatically.

---

## 📁 3. File System & Data Schema

| File/Directory | Purpose |
| :--- | :--- |
| `app.py` | Core Flask API, campaign worker loop, state persistence |
| `services/browser_poster.py` | Playwright multi-account login & posting engine |
| `run_posting_cli.py` | Standalone CLI runner script for Playwright execution |
| `Procfile` | `web: gunicorn --workers 1 --threads 8 --timeout 120 app:app` |
| `build.sh` | Shell build script: `pip install -r requirements.txt && playwright install --with-deps chromium` |
| `render.yaml` | Render cloud deployment specification |
| `PROJECT_MEMORY.md` | Permanent project memory & technical architecture file |
| `data/accounts.json` | Saved account list with status and cookie path |
| `data/projects.json` | Account project assignments, folder paths, and delay limits |
| `data/history.json` | Post publication history and MD5 hash archive |
| `data/campaign_state.json` | Persistent engine state (is_running, delays, active project) |
| `data/logs.json` | Persistent 500-entry telemetry log buffer |
| `uploads/projects/` | Media upload directories per project |

---

## 🌐 4. 24/7 Hosting Options & Deployment Guide

### Option 1: AWS 12-Month 100% Free Windows VPS (Recommended for Desktop Software)
1. Sign up on `aws.amazon.com`.
2. Launch a free **t2.micro / t3.micro Windows Server EC2 Instance**.
3. Connect via **Remote Desktop (RDP)** from your PC or phone.
4. Copy `X AUTO POSTING` project folder onto the VPS desktop.
5. Double-click `Start_Desktop_App.bat` or `1_CLICK_LAUNCH.bat`.
6. Disconnect RDP. The desktop app runs 24/7 in the cloud with full GUI Chrome display for $0 cost!

### Option 2: Render Free Cloud Deployment (`https://x-auto-posting.onrender.com`)
1. Push project repository to GitHub.
2. Link repository to Render Web Service.
3. Set **Build Command**: `bash build.sh` (or `pip install -r requirements.txt && playwright install --with-deps chromium`).
4. Set **Start Command**: `gunicorn --workers 1 --threads 8 --timeout 120 app:app`.
5. Set environment variable: `PLAYWRIGHT_BROWSERS_PATH=0`.

---

## 🛠️ 5. Key Bug Fixes Summary Log
1. **Playwright Thread Deadlock Fix:** Initialized `asyncio.set_event_loop(asyncio.new_event_loop())` inside background thread so Playwright sync API never freezes.
2. **Page Refresh Reset Fix:** Created `STATE_FILE` (`data/campaign_state.json`) and `LOGS_FILE` (`data/logs.json`) so state, logs, and queue folder resolution survive page reloads and server restarts.
3. **Locator Boolean Fix:** Fixed `if file_input:` Python truthiness bug to `if file_input.count() > 0:`.
4. **Fast Failure Cooldown:** Changed failed post handling to retry 3 times and pause 30s instead of triggering a 1-hour delay.
5. **Render Container Launch Fix:** Added `--single-process`, `--no-zygote`, `--disable-dev-shm-usage`, and `--js-flags=--max-old-space-size=256` for 512MB RAM container compatibility.
