import os
import time
import asyncio
import aiofiles
from telethon import TelegramClient, functions, types
from config import settings

class TelegramDownloader:
    def __init__(self, api_id, api_hash, session_file):
        """
        Telegram Downloader Class for Parallel Chunk Downloads.
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.client = None

    async def connect(self):
        """
        Telegram Client ko connect aur start karne ke liye.
        """
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        await self.client.start()
        print("✅ Connected to Telegram!")
        return self.client

    async def download_file(self, filename):
        """
        Saved Messages se file dhoondh kar use 8 parallel chunks me download karega.
        """
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
                    # 1. Khali file create karna block-wise writing ke liye
                    with open(download_path, 'wb') as f:
                        f.truncate(file_size)

                    # 2. Telegram chunks definition (Must be multiple of 4KB/4096 bytes)
                    num_chunks = 8
                    chunk_size = (file_size // num_chunks)
                    chunk_size = (chunk_size // 4096) * 4096 
                    if chunk_size == 0:
                        chunk_size = 4096

                    # Chunks ki ranges distribute karna
                    parts = []
                    current_offset = 0
                    while current_offset < file_size:
                        current_limit = min(chunk_size, file_size - current_offset)
                        parts.append((current_offset, current_limit))
                        current_offset += chunk_size

                    downloaded = 0
                    start_time = time.time()
                    
                    # 3. Exact Low-Level Telegram File Location Access Map
                    file_location = types.InputDocumentFileLocation(
                        id=msg.document.id,
                        access_hash=msg.document.access_hash,
                        file_reference=msg.document.file_reference,
                        thumb_size=''
                    )

                    async def download_chunk(offset, limit):
                        nonlocal downloaded
                        
                        # Direct Telegram MTProto request bina standard wrapper error ke
                        result = await self.client(functions.upload.GetFileRequest(
                            location=file_location,
                            offset=offset,
                            limit=limit
                        ))
                        
                        if isinstance(result, types.upload.File):
                            chunk_data = result.bytes
                            # File me binary block safe seek update karna
                            async with aiofiles.open(download_path, 'r+b') as f:
                                await f.seek(offset)
                                await f.write(chunk_data)
                            
                            downloaded += len(chunk_data)
                            
                            # Real-time Live Progress Bar Display
                            current_mb = downloaded / (1024 * 1024)
                            elapsed = time.time() - start_time
                            speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                            
                            # Progress visual calculation
                            percentage = (downloaded / file_size) * 100
                            bars = int(percentage // 5)
                            progress_bar = '█' * bars + '░' * (20 - bars)
                            
                            print(f'\r⏳ Parallel Download: [{progress_bar}] {percentage:.1f}% | {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

                    # 4. Saare 8 chunks ko ek sath gather karke concurrently run karna
                    tasks = [download_chunk(offset, limit) for offset, limit in parts]
                    await asyncio.gather(*tasks)

                    print() # Loop completion clear newline
                    elapsed = time.time() - start_time
                    avg_speed = total_mb / elapsed if elapsed > 0 else 0
                    print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                    return download_path

                except Exception as e:
                    print(f"\n⚠️ Parallel download failed: {e}")
                    print("⏳ Falling back to single-threaded download...")

                    # Emergency Fallback mechanism agar low level drop ho jaye
                    downloaded = 0
                    start_time = time.time()

                    def progress_callback(current, total):
                        current_mb = current / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        elapsed = time.time() - start_time
                        speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                        
                        percentage = (current / total) * 100
                        bars = int(percentage // 5)
                        progress_bar = '█' * bars + '░' * (20 - bars)
                        
                        print(f'\r⏳ Single Download: [{progress_bar}] {percentage:.1f}% | {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

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
        """
        Session cleanly close karne ke liye.
        """
        if self.client:
            await self.client.disconnect()
