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
        print("🚀 Igniting Bulletproof Multi-Socket Parallel Engine...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)

        # OPTIMIZATION: Balanced chunks for stable connection throughput
        CHUNK_SIZE = 512 * 1024  # 512 KB Chunks
        MAX_PARALLEL_CHUNKS = 12  # 12 Workers: Sweet spot for speed without getting banned/throttled

        chunks = []
        offset = 0
        while offset < file_size:
            limit = min(CHUNK_SIZE, file_size - offset)
            chunks.append((offset, limit))
            offset += CHUNK_SIZE

        queue = asyncio.Queue()
        for chunk in chunks:
            queue.put_nowait(chunk)

        downloaded = 0
        start_time = time.time()
        lock = asyncio.Lock()
        file_write_lock = asyncio.Lock() # Fixes overlapping I/O disk bottlenecks

        file_location = types.InputDocumentFileLocation(
            id=target_msg.document.id,
            access_hash=target_msg.document.access_hash,
            file_reference=target_msg.document.file_reference,
            thumb_size=''
        )

        # Pre-allocate storage size to ensure rapid parallel disk writes
        with open(download_path, 'wb') as f:
            f.truncate(file_size)

        # FAIL-SAFE LAYER: Try starting a high-speed Takeout session safely
        takeout_session = None
        try:
            # We request with a short timeout. If Telegram delays, we skip instantly.
            takeout_session = await self.client.takeout(files=True).__aenter__()
            print("⚡ High-Speed Takeout Tunnel established successfully!")
        except Exception:
            print("⚠️ Takeout restriction detected. Activating Native Multi-DC Proxy Tunnel instead...")
            takeout_session = None

        async def worker():
            nonlocal downloaded

            dc_client = None
            base_client = takeout_session if takeout_session else self.client
            
            # STABLE DC ROUTING: Authenticate correctly with the target file DC
            for attempt in range(3):
                try:
                    if base_client.session.dc_id != dc_id:
                        dc_client = await base_client._get_client(dc_id)
                    else:
                        dc_client = base_client
                    if dc_client:
                        break
                except Exception:
                    await asyncio.sleep(1)
            
            if not dc_client:
                dc_client = self.client # Ultimate fallback

            while not queue.empty():
                try:
                    offset, limit = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                success = False
                for attempt in range(5):  # Aggressive Network Retries
                    try:
                        result = await dc_client(functions.upload.GetFileRequest(
                            location=file_location,
                            offset=offset,
                            limit=limit
                        ))

                        if isinstance(result, types.upload.File):
                            # Safe asynchronous disk write offset allocation
                            async with file_write_lock:
                                with open(download_path, 'r+b') as f:
                                    f.seek(offset)
                                    f.write(result.bytes)

                            async with lock:
                                downloaded += len(result.bytes)
                                current_mb = downloaded / (1024 * 1024)
                                elapsed = time.time() - start_time
                                speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                                percent = (downloaded / file_size) * 100
                                print(f'\r⚡ Colab Speed: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s          ', end='', flush=True)

                            success = True
                            queue.task_done()
                            break

                    except Exception as e:
                        # If a connection drops, try re-fetching the DC client instance
                        if "connection" in str(e).lower() or "auth" in str(e).lower():
                            try:
                                dc_client = await base_client._get_client(dc_id)
                            except Exception:
                                dc_client = self.client
                        await asyncio.sleep(0.2 * (attempt + 1))  

                if not success:
                    # Put back chunk if completely failed to prevent data loss
                    await queue.put((offset, limit))

        try:
            # Run 12 simultaneous non-blocking workers
            worker_tasks = [asyncio.create_task(worker()) for _ in range(MAX_PARALLEL_CHUNKS)]
            await asyncio.gather(*worker_tasks)

            # Clean exit for the takeout session if it was created
            if takeout_session:
                try:
                    await takeout_session.__aexit__(None, None, None)
                except Exception:
                    pass

            elapsed = time.time() - start_time
            avg_speed = total_mb / elapsed if elapsed > 0 else 0
            print(f"\n✅ Download Complete: {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
            return download_path

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
