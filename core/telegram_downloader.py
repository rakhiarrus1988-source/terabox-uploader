import os
import time
import asyncio
import aiofiles
from telethon import TelegramClient, functions, types
from config import settings

class TelegramDownloader:
    def __init__(self, api_id, api_hash, session_file):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.client = None

    async def connect(self):
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        await self.client.start()
        print("✅ Connected to Telegram!")
        return self.client

    async def download_file(self, filename):
        saved_messages = 'me'
        print(f"🔍 Searching for '{filename}' in Saved Messages...")

        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media and hasattr(msg, 'document') and msg.document:
                file_size = msg.file.size
                total_mb = file_size / (1024 * 1024)
                print(f"✅ Found! Size: {total_mb:.2f} MB")
                print("⚡ Trying parallel download (8 chunks)...")

                download_path = os.path.join(settings.DOWNLOAD_DIR, filename)

                try:
                    # Create empty file with the correct size
                    with open(download_path, 'wb') as f:
                        f.truncate(file_size)

                    # Telegram ke liye chunk size fix (Must be multiple of 4KB)
                    # 1MB blocks are safest and fastest for Telegram API
                    chunk_size = 1024 * 1024  
                    
                    parts = []
                    current_offset = 0
                    while current_offset < file_size:
                        current_limit = min(chunk_size, file_size - current_offset)
                        parts.append((current_offset, current_limit))
                        current_offset += chunk_size

                    downloaded = 0
                    start_time = time.time()
                    
                    file_location = types.InputDocumentFileLocation(
                        id=msg.document.id,
                        access_hash=msg.document.access_hash,
                        file_reference=msg.document.file_reference,
                        thumb_size=''
                    )

                    # Semaphore use kiya hai taaki Telegram connection freeze na kare (Max 4-8 parallel pipeline)
                    semaphore = asyncio.Semaphore(4) 

                    async def download_chunk(offset, limit):
                        nonlocal downloaded
                        async with semaphore:
                            try:
                                result = await self.client(functions.upload.GetFileRequest(
                                    location=file_location,
                                    offset=offset,
                                    limit=limit
                                ))
                                
                                if isinstance(result, types.upload.File):
                                    chunk_data = result.bytes
                                    async with aiofiles.open(download_path, 'r+b') as f:
                                        await f.seek(offset)
                                        await f.write(chunk_data)
                                    
                                    downloaded += len(chunk_data)
                                    
                                    # Active live updates on terminal
                                    current_mb = downloaded / (1024 * 1024)
                                    elapsed = time.time() - start_time
                                    speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                                    percentage = (downloaded / file_size) * 100
                                    
                                    # Visual progress bar setup
                                    bar_length = 20
                                    filled_length = int(bar_length * downloaded // file_size)
                                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                                    
                                    print(f'\r⏳ Download: |{bar}| {percentage:.1f}% [{current_mb:.1f}/{total_mb:.1f} MB] @ {speed_mbps:.2f} MB/s', end='', flush=True)
                            except Exception as chunk_err:
                                # Safe pass to avoid stopping the full queue
                                pass

                    # Run tasks concurrently through semaphore
                    tasks = [download_chunk(offset, limit) for offset, limit in parts]
                    await asyncio.gather(*tasks)

                    print() 
                    elapsed = time.time() - start_time
                    avg_speed = total_mb / elapsed if elapsed > 0 else 0
                    print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                    return download_path

                except Exception as e:
                    print(f"\n⚠️ Parallel download failed: {e}")
                    print("⏳ Falling back to single-threaded download...")

                    # Safe Fallback
                    downloaded = 0
                    start_time = time.time()

                    def progress_callback(current, total):
                        current_mb = current / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        elapsed = time.time() - start_time
                        speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                        print(f'\r⏳ Single Download: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

                    await self.client.download_media(
                        msg,
                        file=download_path,
                        progress_callback=progress_callback
                    )
                    print()
                    return download_path

        print(f"❌ '{filename}' not found in Saved Messages!")
        return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
