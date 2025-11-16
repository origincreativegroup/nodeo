"""
Nextcloud WebDAV integration for asset management
"""
from webdav4.client import Client
from pathlib import Path
from typing import List, Dict, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class NextcloudClient:
    """Client for Nextcloud WebDAV operations"""

    def __init__(
        self,
        url: str = None,
        username: str = None,
        password: str = None,
        base_path: str = None
    ):
        """
        Initialize Nextcloud client

        Args:
            url: Nextcloud URL (e.g., https://nextcloud.lan)
            username: Nextcloud username
            password: Nextcloud password
            base_path: Base path for nodeo files (e.g., /nodeo)
        """
        self.url = url or settings.nextcloud_url
        self.username = username or settings.nextcloud_username
        self.password = password or settings.nextcloud_password
        self.base_path = (base_path or settings.nextcloud_base_path).rstrip('/')

        # WebDAV endpoint is at /remote.php/dav/files/username/
        webdav_url = f"{self.url}/remote.php/dav/files/{self.username}/"

        self.client = Client(
            base_url=webdav_url,
            auth=(self.username, self.password)
        )

    def _full_path(self, path: str) -> str:
        """Get full WebDAV path"""
        path = path.lstrip('/')
        return f"{self.base_path}/{path}"

    async def list_files(
        self,
        directory: str = "",
        recursive: bool = False
    ) -> List[Dict]:
        """
        List files in directory

        Args:
            directory: Directory path relative to base_path
            recursive: List recursively

        Returns:
            List of file info dicts
        """
        try:
            full_path = self._full_path(directory)
            logger.info(f"Listing files in: {full_path}")

            # Get directory listing
            items = []
            for item in self.client.ls(full_path, detail=True):
                items.append({
                    'name': item['name'],
                    'path': item['name'],
                    'is_dir': item['type'] == 'directory',
                    'size': item.get('size', 0),
                    'modified': item.get('modified'),
                    'content_type': item.get('content_type')
                })

            logger.info(f"Found {len(items)} items")
            return items

        except Exception as e:
            logger.error(f"Error listing {directory}: {e}")
            raise

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        create_parents: bool = True
    ) -> Dict:
        """
        Upload file to Nextcloud

        Args:
            local_path: Local file path
            remote_path: Remote path relative to base_path
            create_parents: Create parent directories if needed

        Returns:
            Upload result dict
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            full_remote_path = self._full_path(remote_path)
            logger.info(f"Uploading {local_path} to {full_remote_path}")

            # Create parent directories if needed
            if create_parents:
                parent_dir = str(Path(full_remote_path).parent)
                try:
                    self.client.mkdir(parent_dir, parents=True)
                except Exception:
                    pass  # Directory might already exist

            # Upload file
            with open(local_file, 'rb') as f:
                self.client.upload_fileobj(f, full_remote_path)

            logger.info(f"Upload successful: {remote_path}")

            return {
                'success': True,
                'local_path': local_path,
                'remote_path': full_remote_path,
                'size': local_file.stat().st_size
            }

        except Exception as e:
            logger.error(f"Error uploading {local_path}: {e}")
            return {
                'success': False,
                'local_path': local_path,
                'error': str(e)
            }

    async def download_file(
        self,
        remote_path: str,
        local_path: str
    ) -> Dict:
        """
        Download file from Nextcloud

        Args:
            remote_path: Remote path relative to base_path
            local_path: Local destination path

        Returns:
            Download result dict
        """
        try:
            full_remote_path = self._full_path(remote_path)
            logger.info(f"Downloading {full_remote_path} to {local_path}")

            # Create local parent directory
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Download file
            with open(local_path, 'wb') as f:
                self.client.download_fileobj(full_remote_path, f)

            logger.info(f"Download successful: {local_path}")

            return {
                'success': True,
                'remote_path': full_remote_path,
                'local_path': local_path,
                'size': Path(local_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return {
                'success': False,
                'remote_path': remote_path,
                'error': str(e)
            }

    async def create_directory(self, directory: str) -> bool:
        """
        Create directory in Nextcloud

        Args:
            directory: Directory path relative to base_path

        Returns:
            True if successful
        """
        try:
            full_path = self._full_path(directory)
            logger.info(f"Creating directory: {full_path}")

            self.client.mkdir(full_path, parents=True)

            logger.info(f"Directory created: {full_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False

    async def delete_file(self, path: str) -> bool:
        """
        Delete file or directory

        Args:
            path: Path relative to base_path

        Returns:
            True if successful
        """
        try:
            full_path = self._full_path(path)
            logger.info(f"Deleting: {full_path}")

            self.client.remove(full_path)

            logger.info(f"Deleted: {full_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return False

    async def move_file(
        self,
        source: str,
        destination: str
    ) -> bool:
        """
        Move/rename file

        Args:
            source: Source path relative to base_path
            destination: Destination path relative to base_path

        Returns:
            True if successful
        """
        try:
            full_source = self._full_path(source)
            full_dest = self._full_path(destination)

            logger.info(f"Moving {full_source} to {full_dest}")

            self.client.move(full_source, full_dest)

            logger.info(f"Moved successfully")
            return True

        except Exception as e:
            logger.error(f"Error moving {source} to {destination}: {e}")
            return False

    async def batch_upload(
        self,
        files: List[Dict[str, str]],
        base_remote_dir: str = ""
    ) -> Dict:
        """
        Upload multiple files

        Args:
            files: List of dicts with 'local_path' and 'remote_filename'
            base_remote_dir: Base remote directory

        Returns:
            Summary of upload operation
        """
        results = []
        errors = []

        for file_spec in files:
            local_path = file_spec['local_path']
            remote_filename = file_spec['remote_filename']
            remote_path = f"{base_remote_dir}/{remote_filename}".lstrip('/')

            result = await self.upload_file(local_path, remote_path)
            results.append(result)

            if not result['success']:
                errors.append(result)

        return {
            'total': len(files),
            'succeeded': sum(1 for r in results if r['success']),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }


# Global instance
nextcloud_client = NextcloudClient()
