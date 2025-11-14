"""
Folder watcher service for monitoring filesystem changes and triggering analysis
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from datetime import datetime
from uuid import UUID

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import WatchedFolder, WatchedFolderStatus
from app.config import settings

logger = logging.getLogger(__name__)


class FolderEventHandler(FileSystemEventHandler):
    """Handler for filesystem events in watched folders"""

    def __init__(self, folder_id: UUID, folder_path: str, manager: 'WatcherManager'):
        self.folder_id = folder_id
        self.folder_path = folder_path
        self.manager = manager
        self.allowed_extensions = set(
            settings.allowed_image_exts + settings.allowed_video_exts
        )

    def _is_valid_file(self, file_path: str) -> bool:
        """Check if file is a valid media file"""
        path = Path(file_path)
        ext = path.suffix.lower().lstrip('.')
        return ext in self.allowed_extensions and not path.name.startswith('.')

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        if self._is_valid_file(event.src_path):
            logger.info(f"New file detected: {event.src_path}")
            # Queue file for processing
            asyncio.create_task(
                self.manager.queue_file_for_processing(
                    self.folder_id,
                    event.src_path
                )
            )

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        # We can optionally handle modifications
        # For now, we'll ignore them to avoid duplicate processing


class WatcherThread:
    """Manages a single folder watch operation"""

    def __init__(self, folder_id: UUID, folder_path: str, manager: 'WatcherManager'):
        self.folder_id = folder_id
        self.folder_path = folder_path
        self.manager = manager
        self.observer = Observer()
        self.event_handler = FolderEventHandler(folder_id, folder_path, manager)
        self.is_running = False

    def start(self):
        """Start watching the folder"""
        try:
            path = Path(self.folder_path)
            if not path.exists():
                logger.error(f"Folder does not exist: {self.folder_path}")
                asyncio.create_task(self.manager.set_folder_error(
                    self.folder_id,
                    "Folder does not exist"
                ))
                return

            self.observer.schedule(
                self.event_handler,
                str(path),
                recursive=True
            )
            self.observer.start()
            self.is_running = True
            logger.info(f"Started watching folder: {self.folder_path}")

        except Exception as e:
            logger.error(f"Error starting watcher for {self.folder_path}: {e}")
            asyncio.create_task(self.manager.set_folder_error(
                self.folder_id,
                str(e)
            ))

    def stop(self):
        """Stop watching the folder"""
        if self.is_running:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.is_running = False
            logger.info(f"Stopped watching folder: {self.folder_path}")


class WatcherManager:
    """Manages all folder watchers and coordinates processing"""

    def __init__(self):
        self.watchers: Dict[UUID, WatcherThread] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the watcher manager and load existing watched folders"""
        if self._running:
            return

        self._running = True
        logger.info("Starting WatcherManager...")

        # Load existing watched folders from database
        await self._load_watched_folders()

        # Start background worker for processing queue
        self._worker_task = asyncio.create_task(self._process_queue_worker())

        logger.info("WatcherManager started")

    async def stop(self):
        """Stop all watchers"""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping WatcherManager...")

        # Stop all watchers
        for watcher in list(self.watchers.values()):
            watcher.stop()
        self.watchers.clear()

        # Cancel worker task
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("WatcherManager stopped")

    async def _load_watched_folders(self):
        """Load watched folders from database and start watchers"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WatchedFolder).where(
                    WatchedFolder.status.in_([
                        WatchedFolderStatus.ACTIVE,
                        WatchedFolderStatus.SCANNING
                    ])
                )
            )
            folders = result.scalars().all()

            for folder in folders:
                await self.add_watcher(folder.id, folder.path)

                # Trigger initial scan for active folders
                if folder.status == WatchedFolderStatus.ACTIVE:
                    asyncio.create_task(self.scan_folder(folder.id))

    async def add_watcher(self, folder_id: UUID, folder_path: str) -> bool:
        """Add a new folder watcher"""
        if folder_id in self.watchers:
            logger.warning(f"Watcher already exists for folder {folder_id}")
            return False

        try:
            watcher = WatcherThread(folder_id, folder_path, self)
            watcher.start()
            self.watchers[folder_id] = watcher
            return True

        except Exception as e:
            logger.error(f"Error adding watcher for {folder_path}: {e}")
            await self.set_folder_error(folder_id, str(e))
            return False

    async def remove_watcher(self, folder_id: UUID):
        """Remove a folder watcher"""
        watcher = self.watchers.get(folder_id)
        if watcher:
            watcher.stop()
            del self.watchers[folder_id]
            logger.info(f"Removed watcher for folder {folder_id}")

    async def pause_watcher(self, folder_id: UUID):
        """Pause a folder watcher"""
        await self.remove_watcher(folder_id)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WatchedFolder).where(WatchedFolder.id == folder_id)
            )
            folder = result.scalar_one_or_none()
            if folder:
                folder.status = WatchedFolderStatus.PAUSED
                await db.commit()

    async def resume_watcher(self, folder_id: UUID):
        """Resume a paused folder watcher"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WatchedFolder).where(WatchedFolder.id == folder_id)
            )
            folder = result.scalar_one_or_none()
            if folder:
                folder.status = WatchedFolderStatus.ACTIVE
                await db.commit()
                await self.add_watcher(folder_id, folder.path)

    async def scan_folder(self, folder_id: UUID):
        """Perform initial scan of folder for existing files"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WatchedFolder).where(WatchedFolder.id == folder_id)
            )
            folder = result.scalar_one_or_none()

            if not folder:
                logger.error(f"Folder {folder_id} not found")
                return

            try:
                # Update status to scanning
                folder.status = WatchedFolderStatus.SCANNING
                folder.last_scan_at = datetime.utcnow()
                await db.commit()

                # Scan directory
                path = Path(folder.path)
                if not path.exists():
                    await self.set_folder_error(folder_id, "Folder does not exist")
                    return

                allowed_exts = set(
                    settings.allowed_image_exts + settings.allowed_video_exts
                )

                files = []
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        ext = file_path.suffix.lower().lstrip('.')
                        if ext in allowed_exts and not file_path.name.startswith('.'):
                            files.append(str(file_path))

                # Update file count
                folder.file_count = len(files)
                await db.commit()

                # Queue files for processing
                logger.info(f"Found {len(files)} files in {folder.path}")
                for file_path in files:
                    await self.queue_file_for_processing(folder_id, file_path)

                # Update status back to active
                await db.refresh(folder)
                folder.status = WatchedFolderStatus.ACTIVE
                await db.commit()

                logger.info(f"Scan completed for folder {folder_id}")

            except Exception as e:
                logger.error(f"Error scanning folder {folder_id}: {e}")
                await self.set_folder_error(folder_id, str(e))

    async def queue_file_for_processing(self, folder_id: UUID, file_path: str):
        """Add file to processing queue"""
        await self.processing_queue.put({
            'folder_id': folder_id,
            'file_path': file_path,
            'queued_at': datetime.utcnow()
        })

    async def _process_queue_worker(self):
        """Background worker that processes queued files"""
        logger.info("Processing queue worker started")

        while self._running:
            try:
                # Get next item from queue (with timeout to allow checking _running)
                try:
                    item = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the file
                await self._process_file(
                    item['folder_id'],
                    item['file_path']
                )

                # Mark task as done
                self.processing_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue worker: {e}")
                await asyncio.sleep(1)

        logger.info("Processing queue worker stopped")

    async def _process_file(self, folder_id: UUID, file_path: str):
        """Process a single file using the file processor worker"""
        logger.info(f"Processing file: {file_path}")

        try:
            from app.workers.file_processor import file_processor
            success = await file_processor.process_file(folder_id, file_path)

            if success:
                logger.info(f"Successfully processed: {file_path}")
            else:
                logger.warning(f"Failed to process: {file_path}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)

    async def set_folder_error(self, folder_id: UUID, error_message: str):
        """Set folder to error status"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WatchedFolder).where(WatchedFolder.id == folder_id)
            )
            folder = result.scalar_one_or_none()
            if folder:
                folder.status = WatchedFolderStatus.ERROR
                folder.error_message = error_message
                await db.commit()

    async def get_status(self) -> dict:
        """Get status of all watchers"""
        return {
            'running': self._running,
            'active_watchers': len(self.watchers),
            'queue_size': self.processing_queue.qsize(),
            'watchers': {
                str(folder_id): {
                    'folder_path': watcher.folder_path,
                    'is_running': watcher.is_running
                }
                for folder_id, watcher in self.watchers.items()
            }
        }


# Global watcher manager instance
watcher_manager = WatcherManager()
