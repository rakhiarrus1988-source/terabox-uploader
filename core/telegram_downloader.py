import os
import time
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait
from config import settings

class PyrogramDownloader:
    def __init__(self, api_id, api_hash, session_name="my_account"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.app = None

    async def connect(self):
        self.app = Client(
            self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash
        )
        await self.app.start()
        print("✅ Pyrogram connected!")
        return self.app

    async def disconnect(self):
        if self.app:
            await self.app.stop()
            print("🔌 Disconnected!")

    async def download_file(self, filename, workers=8):
        """
        Search file in Saved Messages and download using multiple workers.
        workers = number of parallel connections (default 8)
        """
        print(f"🔍 Searching for '{filename}' in Saved Messages...")
        # Fetch the first matching document
        message = None
        async for msg in self.app.get_chat_history("me"):
            if msg.document and filename.lower() in (msg.document.file_name or "").lower():
                message = msg
                break

        if not message:
            print(f"❌ '{filename}' not found!")
            return None

        file_size = message.document.file_size
        total_mb = file_size / (1024 * 1024)
        print(f"✅ Found! Size: {total_mb:.2f} MB")
        print(f"🚀 Downloading using {workers} parallel workers...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
        start_time = time.time()

        # Progress callback
        def progress(current, total):
            current_mb = current / (1024 * 1024)
            total_mb_progress = total / (1024 * 1024)
            elapsed = time.time() - start_time
            speed = current_mb / elapsed if elapsed > 0 else 0
            percent = (current / total) * 100
            print(
                f"\r⚡ {percent:.1f}% | {current_mb:.1f}/{total_mb_progress:.1f} MB @ {speed:.1f} MB/s    ",
                end="", flush=True
            )

        try:
            # The magic: workers=8 enables parallel chunk downloading internally
            result = await self.app.download_media(
                message,
                file_name=download_path,
                progress=progress,
                block=True,           # wait for completion
                workers=workers       # parallel connections
            )
            elapsed = time.time() - start_time
            avg_speed = total_mb / elapsed if elapsed > 0 else 0
            print(f"\n✅ Downloaded: {result} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
            return result
        except FloodWait as e:
            print(f"\n⚠️ Flood wait: sleeping {e.value} seconds")
            await asyncio.sleep(e.value)
            # Retry once after waiting
            return await self.download_file(filename, workers)
        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            return None