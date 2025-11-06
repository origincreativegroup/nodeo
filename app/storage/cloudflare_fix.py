# Fix: Only initialize clients if credentials are provided
from app.config import settings

# Only create global instances if credentials are configured
r2_client = None
stream_client = None

def get_r2_client():
    global r2_client
    if r2_client is None and settings.cloudflare_r2_endpoint:
        from app.storage.cloudflare import R2Client
        r2_client = R2Client()
    return r2_client

def get_stream_client():
    global stream_client
    if stream_client is None and settings.cloudflare_stream_api_token:
        from app.storage.cloudflare import StreamClient
        stream_client = StreamClient()
    return stream_client
