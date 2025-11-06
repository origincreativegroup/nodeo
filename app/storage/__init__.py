"""Storage integration modules"""
from app.storage.nextcloud import nextcloud_client, NextcloudClient
from app.storage.cloudflare import r2_client, stream_client, R2Client, StreamClient

__all__ = [
    "nextcloud_client",
    "NextcloudClient",
    "r2_client",
    "stream_client",
    "R2Client",
    "StreamClient"
]
