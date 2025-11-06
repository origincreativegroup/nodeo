"""Storage integration modules"""
from app.storage.metadata import MetadataSidecarWriter, metadata_sidecar_writer
from app.storage.nextcloud import nextcloud_client, NextcloudClient
from app.storage.cloudflare import r2_client, stream_client, R2Client, StreamClient
from app.storage.layout import StorageManager, storage_manager

__all__ = [
    "nextcloud_client",
    "NextcloudClient",
    "r2_client",
    "stream_client",
    "R2Client",
    "StreamClient",
    "StorageManager",
    "storage_manager",
    "MetadataSidecarWriter",
    "metadata_sidecar_writer",
]
