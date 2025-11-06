"""AI-powered project classification and identification"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llava_client import LLaVaClient
from app.models import Image, Project, ProjectType

logger = logging.getLogger(__name__)


@dataclass
class ProjectMatch:
    """Represents a potential project match for an image"""

    project_id: int
    project_name: str
    project_slug: str
    confidence: float
    reasons: List[str]
    keyword_matches: List[str]
    theme_matches: List[str]


@dataclass
class ClassificationResult:
    """Result of project classification"""

    image_id: int
    assigned_project_id: Optional[int]
    assigned_project_name: Optional[str]
    confidence: float
    all_matches: List[ProjectMatch]
    requires_review: bool
    reasons: List[str]


class ProjectClassifier:
    """AI-powered project identification and classification"""

    def __init__(
        self,
        db: AsyncSession,
        llava_client: Optional[LLaVaClient] = None,
        confidence_threshold: float = 0.70,
        review_threshold: float = 0.50,
    ):
        """
        Initialize project classifier

        Args:
            db: Database session
            llava_client: LLaVA client for AI analysis
            confidence_threshold: Minimum confidence for auto-assignment (default 0.70)
            review_threshold: Minimum confidence for manual review (default 0.50)
        """
        self.db = db
        self.llava_client = llava_client or LLaVaClient()
        self.confidence_threshold = confidence_threshold
        self.review_threshold = review_threshold

    async def classify_image(
        self,
        image: Image,
        projects: Optional[List[Project]] = None,
        auto_assign: bool = True,
    ) -> ClassificationResult:
        """
        Classify an image and identify which project it belongs to

        Args:
            image: Image to classify
            projects: List of projects to consider (if None, loads all active projects)
            auto_assign: If True, automatically assign to best matching project

        Returns:
            Classification result with matches and confidence scores
        """
        # Load active projects if not provided
        if projects is None:
            result = await self.db.execute(
                select(Project).where(Project.is_active == True)
            )
            projects = list(result.scalars().all())

        if not projects:
            return ClassificationResult(
                image_id=image.id,
                assigned_project_id=None,
                assigned_project_name=None,
                confidence=0.0,
                all_matches=[],
                requires_review=False,
                reasons=["No active projects available"],
            )

        # Ensure image has been analyzed
        if not image.ai_tags and not image.ai_description:
            logger.warning(f"Image {image.id} has not been analyzed yet")

        # Get image metadata
        image_tags = set((image.ai_tags or []))
        image_description = (image.ai_description or "").lower()
        image_scene = (image.ai_scene or "").lower()

        # Score each project
        matches: List[ProjectMatch] = []
        for project in projects:
            score, reasons, keyword_matches, theme_matches = self._score_project_match(
                project=project,
                image_tags=image_tags,
                image_description=image_description,
                image_scene=image_scene,
                image_created_at=image.created_at,
            )

            if score > 0:
                matches.append(
                    ProjectMatch(
                        project_id=project.id,
                        project_name=project.name,
                        project_slug=project.slug,
                        confidence=score,
                        reasons=reasons,
                        keyword_matches=keyword_matches,
                        theme_matches=theme_matches,
                    )
                )

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # Determine best match
        best_match = matches[0] if matches else None
        assigned_project_id = None
        assigned_project_name = None
        requires_review = False
        classification_reasons = []

        if not best_match:
            requires_review = True
            classification_reasons.append("No matching projects found")
        elif best_match.confidence >= self.confidence_threshold:
            # High confidence - auto-assign
            if auto_assign:
                assigned_project_id = best_match.project_id
                assigned_project_name = best_match.project_name
                image.project_id = assigned_project_id
                await self.db.flush()
                classification_reasons.append(
                    f"Auto-assigned with {best_match.confidence:.0%} confidence"
                )
        elif best_match.confidence >= self.review_threshold:
            # Medium confidence - flag for review
            requires_review = True
            classification_reasons.append(
                f"Requires review (confidence: {best_match.confidence:.0%})"
            )
        else:
            # Low confidence - no assignment
            requires_review = True
            classification_reasons.append(
                f"Confidence too low ({best_match.confidence:.0%})"
            )

        return ClassificationResult(
            image_id=image.id,
            assigned_project_id=assigned_project_id,
            assigned_project_name=assigned_project_name,
            confidence=best_match.confidence if best_match else 0.0,
            all_matches=matches,
            requires_review=requires_review,
            reasons=classification_reasons,
        )

    def _score_project_match(
        self,
        project: Project,
        image_tags: set,
        image_description: str,
        image_scene: str,
        image_created_at: Optional[datetime],
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """
        Calculate match score between image and project

        Returns:
            Tuple of (score, reasons, keyword_matches, theme_matches)
        """
        score = 0.0
        reasons = []
        keyword_matches = []
        theme_matches = []

        # Keyword matching (40% weight)
        project_keywords = set(
            kw.lower() for kw in (project.ai_keywords or []) if kw
        )
        if project_keywords:
            # Check tags
            tag_matches = image_tags.intersection(project_keywords)
            if tag_matches:
                keyword_score = min(len(tag_matches) / len(project_keywords), 1.0)
                score += keyword_score * 0.4
                keyword_matches.extend(tag_matches)
                reasons.append(
                    f"{len(tag_matches)} keyword match(es) in tags: {', '.join(list(tag_matches)[:3])}"
                )

            # Check description
            description_matches = [
                kw for kw in project_keywords if kw in image_description
            ]
            if description_matches:
                desc_score = min(
                    len(description_matches) / len(project_keywords), 1.0
                )
                score += desc_score * 0.2
                keyword_matches.extend(description_matches)
                reasons.append(
                    f"{len(description_matches)} keyword(s) in description"
                )

        # Visual theme matching (30% weight)
        visual_themes = project.visual_themes or {}
        if visual_themes:
            # Style matching
            if "styles" in visual_themes:
                project_styles = set(
                    s.lower() for s in visual_themes["styles"] if s
                )
                # Check if scene type matches any style keywords
                if image_scene:
                    style_matches = [s for s in project_styles if s in image_scene]
                    if style_matches:
                        score += 0.15
                        theme_matches.extend(style_matches)
                        reasons.append(f"Style match: {', '.join(style_matches)}")

            # Color matching (simplified - would need actual color extraction)
            if "colors" in visual_themes and image_description:
                project_colors = set(
                    c.lower() for c in visual_themes["colors"] if c
                )
                color_matches = [c for c in project_colors if c in image_description]
                if color_matches:
                    score += 0.15
                    theme_matches.extend(color_matches)
                    reasons.append(f"Color match: {', '.join(color_matches)}")

        # Temporal matching (15% weight)
        if project.start_date and project.end_date and image_created_at:
            if project.start_date <= image_created_at <= project.end_date:
                score += 0.15
                reasons.append(
                    f"Created within project timeframe ({project.start_date.date()} - {project.end_date.date()})"
                )
        elif project.start_date and image_created_at:
            # If no end date, check if after start
            if image_created_at >= project.start_date:
                score += 0.10
                reasons.append(f"Created after project start date")

        # Context boost (15% weight)
        # Boost score for client projects with specific indicators
        if project.project_type == ProjectType.CLIENT:
            client_indicators = ["client", "commercial", "brand", "corporate", "logo"]
            if any(indicator in image_description for indicator in client_indicators):
                score += 0.10
                reasons.append("Client project indicators detected")

        # Portfolio boost
        if project.featured_on_portfolio:
            # Slight boost for featured projects
            score = min(score * 1.05, 1.0)
            reasons.append("Featured portfolio project")

        return score, reasons, keyword_matches, theme_matches

    async def classify_batch(
        self,
        image_ids: List[int],
        auto_assign: bool = True,
    ) -> List[ClassificationResult]:
        """
        Classify multiple images in batch

        Args:
            image_ids: List of image IDs to classify
            auto_assign: Whether to automatically assign to projects

        Returns:
            List of classification results
        """
        # Load images
        result = await self.db.execute(
            select(Image).where(Image.id.in_(image_ids))
        )
        images = list(result.scalars().all())

        # Load all active projects once
        projects_result = await self.db.execute(
            select(Project).where(Project.is_active == True)
        )
        projects = list(projects_result.scalars().all())

        # Classify each image
        results = []
        for image in images:
            try:
                classification = await self.classify_image(
                    image=image,
                    projects=projects,
                    auto_assign=auto_assign,
                )
                results.append(classification)
            except Exception as e:
                logger.error(f"Error classifying image {image.id}: {e}")
                results.append(
                    ClassificationResult(
                        image_id=image.id,
                        assigned_project_id=None,
                        assigned_project_name=None,
                        confidence=0.0,
                        all_matches=[],
                        requires_review=True,
                        reasons=[f"Classification error: {str(e)}"],
                    )
                )

        if auto_assign:
            await self.db.commit()

        return results

    async def suggest_project(self, image_id: int) -> List[ProjectMatch]:
        """
        Get project suggestions for an image without assigning

        Args:
            image_id: Image ID

        Returns:
            List of project matches sorted by confidence
        """
        result = await self.db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            return []

        classification = await self.classify_image(
            image=image,
            auto_assign=False,
        )

        return classification.all_matches

    async def learn_from_assignment(
        self,
        image_id: int,
        project_id: int,
        is_correct: bool = True,
    ) -> None:
        """
        Learn from manual project assignments to improve keywords

        Args:
            image_id: Image that was assigned
            project_id: Project it was assigned to
            is_correct: Whether this was a correct assignment
        """
        if not is_correct:
            # For now, we don't do negative learning
            return

        # Get image and project
        image_result = await self.db.execute(
            select(Image).where(Image.id == image_id)
        )
        image = image_result.scalar_one_or_none()

        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()

        if not image or not project:
            return

        # Extract new keywords from image tags
        image_tags = set(tag.lower() for tag in (image.ai_tags or []))
        current_keywords = set(kw.lower() for kw in (project.ai_keywords or []))

        # Find new tags that should be added as keywords
        new_keywords = image_tags - current_keywords

        # Only add highly relevant tags (those that appear frequently)
        # For now, add all unique tags
        if new_keywords:
            updated_keywords = list(project.ai_keywords or [])
            updated_keywords.extend(new_keywords)

            # Limit to 50 keywords max
            project.ai_keywords = updated_keywords[:50]
            await self.db.commit()

            logger.info(
                f"Learned {len(new_keywords)} new keywords for project {project.name}: {new_keywords}"
            )

    async def get_review_queue(self) -> List[Image]:
        """
        Get images that need manual project assignment review

        Returns:
            List of images without project assignment
        """
        result = await self.db.execute(
            select(Image)
            .where(Image.project_id.is_(None))
            .where(Image.analyzed_at.isnot(None))
            .order_by(Image.created_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())
