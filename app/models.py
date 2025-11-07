"""
Database models for jspow
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Float,
    Enum as SQLEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.database import Base


class ProcessStatus(str, Enum):
    """Status of processing jobs"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageType(str, Enum):
    """Type of storage backend"""
    LOCAL = "local"
    NEXTCLOUD = "nextcloud"
    R2 = "r2"
    STREAM = "stream"


class MediaType(str, Enum):
    """Type of media asset"""

    IMAGE = "image"
    VIDEO = "video"


class GroupType(str, Enum):
    """Types of groupings available for images"""

    AI_TAG_CLUSTER = "ai_tag_cluster"
    AI_SCENE_CLUSTER = "ai_scene_cluster"
    AI_EMBEDDING_CLUSTER = "ai_embedding_cluster"
    AI_PROJECT_CLUSTER = "ai_project_cluster"
    MANUAL_COLLECTION = "manual_collection"
    UPLOAD_BATCH = "upload_batch"


class ProjectType(str, Enum):
    """Type of portfolio project"""
    CLIENT = "client"
    PERSONAL = "personal"
    COMMERCIAL = "commercial"
    STOCK = "stock"
    EXHIBITION = "exhibition"
    EXPERIMENTAL = "experimental"


class Project(Base):
    """Portfolio project entity for organizing assets"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.PERSONAL)

    # AI identification keywords
    ai_keywords = Column(JSON)  # List of keywords for AI project matching
    visual_themes = Column(JSON)  # Color palettes, styles, visual patterns

    # Date range for temporal grouping
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    # Storage configuration
    nextcloud_folder = Column(String(500))  # Dedicated Nextcloud path
    default_naming_template = Column(String(500))  # Project-specific naming

    # Portfolio metadata
    portfolio_metadata = Column(JSON)  # Client, industry, URL, testimonials, etc.

    # Status
    is_active = Column(Boolean, default=True)
    featured_on_portfolio = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    images = relationship("Image", back_populates="project")
    groups = relationship("ImageGroup", back_populates="project")


class MediaMetadata(Base):
    """Cached technical metadata for media assets"""

    __tablename__ = "media_metadata"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(1000), nullable=False, unique=True)
    file_mtime = Column(Float, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    duration_s = Column(Float)
    frame_rate = Column(Float)
    codec = Column(String(100))
    media_format = Column(String(100))
    raw_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assets = relationship("Image", back_populates="media_metadata")


class Image(Base):
    """Media asset metadata"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(500), nullable=False)
    current_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String(100), nullable=False)
    media_type = Column(SQLEnum(MediaType), default=MediaType.IMAGE, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    duration_s = Column(Float)
    frame_rate = Column(Float)
    codec = Column(String(100))
    media_format = Column(String(100))
    metadata_id = Column(Integer, ForeignKey("media_metadata.id"))

    # AI Analysis
    ai_description = Column(Text)
    ai_tags = Column(JSON)  # List of tags
    ai_objects = Column(JSON)  # Detected objects
    ai_scene = Column(String(200))  # Scene type (indoor, outdoor, etc.)
    ai_embedding = Column(JSON)  # Vector embedding for similarity clustering
    analyzed_at = Column(DateTime(timezone=True))

    # Smart Rename Tracking
    suggested_filename = Column(String(500))  # LLaVA-generated filename suggestion
    filename_accepted = Column(Boolean, default=False)  # User accepted suggestion
    last_renamed_at = Column(DateTime(timezone=True))  # Last rename timestamp

    # Storage
    storage_type = Column(SQLEnum(StorageType), default=StorageType.LOCAL)
    nextcloud_path = Column(String(1000))
    r2_key = Column(String(1000))
    stream_id = Column(String(200))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id", ondelete="SET NULL"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))

    # Relationships
    rename_jobs = relationship("RenameJob", back_populates="image")
    media_metadata = relationship("MediaMetadata", back_populates="assets")
    group_assignments = relationship(
        "ImageGroupAssociation",
        back_populates="image",
        cascade="all, delete-orphan",
    )
    groups = relationship(
        "ImageGroup",
        secondary="image_group_associations",
        back_populates="images",
        overlaps="group_assignments",
    )
    upload_batch = relationship("UploadBatch", back_populates="images")
    project = relationship("Project", back_populates="images")


class RenameJob(Base):
    """Batch rename job"""
    __tablename__ = "rename_jobs"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    template = Column(String(500), nullable=False)
    proposed_filename = Column(String(500), nullable=False)
    applied = Column(Boolean, default=False)
    status = Column(SQLEnum(ProcessStatus), default=ProcessStatus.PENDING)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True))

    # Relationships
    image = relationship("Image", back_populates="rename_jobs")


class Template(Base):
    """Naming templates"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    pattern = Column(String(500), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)  # Mark as favorite
    category = Column(String(50), default='custom')  # basic, portfolio, custom, media, etc.
    usage_count = Column(Integer, default=0)  # Track usage frequency
    variables_used = Column(JSON)  # List of variables used in template

    # Example: {description}_{date}_{index}
    # Variables: {description}, {tags}, {scene}, {date}, {time}, {index}, {original}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Integration(Base):
    """Storage integration configurations"""
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(SQLEnum(StorageType), nullable=False)
    config = Column(JSON)  # Encrypted credentials and settings
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProcessingQueue(Base):
    """Queue for background processing tasks"""
    __tablename__ = "processing_queue"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(100), nullable=False)  # analyze, rename, upload
    image_ids = Column(JSON)  # List of image IDs
    params = Column(JSON)  # Task parameters
    status = Column(SQLEnum(ProcessStatus), default=ProcessStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))


class UploadBatch(Base):
    """Logical grouping of uploaded images"""

    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(255), nullable=False)
    source = Column(String(255))
    attributes = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    images = relationship("Image", back_populates="upload_batch")
    group = relationship("ImageGroup", back_populates="upload_batch", uselist=False)


class ImageGroup(Base):
    """Persistent representation of group assignments"""

    __tablename__ = "image_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    group_type = Column(SQLEnum(GroupType), nullable=False)
    attributes = Column(JSON)
    is_user_defined = Column(Boolean, default=False)
    created_by = Column(String(255))
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id", ondelete="SET NULL"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))

    # Folder hierarchy support
    parent_id = Column(Integer, ForeignKey("image_groups.id", ondelete="CASCADE"))
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    images = relationship(
        "Image",
        secondary="image_group_associations",
        back_populates="groups",
        overlaps="group_assignments",
    )
    assignments = relationship(
        "ImageGroupAssociation",
        back_populates="group",
        cascade="all, delete-orphan",
        overlaps="groups,images",
    )
    upload_batch = relationship("UploadBatch", back_populates="group")
    project = relationship("Project", back_populates="groups")

    # Folder hierarchy relationships
    parent = relationship("ImageGroup", remote_side=[id], backref="children")


class ImageGroupAssociation(Base):
    """Mapping table between images and their groups"""

    __tablename__ = "image_group_associations"
    __table_args__ = (
        UniqueConstraint("group_id", "image_id", name="uq_image_group_assignment"),
    )

    group_id = Column(Integer, ForeignKey("image_groups.id", ondelete="CASCADE"), primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)
    attributes = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("ImageGroup", back_populates="assignments", overlaps="groups,images")
    image = relationship("Image", back_populates="group_assignments", overlaps="groups,images")
