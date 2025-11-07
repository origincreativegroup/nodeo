"""
LLaVA image analysis client using Ollama
"""
import base64
import json
import asyncio
from typing import Dict, List, Optional
import ollama
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}


class LLaVAClient:
    """Client for LLaVA vision model via Ollama"""

    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    def _is_video(self, file_path: str) -> bool:
        """Check if file is a video based on extension."""
        return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    async def prompt_with_image(
        self,
        image_path: str,
        prompt: str,
        *,
        temperature: float = 0.3,
        num_predict: int = 256,
    ) -> str:
        """Send a custom prompt alongside an image or video and return the raw response.

        For videos, extracts frames and analyzes the middle frame.
        """
        try:
            # Handle videos by extracting frames
            if self._is_video(image_path):
                from app.services.video_frame_extractor import video_frame_extractor

                frame_paths = []
                try:
                    logger.info(f"Extracting frames from video for prompt: {image_path}")
                    frame_paths = await video_frame_extractor.extract_frames(image_path)

                    if not frame_paths:
                        raise RuntimeError(f"Failed to extract frames from video: {image_path}")

                    # Use the middle frame for analysis
                    middle_frame = frame_paths[len(frame_paths) // 2]
                    logger.info(f"Using frame {middle_frame} for video analysis")

                    # Update prompt to indicate it's a video
                    video_prompt = f"{prompt}\n\nNote: This is a frame extracted from a video."

                    client = ollama.Client(host=self.host)
                    response = client.chat(
                        model=self.model,
                        messages=[
                            {
                                'role': 'user',
                                'content': video_prompt,
                                'images': [str(middle_frame)],
                            }
                        ],
                        options={
                            'temperature': temperature,
                            'num_predict': num_predict,
                        },
                    )
                    return response['message']['content'].strip()

                finally:
                    # Cleanup frames
                    if frame_paths:
                        try:
                            await video_frame_extractor.cleanup_frames(frame_paths)
                        except Exception as e:
                            logger.warning(f"Failed to cleanup frames: {e}")

            # Handle images normally
            client = ollama.Client(host=self.host)
            response = client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [image_path],
                    }
                ],
                options={
                    'temperature': temperature,
                    'num_predict': num_predict,
                },
            )
            return response['message']['content'].strip()
        except Exception as exc:
            logger.error(f"Error running custom prompt for {image_path}: {exc}")
            raise

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = None,
        detailed: bool = False
    ) -> str:
        """
        Analyze an image or video using LLaVA with improved prompts

        Args:
            image_path: Path to the image or video file
            prompt: Custom prompt for analysis (optional)
            detailed: If True, use a more detailed analysis prompt

        Returns:
            Analysis text from LLaVA
        """
        try:
            is_video = self._is_video(image_path)
            media_type = "video" if is_video else "image"
            logger.info(f"Analyzing {media_type}: {image_path}")

            # Use enhanced default prompt if none provided
            if prompt is None:
                if detailed:
                    if is_video:
                        prompt = f"""Provide a comprehensive analysis of this video:

1. Main Subject: What is the primary focus or subject?
2. Action/Content: What's happening in the video?
3. Visual Elements: Key objects, people, or elements visible
4. Setting/Scene: Where does this appear to be? What's the context?
5. Colors and Lighting: Dominant colors, lighting conditions, mood
6. Notable Details: Any interesting or distinctive features

Be specific and descriptive."""
                    else:
                        prompt = """Provide a comprehensive analysis of this image:

1. Main Subject: What is the primary focus or subject?
2. Composition: How is the image composed? (framing, perspective, layout)
3. Visual Elements: Key objects, people, or elements visible
4. Setting/Scene: Where does this appear to be? What's the context?
5. Colors and Lighting: Dominant colors, lighting conditions, mood
6. Notable Details: Any interesting or distinctive features

Be specific and descriptive."""
                else:
                    if is_video:
                        prompt = """Analyze this video and describe:
- What you see (main subjects and action)
- The scene type and setting
- Notable visual characteristics
- The overall composition and mood

Provide a clear, detailed description in 2-3 sentences."""
                    else:
                        prompt = """Analyze this image and describe:
- What you see (main subjects and objects)
- The scene type and setting
- Notable visual characteristics
- The overall composition and mood

Provide a clear, detailed description in 2-3 sentences."""

            # Use prompt_with_image which handles both images and videos
            num_predict = 300 if detailed else 200
            analysis = await self.prompt_with_image(
                image_path,
                prompt,
                temperature=0.5,
                num_predict=num_predict
            )

            logger.info(f"Analysis completed: {len(analysis)} chars")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing {media_type if 'media_type' in locals() else 'media'} {image_path}: {e}")
            raise

    async def extract_metadata(self, image_path: str, use_fast: bool = True) -> Dict:
        """
        Extract structured metadata from image or video

        Args:
            image_path: Path to the image or video file
            use_fast: If True, use optimized single-call method (default).
                     If False, use legacy 4-call method.

        Returns:
            {
                'description': str,
                'tags': List[str],
                'objects': List[str],
                'scene': str
            }
        """
        # Handle videos by extracting frames
        if self._is_video(image_path):
            return await self._extract_metadata_from_video(image_path, use_fast=use_fast)

        # Handle images
        if use_fast:
            return await self._extract_metadata_fast(image_path)
        else:
            return await self._extract_metadata_legacy(image_path)

    async def _extract_metadata_fast(self, image_path: str) -> Dict:
        """
        Optimized metadata extraction using a single API call with JSON response.
        This is 4x faster than the legacy method.
        """
        try:
            client = ollama.Client(host=self.host)

            # Enhanced prompt for better accuracy with structured JSON output
            prompt = """Analyze this image in detail and provide a comprehensive analysis in JSON format.

Your response must be valid JSON with these exact keys:
{
  "description": "A detailed 2-3 sentence description covering the main subject, composition, and notable elements",
  "tags": ["array", "of", "5-10", "relevant", "lowercase", "keywords"],
  "objects": ["list", "of", "main", "visible", "objects"],
  "scene": "scene type in 1-2 words",
  "mood": "optional mood/atmosphere descriptor",
  "colors": ["dominant", "color", "palette"]
}

Guidelines:
- Description: Be specific about what makes this image unique. Include composition, subjects, and context.
- Tags: Use semantically relevant, searchable keywords (e.g., "sunset", "architecture", "portrait")
- Objects: List concrete, visible items (e.g., "person", "building", "tree", "car")
- Scene: Choose from: indoor, outdoor, portrait, landscape, urban, nature, abstract, close-up, aerial, street, studio
- Mood: Describe the atmosphere (e.g., "peaceful", "energetic", "moody", "bright")
- Colors: List 2-4 dominant colors (e.g., "blue", "warm tones", "monochrome")

Respond with valid JSON only, no additional text."""

            response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }],
                options={
                    'temperature': 0.3,  # Lower for more consistent JSON output
                    'num_predict': 300,  # Reduced from 400, sufficient for structured output
                }
            )

            # Parse JSON response
            content = response['message']['content'].strip()

            # Handle markdown code blocks if present
            if content.startswith('```'):
                # Extract JSON from code block
                lines = content.split('\n')
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or (not line.strip().startswith('```')):
                        json_lines.append(line)
                content = '\n'.join(json_lines).strip()

            try:
                metadata = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response for {image_path}: {e}")
                logger.debug(f"Raw response: {content}")
                # Fallback to legacy method if JSON parsing fails
                return await self._extract_metadata_legacy(image_path)

            # Validate and clean the response
            description = metadata.get('description', '').strip()

            # Process tags - ensure they're lowercase and cleaned
            tags = metadata.get('tags', [])
            if isinstance(tags, str):
                tags = [t.strip().lower() for t in tags.split(',') if t.strip()]
            else:
                tags = [str(t).strip().lower() for t in tags if str(t).strip()]

            # Process objects
            objects = metadata.get('objects', [])
            if isinstance(objects, str):
                objects = [o.strip() for o in objects.split(',') if o.strip()]
            else:
                objects = [str(o).strip() for o in objects if str(o).strip()]

            # Process scene
            scene = metadata.get('scene', '').strip().lower()

            # Additional metadata (optional fields)
            mood = metadata.get('mood', '').strip()
            colors = metadata.get('colors', [])
            if isinstance(colors, str):
                colors = [c.strip() for c in colors.split(',') if c.strip()]

            result = {
                'description': description,
                'tags': tags[:10],  # Limit to 10 tags
                'objects': objects[:10],  # Limit to 10 objects
                'scene': scene
            }

            # Add optional fields if present
            if mood:
                result['mood'] = mood
            if colors:
                result['colors'] = colors[:5]

            return result

        except Exception as e:
            logger.error(f"Error in fast metadata extraction from {image_path}: {e}")
            # Fallback to legacy method
            logger.info(f"Falling back to legacy method for {image_path}")
            return await self._extract_metadata_legacy(image_path)

    async def _extract_metadata_legacy(self, image_path: str) -> Dict:
        """
        Legacy metadata extraction using 4 separate API calls.
        Kept for backward compatibility and as fallback.
        """
        try:
            # Multi-step analysis for structured data
            client = ollama.Client(host=self.host)

            # 1. Get general description
            desc_response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': 'Provide a concise 1-2 sentence description of this image.',
                    'images': [image_path]
                }]
            )
            description = desc_response['message']['content'].strip()

            # 2. Extract tags
            tags_response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': 'List 5-10 relevant tags for this image (comma-separated, lowercase).',
                    'images': [image_path]
                }]
            )
            tags_text = tags_response['message']['content'].strip()
            tags = [t.strip() for t in tags_text.split(',')]

            # 3. Identify main objects
            objects_response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': 'List the main objects visible in this image (comma-separated).',
                    'images': [image_path]
                }]
            )
            objects_text = objects_response['message']['content'].strip()
            objects = [o.strip() for o in objects_text.split(',')]

            # 4. Determine scene type
            scene_response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': 'What type of scene is this? (e.g., indoor, outdoor, portrait, landscape, urban, nature). Answer with 1-2 words only.',
                    'images': [image_path]
                }]
            )
            scene = scene_response['message']['content'].strip().lower()

            return {
                'description': description,
                'tags': tags[:10],  # Limit to 10 tags
                'objects': objects[:10],  # Limit to 10 objects
                'scene': scene
            }

        except Exception as e:
            logger.error(f"Error extracting metadata from {image_path}: {e}")
            raise

    async def _extract_metadata_from_video(self, video_path: str, use_fast: bool = True) -> Dict:
        """
        Extract metadata from video by analyzing extracted frames.

        Args:
            video_path: Path to the video file
            use_fast: Whether to use fast extraction method

        Returns:
            Aggregated metadata from video frames
        """
        from app.services.video_frame_extractor import video_frame_extractor

        frame_paths = []
        try:
            # Extract frames from video
            logger.info(f"Extracting frames from video: {video_path}")
            frame_paths = await video_frame_extractor.extract_frames(video_path)

            if not frame_paths:
                logger.error(f"No frames extracted from video: {video_path}")
                raise RuntimeError(f"Failed to extract frames from video: {video_path}")

            logger.info(f"Analyzing {len(frame_paths)} frames from video: {video_path}")

            # Analyze each frame
            frame_metadata_list = []
            for frame_path in frame_paths:
                try:
                    if use_fast:
                        metadata = await self._extract_metadata_fast(str(frame_path))
                    else:
                        metadata = await self._extract_metadata_legacy(str(frame_path))
                    frame_metadata_list.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to analyze frame {frame_path}: {e}")
                    continue

            if not frame_metadata_list:
                raise RuntimeError(f"Failed to analyze any frames from video: {video_path}")

            # Aggregate metadata from all frames
            aggregated = self._aggregate_video_metadata(frame_metadata_list)
            logger.info(f"Successfully analyzed video: {video_path}")
            return aggregated

        finally:
            # Cleanup extracted frames
            if frame_paths:
                try:
                    await video_frame_extractor.cleanup_frames(frame_paths)
                except Exception as e:
                    logger.warning(f"Failed to cleanup frames: {e}")

    def _aggregate_video_metadata(self, frame_metadata_list: List[Dict]) -> Dict:
        """
        Aggregate metadata from multiple video frames into a single result.

        Args:
            frame_metadata_list: List of metadata dicts from individual frames

        Returns:
            Aggregated metadata
        """
        if not frame_metadata_list:
            return {
                'description': '',
                'tags': [],
                'objects': [],
                'scene': ''
            }

        # Collect all descriptions and create a comprehensive one
        descriptions = [m.get('description', '') for m in frame_metadata_list if m.get('description')]

        # If we have multiple descriptions, combine them
        if len(descriptions) > 1:
            # Create a video-specific description mentioning it's from multiple scenes
            description = f"Video showing {descriptions[0]}"
            # Add variety if descriptions are different
            if len(set(descriptions)) > 1:
                description += f". The video transitions through scenes including {', '.join(descriptions[1:])}"
        elif descriptions:
            description = f"Video of {descriptions[0]}"
        else:
            description = "Video content"

        # Aggregate tags (merge and deduplicate)
        all_tags = []
        for metadata in frame_metadata_list:
            tags = metadata.get('tags', [])
            if isinstance(tags, list):
                all_tags.extend(tags)

        # Count tag occurrences and sort by frequency
        tag_counts = {}
        for tag in all_tags:
            tag_lower = str(tag).lower().strip()
            if tag_lower:
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        # Keep top tags that appear most frequently
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        aggregated_tags = [tag for tag, count in sorted_tags[:10]]

        # Add 'video' tag if not present
        if 'video' not in aggregated_tags:
            aggregated_tags.insert(0, 'video')

        # Aggregate objects (similar to tags)
        all_objects = []
        for metadata in frame_metadata_list:
            objects = metadata.get('objects', [])
            if isinstance(objects, list):
                all_objects.extend(objects)

        object_counts = {}
        for obj in all_objects:
            obj_lower = str(obj).lower().strip()
            if obj_lower:
                object_counts[obj_lower] = object_counts.get(obj_lower, 0) + 1

        sorted_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)
        aggregated_objects = [obj for obj, count in sorted_objects[:10]]

        # Determine scene - use most common scene or combine
        scenes = [m.get('scene', '').lower() for m in frame_metadata_list if m.get('scene')]
        if scenes:
            # Use most common scene
            scene_counts = {}
            for s in scenes:
                scene_counts[s] = scene_counts.get(s, 0) + 1
            scene = max(scene_counts.items(), key=lambda x: x[1])[0]
        else:
            scene = 'video'

        # Aggregate colors and mood if present
        result = {
            'description': description[:500],  # Limit description length
            'tags': aggregated_tags,
            'objects': aggregated_objects,
            'scene': scene
        }

        # Add optional fields if they exist
        all_moods = [m.get('mood', '') for m in frame_metadata_list if m.get('mood')]
        if all_moods:
            result['mood'] = all_moods[0]  # Use first mood

        all_colors = []
        for metadata in frame_metadata_list:
            colors = metadata.get('colors', [])
            if isinstance(colors, list):
                all_colors.extend(colors)
        if all_colors:
            # Deduplicate colors while preserving order
            seen = set()
            unique_colors = []
            for color in all_colors:
                color_lower = str(color).lower()
                if color_lower not in seen:
                    seen.add(color_lower)
                    unique_colors.append(color)
            result['colors'] = unique_colors[:5]

        return result

    async def generate_filename(
        self,
        image_path: str,
        metadata: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate a descriptive filename based on image content with context awareness

        Args:
            image_path: Path to image
            metadata: Pre-analyzed metadata (optional)
            context: Additional context (project, folder, scene cluster, etc.)

        Returns:
            Suggested filename (without extension)

        Context structure:
            {
                'project_name': str,        # Portfolio project name
                'folder_type': str,         # 'project', 'scene', 'tag', 'manual'
                'folder_name': str,         # Current folder context
                'scene_type': str,          # Scene cluster type
                'date': str,                # Date for temporal naming (YYYYMMDD)
                'index': int,               # Sequential index in batch
            }
        """
        try:
            if not metadata:
                metadata = await self.extract_metadata(image_path)

            context = context or {}

            # Build context-aware filename strategy
            description = metadata.get('description', '')
            tags = metadata.get('tags', [])[:5]
            scene = metadata.get('scene', '')

            # Extract key terms from description (remove stop words)
            stop_words = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'this', 'that', 'is', 'are'}
            description_words = [w.lower() for w in description.split() if w.lower() not in stop_words and len(w) > 2]
            key_terms = description_words[:4]  # First 4 meaningful words

            # Determine naming strategy based on context
            if context.get('folder_type') == 'project' and context.get('project_name'):
                # Project-based naming: {project}_{description}_{index}
                project_slug = context['project_name'].lower().replace(' ', '_')
                desc_part = '_'.join(key_terms[:2]) if key_terms else '_'.join(tags[:2])
                index = context.get('index', 1)
                filename = f"{project_slug}_{desc_part}_{index:03d}"

            elif context.get('folder_type') == 'scene' and scene:
                # Scene-based naming: {scene}_{description}_{date}
                scene_slug = scene.lower().replace(' ', '_')
                desc_part = '_'.join(key_terms[:3]) if key_terms else '_'.join(tags[:2])
                date_part = context.get('date', '')
                if date_part:
                    filename = f"{scene_slug}_{desc_part}_{date_part}"
                else:
                    filename = f"{scene_slug}_{desc_part}"

            elif context.get('folder_type') == 'tag' and tags:
                # Tag-based naming: {primary_tag}_{description}
                primary_tag = tags[0].lower().replace(' ', '_')
                desc_part = '_'.join(key_terms[:3]) if key_terms else '_'.join(tags[1:3])
                filename = f"{primary_tag}_{desc_part}"

            else:
                # Default: {description}_{date}_{hash_short}
                desc_part = '_'.join(key_terms[:4]) if key_terms else '_'.join(tags[:3])
                date_part = context.get('date', '')

                if date_part:
                    # Add short hash for uniqueness
                    import hashlib
                    hash_short = hashlib.md5(description.encode()).hexdigest()[:6]
                    filename = f"{desc_part}_{date_part}_{hash_short}"
                else:
                    filename = desc_part

            # Clean and validate filename
            filename = filename.lower().replace(' ', '_').replace('-', '_')
            # Remove any non-alphanumeric except underscores
            filename = ''.join(c for c in filename if c.isalnum() or c == '_')

            # Ensure not too long (max 50 chars before extension)
            if len(filename) > 50:
                filename = filename[:50]

            # Ensure not empty
            if not filename:
                filename = 'unnamed_image'

            return filename

        except Exception as e:
            logger.error(f"Error generating filename for {image_path}: {e}")
            # Fallback to simple description-based name
            if metadata and metadata.get('tags'):
                return '_'.join(metadata['tags'][:3]).lower()
            return "unnamed_image"

    async def batch_analyze(
        self,
        image_paths: List[str],
        extract_full_metadata: bool = True,
        concurrent: bool = True,
        max_concurrent: int = 5
    ) -> List[Dict]:
        """
        Analyze multiple images in batch with optional concurrent processing

        Args:
            image_paths: List of image paths
            extract_full_metadata: If True, extract full metadata; else just description
            concurrent: If True, process images concurrently (default: True)
            max_concurrent: Maximum number of concurrent requests (default: 5)

        Returns:
            List of metadata dicts
        """
        if not concurrent:
            # Sequential processing (legacy behavior)
            return await self._batch_analyze_sequential(image_paths, extract_full_metadata)

        # Concurrent processing with semaphore to limit simultaneous requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_single(image_path: str) -> Dict:
            async with semaphore:
                try:
                    if extract_full_metadata:
                        metadata = await self.extract_metadata(image_path)
                    else:
                        description = await self.analyze_image(image_path)
                        metadata = {'description': description}

                    metadata['image_path'] = image_path
                    return metadata

                except Exception as e:
                    logger.error(f"Failed to analyze {image_path}: {e}")
                    return {
                        'image_path': image_path,
                        'error': str(e)
                    }

        # Process all images concurrently
        results = await asyncio.gather(
            *[analyze_single(path) for path in image_paths],
            return_exceptions=False
        )

        return results

    async def _batch_analyze_sequential(
        self,
        image_paths: List[str],
        extract_full_metadata: bool = True
    ) -> List[Dict]:
        """
        Sequential batch analysis (legacy method)
        """
        results = []
        for image_path in image_paths:
            try:
                if extract_full_metadata:
                    metadata = await self.extract_metadata(image_path)
                else:
                    description = await self.analyze_image(image_path)
                    metadata = {'description': description}

                metadata['image_path'] = image_path
                results.append(metadata)

            except Exception as e:
                logger.error(f"Failed to analyze {image_path}: {e}")
                results.append({
                    'image_path': image_path,
                    'error': str(e)
                })

        return results


# Global instance
llava_client = LLaVAClient()
