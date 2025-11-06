"""Utility for extracting and caching media metadata using external tools."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MediaMetadata, MediaType

logger = logging.getLogger(__name__)


@dataclass
class MediaMetadataResult:
    """Normalized metadata payload returned by the service."""

    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_s: Optional[float] = None
    frame_rate: Optional[float] = None
    codec: Optional[str] = None
    format: Optional[str] = None
    file_path: Optional[str] = None
    file_mtime: Optional[float] = None
    metadata_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return metadata as a plain dictionary with JSON-safe values."""
        payload: Dict[str, Any] = asdict(self)
        return payload


class MediaMetadataService:
    """Fetch and cache technical metadata for media assets."""

    IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}
    VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metadata(
        self, file_path: Path | str, mime_type: Optional[str] = None
    ) -> MediaMetadataResult:
        """Return normalized metadata for the provided file.

        The method will attempt to read cached metadata from the database before
        shelling out to ``ffprobe`` (videos) or ``magick identify`` (images).
        Results are persisted for subsequent requests.
        """

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file does not exist: {file_path}")

        file_mtime = path.stat().st_mtime

        cached = await self._get_cached(path, file_mtime)
        if cached:
            return cached

        media_type = self._guess_media_type(path, mime_type)

        if media_type == MediaType.VIDEO.value:
            raw_metadata = await self._probe_video(path)
        else:
            raw_metadata = await self._probe_image(path)

        normalized = self._normalize_metadata(raw_metadata, media_type, path, file_mtime)
        record = await self._store_metadata(normalized, raw_metadata)
        normalized.metadata_id = record.id if record else None
        return normalized

    async def _get_cached(
        self, path: Path, file_mtime: float
    ) -> Optional[MediaMetadataResult]:
        stmt = select(MediaMetadata).where(MediaMetadata.file_path == str(path))
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record and record.file_mtime == file_mtime:
            return MediaMetadataResult(
                media_type=record.media_type.value
                if isinstance(record.media_type, MediaType)
                else str(record.media_type),
                width=record.width,
                height=record.height,
                duration_s=record.duration_s,
                frame_rate=record.frame_rate,
                codec=record.codec,
                format=record.media_format,
                file_path=record.file_path,
                file_mtime=record.file_mtime,
                metadata_id=record.id,
            )
        return None

    async def _store_metadata(
        self, normalized: MediaMetadataResult, raw_metadata: Dict[str, Any]
    ) -> Optional[MediaMetadata]:
        stmt = select(MediaMetadata).where(MediaMetadata.file_path == normalized.file_path)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        now = datetime.utcnow()

        if record:
            record.file_mtime = normalized.file_mtime or record.file_mtime
            record.media_type = MediaType(normalized.media_type)
            record.width = normalized.width
            record.height = normalized.height
            record.duration_s = normalized.duration_s
            record.frame_rate = normalized.frame_rate
            record.codec = normalized.codec
            record.media_format = normalized.format
            record.raw_metadata = raw_metadata
            record.updated_at = now
        else:
            record = MediaMetadata(
                file_path=normalized.file_path,
                file_mtime=normalized.file_mtime or 0.0,
                media_type=MediaType(normalized.media_type),
                width=normalized.width,
                height=normalized.height,
                duration_s=normalized.duration_s,
                frame_rate=normalized.frame_rate,
                codec=normalized.codec,
                media_format=normalized.format,
                raw_metadata=raw_metadata,
                created_at=now,
                updated_at=now,
            )
            self.db.add(record)

        await self.db.flush()
        return record

    def _guess_media_type(self, path: Path, mime_type: Optional[str]) -> str:
        if mime_type:
            if mime_type.startswith("video"):
                return MediaType.VIDEO.value
            if mime_type.startswith("image"):
                return MediaType.IMAGE.value

        ext = path.suffix.lower().lstrip(".")
        if ext in self.VIDEO_EXTENSIONS:
            return MediaType.VIDEO.value
        if ext in self.IMAGE_EXTENSIONS:
            return MediaType.IMAGE.value
        # Default to image so we can still fall back to Pillow
        return MediaType.IMAGE.value

    async def _probe_image(self, path: Path) -> Dict[str, Any]:
        cmd = [
            "magick",
            "identify",
            "-format",
            "%w %h %m",
            str(path),
        ]
        try:
            output = await self._run_command(cmd)
            parts = output.strip().split()
            width = int(parts[0]) if len(parts) >= 1 else None
            height = int(parts[1]) if len(parts) >= 2 else None
            fmt = parts[2] if len(parts) >= 3 else path.suffix.lstrip(".").upper()
            return {
                "width": width,
                "height": height,
                "format": fmt,
            }
        except FileNotFoundError:
            logger.warning("magick identify not found; falling back to Pillow for image metadata")
        except (ValueError, IndexError, asyncio.TimeoutError, RuntimeError) as exc:
            logger.warning("magick identify failed for %s: %s", path, exc)

        # Fallback to Pillow
        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as img:
                width, height = img.size
                fmt = img.format or path.suffix.lstrip(".").upper()
            return {
                "width": width,
                "height": height,
                "format": fmt,
            }
        except Exception as exc:  # pragma: no cover - unlikely failure
            logger.error("Failed to read image metadata for %s: %s", path, exc)
            return {}

    async def _probe_video(self, path: Path) -> Dict[str, Any]:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name",
            "-show_entries",
            "format=duration,format_name",
            "-of",
            "json",
            str(path),
        ]
        try:
            output = await self._run_command(cmd)
            data = json.loads(output or "{}")
        except FileNotFoundError as exc:
            logger.error("ffprobe is required for video metadata but was not found: %s", exc)
            return {}
        except RuntimeError as exc:
            logger.error("ffprobe failed for %s: %s", path, exc)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("ffprobe returned invalid JSON for %s: %s", path, exc)
            return {}

        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        width = self._safe_int(stream.get("width"))
        height = self._safe_int(stream.get("height"))
        codec = stream.get("codec_name")
        duration_s = self._safe_float(fmt.get("duration"))
        frame_rate = self._parse_frame_rate(stream.get("r_frame_rate"))
        format_name = fmt.get("format_name")
        return {
            "width": width,
            "height": height,
            "codec": codec,
            "duration_s": duration_s,
            "frame_rate": frame_rate,
            "format": format_name,
        }

    async def _run_command(self, cmd: list[str]) -> str:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            stderr_text = stderr.decode().strip()
            raise RuntimeError(f"Command {' '.join(cmd)} failed: {stderr_text}")
        return stdout.decode()

    def _normalize_metadata(
        self,
        raw: Dict[str, Any],
        media_type: str,
        path: Path,
        file_mtime: float,
    ) -> MediaMetadataResult:
        return MediaMetadataResult(
            media_type=media_type,
            width=self._safe_int(raw.get("width")),
            height=self._safe_int(raw.get("height")),
            duration_s=self._safe_float(raw.get("duration_s")),
            frame_rate=self._safe_float(raw.get("frame_rate")),
            codec=(raw.get("codec") or raw.get("codec_name")),
            format=raw.get("format"),
            file_path=str(path),
            file_mtime=file_mtime,
        )

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_frame_rate(value: Any) -> Optional[float]:
        if not value:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and "/" in value:
            try:
                numerator, denominator = value.split("/", 1)
                denominator_value = float(denominator)
                if denominator_value == 0:
                    return None
                return float(numerator) / denominator_value
            except (ValueError, ZeroDivisionError):
                return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["MediaMetadataService", "MediaMetadataResult"]
