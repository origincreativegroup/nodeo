# nodeo Capability Audit & Roadmap

**Date:** 2025-11-16
**Version:** 1.0.0
**Status:** Post-Refactoring Audit

---

## Executive Summary

This audit was conducted after renaming the project from "jspow" to "nodeo" with an updated product narrative positioning it as a "local-first AI media orchestrator for intelligent renaming, tagging, and transcription across images, audio, and video."

**Key Finding:** nodeo is currently a **powerful image renaming tool** with excellent AI integration, but the multi-modal media orchestrator narrative is aspirational rather than fully implemented. Audio and video "support" is limited to basic file handling and metadata extraction.

---

## Current State Analysis

### ✅ Fully Implemented (Production Ready)

#### 1. Image AI Analysis
- **LLaVA Integration:** Complete vision model integration via Ollama
- **Capabilities:**
  - AI-generated descriptions
  - Smart tag extraction (5-10 relevant tags)
  - Object detection
  - Scene classification (indoor, outdoor, portrait, landscape, etc.)
  - Batch processing with concurrency
  - 4x performance improvement over legacy implementation
- **Project Classifier:**
  - AI-powered project identification
  - 70% confidence threshold for auto-assignment
  - Learning from manual corrections
  - Batch classification support

#### 2. Batch Renaming Engine
- **Template Parser:** 70+ variables including:
  - Basic: `{description}`, `{tags}`, `{scene}`, `{index}`
  - Date/time: `{date}`, `{time}`, `{year}`, `{month}`, etc.
  - Media: `{width}`, `{height}`, `{duration_s}`, `{codec}`, `{format}`
  - AI: `{primary_color}`, `{dominant_object}`, `{mood}`, `{style}`
  - Project: `{project}`, `{project_name}`, `{client}`, `{project_type}`
- **Features:**
  - Preview before apply
  - Batch operations
  - Backup creation
  - Rollback support
  - 16 predefined templates
  - Project-aware sequential numbering

#### 3. Cloud Integration
- **Nextcloud WebDAV:** Full asset management integration
- **Cloudflare R2:** Object storage with originals/working/exports structure
- **Cloudflare Stream:** Video hosting (storage only, no transcription)
- **Storage Manager:** Manifest generation for sync preparation

#### 4. Database Architecture
- **Comprehensive schema** supporting all claimed features
- **Models:** Image, MediaMetadata, Project, Template, RenameJob, WatchedFolder, RenameSuggestion, ActivityLog, Tag, ImageGroup
- **AI metadata fields:** Ready for multi-modal expansion

### 🚧 Partially Implemented (90% Complete)

#### 5. Automated Folder Monitoring (v2)
- **Infrastructure:** ✅ Complete
  - WatcherManager with real-time detection
  - watchdog library integration
  - Background processing queue
  - Database models and REST API
  - WebSocket real-time updates
  - Status management (Active, Paused, Error, Scanning)

- **Missing:** ❌ Processing Logic
  - `_process_file()` method is stubbed (line 324-337 in folder_watcher.py)
  - Files are detected but not automatically analyzed
  - No AI-based rename suggestions generated
  - Worker integration incomplete

**Gap:** Infrastructure exists, but the actual processing pipeline needs to be wired up to the AI analysis and rename suggestion services.

### ❌ Not Implemented (Claims Not Supported)

#### 6. Audio Processing
**Claimed:** "Speech-to-text, transcription, and basic tagging"

**Reality:**
- ❌ No speech-to-text implementation
- ❌ No transcription services
- ❌ No Whisper or audio AI integration
- ❌ No audio content analysis
- ✅ Can store audio files and extract technical metadata (duration, codec, format via ffprobe)
- ✅ Database schema supports audio metadata

**Gap:** **Critical** - The entire audio analysis stack is missing. Only file handling exists.

#### 7. Video Processing
**Claimed:** "Transcription, scene/segment naming, and tagging"

**Reality:**
- ❌ No video transcription (audio-to-text from video)
- ❌ No scene detection or segmentation
- ❌ No intelligent chapter marking
- ❌ No video frame analysis (LLaVA not applied to video)
- ❌ No video-specific AI tagging
- ✅ Can upload/store video files
- ✅ Can extract technical metadata (resolution, frame rate, duration, codec)
- ✅ Cloudflare Stream integration for hosting

