import asyncio
import os
import nest_asyncio
from config import settings
from core.drive_manager import DriveManager
from core.credentials_manager import CredentialsManager
from core.telegram_downloader import TelegramDownloader
from core.terabox_uploader import TeraboxUploader

# Apply nest_asyncio for Colab compatibility
nest_asyncio.apply()

async def main():
    print("="*50)
    print("🚀 TELEGRAM → TERABOX UPLOADER")
    print("="*50)

    # Step 1: Mount Google Drive
    DriveManager.mount()

    # Step 2: Load credentials
    api_id, api_hash = CredentialsManager.load_or_get_credentials()

    # Step 3: Get file name from user
    file_name = input("\n📝 Enter file name to download from Saved Messages: ").strip()
    if not file_name:
        print("❌ Please enter a file name!")
        return

    # Step 4: Download from Telegram
    downloader = TelegramDownloader(api_id, api_hash, settings.SESSION_FILE)
    await downloader.connect()

    downloaded_file = await downloader.download_file(file_name)
    await downloader.disconnect()

    if not downloaded_file:
        return

    # Step 5: Upload to Terabox (Fixed line below)
    # settings object se terabox ki email aur password pass kiya hai
    uploader = TeraboxUploader(email=settings.TERABOX_EMAIL, password=settings.TERABOX_PASSWORD)
    uploader.login_with_cookies()
    result = uploader.upload_file(downloaded_file)
    uploader.close()

    if result:
        print("\n🎉 SUCCESS! File downloaded and uploaded to Terabox!")
    else:
        print(f"\n⚠️ File saved at: {downloaded_file}")
        print("Upload to Terabox manually if auto-upload failed.")

if __name__ == "__main__":
    asyncio.run(main())
