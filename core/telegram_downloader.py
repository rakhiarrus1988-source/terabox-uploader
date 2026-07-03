import os
import time
import asyncio
import aiofiles
from telethon import TelegramClient
from telethon.tl.types import InputDocumentFileLocation
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
        """Search and download file from Saved Messages - FULL BANDWIDTH"""
        saved_messages = 'me'
        
        print(f"🔍 Searching for '{filename}' in Saved Messages...")
        
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media:
                file_size = msg.file.size
                total_mb = file_size / (1024 * 1024)
                print(f"✅ Found! Size: {total_mb:.2f} MB")
                print("⚡ Parallel download starting (FULL BANDWIDTH)...")
                
                download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
                
                # Create empty file
                with open(download_path, 'wb') as f:
                    f.truncate(file_size)
                
                # Parallel chunk download
                chunk_size = 10 * 1024 * 1024  # 10MB per chunk
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                
                # Get file location
                location = InputDocumentFileLocation(
                    id=msg.document.id,
                    access_hash=msg.document.access_hash,
                    file_reference=msg.document.file_reference,
                    thumb_size=''
                )
                
                downloaded = 0
                last_update = 0
                start_time = time.time()
                
                async def download_chunk(chunk_num):
                    start = chunk_num * chunk_size
                    end = min(start + chunk_size, file_size)
                    
                    try:
                        # Download chunk
                        chunk_data = await self.client.download_file(
                            location,
                            offset=start,
                            limit=end - start,
                            request_size=2 * 1024 * 1024  # 2MB request size for speed
                        )
                        
                        # Write chunk to file
                        async with aiofiles.open(download_path, 'r+b') as f:
                            await f.seek(start)
                            await f.write(chunk_data)
                        
                        return chunk_num, (end - start)
                    except Exception as e:
                        print(f"\n❌ Chunk {chunk_num} failed: {e}")
                        return chunk_num, 0
                
                # Create tasks
                tasks = [download_chunk(i) for i in range(total_chunks)]
                
                # Process with progress
                for task in asyncio.as_completed(tasks):
                    chunk_num, size = await task
                    downloaded += size
                    
                    # Update progress every 0.5 seconds
                    if time.time() - last_update > 0.5 or downloaded >= file_size:
                        last_update = time.time()
                        current_mb = downloaded / (1024 * 1024)
                        total_mb = file_size / (1024 * 1024)
                        
                        # Speed calculation
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                            print(f'\r⏳ Downloading: {current_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mbps:.1f} MB/s', end='')
                        else:
                            print(f'\r⏳ Downloading: {current_mb:.1f}MB / {total_mb:.1f}MB', end='')
                        
                        if downloaded >= file_size:
                            print()  # New line
                            elapsed = time.time() - start_time
                            avg_speed = (file_size / (1024 * 1024)) / elapsed
                            print(f"✅ Downloaded: {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                            return download_path
        
        print(f"❌ '{filename}' not found in Saved Messages!")
        return None
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()