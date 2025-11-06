"""
Template parser for custom file naming patterns
"""
import re
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


class TemplateParser:
    """
    Parse and apply naming templates to images

    Supported variables:
        {description} - AI-generated description (first N words)
        {tags} - Top tags joined with underscores
        {scene} - Scene type (indoor, outdoor, etc.)
        {date} - Current date (YYYYMMDD)
        {time} - Current time (HHMMSS)
        {datetime} - Combined datetime (YYYYMMDD_HHMMSS)
        {index} - Sequential index
        {original} - Original filename (without extension)
        {width} - Image width
        {height} - Image height
        {resolution} - width x height
    """

    VARIABLE_PATTERN = re.compile(r'\{([^}]+)\}')

    def __init__(self, template: str):
        """
        Initialize parser with template

        Args:
            template: Template string (e.g., "{description}_{date}_{index}")
        """
        self.template = template
        self.variables = self._extract_variables()

    def _extract_variables(self) -> list:
        """Extract variable names from template"""
        return self.VARIABLE_PATTERN.findall(self.template)

    def _sanitize(self, text: str, max_length: int = 50) -> str:
        """Sanitize text for filename use"""
        # Convert to lowercase
        text = text.lower()
        # Replace spaces with underscores
        text = text.replace(' ', '_')
        # Remove special characters
        text = re.sub(r'[^a-z0-9_-]', '', text)
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        # Trim length
        if len(text) > max_length:
            text = text[:max_length].rstrip('_')
        return text

    def _get_description_slug(self, description: str, word_count: int = 4) -> str:
        """Convert description to filename-safe slug"""
        if not description:
            return "untitled"
        words = description.split()[:word_count]
        slug = '_'.join(words)
        return self._sanitize(slug)

    def _get_tags_slug(self, tags: list, count: int = 3) -> str:
        """Convert tags to filename-safe slug"""
        if not tags:
            return ""
        top_tags = tags[:count]
        return self._sanitize('_'.join(top_tags))

    def apply(
        self,
        metadata: Dict[str, Any],
        index: int = 1,
        current_time: datetime = None
    ) -> str:
        """
        Apply template to generate filename

        Args:
            metadata: Image metadata dict with keys:
                - description (str)
                - tags (list)
                - scene (str)
                - original_filename (str)
                - width (int)
                - height (int)
            index: Sequential index for batch operations
            current_time: Datetime to use (defaults to now)

        Returns:
            Generated filename (without extension)
        """
        if current_time is None:
            current_time = datetime.now()

        # Prepare variable replacements
        replacements = {
            'description': self._get_description_slug(
                metadata.get('description', ''), word_count=4
            ),
            'tags': self._get_tags_slug(
                metadata.get('tags', []), count=3
            ),
            'scene': self._sanitize(metadata.get('scene', '')),
            'date': current_time.strftime('%Y%m%d'),
            'time': current_time.strftime('%H%M%S'),
            'datetime': current_time.strftime('%Y%m%d_%H%M%S'),
            'index': str(index).zfill(3),  # Zero-padded index (001, 002, etc.)
            'original': self._sanitize(
                Path(metadata.get('original_filename', 'unknown')).stem
            ),
            'width': str(metadata.get('width', '')),
            'height': str(metadata.get('height', '')),
            'resolution': f"{metadata.get('width', '')}x{metadata.get('height', '')}"
        }

        # Apply replacements
        filename = self.template
        for var, value in replacements.items():
            filename = filename.replace(f'{{{var}}}', value)

        # Clean up any remaining empty patterns or multiple underscores
        filename = re.sub(r'_+', '_', filename)
        filename = filename.strip('_-')

        # Final sanitization
        filename = self._sanitize(filename, max_length=100)

        return filename

    def preview(self, metadata: Dict[str, Any], count: int = 1) -> list:
        """
        Generate preview of filenames for multiple images

        Args:
            metadata: Single image metadata or template values
            count: Number of preview examples to generate

        Returns:
            List of preview filenames
        """
        now = datetime.now()
        previews = []

        for i in range(1, count + 1):
            filename = self.apply(metadata, index=i, current_time=now)
            previews.append(filename)

        return previews

    @staticmethod
    def validate_template(template: str) -> tuple[bool, str]:
        """
        Validate a template string

        Args:
            template: Template string to validate

        Returns:
            (is_valid, error_message)
        """
        if not template or template.strip() == "":
            return False, "Template cannot be empty"

        # Check for valid variable syntax
        try:
            parser = TemplateParser(template)
            variables = parser.variables

            # Check for unknown variables
            valid_vars = {
                'description', 'tags', 'scene', 'date', 'time',
                'datetime', 'index', 'original', 'width', 'height', 'resolution'
            }
            unknown = set(variables) - valid_vars
            if unknown:
                return False, f"Unknown variables: {', '.join(unknown)}"

            # Test with dummy data
            dummy_metadata = {
                'description': 'test image',
                'tags': ['test', 'sample'],
                'scene': 'indoor',
                'original_filename': 'test.jpg',
                'width': 1920,
                'height': 1080
            }
            result = parser.apply(dummy_metadata)

            if not result or result.strip() == "":
                return False, "Template produces empty filename"

            return True, "Valid template"

        except Exception as e:
            return False, f"Invalid template: {str(e)}"


# Predefined templates
PREDEFINED_TEMPLATES = {
    "descriptive": "{description}_{date}",
    "detailed": "{description}_{tags}_{datetime}",
    "simple": "{description}_{index}",
    "tagged": "{tags}_{scene}_{date}",
    "dated": "{date}_{time}_{description}",
    "indexed": "{index}_{description}",
    "scene_based": "{scene}_{tags}_{date}",
    "original_preserved": "{original}_{description}_{date}",
}
