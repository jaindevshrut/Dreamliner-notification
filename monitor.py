import os
import requests
import json
import sys

# --- CONFIGURATION ---
# Load secrets from GitHub Environment Variables
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
AUTH_TOKEN = os.environ["SCALER_AUTH"]

API_URL = "https://api.dreamliner.scaler.com/v1/projects?page=1&page_size=8"
STATE_FILE = "task_state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Authorization": AUTH_TOKEN, # Ensure this includes 'Bearer ' if your secret doesn't have it
    "Accept": "application/json"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send alert: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def main():
    print("Checking API for new tasks...")
    
    try:
        response = requests.get(API_URL, headers=HEADERS)
        
        # 1. Handle Errors
        if response.status_code == 401:
            send_telegram("⚠️ *Monitor Alert:* Token Expired! Update GitHub Secrets.")
            sys.exit(1)
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            sys.exit(0)

        # 2. Parse Data
        json_data = response.json()
        current_projects = json_data.get("data", [])
        
        if not current_projects:
            print("No projects found.")
            sys.exit(0)

        # 3. Compare with Last State
        last_state = load_state() # Format: {"project_id": total_count}
        new_state = {}
        changes_detected = False

        for project in current_projects:
            p_id = project.get("id")
            p_name = project.get("name", "Unknown Project")
            stats = project.get("task_statistics", {})
            
            # We track 'total' tasks. You can change this to 'draft' if you only want pending work.
            current_count = stats.get("total", 0)
            draft_count = stats.get("draft", 0)
            
            # Save to new state for next run
            new_state[p_id] = current_count

            # LOGIC CHECK:
            if p_id not in last_state:
                # SCENARIO A: Brand New Project found
                msg = (f"🚀 *NEW PROJECT FOUND*\n"
                       f"Name: `{p_name}`\n"
                       f"Total Tasks: {current_count}\n"
                       f"Drafts (Available): {draft_count}")
                send_telegram(msg)
                changes_detected = True
            
            elif current_count > last_state[p_id]:
                # SCENARIO B: Existing Project has NEW tasks
                new_tasks = current_count - last_state[p_id]
                msg = (f"🔔 *TASKS ADDED*\n"
                       f"Project: `{p_name}`\n"
                       f"New Tasks: +{new_tasks}\n"
                       f"Total Drafts: {draft_count}")
                send_telegram(msg)
                changes_detected = True

        # 4. Cleanup & Save
        # If a project disappeared from API, it won't be in new_state, so it's removed naturally.
        if changes_detected:
            print("Changes detected. updating state.")
            save_state(new_state)
        else:
            print("No changes found.")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    main()
