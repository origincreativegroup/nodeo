"""Utilities for clustering and grouping images"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    GroupType,
    Image,
    ImageGroup,
    ImageGroupAssociation,
)


@dataclass
class GroupSummary:
    """Serializable representation of a group and its members."""

    id: int
    name: str
    group_type: str
    description: Optional[str]
    image_ids: List[int]
    metadata: Dict[str, Any]
    is_user_defined: bool
    created_by: Optional[str]
    created_at: Optional[str]


class GroupingService:
    """Service responsible for generating and managing image groupings."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def rebuild_ai_groups(self) -> None:
        """Rebuild AI-driven groupings (tags, scenes, embeddings)."""

        await self._build_tag_clusters()
        await self._build_scene_clusters()
        await self._build_embedding_clusters()
        await self.db.commit()

    async def list_groups(self, group_type: Optional[GroupType] = None) -> List[GroupSummary]:
        """Return a serialized list of groups."""

        query = (
            select(ImageGroup)
            .options(selectinload(ImageGroup.assignments))
            .order_by(ImageGroup.created_at.desc())
        )
        if group_type:
            query = query.where(ImageGroup.group_type == group_type)

        result = await self.db.execute(query)
        groups = result.scalars().unique().all()

        summaries: List[GroupSummary] = []
        for group in groups:
            summaries.append(
                GroupSummary(
                    id=group.id,
                    name=group.name,
                    group_type=group.group_type.value if group.group_type else None,
                    description=group.description,
                    image_ids=[assignment.image_id for assignment in group.assignments],
                    metadata=group.attributes or {},
                    is_user_defined=group.is_user_defined,
                    created_by=group.created_by,
                    created_at=group.created_at.isoformat() if group.created_at else None,
                )
            )
        return summaries

    async def create_manual_collection(
        self,
        name: str,
        description: Optional[str] = None,
        image_ids: Optional[Sequence[int]] = None,
        created_by: Optional[str] = None,
    ) -> ImageGroup:
        """Create a user-defined collection and assign images to it."""

        group = ImageGroup(
            name=name,
            description=description,
            group_type=GroupType.MANUAL_COLLECTION,
            is_user_defined=True,
            created_by=created_by,
            attributes={"cluster_key": f"manual:{name.lower()}"},
        )
        self.db.add(group)
        await self.db.flush()

        if image_ids:
            await self.assign_images_to_group(group.id, image_ids, replace=True)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def assign_images_to_group(
        self,
        group_id: int,
        image_ids: Sequence[int],
        *,
        replace: bool = False,
    ) -> ImageGroup:
        """Assign a set of images to an existing group."""

        result = await self.db.execute(
            select(ImageGroup).options(selectinload(ImageGroup.assignments)).where(ImageGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            raise ValueError("Group not found")

        new_ids = set(image_ids)
        if replace:
            for assignment in list(group.assignments):
                if assignment.image_id not in new_ids:
                    await self.db.delete(assignment)
        existing_ids = {assignment.image_id for assignment in group.assignments}
        for image_id in new_ids:
            if image_id not in existing_ids:
                self.db.add(ImageGroupAssociation(group_id=group.id, image_id=image_id))

        await self.db.flush()
        refreshed_ids = {assignment.image_id for assignment in group.assignments}
        metadata = {**(group.attributes or {}), "image_count": len(refreshed_ids)}
        group.attributes = metadata
        await self.db.refresh(group)
        return group

    async def _build_tag_clusters(self, min_shared_tags: int = 2, min_cluster_size: int = 2) -> None:
        result = await self.db.execute(select(Image).where(Image.ai_tags.isnot(None)))
        images = result.scalars().all()

        clusters: Dict[str, List[int]] = defaultdict(list)
        for image in images:
            tags = _normalize_tags(image.ai_tags or [])
            if len(tags) < min_shared_tags:
                continue
            key_tags = tuple(sorted(tags[:min_shared_tags]))
            if not key_tags:
                continue
            key = "|".join(key_tags)
            clusters[key].append(image.id)

        filtered = {key: ids for key, ids in clusters.items() if len(ids) >= min_cluster_size}
        await self._sync_clusters(
            GroupType.AI_TAG_CLUSTER,
            filtered,
            name_factory=lambda key, ids: f"Tags: {', '.join(key.split('|'))}",
            metadata_factory=lambda key, ids: {
                "cluster_key": key,
                "tags": key.split("|"),
                "image_count": len(ids),
            },
        )

    async def _build_scene_clusters(self, min_cluster_size: int = 2) -> None:
        result = await self.db.execute(select(Image).where(Image.ai_scene.isnot(None)))
        images = result.scalars().all()

        clusters: Dict[str, List[int]] = defaultdict(list)
        for image in images:
            scene = (image.ai_scene or "").strip().lower()
            if not scene:
                continue
            clusters[scene].append(image.id)

        filtered = {key: ids for key, ids in clusters.items() if len(ids) >= min_cluster_size}
        await self._sync_clusters(
            GroupType.AI_SCENE_CLUSTER,
            filtered,
            name_factory=lambda key, ids: f"Scene: {key.title()}",
            metadata_factory=lambda key, ids: {
                "cluster_key": key,
                "scene": key,
                "image_count": len(ids),
            },
        )

    async def _build_embedding_clusters(self, similarity_threshold: float = 0.85, min_cluster_size: int = 2) -> None:
        result = await self.db.execute(select(Image).where(Image.ai_embedding.isnot(None)))
        images = result.scalars().all()

        clusters: List[Dict[str, Any]] = []
        for image in images:
            vector = _ensure_vector(image.ai_embedding)
            if not vector:
                continue

            best_index: Optional[int] = None
            best_similarity = 0.0
            for index, cluster in enumerate(clusters):
                similarity = _cosine_similarity(vector, cluster["centroid"])
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_index = index

            if best_index is None:
                clusters.append({
                    "centroid": vector,
                    "vectors": [vector],
                    "image_ids": [image.id],
                })
            else:
                cluster = clusters[best_index]
                cluster["image_ids"].append(image.id)
                cluster["vectors"].append(vector)
                cluster["centroid"] = _mean_vector(cluster["vectors"])

        cluster_map: Dict[str, List[int]] = {}
        for index, cluster in enumerate(clusters):
            if len(cluster["image_ids"]) < min_cluster_size:
                continue
            key = f"embedding_{index}"
            cluster_map[key] = cluster["image_ids"]

        await self._sync_clusters(
            GroupType.AI_EMBEDDING_CLUSTER,
            cluster_map,
            name_factory=lambda key, ids: f"Embedding cluster {key.split('_')[-1]}",
            metadata_factory=lambda key, ids: {
                "cluster_key": key,
                "image_count": len(ids),
            },
        )

    async def _sync_clusters(
        self,
        group_type: GroupType,
        clusters: Dict[str, List[int]],
        *,
        name_factory,
        metadata_factory,
    ) -> None:
        result = await self.db.execute(
            select(ImageGroup)
            .options(selectinload(ImageGroup.assignments))
            .where(ImageGroup.group_type == group_type)
        )
        existing_groups = result.scalars().unique().all()
        existing_by_key = {
            (group.attributes or {}).get("cluster_key"): group for group in existing_groups
        }

        processed_keys = set()
        for key, image_ids in clusters.items():
            metadata = metadata_factory(key, image_ids) or {}
            metadata.setdefault("cluster_key", key)
            group = existing_by_key.get(key)
            if group is None:
                group = ImageGroup(
                    name=name_factory(key, image_ids),
                    group_type=group_type,
                    attributes=metadata,
                )
                self.db.add(group)
                await self.db.flush()
            else:
                group.name = name_factory(key, image_ids)
                group.attributes = {**(group.attributes or {}), **metadata}

            await self._sync_group_membership(group, image_ids)
            processed_keys.add(key)

        for key, group in existing_by_key.items():
            if key not in processed_keys and key is not None:
                await self.db.delete(group)
        await self.db.flush()

    async def _sync_group_membership(self, group: ImageGroup, image_ids: Iterable[int]) -> None:
        target_ids = set(image_ids)
        existing_assignments = {assignment.image_id: assignment for assignment in group.assignments}

        for image_id in target_ids:
            if image_id not in existing_assignments:
                self.db.add(ImageGroupAssociation(group_id=group.id, image_id=image_id))

        for image_id, assignment in list(existing_assignments.items()):
            if image_id not in target_ids:
                await self.db.delete(assignment)

        metadata = group.attributes or {}
        metadata["image_count"] = len(target_ids)
        group.attributes = metadata
        await self.db.flush()


def _normalize_tags(tags: Sequence[str]) -> List[str]:
    return [tag.strip().lower() for tag in tags if isinstance(tag, str) and tag.strip()]


def _ensure_vector(raw: Any) -> Optional[List[float]]:
    if isinstance(raw, list) and all(isinstance(value, (int, float)) for value in raw):
        return [float(value) for value in raw]
    if isinstance(raw, dict):
        # Allow {"values": [...]} style payloads
        values = raw.get("values")
        if isinstance(values, list) and all(isinstance(value, (int, float)) for value in values):
            return [float(value) for value in values]
    return None


def _mean_vector(vectors: Sequence[Sequence[float]]) -> List[float]:
    if not vectors:
        return []
    length = len(vectors[0])
    totals = [0.0] * length
    for vector in vectors:
        for index, value in enumerate(vector):
            totals[index] += float(value)
    return [value / len(vectors) for value in totals]


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = sqrt(sum(a * a for a in vec_a))
    magnitude_b = sqrt(sum(b * b for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot / (magnitude_a * magnitude_b)
