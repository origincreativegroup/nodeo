"""
WebSocket endpoints for real-time progress updates (JSPOW v2)
"""
import asyncio
import logging
import json
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import WatchedFolder
from app.services.folder_watcher import watcher_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket v2"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._broadcast_task: asyncio.Task = None
        self._running = False

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket client {client_id} connected. Total connections: {self.total_connections}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket client {client_id} disconnected. Total connections: {self.total_connections}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for client_id, connections in self.active_connections.items():
            for websocket in list(connections):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {e}")
                    disconnected.append((websocket, client_id))

        # Clean up disconnected clients
        for websocket, client_id in disconnected:
            self.disconnect(websocket, client_id)

    async def broadcast_to_folder(self, folder_id: UUID, message: dict):
        """Broadcast a message to all clients watching a specific folder"""
        message["folder_id"] = str(folder_id)
        await self.broadcast(message)

    @property
    def total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())

    async def start_broadcast_loop(self):
        """Start the periodic broadcast loop for progress updates"""
        if self._running:
            return

        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_worker())
        logger.info("WebSocket broadcast loop started")

    async def stop_broadcast_loop(self):
        """Stop the periodic broadcast loop"""
        if not self._running:
            return

        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket broadcast loop stopped")

    async def _broadcast_worker(self):
        """Background worker that broadcasts progress updates"""
        while self._running:
            try:
                # Broadcast progress updates every 2 seconds
                await asyncio.sleep(2)

                if self.total_connections == 0:
                    continue

                # Get watcher status
                watcher_status = await watcher_manager.get_status()

                # Get folder progress from database
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(WatchedFolder)
                    )
                    folders = result.scalars().all()

                    folder_updates = []
                    for folder in folders:
                        progress = 0
                        if folder.file_count > 0:
                            progress = int((folder.analyzed_count / folder.file_count) * 100)

                        folder_updates.append({
                            "folder_id": str(folder.id),
                            "status": folder.status.value,
                            "progress": progress,
                            "file_count": folder.file_count,
                            "analyzed_count": folder.analyzed_count,
                            "pending_count": folder.pending_count
                        })

                # Broadcast update
                if folder_updates:
                    await self.broadcast({
                        "type": "progress_update",
                        "timestamp": asyncio.get_event_loop().time(),
                        "watcher_status": {
                            "running": watcher_status["running"],
                            "active_watchers": watcher_status["active_watchers"],
                            "queue_size": watcher_status["queue_size"]
                        },
                        "folders": folder_updates
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast worker: {e}")
                await asyncio.sleep(1)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates

    Clients will receive periodic updates about:
    - Folder scanning progress
    - File analysis status
    - Rename suggestion counts
    - Processing queue status
    """
    client_id = f"client_{id(websocket)}"

    await manager.connect(websocket, client_id)

    try:
        # Send initial status
        watcher_status = await watcher_manager.get_status()
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to JSPOW v2 progress stream",
            "watcher_status": watcher_status
        }, websocket)

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for messages from client (e.g., ping to keep alive)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                # Handle client messages
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await manager.send_personal_message({
                            "type": "pong"
                        }, websocket)
                    elif message.get("type") == "subscribe_folder":
                        folder_id = message.get("folder_id")
                        # TODO: Implement folder-specific subscriptions
                        await manager.send_personal_message({
                            "type": "subscribed",
                            "folder_id": folder_id
                        }, websocket)

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}: {data}")

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_personal_message({
                    "type": "ping"
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        logger.info(f"Client {client_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket, client_id)


@router.get("/ws/status")
async def get_websocket_status():
    """
    Get current WebSocket connection status
    """
    return {
        "active_connections": manager.total_connections,
        "broadcast_running": manager._running
    }
