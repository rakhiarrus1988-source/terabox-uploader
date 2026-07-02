import os

# Google Drive paths
DRIVE_MOUNT_PATH = "/content/drive"
CREDENTIALS_DIR = os.path.join(DRIVE_MOUNT_PATH, "MyDrive", "TelegramTerabox")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "telegram_creds.json")
SESSION_FILE = os.path.join(CREDENTIALS_DIR, "telegram_session.session")
DOWNLOAD_DIR = os.path.join(CREDENTIALS_DIR, "downloads")

# Terabox settings
TERABOX_COOKIES_FILE = os.path.join(CREDENTIALS_DIR, "terabox_cookies.json")

# Telegram API (will be loaded from credentials)
API_ID = None
API_HASH = None