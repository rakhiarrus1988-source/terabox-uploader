import os
import json
from config import settings

class CredentialsManager:
    @staticmethod
    def load_or_get_credentials():
        """Load credentials from Google Drive or ask user"""
        os.makedirs(settings.CREDENTIALS_DIR, exist_ok=True)
        
        if os.path.exists(settings.CREDENTIALS_FILE):
            with open(settings.CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
            print("✅ Credentials loaded from Google Drive!")
            return creds.get('api_id'), creds.get('api_hash')
        
        print("\n🔑 First time setup - Enter Telegram API credentials:")
        api_id = int(input("API ID: ").strip())
        api_hash = input("API Hash: ").strip()
        
        with open(settings.CREDENTIALS_FILE, 'w') as f:
            json.dump({'api_id': api_id, 'api_hash': api_hash}, f)
        print("✅ Credentials saved to Google Drive!")
        return api_id, api_hash
    
    @staticmethod
    def save_terabox_cookies(cookies):
        """Save Terabox cookies for future use"""
        with open(settings.TERABOX_COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        print("✅ Terabox cookies saved!")
    
    @staticmethod
    def load_terabox_cookies():
        """Load Terabox cookies from Google Drive"""
        if os.path.exists(settings.TERABOX_COOKIES_FILE):
            with open(settings.TERABOX_COOKIES_FILE, 'r') as f:
                return json.load(f)
        return None