import os
import time
from telethon import TelegramClient
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
        """Search and download file from Saved Messages with progress"""
        saved_messages = 'me'
        
        print(f"🔍 Searching for '{filename}' in Saved Messages...")
        
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media:
                file_size = msg.file.size
                total_mb = file_size / (1024 * 1024)
                print(f"✅ Found! Size: {total_mb:.2f} MB")
                print("⚡ Downloading...")
                
                download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
                
                # Progress tracker
                downloaded = 0
                last_update = 0
                start_time = time.time()
                
                def progress_callback(current, total):
                    nonlocal downloaded, last_update
                    downloaded = current
                    
                    # Update every 0.5 seconds
                    if time.time() - last_update > 0.5 or current == total:
                        last_update = time.time()
                        
                        # Calculate MB
                        current_mb = current / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        
                        # Calculate speed
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_mbps = (current / (1024 * 1024)) / elapsed
                            print(f'\r⏳ Downloading: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='')
                        else:
                            print(f'\r⏳ Downloading: {current_mb:.1f}MB / {total_mb:.1f}MB', end='')
                        
                        if current == total:
                            print()  # New line after complete
                
                # Download with progress
                await self.client.download_media(
                    msg,
                    file=download_path,
                    progress_callback=progress_callback
                )
                
                # Final stats
                elapsed = time.time() - start_time
                avg_speed = (file_size / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                print(f"✅ Downloaded: {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                return download_path
        
        print(f"❌ '{filename}' not found in Saved Messages!")
        return None
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()