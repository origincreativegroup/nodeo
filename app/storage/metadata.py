"""Utilities for persisting metadata sidecar files."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class MetadataSidecarWriter:
    """Persist metadata alongside assets in JSON sidecar files."""

    def __init__(self, *, suffix: str = ".metadata.json") -> None:
        self.suffix = suffix

    def write(self, asset_path: str, metadata: Dict[str, Any]) -> Path:
        asset = Path(asset_path)
        if not asset.exists():
            raise FileNotFoundError(f"Asset not found: {asset_path}")

        sidecar_path = asset.with_name(asset.stem + self.suffix)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        with sidecar_path.open('w', encoding='utf-8') as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)

        logger.info("Metadata sidecar written to %s", sidecar_path)
        return sidecar_path

    def load(self, asset_path: str) -> Optional[Dict[str, Any]]:
        sidecar = self._sidecar_path(asset_path)
        if not sidecar.exists():
            return None

        try:
            with sidecar.open('r', encoding='utf-8') as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            logger.error("Failed to decode metadata sidecar %s: %s", sidecar, exc)
            return None

    def exists(self, asset_path: str) -> bool:
        return self._sidecar_path(asset_path).exists()

    def path(self, asset_path: str) -> Path:
        return self._sidecar_path(asset_path)

    def _sidecar_path(self, asset_path: str) -> Path:
        asset = Path(asset_path)
        return asset.with_name(asset.stem + self.suffix)


metadata_sidecar_writer = MetadataSidecarWriter()

