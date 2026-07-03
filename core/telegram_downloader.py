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
                    # 1. Khali file create karein sahi size ki
                    with open(download_path, 'wb') as f:
                        f.truncate(file_size)

                    # 2. Telegram API ke mutabik strictly max 512KB (524288 bytes) ka chunk size
                    CHUNK_LIMIT = 512 * 1024  
                    
                    # 3. Saare chunks (parts) ki list taiyar karein
                    queue = asyncio.Queue()
                    current_offset = 0
                    while current_offset < file_size:
                        current_limit = min(CHUNK_LIMIT, file_size - current_offset)
                        # Telegram ko offset hamesha 1024 se divide hone waala chahiye (jo 512KB hamesha hota hai)
                        await queue.put((current_offset, current_limit))
                        current_offset += CHUNK_LIMIT

                    downloaded = 0
                    start_time = time.time()
                    
                    # File ki exact location taiyar karein low-level API ke liye
                    file_location = types.InputDocumentFileLocation(
                        id=msg.document.id,
                        access_hash=msg.document.access_hash,
                        file_reference=msg.document.file_reference,
                        thumb_size=''
                    )

                    # 4. Worker function jo parallel mein chunks download karega
                    async def worker():
                        nonlocal downloaded
                        while not queue.empty():
                            try:
                                offset, limit = await queue.get()
                            except asyncio.QueueEmpty:
                                break
                            
                            # Low-level Telegram API call bina kisi limit error ke
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
                                    
                                    # Progress aur speed show karne ke liye
                                    current_mb = downloaded / (1024 * 1024)
                                    elapsed = time.time() - start_time
                                    speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                                    print(f'\r⏳ Parallel Download: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='', flush=True)
                            except Exception as chunk_err:
                                # Agar koi chunk fail ho toh use wapas queue mein daal dein retry ke liye
                                await queue.put((offset, limit))
                                await asyncio.sleep(1)
                            finally:
                                queue.task_done()

                    # 5. Exactly 8 parallel workers chalaein
                    num_workers = 8
                    tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]
                    
                    # Sabhi workers ke khatam hone ka wait karein
                    await asyncio.gather(*tasks)

                    print() # Loop ke baad nayi line ke liye
                    elapsed = time.time() - start_time
                    avg_speed = total_mb / elapsed if elapsed > 0 else 0
                    print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                    return download_path

                except Exception as e:
                    print(f"\n⚠️ Parallel download failed: {e}")
                    print("⏳ Falling back to single-threaded download...")

                    # Fallback System (Agar parallel bilkul hi fail ho jaye)
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
