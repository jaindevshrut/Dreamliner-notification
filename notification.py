import requests
import time
import json

# --- CONFIGURATION ---
API_URL = "https://api.dreamliner.scaler.com/v1/projects?page=1&page_size=8"
TELEGRAM_BOT_TOKEN = "8445233522:AAEwohPMp5UbNluDQm-N6Vqu4ybVK4vPQL8" # Get from @BotFather
TELEGRAM_CHAT_ID = "1439027244" # Get from @userinfobot

# PASTE YOUR HEADER DATA HERE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNDIzMWI1My00MjgyLTQ4OGMtYTE2OS1mOWQxZDNjYWUzMjgiLCJpYXQiOjE3NjgzOTI4MDQsImV4cCI6MTc2ODQ3OTIwNCwianRpIjoiOTQ2MTViYzMtMWExNS00MDEyLWE0MjktZmY1ZWZiMDQyMTM0IiwidHlwZSI6ImFjY2VzcyIsImVtYWlsIjoiamFpbmRldnNocnV0QGdtYWlsLmNvbSIsInJvbGUiOiJ1c2VyIn0.lMV6i2CEyeeZRs_Hz-4nR2hzKfXXl4zFsJo83JHNS5g",
    "Accept": "application/json"
}

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

def check_tasks():
    print("Checking for tasks...")
    try:
        response = requests.get(API_URL, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            print(data)
            # Assuming 'projects' is the key holding the list. 
            # Adjust 'items' based on actual JSON structure (e.g., data['data'], data['projects'])
            projects = data.get('projects', []) 
            
            if projects:
                latest_project = projects[0] # Get the top project
                return latest_project['id'], latest_project['title'] # Return ID and Title
            else:
                return None, None
        elif response.status_code == 401:
            print("Token Expired! Update your headers.")
            send_telegram_alert("⚠️ Monitor Stopped: Token Expired.")
            return "EXPIRED", None
        else:
            print(f"Status Code: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def main():
    last_id = None
    
    # Initial check to set the baseline
    last_id, _ = check_tasks()
    print(f"Monitor started. Last Project ID: {last_id}")
    send_telegram_alert("🚀 Task Monitor Started!")

    while True:
        time.sleep(60) # Check every 60 seconds
        
        current_id, current_title = check_tasks()
        
        if current_id == "EXPIRED":
            break # Stop script if token dies
            
        if current_id and current_id != last_id:
            msg = f"🔔 NEW TASK AVAILABLE!\nTitle: {current_title}\nID: {current_id}"
            send_telegram_alert(msg)
            last_id = current_id # Update last_id so we don't notify again
        else:
            print("No new tasks...")

if __name__ == "__main__":
    main()