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
        # Hinting the client to keep multiple parallel sockets active
        self.client = TelegramClient(
            self.session_file, 
            self.api_id, 
            self.api_hash,
            auto_reconnect=True,
            connection_retries=10
        )
        await self.client.start()
        print("✅ Connected to Telegram!")
        return self.client

    async def download_file(self, filename):
        saved_messages = 'me'
        print(f"🔍 Searching for '{filename}' in Saved Messages...")

        target_msg = None
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media and hasattr(msg, 'document') and msg.document:
                target_msg = msg
                break

        if not target_msg:
            print(f"❌ '{filename}' not found in Saved Messages!")
            return None

        file_size = target_msg.file.size
        total_mb = file_size / (1024 * 1024)
        dc_id = target_msg.document.dc_id

        print(f"✅ Found in DC {dc_id}! Size: {total_mb:.2f} MB")
        print(f"🚀 Igniting Colab Engine (Native Multi-Socket Parallel Engine)...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
        start_time = time.time()

        # Telethon ka high-level optimized tracking callback function
        def progress_callback(downloaded_bytes, total_bytes):
            current_mb = downloaded_bytes / (1024 * 1024)
            elapsed = time.time() - start_time
            speed_mbps = current_mb / elapsed if elapsed > 0 else 0
            percent = (downloaded_bytes / total_bytes) * 100 if total_bytes else 0
            print(f'\r⚡ Colab Speed: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s          ', end='', flush=True)

        try:
            # FIX: High-level client wrapper automatically negotiates auth with DC 4
            # Background me automatic chunk segments concurrently stream hote hain
            actual_download_path = await self.client.download_media(
                target_msg,
                file=download_path,
                progress_callback=progress_callback
            )

            if actual_download_path:
                elapsed = time.time() - start_time
                avg_speed = total_mb / elapsed if elapsed > 0 else 0
                print(f"\n✅ Downloaded (Parallel Stream): {actual_download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                return actual_download_path
            else:
                print("\n❌ Download failed: Path not generated.")
                return None

        except Exception as e:
            print(f"\n❌ High-Speed Native Stream failed: {e}")
            return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
