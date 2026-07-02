import os
import time
from telethon import TelegramClient
from config import settings
from utils.progress_bar import progress_bar

class TelegramDownloader:
    def __init__(self, api_id, api_hash, session_file):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.client = None
    
    async def connect(self):
        """Connect to Telegram"""
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        await self.client.start()
        print("✅ Connected to Telegram!")
        return self.client
    
    async def download_file(self, filename):
        """Search and download file from Saved Messages with progress bar"""
        saved_messages = 'me'  # Saved Messages
        
        print(f"🔍 Searching for '{filename}' in Saved Messages...")
        
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media:
                file_size = msg.file.size
                print(f"✅ Found! Size: {file_size / (1024*1024):.2f} MB")
                print("⚡ Downloading...")
                
                download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
                
                # Download with progress bar
                await self.client.download_media(
                    msg,
                    file=download_path,
                    progress_callback=lambda current, total: progress_bar(
                        current, 
                        total, 
                        prefix='⏳ Downloading',
                        suffix=f'{current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB'
                    )
                )
                
                print(f"\n✅ Downloaded: {download_path}")
                return download_path
        
        print(f"❌ '{filename}' not found in Saved Messages!")
        return None
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()