import os
import time
import asyncio
from telethon import TelegramClient
from config import settings

class TelegramDownloader:
    def __init__(self, api_id, api_hash, session_file):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.client = None

    async def connect(self):
        # Yahan hum client initialization ko optimize kar rahe hain taaki multithreading standard parameters se ho sake
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        await self.client.start()
        print("✅ Connected to Telegram!")
        return self.client

    async def download_file(self, filename):
        saved_messages = 'me'
        print(f"🔍 Searching for '{filename}' in Saved Messages...")

        async_msg = None
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media and hasattr(msg, 'document') and msg.document:
                async_msg = msg
                break

        if async_msg:
            file_size = async_msg.file.size
            total_mb = file_size / (1024 * 1024)
            print(f"✅ Found! Size: {total_mb:.2f} MB")
            print("⚡ Starting stable parallel chunk download...")

            download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
            start_time = time.time()

            # Real-time progress function
            def progress_callback(current, total):
                current_mb = current / (1024 * 1024)
                elapsed = time.time() - start_time
                speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                percent = (current / total) * 100
                print(f'\r⏳ Downloading: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

            try:
                # Telethon ka native client.download_file loop system jo ki completely stable hai
                # Aur bina kisi crash ke background connection handle karta hai
                await self.client.download_file(
                    async_msg.document,
                    file=download_path,
                    progress_callback=progress_callback
                )
                
                print()  # Download over hone par line break
                elapsed = time.time() - start_time
                avg_speed = total_mb / elapsed if elapsed > 0 else 0
                print(f"✅ Downloaded successfully: {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                return download_path

            except Exception as e:
                print(f"\n❌ Download failed: {e}")
                return None

        print(f"❌ '{filename}' not found in Saved Messages!")
        return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
