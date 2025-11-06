"""
LLaVA image analysis client using Ollama
"""
import base64
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

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail, including objects, scene, and key elements."
    ) -> str:
        """
        Analyze an image using LLaVA

        Args:
            image_path: Path to the image file
            prompt: Custom prompt for analysis

        Returns:
            Analysis text from LLaVA
        """
        try:
            logger.info(f"Analyzing image: {image_path}")

            # Create client with custom host
            client = ollama.Client(host=self.host)

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
                    'temperature': 0.7,
                    'num_predict': 200,
                }
            )

            analysis = response['message']['content']
            logger.info(f"Analysis completed: {len(analysis)} chars")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            raise

    async def extract_metadata(self, image_path: str) -> Dict:
        """
        Extract structured metadata from image

        Returns:
            {
                'description': str,
                'tags': List[str],
                'objects': List[str],
                'scene': str
            }
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
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Generate a descriptive filename based on image content

        Args:
            image_path: Path to image
            metadata: Pre-analyzed metadata (optional)

        Returns:
            Suggested filename (without extension)
        """
        try:
            if not metadata:
                metadata = await self.extract_metadata(image_path)

            # Use LLaVA to create a concise filename
            client = ollama.Client(host=self.host)

            prompt = f"""Based on this image description: "{metadata.get('description', '')}"
And these tags: {', '.join(metadata.get('tags', [])[:5])}

Generate a short, descriptive filename (3-5 words, lowercase, use underscores).
Only respond with the filename, nothing else."""

            response = client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }],
                options={'temperature': 0.5}
            )

            filename = response['message']['content'].strip()
            # Clean filename
            filename = filename.lower().replace(' ', '_').replace('-', '_')
            # Remove any non-alphanumeric except underscores
            filename = ''.join(c for c in filename if c.isalnum() or c == '_')

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
        extract_full_metadata: bool = True
    ) -> List[Dict]:
        """
        Analyze multiple images in batch

        Args:
            image_paths: List of image paths
            extract_full_metadata: If True, extract full metadata; else just description

        Returns:
            List of metadata dicts
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
