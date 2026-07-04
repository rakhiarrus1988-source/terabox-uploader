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
        print("🚀 Igniting Colab Engine (High-Speed Multi-Context Tunnel Engine)...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)

        # OPTIMIZATION: Bigger chunk size for aggressive network pipe throughput
        CHUNK_SIZE = 512 * 1024  # 512 KB Chunks
        MAX_PARALLEL_CHUNKS = 16  # 16 Workers instead of 8 to saturate bandwidth

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

        file_location = types.InputDocumentFileLocation(
            id=target_msg.document.id,
            access_hash=target_msg.document.access_hash,
            file_reference=target_msg.document.file_reference,
            thumb_size=''
        )

        # Open file stream in append-write mode directly on storage (No heavy RAM arrays)
        with open(download_path, 'wb') as f:
            # Setting exact size beforehand prevents Colab I/O delays later
            f.truncate(file_size)

        # High-level client-based DC transfer wrapper using authenticated Takeout sessions
        async def worker():
            nonlocal downloaded

            try:
                # OPTIMIZATION: Takeout avoids Telegram's download throttling triggers
                async with self.client.takeout(files=True) as takeout_client:
                    # Switch internal routing dynamically to file center context
                    if takeout_client.session.dc_id != dc_id:
                        dc_client = await takeout_client._get_client(dc_id)
                    else:
                        dc_client = takeout_client
            except Exception:
                dc_client = self.client

            while not queue.empty():
                try:
                    offset, limit = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                success = False
                for attempt in range(5):
                    try:
                        result = await dc_client(functions.upload.GetFileRequest(
                            location=file_location,
                            offset=offset,
                            limit=limit
                        ))

                        if isinstance(result, types.upload.File):
                            # Concurrent chunk dumping onto block storage without long execution delays
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

                    except Exception:
                        await asyncio.sleep(0.3 * (attempt + 1))  

                if not success:
                    await queue.put((offset, limit))

        try:
            # Launching 16 simultaneous multi-context execution tasks
            worker_tasks = [asyncio.create_task(worker()) for _ in range(MAX_PARALLEL_CHUNKS)]
            await asyncio.gather(*worker_tasks)

            elapsed = time.time() - start_time
            avg_speed = total_mb / elapsed if elapsed > 0 else 0
            print(f"\n✅ High-Speed Download Complete: {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
            return download_path

        except Exception as e:
            print(f"\n❌ High-Speed Multi-Context Engine failed: {e}")
            return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
