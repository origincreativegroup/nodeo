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
        """Send a custom prompt alongside an image and return the raw response."""
        try:
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
        Analyze an image using LLaVA with improved prompts

        Args:
            image_path: Path to the image file
            prompt: Custom prompt for analysis (optional)
            detailed: If True, use a more detailed analysis prompt

        Returns:
            Analysis text from LLaVA
        """
        try:
            logger.info(f"Analyzing image: {image_path}")

            # Create client with custom host
            client = ollama.Client(host=self.host)

            # Use enhanced default prompt if none provided
            if prompt is None:
                if detailed:
                    prompt = """Provide a comprehensive analysis of this image:

1. Main Subject: What is the primary focus or subject?
2. Composition: How is the image composed? (framing, perspective, layout)
3. Visual Elements: Key objects, people, or elements visible
4. Setting/Scene: Where does this appear to be? What's the context?
5. Colors and Lighting: Dominant colors, lighting conditions, mood
6. Notable Details: Any interesting or distinctive features

Be specific and descriptive."""
                else:
                    prompt = """Analyze this image and describe:
- What you see (main subjects and objects)
- The scene type and setting
- Notable visual characteristics
- The overall composition and mood

Provide a clear, detailed description in 2-3 sentences."""

            # Make request with image
            response = client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [image_path]
                    }
                ],
                options={
                    'temperature': 0.5,  # Reduced from 0.7 for more consistent results
                    'num_predict': 300 if detailed else 200,
                }
            )

            analysis = response['message']['content'].strip()
            logger.info(f"Analysis completed: {len(analysis)} chars")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            raise

    async def extract_metadata(self, image_path: str, use_fast: bool = True) -> Dict:
        """
        Extract structured metadata from image

        Args:
            image_path: Path to the image file
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
