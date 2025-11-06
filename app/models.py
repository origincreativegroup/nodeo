"""
Database models for jspow
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
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


class Image(Base):
    """Image metadata"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(500), nullable=False)
    current_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer)
    height = Column(Integer)

    # AI Analysis
    ai_description = Column(Text)
    ai_tags = Column(JSON)  # List of tags
    ai_objects = Column(JSON)  # Detected objects
    ai_scene = Column(String(200))  # Scene type (indoor, outdoor, etc.)
    analyzed_at = Column(DateTime(timezone=True))

    # Storage
    storage_type = Column(SQLEnum(StorageType), default=StorageType.LOCAL)
    nextcloud_path = Column(String(1000))
    r2_key = Column(String(1000))
    stream_id = Column(String(200))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    rename_jobs = relationship("RenameJob", back_populates="image")


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
