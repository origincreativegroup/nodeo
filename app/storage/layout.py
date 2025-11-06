"""Local storage layout helpers and manifest generation"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings


def _slugify_segment(value: str) -> str:
    """Create a filesystem safe slug for folders."""

    sanitized = "-".join(part for part in value.replace("\\", "/").split("/") if part)
    if not sanitized:
        sanitized = "default"
    return "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in sanitized.lower())


def _hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the sha256 hash of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ManifestAsset:
    """Represents a single asset entry inside a manifest."""

    asset_id: str
    files: Dict[str, str]
    metadata: Dict[str, object] = field(default_factory=dict)
    published: bool = False


@dataclass
class Manifest:
    """Manifest information for a folder."""

    asset_type: str
    year: int
    project: str
    project_slug: str
    generated_at: str
    assets: List[ManifestAsset]

    def to_dict(self) -> Dict[str, object]:
        """Convert manifest to a JSON serialisable dictionary."""

        return {
            "asset_type": self.asset_type,
            "year": self.year,
            "project": self.project,
            "generated_at": self.generated_at,
            "project_slug": self.project_slug,
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "files": asset.files,
                    "metadata": asset.metadata,
                    "published": asset.published,
                }
                for asset in self.assets
            ],
        }


class StorageManager:
    """Manage the on-disk storage layout for jspow assets."""

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or settings.storage_root)
        self.type_dirs = {
            "originals": self.root / settings.storage_originals_dirname,
            "working": self.root / settings.storage_working_dirname,
            "exports": self.root / settings.storage_exports_dirname,
            "metadata": self.root / settings.storage_metadata_dirname,
        }

    def ensure_layout(self) -> None:
        """Create the base folder layout if required."""

        for path in self.type_dirs.values():
            path.mkdir(parents=True, exist_ok=True)

    def _normalize_project(self, project: Optional[str]) -> str:
        return _slugify_segment(project or settings.default_project_code)

    def project_slug(self, project: Optional[str] = None) -> str:
        """Public helper to normalise project strings for folder usage."""

        return self._normalize_project(project)

    def _resolve_asset_dir(
        self,
        asset_type: str,
        asset_id: str,
        created_at: Optional[datetime] = None,
        project: Optional[str] = None,
    ) -> Path:
        if asset_type not in self.type_dirs:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        created_at = created_at or datetime.utcnow()
        year = str(created_at.year)
        project_segment = self._normalize_project(project)

        return self.type_dirs[asset_type] / year / project_segment / asset_id

    def asset_file_path(
        self,
        asset_type: str,
        asset_id: str,
        filename: str,
        created_at: Optional[datetime] = None,
        project: Optional[str] = None,
    ) -> Path:
        """Return the destination path for an asset file without creating it."""

        return self._resolve_asset_dir(asset_type, asset_id, created_at, project) / filename

    def write_file(
        self,
        asset_type: str,
        asset_id: str,
        filename: str,
        data: bytes,
        created_at: Optional[datetime] = None,
        project: Optional[str] = None,
    ) -> Path:
        """Write a binary file inside the layout and return the path."""

        destination = self.asset_file_path(
            asset_type,
            asset_id,
            filename,
            created_at=created_at,
            project=project,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            handle.write(data)
        return destination

    def write_metadata(
        self,
        asset_id: str,
        metadata: Dict[str, object],
        created_at: Optional[datetime] = None,
        project: Optional[str] = None,
    ) -> Path:
        """Persist metadata alongside an asset."""

        payload = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
        return self.write_file(
            "metadata",
            asset_id,
            "metadata.json",
            payload,
            created_at=created_at,
            project=project,
        )

    def read_metadata(
        self,
        asset_id: str,
        year: int,
        project: str,
    ) -> Dict[str, object]:
        """Read stored metadata for an asset if available."""

        project_segment = self._normalize_project(project)
        metadata_path = (
            self.type_dirs["metadata"]
            / str(year)
            / project_segment
            / asset_id
            / "metadata.json"
        )

        if not metadata_path.exists():
            return {}

        try:
            return json.loads(metadata_path.read_text())
        except json.JSONDecodeError:
            return {}

    def generate_manifest(
        self,
        asset_type: str,
        year: int,
        project: str,
        *,
        include_metadata: bool = True,
    ) -> Path:
        """Generate a manifest.json for the requested folder."""

        if asset_type not in self.type_dirs:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        project_segment = self._normalize_project(project)
        folder = self.type_dirs[asset_type] / str(year) / project_segment
        folder.mkdir(parents=True, exist_ok=True)

        assets: List[ManifestAsset] = []

        for asset_dir in sorted(folder.iterdir() if folder.exists() else []):
            if not asset_dir.is_dir():
                continue

            files: Dict[str, str] = {}
            for file_path in sorted(asset_dir.iterdir()):
                if file_path.is_file():
                    files[file_path.name] = _hash_file(file_path)

            metadata: Dict[str, object] = {}
            published = False
            if include_metadata:
                metadata = self.read_metadata(asset_dir.name, year, project)
                published = bool(metadata.get("published", False))

            assets.append(
                ManifestAsset(
                    asset_id=asset_dir.name,
                    files=files,
                    metadata=metadata,
                    published=published,
                )
            )

        manifest = Manifest(
            asset_type=asset_type,
            year=year,
            project=project,
            project_slug=project_segment,
            generated_at=datetime.utcnow().isoformat(),
            assets=assets,
        )

        manifest_path = folder / "manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
        return manifest_path


# Shared instance for convenience when importing from app.storage
storage_manager = StorageManager()
