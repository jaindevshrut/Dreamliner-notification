import auth_helper 
import os
import requests
import json
import sys

# --- CONFIGURATION ---
# Load secrets
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
# We try to load the token from env, but we might overwrite it with a fresh one later
INITIAL_AUTH_TOKEN = os.environ.get("SCALER_AUTH", "") 

API_URL = "https://api.dreamliner.scaler.com/v1/projects?page=1&page_size=8"
STATE_FILE = "task_state.json"
TOKEN_FILE = "tokens.json" # New file to store fresh tokens

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send alert: {e}")

# --- TOKEN MANAGEMENT ---
def load_valid_token():
    """Checks for a saved fresh token, otherwise uses the GitHub Secret."""
    # 1. Try to load from local file (created by previous runs)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("access_token")
        except:
            pass
    
    # 2. Fallback to the Secret
    return INITIAL_AUTH_TOKEN

def save_access_token(token):
    """Saves the fresh token so we can reuse it next time."""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": token}, f)
    except Exception as e:
        print(f"Error saving token: {e}")

def refresh_the_token():
    print("🔄 Token expired. Starting Gmail Auto-Login...")
    try:
        # Calls the script we made earlier
        new_token = auth_helper.full_login_flow()
        
        if new_token:
            print("✅ Successfully grabbed new token via Gmail!")
            save_access_token(new_token)
            return new_token
        else:
            print("❌ Gmail Login Failed.")
            send_telegram("⚠️ CRITICAL: Gmail Login Failed. Check script logs.")
            return None
    except Exception as e:
        print(f"Auto-Login Error: {e}")
        return None

# --- STATE MANAGEMENT ---
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

# --- MAIN LOGIC ---
def get_projects_data():
    """Handles the API call, including the retry logic if token dies."""
    
    # 1. Get the best available token
    current_token = load_valid_token()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Authorization": f"Bearer {current_token}", 
        "Accept": "application/json"
    }

    print("Checking API...")
    response = requests.get(API_URL, headers=headers)

    # 2. IF TOKEN EXPIRED (401) -> REFRESH AND RETRY
    if response.status_code == 401:
        print("⚠️ Token Expired (401). Attempting Auto-Refresh...")
        
        new_token = refresh_the_token() # <--- CALLING THE REFRESH FUNCTION
        
        if new_token:
            # Update headers with new token
            headers["Authorization"] = f"Bearer {new_token}"
            # Retry the request
            response = requests.get(API_URL, headers=headers)
        else:
            # Refresh failed, give up
            return None

    if response.status_code == 200:
        return response.json()
    else:
        print(f"API Error: {response.status_code}")
        return None

def main():
    json_data = get_projects_data()
    
    if not json_data:
        save_state({})
        print("Failed to get data.")
        sys.exit(0) # Stop if we couldn't get data even after refresh

    current_projects = json_data.get("data", [])
    
    if not current_projects:
        save_state({})
        print("No projects found.")
        sys.exit(0)

    last_state = load_state()
    new_state = {}
    changes_detected = False

    for project in current_projects:
        p_id = project.get("id")
        p_name = project.get("name", "Unknown Project")
        stats = project.get("task_statistics", {})
        
        current_count = stats.get("total", 0)
        draft_count = stats.get("draft", 0)
        
        new_state[p_id] = current_count

        # COMPARE
        if p_id not in last_state:
            msg = (f"🚀 *NEW PROJECT FOUND*\n"
                   f"Name: `{p_name}`\n"
                   f"Total Tasks: {current_count}\n"
                   f"Drafts (Available): {draft_count}")
            send_telegram(msg)
            changes_detected = True
        
        elif current_count > last_state[p_id]:
            new_tasks = current_count - last_state[p_id]
            msg = (f"🔔 *TASKS ADDED*\n"
                   f"Project: `{p_name}`\n"
                   f"New Tasks: +{new_tasks}\n"
                   f"Total Drafts: {draft_count}")
            send_telegram(msg)
            changes_detected = True

    if changes_detected:
        print("Changes detected. updating state.")
        save_state(new_state)
    else:
        print("No changes found.")

if __name__ == "__main__":
    main()

