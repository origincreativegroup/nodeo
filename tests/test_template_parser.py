"""
Tests for template parser
"""
import pytest
from app.services.template_parser import TemplateParser


def test_basic_template():
    """Test basic template parsing"""
    parser = TemplateParser("{description}_{date}")

    metadata = {
        'description': 'Beautiful sunset over mountains',
        'tags': ['nature', 'sunset', 'mountains'],
        'scene': 'outdoor',
        'original_filename': 'IMG_1234.jpg',
        'width': 1920,
        'height': 1080
    }

    result = parser.apply(metadata, index=1)

    # Should contain description words and date
    assert 'beautiful' in result
    assert 'sunset' in result
    assert len(result) > 0


def test_tags_template():
    """Test template with tags"""
    parser = TemplateParser("{tags}_{index}")

    metadata = {
        'description': 'Test image',
        'tags': ['nature', 'landscape', 'outdoor'],
        'scene': 'outdoor',
        'original_filename': 'test.jpg',
        'width': 1920,
        'height': 1080
    }

    result = parser.apply(metadata, index=5)

    assert 'nature' in result
    assert '005' in result  # Zero-padded index


def test_template_validation():
    """Test template validation"""
    # Valid template
    is_valid, msg = TemplateParser.validate_template("{description}_{date}")
    assert is_valid

    # Invalid template (unknown variable)
    is_valid, msg = TemplateParser.validate_template("{unknown_var}")
    assert not is_valid

    # Empty template
    is_valid, msg = TemplateParser.validate_template("")
    assert not is_valid


def test_sanitization():
    """Test filename sanitization"""
    parser = TemplateParser("{description}")

    metadata = {
        'description': 'Test with Special!@#$ Characters & Spaces',
        'tags': [],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 800,
        'height': 600
    }

    result = parser.apply(metadata)

    # Should be sanitized (no special chars, underscores for spaces)
    assert '!' not in result
    assert '@' not in result
    assert '#' not in result
    assert '&' not in result
    assert ' ' not in result
    assert '_' in result


def test_media_metadata_variables():
    """Ensure media-specific variables are supported"""
    parser = TemplateParser("{media_type}_{codec}_{duration_s}_{frame_rate}_{format}")

    metadata = {
        'description': 'Sample clip',
        'tags': ['demo'],
        'scene': 'indoor',
        'original_filename': 'clip.mp4',
        'width': 1280,
        'height': 720,
        'duration_s': 12.5,
        'frame_rate': 29.97,
        'codec': 'h264',
        'format': 'mp4',
        'media_type': 'video',
    }

    result = parser.apply(metadata)

    assert 'video' in result
    assert 'h264' in result
    # Numeric values should be normalized with underscores
    assert '12_5' in result
    assert '29_97' in result
    assert result.endswith('mp4')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
