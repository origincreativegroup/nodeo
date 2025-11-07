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


def test_new_datetime_variables():
    """Test new granular date/time variables"""
    parser = TemplateParser("{year}_{month}_{day}_{hour}_{minute}")

    from datetime import datetime
    test_time = datetime(2025, 11, 7, 14, 30, 45)

    metadata = {
        'description': 'Test',
        'tags': [],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1920,
        'height': 1080
    }

    result = parser.apply(metadata, current_time=test_time)

    assert '2025' in result
    assert '11' in result
    assert '07' in result
    assert '14' in result
    assert '30' in result


def test_orientation_variable():
    """Test orientation detection variable"""
    # Landscape
    parser = TemplateParser("{orientation}")

    metadata_landscape = {
        'description': 'Test',
        'tags': [],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1920,
        'height': 1080
    }

    result = parser.apply(metadata_landscape)
    assert 'landscape' in result

    # Portrait
    metadata_portrait = {
        'description': 'Test',
        'tags': [],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1080,
        'height': 1920
    }

    result = parser.apply(metadata_portrait)
    assert 'portrait' in result

    # Square
    metadata_square = {
        'description': 'Test',
        'tags': [],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1080,
        'height': 1080
    }

    result = parser.apply(metadata_square)
    assert 'square' in result


def test_ai_analysis_variables():
    """Test AI analysis variables"""
    parser = TemplateParser("{primary_color}_{dominant_object}_{mood}_{style}")

    metadata = {
        'description': 'Test image',
        'tags': ['test'],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1920,
        'height': 1080,
        'primary_color': 'blue',
        'dominant_object': 'person',
        'mood': 'happy',
        'style': 'modern'
    }

    result = parser.apply(metadata)

    assert 'blue' in result
    assert 'person' in result
    assert 'happy' in result
    assert 'modern' in result


def test_utility_variables():
    """Test utility variables (random, uuid)"""
    parser = TemplateParser("{description}_{random}_{uuid}")

    metadata = {
        'description': 'Test image',
        'tags': ['test'],
        'scene': 'indoor',
        'original_filename': 'test.jpg',
        'width': 1920,
        'height': 1080
    }

    result1 = parser.apply(metadata)
    result2 = parser.apply(metadata)

    # Random values should make results different
    assert result1 != result2
    # Both should contain 'test'
    assert 'test' in result1
    assert 'test' in result2


def test_extension_variable():
    """Test file extension variable"""
    parser = TemplateParser("{original}_{extension}")

    metadata = {
        'description': 'Test image',
        'tags': ['test'],
        'scene': 'indoor',
        'original_filename': 'photo.jpg',
        'width': 1920,
        'height': 1080
    }

    result = parser.apply(metadata)

    assert 'photo' in result
    assert 'jpg' in result


def test_all_new_variables_validation():
    """Test that all new variables are recognized as valid"""
    new_vars = [
        'year', 'month', 'day', 'hour', 'minute', 'second',
        'orientation', 'file_size', 'file_size_kb', 'created_date', 'modified_date', 'extension',
        'primary_color', 'dominant_object', 'mood', 'style',
        'random', 'random4', 'uuid'
    ]

    for var in new_vars:
        template = f"{{{var}}}_test"
        is_valid, msg = TemplateParser.validate_template(template)
        assert is_valid, f"Variable {var} should be valid but got error: {msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
