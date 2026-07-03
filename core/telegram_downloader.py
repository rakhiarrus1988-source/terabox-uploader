import os
import time
import asyncio
import aiofiles
from telethon import TelegramClient
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
                
                # Try parallel first
                try:
                    # Create empty file
                    with open(download_path, 'wb') as f:
                        f.truncate(file_size)
                    
                    num_chunks = 8
                    chunk_size = file_size // num_chunks
                    
                    downloaded = 0
                    last_update = 0
                    start_time = time.time()
                    
                    async def download_chunk(chunk_num):
                        nonlocal downloaded
                        start = chunk_num * chunk_size
                        end = start + chunk_size if chunk_num < num_chunks - 1 else file_size
                        
                        # Download chunk using msg.document directly
                        chunk_data = await self.client.download_file(
                            msg.document,
                            offset=start,
                            limit=end - start,
                            request_size=2 * 1024 * 1024
                        )
                        
                        async with aiofiles.open(download_path, 'r+b') as f:
                            await f.seek(start)
                            await f.write(chunk_data)
                        
                        downloaded += (end - start)
                        return True
                    
                    tasks = [download_chunk(i) for i in range(num_chunks)]
                    for task in asyncio.as_completed(tasks):
                        await task
                        
                        if time.time() - last_update > 0.5 or downloaded >= file_size:
                            last_update = time.time()
                            current_mb = downloaded / (1024 * 1024)
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                                print(f'\r⏳ Parallel Download: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='')
                            else:
                                print(f'\r⏳ Parallel Download: {current_mb:.1f}MB / {total_mb:.1f}MB', end='')
                            
                            if downloaded >= file_size:
                                print()
                                elapsed = time.time() - start_time
                                avg_speed = (file_size / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                                print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                                return download_path
                    
                    # If we reach here, parallel succeeded
                    return download_path
                    
                except Exception as e:
                    print(f"\n⚠️ Parallel download failed: {e}")
                    print("⏳ Falling back to single-threaded download...")
                    
                    # Fallback: single-threaded download with progress
                    downloaded = 0
                    last_update = 0
                    start_time = time.time()
                    
                    def progress_callback(current, total):
                        nonlocal downloaded, last_update
                        downloaded = current
                        if time.time() - last_update > 0.5 or current == total:
                            last_update = time.time()
                            current_mb = current / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed_mbps = (current / (1024 * 1024)) / elapsed
                                print(f'\r⏳ Single Download: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='')
                            else:
                                print(f'\r⏳ Single Download: {current_mb:.1f}MB / {total_mb:.1f}MB', end='')
                            if current == total:
                                print()
                    
                    await self.client.download_media(
                        msg,
                        file=download_path,
                        progress_callback=progress_callback
                    )
                    
                    elapsed = time.time() - start_time
                    avg_speed = (file_size / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    print(f"✅ Downloaded (Single): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                    return download_path
        
        print(f"❌ '{filename}' not found in Saved Messages!")
        return None
    
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()