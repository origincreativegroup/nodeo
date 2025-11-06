"""
Cloudflare R2 and Stream integration
"""
import boto3
from botocore.client import Config
from pathlib import Path
from typing import List, Dict, Optional
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class R2Client:
    """Client for Cloudflare R2 storage (S3-compatible)"""

    def __init__(
        self,
        account_id: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        bucket: str = None,
        endpoint: str = None
    ):
        """
        Initialize R2 client

        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket: R2 bucket name
            endpoint: R2 endpoint URL
        """
        self.account_id = account_id or settings.cloudflare_r2_account_id
        self.access_key_id = access_key_id or settings.cloudflare_r2_access_key_id
        self.secret_access_key = secret_access_key or settings.cloudflare_r2_secret_access_key
        self.bucket = bucket or settings.cloudflare_r2_bucket
        self.endpoint = endpoint or settings.cloudflare_r2_endpoint

        # Create S3-compatible client
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )

    async def upload_file(
        self,
        local_path: str,
        key: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Upload file to R2

        Args:
            local_path: Local file path
            key: Object key (path in bucket)
            metadata: Optional metadata dict

        Returns:
            Upload result dict
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            logger.info(f"Uploading {local_path} to R2: {key}")

            # Prepare upload args
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            # Upload file
            self.s3.upload_file(
                str(local_file),
                self.bucket,
                key,
                ExtraArgs=extra_args
            )

            logger.info(f"Upload successful: {key}")

            # Get public URL
            public_url = f"{self.endpoint}/{self.bucket}/{key}"

            return {
                'success': True,
                'local_path': local_path,
                'key': key,
                'size': local_file.stat().st_size,
                'url': public_url
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
        key: str,
        local_path: str
    ) -> Dict:
        """
        Download file from R2

        Args:
            key: Object key in bucket
            local_path: Local destination path

        Returns:
            Download result dict
        """
        try:
            logger.info(f"Downloading R2 object {key} to {local_path}")

            # Create local parent directory
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Download file
            self.s3.download_file(
                self.bucket,
                key,
                local_path
            )

            logger.info(f"Download successful: {local_path}")

            return {
                'success': True,
                'key': key,
                'local_path': local_path,
                'size': Path(local_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"Error downloading {key}: {e}")
            return {
                'success': False,
                'key': key,
                'error': str(e)
            }

    async def list_objects(self, prefix: str = "") -> List[Dict]:
        """
        List objects in bucket

        Args:
            prefix: Object key prefix filter

        Returns:
            List of object info dicts
        """
        try:
            logger.info(f"Listing R2 objects with prefix: {prefix}")

            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )

            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })

            logger.info(f"Found {len(objects)} objects")
            return objects

        except Exception as e:
            logger.error(f"Error listing objects: {e}")
            raise

    async def delete_object(self, key: str) -> bool:
        """
        Delete object from R2

        Args:
            key: Object key

        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting R2 object: {key}")

            self.s3.delete_object(
                Bucket=self.bucket,
                Key=key
            )

            logger.info(f"Deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"Error deleting {key}: {e}")
            return False

    async def batch_upload(
        self,
        files: List[Dict[str, str]],
        prefix: str = ""
    ) -> Dict:
        """
        Upload multiple files

        Args:
            files: List of dicts with 'local_path' and 'key'
            prefix: Key prefix for all uploads

        Returns:
            Summary of upload operation
        """
        results = []
        errors = []

        for file_spec in files:
            local_path = file_spec['local_path']
            key = f"{prefix}/{file_spec['key']}".lstrip('/')

            result = await self.upload_file(local_path, key)
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


class StreamClient:
    """Client for Cloudflare Stream video hosting"""

    def __init__(
        self,
        account_id: str = None,
        api_token: str = None
    ):
        """
        Initialize Stream client

        Args:
            account_id: Cloudflare account ID
            api_token: Stream API token
        """
        self.account_id = account_id or settings.cloudflare_stream_account_id
        self.api_token = api_token or settings.cloudflare_stream_api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/stream"

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def upload_video(
        self,
        local_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Upload video to Stream

        Args:
            local_path: Local video file path
            metadata: Optional metadata (name, requireSignedURLs, etc.)

        Returns:
            Upload result with video details
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            logger.info(f"Uploading video to Stream: {local_path}")

            async with httpx.AsyncClient() as client:
                # Prepare form data
                files = {
                    'file': (local_file.name, open(local_file, 'rb'), 'video/mp4')
                }

                # Add metadata if provided
                data = {}
                if metadata:
                    if 'name' in metadata:
                        data['meta'] = {'name': metadata['name']}
                    if 'requireSignedURLs' in metadata:
                        data['requireSignedURLs'] = metadata['requireSignedURLs']

                # Upload
                response = await client.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    files=files,
                    data=data,
                    timeout=600.0  # 10 minute timeout for large videos
                )

                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    video_data = result['result']
                    logger.info(f"Upload successful: {video_data['uid']}")

                    return {
                        'success': True,
                        'local_path': local_path,
                        'uid': video_data['uid'],
                        'playback_url': f"https://customer-{self.account_id}.cloudflarestream.com/{video_data['uid']}/manifest/video.m3u8",
                        'thumbnail': video_data.get('thumbnail'),
                        'status': video_data.get('status')
                    }
                else:
                    return {
                        'success': False,
                        'local_path': local_path,
                        'error': result.get('errors', 'Unknown error')
                    }

        except Exception as e:
            logger.error(f"Error uploading video {local_path}: {e}")
            return {
                'success': False,
                'local_path': local_path,
                'error': str(e)
            }

    async def get_video_details(self, video_id: str) -> Dict:
        """
        Get video details from Stream

        Args:
            video_id: Stream video UID

        Returns:
            Video details dict
        """
        try:
            logger.info(f"Fetching Stream video details: {video_id}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{video_id}",
                    headers=self.headers
                )

                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return result['result']
                else:
                    raise Exception(result.get('errors', 'Unknown error'))

        except Exception as e:
            logger.error(f"Error fetching video {video_id}: {e}")
            raise

    async def delete_video(self, video_id: str) -> bool:
        """
        Delete video from Stream

        Args:
            video_id: Stream video UID

        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting Stream video: {video_id}")

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/{video_id}",
                    headers=self.headers
                )

                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    logger.info(f"Deleted video: {video_id}")
                    return True
                else:
                    raise Exception(result.get('errors', 'Unknown error'))

        except Exception as e:
            logger.error(f"Error deleting video {video_id}: {e}")
            return False


# Global instances (only initialize if credentials are configured)
r2_client = R2Client() if settings.cloudflare_r2_endpoint else None
stream_client = StreamClient() if settings.cloudflare_stream_api_token else None