**Gap:** **Critical** - Videos are treated as binary files with technical metadata only. No AI capabilities.

---

## Recommendation: Update Product Narrative

The current product narrative overpromises capabilities. Here are two options:

### Option A: Honest Current State (Recommended)

```markdown
# nodeo

**AI-powered image organization with intelligent renaming, tagging, and scene detection.**

> **Formerly jspow** - Renamed and repositioned to reflect the evolution toward a multi-modal media orchestrator.

## Overview

nodeo is a local-first AI image organizer that uses vision models to automatically analyze, tag, and intelligently rename your photos. Built on LLaVA and designed for privacy-conscious users who want control over their media library.

### Current Capabilities

- **Images** ✅ Production Ready:
  - AI-powered description generation
  - Smart tag extraction (5-10 relevant tags per image)
  - Scene detection (indoor, outdoor, portrait, landscape, etc.)
  - Object recognition
  - Project classification
  - Batch processing with concurrent analysis

- **Automated Folder Monitoring** 🚧 Beta:
  - Real-time folder watching
  - Automatic file detection
  - Background processing queue
  - WebSocket progress updates

- **Batch Renaming** ✅ Production Ready:
  - 70+ template variables
  - Preview before apply
  - Backup and rollback
  - Project-aware naming

- **Cloud Integration** ✅ Production Ready:
  - Nextcloud WebDAV
  - Cloudflare R2 storage
  - Cloudflare Stream hosting

### Roadmap

**Phase 1** (Current): Image AI & Renaming
**Phase 2** (Planned): Audio transcription with Whisper integration
**Phase 3** (Planned): Video scene detection and chapter marking
**Phase 4** (Vision): Full multi-modal orchestration with cross-media correlation
```

### Option B: Aspirational with Clear Labeling

```markdown
# nodeo

**Local-first AI media orchestrator for intelligent renaming, tagging, and transcription.**

> Building the future of multi-modal media organization, starting with world-class image AI.

## Feature Status

### ✅ Production Ready
- **Images**: AI-powered description, tagging, scene detection, and object recognition using LLaVA
- **Batch Renaming**: Custom templates with 70+ variables, preview, and rollback
- **Cloud Integration**: Nextcloud WebDAV, Cloudflare R2, Cloudflare Stream
- **Folder Monitoring**: Real-time file detection with background processing

### 🔬 Early Access / Beta
- **Video Handling**: File management and technical metadata extraction
- **Audio Handling**: File management and technical metadata extraction

### 🗓️ Planned
- **Audio Transcription**: Speech-to-text with Whisper AI
- **Video Analysis**: Scene detection, segment naming, frame analysis
- **Multi-modal Tagging**: Cross-reference tags across media types
- **Vector Search**: Semantic similarity with AI embeddings
```

---

## Immediate Action Items

### 1. Complete Folder Watcher Processing ⏱️ 2-4 hours
**File:** `app/services/folder_watcher.py` line 324-337

Replace the stub:
```python
async def _process_file(self, folder_id: UUID, file_path: str):
    """Process a single file (stub for now - will be implemented in workers)"""
    logger.info(f"Processing file: {file_path}")
    # TODO: This will be implemented in the workers module
```

With actual processing:
```python
async def _process_file(self, folder_id: UUID, file_path: str):
    """Process a single file and generate rename suggestions"""
    async with AsyncSessionLocal() as db:
        # 1. Determine file type
        ext = Path(file_path).suffix.lower()

        # 2. For images, run AI analysis
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']:
            from app.ai.llava_client import LLaVAClient
            llava = LLaVAClient()

            # Analyze image
            analysis = await llava.analyze_image(file_path)

            # Generate suggested name
            suggested_name = await llava.generate_filename(file_path, analysis)

            # Store in database
            suggestion = RenameSuggestion(
                id=uuid4(),
                folder_id=folder_id,
                original_path=file_path,
                suggested_name=suggested_name,
                confidence=0.85,
                ai_metadata=analysis,
                status=SuggestionStatus.PENDING
            )
            db.add(suggestion)
            await db.commit()

        # 3. For video/audio, extract metadata only (for now)
        else:
            from app.services.media_metadata import MediaMetadataService
            metadata_service = MediaMetadataService()
            metadata = await metadata_service.extract_metadata(file_path)
            # Store with note that AI analysis is pending
```

