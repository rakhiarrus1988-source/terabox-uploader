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
        print("🚀 Igniting High-Speed Single-Threaded Turbo Tunnel...")

        download_path = os.path.join(settings.DOWNLOAD_DIR, filename)

        # FIX 1: Max allowed chunk size for Telegram (512 KB)
        # Bada chunk size = Kam requests = Single thread mein maximum speed.
        CHUNK_SIZE = 512 * 1024  
        
        file_location = types.InputDocumentFileLocation(
            id=target_msg.document.id,
            access_hash=target_msg.document.access_hash,
            file_reference=target_msg.document.file_reference,
            thumb_size=''
        )

        # Auto DC Migration Check
        dc_client = self.client
        try:
            if self.client.session.dc_id != dc_id:
                print(f"🔄 Migrating connection tunnel to DC {dc_id}...")
                dc_client = await self.client._get_client(dc_id)
        except Exception:
            dc_client = self.client

        downloaded = 0
        start_time = time.time()

        print(f'\r⚡ Colab Speed: [0.0%] 0.0/{total_mb:.1f} MB @ 0.0 MB/s', end='', flush=True)

        # FIX 2: Streaming directly to file to prevent RAM fragmentation
        try:
            with open(download_path, 'wb') as f:
                offset = 0
                while offset < file_size:
                    limit = min(CHUNK_SIZE, file_size - offset)
                    
                    success = False
                    for attempt in range(5):
                        try:
                            # Pure sequential single-threaded execution
                            result = await dc_client(functions.upload.GetFileRequest(
                                location=file_location,
                                offset=offset,
                                limit=limit
                            ))

                            if isinstance(result, types.upload.File):
                                f.write(result.bytes)
                                downloaded += len(result.bytes)
                                
                                # Progress & Real-time Speed Monitoring
                                current_mb = downloaded / (1024 * 1024)
                                elapsed = time.time() - start_time
                                speed_mbps = current_mb / elapsed if elapsed > 0 else 0
                                percent = (downloaded / file_size) * 100
                                print(f'\r⚡ Colab Speed: [{percent:.1f}%] {current_mb:.1f}/{total_mb:.1f} MB @ {speed_mbps:.1f} MB/s          ', end='', flush=True)
                                
                                success = True
                                break
                            
                            elif isinstance(result, types.upload.FileCdnRedirect):
                                await asyncio.sleep(1)
                                break
                                
                        except Exception as e:
                            # Network fluctuation handling
                            await asyncio.sleep(1)

                    if not success:
                        print(f"\n❌ Failed to fetch chunk at offset {offset}. Retrying block...")
                        return None
                        
                    offset += limit

            elapsed = time.time() - start_time
            avg_speed = total_mb / elapsed if elapsed > 0 else 0
            print(f"\n✅ Downloaded (Single-Thread Turbo): {download_path} ({total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed:.1f} MB/s)")
            return download_path

        except Exception as e:
            print(f"\n❌ Single thread download failed: {e}")
            return None

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("🔌 Disconnected from Telegram!")
