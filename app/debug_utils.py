"""Debug utilities for nodeo"""
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class DebugInfo:
    """System debug information collector"""

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": sys.platform,
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "process_id": os.getpid(),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """Get environment configuration"""
        from app.config import settings

        return {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug_mode": settings.debug,
            "database_url": settings.database_url.split('@')[-1] if '@' in settings.database_url else "configured",
            "redis_url": settings.redis_url.split('@')[-1] if '@' in settings.redis_url else "configured",
            "ollama_host": settings.ollama_host,
            "ollama_model": settings.ollama_model,
            "nextcloud_url": settings.nextcloud_url,
            "nextcloud_auto_sync": settings.nextcloud_auto_sync,
            "storage_root": settings.storage_root,
            "upload_dir": settings.upload_dir,
        }

    @staticmethod
    async def check_database_connection(db) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from sqlalchemy import text

            start = time.time()
            result = await db.execute(text("SELECT 1"))
            duration = time.time() - start

            return {
                "status": "connected",
                "response_time_ms": round(duration * 1000, 2),
                "result": result.scalar(),
            }
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    async def check_ollama_connection() -> Dict[str, Any]:
        """Check Ollama/LLaVA connectivity"""
        try:
            from app.ai import llava_client

            start = time.time()
            # Simple test - check if we can reach the host
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{llava_client.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    duration = time.time() - start
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "connected",
                            "response_time_ms": round(duration * 1000, 2),
                            "models": [m.get("name") for m in data.get("models", [])],
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                        }
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    async def check_nextcloud_connection() -> Dict[str, Any]:
        """Check Nextcloud connectivity"""
        try:
            from app.storage import nextcloud_client

            start = time.time()
            files = await nextcloud_client.list_files("")
            duration = time.time() - start

            return {
                "status": "connected",
                "response_time_ms": round(duration * 1000, 2),
                "url": nextcloud_client.url,
                "username": nextcloud_client.username,
                "base_path": nextcloud_client.base_path,
                "files_in_root": len(files),
            }
        except Exception as e:
            logger.error(f"Nextcloud connection error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    async def get_storage_info() -> Dict[str, Any]:
        """Get storage directory information"""
        from app.config import settings

        try:
            storage_root = Path(settings.storage_root)
            storage_info = {
                "storage_root": str(storage_root),
                "exists": storage_root.exists(),
            }

            if storage_root.exists():
                # Count files in each directory
                for dir_name in ["originals", "working", "exports", "metadata"]:
                    dir_path = storage_root / dir_name
                    if dir_path.exists():
                        file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
                        storage_info[f"{dir_name}_count"] = file_count
                    else:
                        storage_info[f"{dir_name}_count"] = 0
                        storage_info[f"{dir_name}_exists"] = False

            return storage_info
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_database_stats(db) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            from sqlalchemy import func, select
            from app.models import Image, Project, ImageGroup

            # Count records
            image_count = await db.scalar(select(func.count(Image.id)))
            project_count = await db.scalar(select(func.count(Project.id)))
            group_count = await db.scalar(select(func.count(ImageGroup.id)))

            # Count analyzed images
            analyzed_count = await db.scalar(
                select(func.count(Image.id)).where(Image.analyzed_at.isnot(None))
            )

            # Count images by storage type
            from app.models import StorageType

            local_count = await db.scalar(
                select(func.count(Image.id)).where(Image.storage_type == StorageType.LOCAL)
            )
            nextcloud_count = await db.scalar(
                select(func.count(Image.id)).where(Image.storage_type == StorageType.NEXTCLOUD)
            )

            # Count assigned to projects
            assigned_count = await db.scalar(
                select(func.count(Image.id)).where(Image.project_id.isnot(None))
            )

            return {
                "total_images": image_count,
                "total_projects": project_count,
                "total_groups": group_count,
                "analyzed_images": analyzed_count,
                "unanalyzed_images": image_count - analyzed_count,
                "local_storage": local_count,
                "nextcloud_storage": nextcloud_count,
                "assigned_to_projects": assigned_count,
                "unassigned_images": image_count - assigned_count,
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}


class RequestLogger:
    """Request/response logging middleware"""

    @staticmethod
    def log_request(method: str, path: str, status_code: int, duration_ms: float):
        """Log HTTP request details"""
        logger.info(
            f"{method} {path} - {status_code} - {duration_ms:.2f}ms"
        )

    @staticmethod
    def log_error(method: str, path: str, error: Exception):
        """Log HTTP error details"""
        logger.error(
            f"{method} {path} - ERROR: {type(error).__name__}: {str(error)}",
            exc_info=True
        )


class DebugTimer:
    """Context manager for timing operations"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000
        if exc_type is None:
            logger.debug(f"Completed: {self.operation_name} in {duration:.2f}ms")
        else:
            logger.error(
                f"Failed: {self.operation_name} after {duration:.2f}ms - {exc_type.__name__}: {exc_val}"
            )

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0


def setup_enhanced_logging(log_level: str = "INFO"):
    """Setup enhanced logging configuration"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / "nodeo.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # Separate error log
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    root_logger.addHandler(error_handler)

    logger.info("Enhanced logging configured")
