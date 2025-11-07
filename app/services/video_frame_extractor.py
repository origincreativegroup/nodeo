"""Video frame extraction utility for AI analysis."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """Extract representative frames from videos for AI analysis."""

    def __init__(self, num_frames: int = 3):
        """
        Initialize frame extractor.

        Args:
            num_frames: Number of frames to extract from video (default: 3)
                       - 1 frame: Middle of video
                       - 3 frames: Beginning, middle, end
                       - 5+ frames: Evenly distributed
        """
        self.num_frames = max(1, num_frames)

    async def extract_frames(
        self,
        video_path: str | Path,
        output_dir: Optional[str | Path] = None,
    ) -> List[Path]:
        """
        Extract representative frames from a video.

        Args:
            video_path: Path to the video file
            output_dir: Directory to save frames (uses temp dir if None)

        Returns:
            List of paths to extracted frame images

        Raises:
            FileNotFoundError: If video file doesn't exist or ffmpeg not found
            RuntimeError: If frame extraction fails
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Use temp directory if no output dir specified
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="jspow_frames_")
            output_dir = Path(temp_dir)
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Get video duration first
        duration = await self._get_video_duration(video_path)
        if duration is None or duration <= 0:
            logger.warning(f"Could not determine video duration for {video_path}, using default frame extraction")
            return await self._extract_frames_default(video_path, output_dir)

        # Calculate timestamps for frame extraction
        timestamps = self._calculate_timestamps(duration)

        # Extract frames at calculated timestamps
        frame_paths = []
        for i, timestamp in enumerate(timestamps):
            frame_path = output_dir / f"frame_{i:03d}.jpg"
            success = await self._extract_frame_at_timestamp(
                video_path, timestamp, frame_path
            )
            if success and frame_path.exists():
                frame_paths.append(frame_path)
            else:
                logger.warning(f"Failed to extract frame at {timestamp}s from {video_path}")

        if not frame_paths:
            logger.error(f"No frames extracted from {video_path}")
            raise RuntimeError(f"Failed to extract any frames from video: {video_path}")

        logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
        return frame_paths

    async def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"ffprobe failed: {stderr.decode().strip()}")
                return None

            duration_str = stdout.decode().strip()
            return float(duration_str)

        except FileNotFoundError:
            logger.error("ffprobe not found - ensure ffmpeg is installed")
            raise
        except (ValueError, asyncio.TimeoutError) as e:
            logger.error(f"Error getting video duration: {e}")
            return None

    def _calculate_timestamps(self, duration: float) -> List[float]:
        """Calculate timestamps for frame extraction."""
        if self.num_frames == 1:
            # Extract middle frame
            return [duration / 2]
        elif self.num_frames == 2:
            # Extract at 25% and 75%
            return [duration * 0.25, duration * 0.75]
        elif self.num_frames == 3:
            # Extract at beginning (10%), middle (50%), and end (90%)
            return [duration * 0.1, duration * 0.5, duration * 0.9]
        else:
            # Evenly distribute frames, avoiding very start and very end
            # Use range from 5% to 95% of video duration
            start_offset = duration * 0.05
            end_offset = duration * 0.95
            span = end_offset - start_offset
            step = span / (self.num_frames - 1) if self.num_frames > 1 else 0
            return [start_offset + (i * step) for i in range(self.num_frames)]

    async def _extract_frame_at_timestamp(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path,
    ) -> bool:
        """Extract a single frame at the specified timestamp."""
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-ss", str(timestamp),  # Seek to timestamp
            "-i", str(video_path),  # Input file
            "-vframes", "1",  # Extract 1 frame
            "-q:v", "2",  # High quality (scale 2-31, lower is better)
            str(output_path),  # Output file
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"ffmpeg frame extraction failed: {stderr.decode().strip()}")
                return False

            return True

        except FileNotFoundError:
            logger.error("ffmpeg not found - ensure ffmpeg is installed")
            raise
        except Exception as e:
            logger.error(f"Error extracting frame at {timestamp}s: {e}")
            return False

    async def _extract_frames_default(
        self,
        video_path: Path,
        output_dir: Path,
    ) -> List[Path]:
        """Fallback method: extract frames using default ffmpeg behavior."""
        # Extract frames at 1 frame per second for first few seconds
        frame_path_pattern = output_dir / "frame_%03d.jpg"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"fps=1/{max(1, self.num_frames)}",  # Extract N frames total
            "-vframes", str(self.num_frames),
            "-q:v", "2",
            str(frame_path_pattern),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            # Find all extracted frames
            frame_paths = sorted(output_dir.glob("frame_*.jpg"))
            return list(frame_paths[:self.num_frames])

        except Exception as e:
            logger.error(f"Default frame extraction failed: {e}")
            return []

    async def cleanup_frames(self, frame_paths: List[Path]) -> None:
        """Clean up extracted frame files."""
        for frame_path in frame_paths:
            try:
                if frame_path.exists():
                    frame_path.unlink()
                    logger.debug(f"Cleaned up frame: {frame_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup frame {frame_path}: {e}")

        # Try to remove parent directory if it's a temp directory
        if frame_paths:
            parent_dir = frame_paths[0].parent
            try:
                if parent_dir.name.startswith("jspow_frames_"):
                    parent_dir.rmdir()
                    logger.debug(f"Cleaned up temp directory: {parent_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {parent_dir}: {e}")


# Global instance
video_frame_extractor = VideoFrameExtractor(num_frames=3)


__all__ = ["VideoFrameExtractor", "video_frame_extractor"]
