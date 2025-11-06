"""Service for generating AI-powered asset metadata."""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Dict, Optional

from app.ai import LLaVAClient, llava_client


logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """Supported asset types for metadata generation."""

    IMAGE = "image"
    VIDEO = "video"


class MetadataService:
    """High-level orchestrator for producing descriptive metadata."""

    def __init__(self, client: Optional[LLaVAClient] = None) -> None:
        self.client = client or llava_client

    async def generate_metadata(
        self,
        asset_path: str,
        *,
        asset_type: AssetType = AssetType.IMAGE,
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured metadata for an image or video."""

        prompt = self._build_prompt(asset_type)
        raw_response = await self.client.prompt_with_image(
            asset_path,
            prompt,
            temperature=0.2,
            num_predict=400,
        )

        metadata = self._parse_structured_response(raw_response)
        if metadata:
            metadata['source'] = 'llava'
        else:
            logger.warning(
                "Structured metadata response could not be parsed for %s; falling back",
                asset_path,
            )
            metadata = await self._fallback_metadata(asset_path, asset_type, existing)

        return self.ensure_metadata_shape(metadata, asset_type)

    def ensure_metadata_shape(
        self,
        metadata: Optional[Dict[str, Any]],
        asset_type: AssetType = AssetType.IMAGE,
        *,
        default_source: str = 'manual',
    ) -> Dict[str, Any]:
        """Ensure returned metadata contains all required fields."""

        metadata = metadata or {}
        tags = metadata.get('tags') or []
        if isinstance(tags, str):
            tags = [segment.strip() for segment in tags.split(',') if segment.strip()]
        else:
            tags = [str(tag).strip() for tag in tags if str(tag).strip()]

        description = metadata.get('description') or ''
        title = metadata.get('title') or self._title_from_description(description)
        alt_text = metadata.get('alt_text') or self._alt_text_from_description(
            description,
            asset_type,
        )

        ensured = {
            'title': title.strip(),
            'description': description.strip(),
            'alt_text': alt_text.strip(),
            'tags': tags,
            'asset_type': asset_type.value,
            'source': metadata.get('source', default_source),
        }

        return ensured

    async def _fallback_metadata(
        self,
        asset_path: str,
        asset_type: AssetType,
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fallback path that reuses previously stored metadata where possible."""

        existing = existing or {}
        description = existing.get('description') or ''
        tags = existing.get('tags') or []

        if not description or not tags:
            try:
                ai_metadata = await self.client.extract_metadata(asset_path)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to fallback to extract_metadata for %s: %s", asset_path, exc)
                ai_metadata = {}

            description = description or ai_metadata.get('description', '')
            tags = tags or ai_metadata.get('tags', [])

        return {
            'title': existing.get('title'),
            'description': description,
            'alt_text': existing.get('alt_text'),
            'tags': tags,
            'source': existing.get('source', 'fallback'),
        }

    def _build_prompt(self, asset_type: AssetType) -> str:
        context = 'image' if asset_type == AssetType.IMAGE else 'video'
        return (
            "You are an assistant that writes metadata for digital assets. "
            f"Analyze the provided {context} and respond with JSON using the keys "
            "title, description, alt_text, tags. The title should be concise (5-8 words). "
            "The description should be 1-2 sentences suitable for cataloging. Alt text should "
            "describe the asset for accessibility in a single sentence. Tags must be an array of "
            "5-8 short lowercase keywords without special characters. Respond with JSON only."
        )

    def _parse_structured_response(self, raw: str) -> Optional[Dict[str, Any]]:
        raw = raw.strip()
        if not raw:
            return None

        if raw.startswith('```'):
            raw = raw.strip('`')
            parts = raw.split('\n', 1)
            raw = parts[1] if len(parts) > 1 else ''

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("Metadata JSON parsing failed: %s", raw)
            return None

    def _title_from_description(self, description: str) -> str:
        words = [word.strip(',.!?') for word in description.split() if word]
        return ' '.join(words[:6]) or 'Untitled asset'

    def _alt_text_from_description(self, description: str, asset_type: AssetType) -> str:
        if description:
            return description
        label = 'image' if asset_type == AssetType.IMAGE else 'video'
        return f"AI generated {label} without additional description"


metadata_service = MetadataService()

