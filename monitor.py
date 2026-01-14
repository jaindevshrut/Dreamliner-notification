import os
import requests
import sys

# Load secrets from GitHub Environment Variables
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
AUTH_TOKEN = os.environ["SCALER_AUTH"]

API_URL = "https://api.dreamliner.scaler.com/v1/projects?page=1&page_size=8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Authorization": AUTH_TOKEN,
    "Accept": "application/json"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

def get_last_seen_id():
    try:
        with open("last_id.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0"

def save_last_seen_id(task_id):
    with open("last_id.txt", "w") as f:
        f.write(str(task_id))

def main():
    print("Checking API...")
    try:
        response = requests.get(API_URL, headers=HEADERS)
        
        if response.status_code == 401:
            send_telegram("⚠️ Alert: Scaler Token Expired! Please update GitHub Secrets.")
            sys.exit(1)
        
        if response.status_code != 200:
            print(f"Error: Status {response.status_code}")
            sys.exit(0)

        data = response.json()
        projects = data.get("projects", []) # Adjust key if needed based on API response

        if not projects:
            print("No projects found in list.")
            sys.exit(0)

        latest_task = projects[0]
        latest_id = str(latest_task.get("id"))
        latest_title = latest_task.get("title", "Unknown Title")

        last_seen_id = get_last_seen_id()

        if latest_id != last_seen_id:
            print(f"New Task Found: {latest_id}")
            send_telegram(f"🚨 NEW TASK!\n\nTitle: {latest_title}\nLink: https://dreamliner.scaler.com/projects/{latest_id}")
            save_last_seen_id(latest_id)
        else:
            send_telegram(latest_task)
            print("No new tasks.")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    main()
