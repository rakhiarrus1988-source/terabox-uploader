import os
import time
import asyncio
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
        print("🚀 Igniting Colab Engine (Multi-DC Socket Routing via 8 Workers)...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
        
        CHUNK_SIZE = 512 * 1024  # 512 KB Chunks
        MAX_PARALLEL_CHUNKS = 8  # 8 Parallel Threads

        # Pre-allocate buffer to avoid disk bottlenecks
        file_buffer = bytearray(file_size)

        chunks = []
        offset = 0
        while offset < file_size:
            limit = min(CHUNK_SIZE, file_size - offset)
            chunks.append((offset, limit))
            offset += CHUNK_SIZE

        queue = asyncio.Queue()
        for chunk in chunks:
            await queue.put(chunk)

        downloaded = 0
        start_time = time.time()
        lock = asyncio.Lock()

        file_location = types.InputDocumentFileLocation(
            id=target_msg.document.id,
            access_hash=target_msg.document.access_hash,
            file_reference=target_msg.document.file_reference,
            thumb_size=''
        )

        # Initial progress bar trigger
        print(f'\r⚡ Colab Speed: [0.0%] 0.0/{total_mb:.1f} MB @ 0.0 MB/s', end='', flush=True)

        # High-level client-based DC transfer wrapper
        async def worker():
            nonlocal downloaded
            
            # Agar main client usi DC par nahi hai jahan file hai, toh export use karenge
            # Yeh bina freeze hue background mein automatic authorization switch karta hai
            try:
                if self.client.session.dc_id != dc_id:
                    # Dynamic connection pool for target DC
                    dc_client = await self.client.create_exported_phone_connection(dc_id)
                else:
                    dc_client = self.client
            except Exception:
                dc_client = self.client

            while not queue.empty():
                try:
                    offset, limit = await queue.get()
                except asyncio.QueueEmpty:
                    break

                success = False
                for attempt in range(5):  # Network fallback retries
                    try:
                        result = await dc_client(functions.upload.GetFileRequest(
                            location=file_location,
                            offset=offset,
                            limit=limit
                        ))

                        if isinstance(result, types.upload.File):
                            async with lock:
                                file_buffer[offset:offset+len(result.bytes)] = result.bytes
                                downloaded += len(result.bytes)
                            
                                current_mb = downloaded / (1024 * 1024)
                                elapsed = time.time() - start_time
                                speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                                percent = (downloaded / file_size) * 100
                                print(f'\r⚡ Colab Speed: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s          ', end='', flush=True)
                            
                            success = True
                            break
                        
                        elif isinstance(result, types.upload.FileCdnRedirect):
                            # Handle rare CDN redirections if Telegram pushes it
                            await asyncio.sleep(1)
                            break
                            
                    except Exception:
                        await asyncio.sleep(0.5)  
                
                queue.task_done()
                if not success:
                    await queue.put((offset, limit))

        try:
            # Spawning 8 non-blocking workers simultaneously
            worker_tasks = [asyncio.create_task(worker()) for _ in range(MAX_PARALLEL_CHUNKS)]
            await asyncio.gather(*worker_tasks)

            print("\n💾 Dumping downloaded bytes into Colab Storage...")
            with open(download_path, 'wb') as f:
                f.write(file_buffer)
                
            del file_buffer  # Clear RAM immediately

            elapsed = time.time() - start_time
            avg_speed = total_mb / elapsed if elapsed > 0 else 0
            print(f"✅ Downloaded (Parallel): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
            return download_path

        except Exception as e:
            print(f"\n❌ Parallel download failed: {e}")
            return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
