import imaplib
import email
import re
import requests
import time
import os

# --- CONFIGURATION ---
GMAIL_USER = os.environ["GMAIL_USER"]         
GMAIL_APP_PASSWORD = os.environ["GMAIL_PASSWORD"]
SCALER_LOGIN_URL = "https://api.dreamliner.scaler.com/v1/auth/login/magic-link" # Double check this URL in network tab

def trigger_login_email():
    """Tells Scaler to send a fresh login email."""
    print("📧 Requesting new login email from Scaler...")
    payload = {"email": GMAIL_USER, "callback_url": "https://dreamliner.scaler.com/auth/verify"} 
    # ^ The callback_url might be optional or different. Check your Network tab Payload to be sure.
    
    try:
        requests.post(SCALER_LOGIN_URL, json=payload)
        print("✅ Email requested. Waiting for it to arrive...")
        time.sleep(15) # Wait 15s for email to arrive
    except Exception as e:
        print(f"❌ Failed to trigger email: {e}")

def get_latest_magic_link():
    """Logs into Gmail and grabs the link from the latest Scaler email."""
    print("Opeing Inbox...")
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for emails from Scaler (adjust keyword if needed)
        status, messages = mail.search(None, '(FROM "noreply@dreamliner.scaler.com")') 
        # If "no-reply" doesn't work, try '(SUBJECT "Login")' or '(TEXT "dreamliner")'
        print("------")
        print(messages)
        if not messages[0]:
            print("❌ No emails found from Scaler.")
            return None

        # Get the latest email ID
        latest_email_id = messages[0].split()[-1]
        
        # Fetch the email body
        status, data = mail.fetch(latest_email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html": # Get HTML body
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Regex to find the link: https://dreamliner.scaler.com/auth/verify?token=...
        # We look for the pattern starting with the URL and capturing the token
        link_pattern = re.search(r'https://dreamliner\.scaler\.com/auth/verify\?token=([a-zA-Z0-9_\-\.]+)', body)
        
        if link_pattern:
            full_link = link_pattern.group(0)
            verify_token = link_pattern.group(1)
            print(f"🔗 Found Magic Link!")
            return full_link, verify_token
        else:
            print("❌ Could not find link in email body.")
            return None, None

    except Exception as e:
        print(f"❌ Gmail Error: {e}")
        return None, None

def exchange_link_for_token(verify_token):
    """
    Exchanges the email verification token for the real Access Token.
    Note: Sometimes hitting the link sets a cookie, sometimes it returns JSON.
    We try the API endpoint usually associated with the verification.
    """
    verify_api_url = "https://api.dreamliner.scaler.com/v1/auth/magic-link/verify" # Guessing endpoint based on standard patterns
    
    # Try POSTing the token
    try:
        response = requests.post(verify_api_url, json={"token": verify_token})
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
    except:
        pass
        
    # Fallback: Just return the verify_token if the API uses it directly as the bearer (Unlikely but possible)
    return verify_token

def full_login_flow():
    trigger_login_email()
    link, verify_token = get_latest_magic_link()
    
    if verify_token:
        # Depending on Scaler's architecture, the token in the email MIGHT be the access token,
        # or (more likely) it is exchanged for one.
        # Let's try to verify it.
        final_token = exchange_link_for_token(verify_token)
        return final_token
    return None

if __name__ == "__main__":
    # Test run
    print(full_login_flow())
