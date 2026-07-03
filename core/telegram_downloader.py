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

        async_msg = None
        async for msg in self.client.iter_messages(saved_messages, search=filename):
            if msg.media and hasattr(msg, 'document') and msg.document:
                async_msg = msg
                break

        if async_msg:
            file_size = async_msg.file.size
            total_mb = file_size / (1024 * 1024)
            print(f"✅ Found! Size: {total_mb:.2f} MB")
            print("⚡ Trying parallel download (8 chunks max concurrency)...")

            download_path = os.path.join(settings.DOWNLOAD_DIR, filename)

            try:
                # File ko correct size par truncate karke khali file create karna
                with open(download_path, 'wb') as f:
                    f.truncate(file_size)

                # Telegram API limits ke mutabik 512KB chunks sabse stable hain
                # Yeh 4KB aur 1MB dono rules ko strictly follow karta hai
                chunk_size = 512 * 1024  
                
                parts = []
                current_offset = 0
                while current_offset < file_size:
                    current_limit = min(chunk_size, file_size - current_offset)
                    # Last chunk ko chhodkar baki sabhi 4KB boundary se align hone chahiye
                    if current_limit % 4096 != 0 and current_offset + current_limit < file_size:
                        current_limit = (current_limit // 4096) * 4096

                    parts.append((current_offset, current_limit))
                    current_offset += current_limit

                downloaded = 0
                start_time = time.time()
                
                # Ek baar mein sirf 8 requests parallel bhejne ke liye Semaphore
                semaphore = asyncio.Semaphore(8)

                file_location = types.InputDocumentFileLocation(
                    id=async_msg.document.id,
                    access_hash=async_msg.document.access_hash,
                    file_reference=async_msg.document.file_reference,
                    thumb_size=''
                )

                def get_progress_bar(percentage, bar_length=20):
                    """Custom loading percentage bar generator"""
                    filled_length = int(round(bar_length * percentage / 100))
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    return f"[{bar}] {percentage:.1f}%"

                async def download_chunk(offset, limit):
                    nonlocal downloaded
                    async with semaphore:
                        # Low-level exact chunk fetch request
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
                            
                            # Percentage aur live download speed calculation
                            current_mb = downloaded / (1024 * 1024)
                            percentage = (downloaded / file_size) * 100
                            elapsed = time.time() - start_time
                            speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                            
                            bar_str = get_progress_bar(percentage)
                            print(f'\r⏳ Parallel Download: {bar_str} | {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

                # Saare chunks ko asynchronously parallel queue mein execute karna
                tasks = [download_chunk(offset, limit) for offset, limit in parts]
                await asyncio.gather(*tasks)

                print()  # Line break for cleanup
                elapsed = time.time() - start_time
                avg_speed = total_mb / elapsed if elapsed > 0 else 0
                print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
                return download_path

            except Exception as e:
                print(f"\n⚠️ Parallel download failed: {e}")
                print("⏳ Falling back to single-threaded download...")

                downloaded = 0
                start_time = time.time()

                def progress_callback(current, total):
                    current_mb = current / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    percentage = (current / total) * 100
                    elapsed = time.time() - start_time
                    speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                    
                    filled_length = int(round(20 * percentage / 100))
                    bar = '█' * filled_length + '░' * (20 - filled_length)
                    
                    print(f'\r⏳ Single Download: [{bar}] {percentage:.1f}% | {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)

                await self.client.download_media(
                    async_msg,
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
