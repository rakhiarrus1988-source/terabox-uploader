import os
from google.colab import drive
from config import settings

class DriveManager:
    @staticmethod
    def mount():
        """Mount Google Drive"""
        print("📁 Mounting Google Drive...")
        drive.mount(settings.DRIVE_MOUNT_PATH)
        os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
        print("✅ Google Drive mounted successfully!")
        return True
    
    @staticmethod
    def get_download_path(filename):
        """Get full path for downloaded file"""
        return os.path.join(settings.DOWNLOAD_DIR, filename)