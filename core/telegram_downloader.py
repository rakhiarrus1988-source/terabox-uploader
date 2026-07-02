import asyncio
from telethon import TelegramClient
from telethon.tl.types import PeerUser
from FastTelethonhelper import fast_download
from config import settings

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
        """Search and download file from Saved Messages"""
        saved_messages = await self.client.get_entity(PeerUser(0))
        
        print(f"🔍 Searching for '{filename}' in Saved Messages...")
        
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media:
                print(f"✅ Found! Size: {msg.file.size / (1024*1024):.2f} MB")
                print("⚡ Downloading at high speed...")
                
                download_path = await fast_download(
                    self.client,
                    msg,
                    msg,
                    settings.DOWNLOAD_DIR,
                    lambda current, total: print(
                        f"\r⏳ {current/(1024*1024):.1f} MB / {total/(1024*1024):.1f} MB",
                        end=""
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