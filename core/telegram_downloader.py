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

    async def _get_dc_client(self, dc_id):
        """Colab High-Speed dynamic DC pipeline connection"""
        if self.client.session.dc_id == dc_id:
            return self.client
        try:
            return await self.client._get_client(dc_id)
        except Exception:
            return await self.client.create_exported_phone_connection(dc_id)

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
        print("🚀 Igniting Colab Engine (In-Memory Ring Buffering via 8 Workers)...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)
        
        # 8 Workers optimization for Google Colab Network Bandwidth
        CHUNK_SIZE = 512 * 1024  # 512 KB (Maximum legal MTProto chunk)
        MAX_PARALLEL_CHUNKS = 8  # Strictly locked to 8 workers as requested

        # Memory Buffer Allocation to bypass Colab Disk I/O Bottleneck
        file_buffer = bytearray(file_size)

        # Chunks distribution mapping
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

        # Worker logic: Direct raw memory insertion
        async def worker():
            nonlocal downloaded
            try:
                dc_client = await self._get_dc_client(dc_id)
            except Exception:
                dc_client = self.client

            while not queue.empty():
                try:
                    offset, limit = await queue.get()
                except asyncio.QueueEmpty:
                    break

                success = False
                for attempt in range(5):  # Network spike retry limit
                    try:
                        result = await dc_client(functions.upload.GetFileRequest(
                            location=file_location,
                            offset=offset,
                            limit=limit
                        ))

                        if isinstance(result, types.upload.File):
                            # Fast pointer array slice replacement (Zero Disk Overhead)
                            async with lock:
                                file_buffer[offset:offset+len(result.bytes)] = result.bytes
                                downloaded += len(result.bytes)
                            
                            # Speed speedometer calculation
                            current_mb = downloaded / (1024 * 1024)
                            elapsed = time.time() - start_time
                            speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                            percent = (downloaded / file_size) * 100
                            print(f'\r⚡ Colab Speed: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s', end='', flush=True)
                            
                            success = True
                            break
                    except Exception:
                        await asyncio.sleep(0.3)  # Short sleep before retry
                
                queue.task_done()
                if not success:
                    await queue.put((offset, limit))

        try:
            # 8 Multi-sockets firing in parallel
            worker_tasks = [asyncio.create_task(worker()) for _ in range(MAX_PARALLEL_CHUNKS)]
            await asyncio.gather(*worker_tasks)

            print("\n💾 Dumping downloaded bytes into Colab Storage...")
            with open(download_path, 'wb') as f:
                f.write(file_buffer)
                
            del file_buffer  # Instant RAM Cleanup

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