### 2. Update README.md ⏱️ 15 minutes
Choose Option A or B above and update the README to accurately reflect current capabilities.

### 3. Add ROADMAP.md ⏱️ 30 minutes
Create a public roadmap document outlining:
- **Now:** What's production-ready
- **Next:** What's being actively developed
- **Later:** Future vision
- **Contributions Welcome:** Where community can help

### 4. Mark Audio/Video as Experimental ⏱️ 10 minutes
Update configuration and documentation:
- Add `EXPERIMENTAL_AUDIO=false` flag
- Add `EXPERIMENTAL_VIDEO=false` flag
- Only enable when features are implemented

---

## Long-Term Roadmap

### Phase 2: Audio Transcription (Estimated: 2-3 weeks)

**Requirements:**
1. Integrate Whisper AI (OpenAI or faster-whisper)
2. Add audio file processing pipeline
3. Implement transcription service
4. Store transcripts in database
5. Generate tags from transcript content
6. Update renaming engine to use transcript data

**Deliverables:**
- Speech-to-text for audio files
- Transcript-based tagging
- Speaker diarization (optional)
- Template variables: `{transcript}`, `{speaker}`, `{audio_tags}`

### Phase 3: Video Analysis (Estimated: 4-6 weeks)

**Requirements:**
1. Implement video frame extraction
2. Apply LLaVA to keyframes
3. Integrate Whisper for audio track transcription
4. Add scene detection algorithm
5. Implement chapter/segment naming
6. Create video-specific templates

**Deliverables:**
- Video frame analysis with LLaVA
- Audio transcription from video
- Scene segmentation
- Intelligent chapter markers
- Template variables: `{scene_count}`, `{chapter_N_name}`, `{video_tags}`

### Phase 4: Multi-Modal Orchestration (Estimated: 8-12 weeks)

**Requirements:**
1. Implement vector embeddings (ai_embedding field)
2. Add cross-media correlation
3. Build semantic similarity search
4. Create unified tagging system
5. Implement smart collections

**Deliverables:**
- Vector similarity search
- "Find similar" across all media types
- Smart collections based on content
- Cross-media tag propagation
- Advanced filtering and search

---

## Metrics for Success

### Current Baseline
- **Image Analysis:** ✅ Production ready
- **Audio Analysis:** ❌ 0% complete
- **Video Analysis:** ❌ 5% complete (file handling only)
- **Folder Monitoring:** 🚧 90% complete (needs processing wiring)

### Target for v1.1
- **Image Analysis:** ✅ Production ready
- **Audio Analysis:** 🎯 60% (transcription working, tagging beta)
- **Video Analysis:** 🎯 30% (transcription working, frame analysis experimental)
- **Folder Monitoring:** ✅ 100% (processing complete)

### Target for v2.0 (Multi-Modal)
- **Image Analysis:** ✅ Production ready
- **Audio Analysis:** ✅ 100% (transcription, tagging, speaker detection)
- **Video Analysis:** ✅ 90% (transcription, scene detection, frame analysis)
- **Multi-Modal:** 🎯 70% (cross-media correlation, vector search)

---

## Conclusion

nodeo has a **solid foundation** as an image AI tool with **excellent renaming capabilities**. The architecture is well-designed to support multi-modal expansion, but the audio and video claims are currently aspirational.

**Recommended Path Forward:**
1. ✅ Update product narrative to accurately reflect current state
2. ✅ Complete folder watcher processing (quick win)
3. 🎯 Implement audio transcription (Phase 2)
4. 🎯 Add video analysis (Phase 3)
5. 🎯 Build multi-modal orchestration (Phase 4)

This honest positioning will build trust with users while the roadmap shows the exciting vision for the future.

---

**Audit Conducted By:** Claude (AI Assistant)
**Reviewed:** Repository exploration and code analysis
**Next Review:** After Phase 2 (Audio Transcription) completion
