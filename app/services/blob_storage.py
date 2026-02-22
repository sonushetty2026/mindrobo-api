"""Azure Blob Storage service for call recordings and transcripts."""

import logging
import json
import httpx
from azure.storage.blob.aio import BlobServiceClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Service for uploading call recordings and transcripts to Azure Blob."""
    
    def __init__(self):
        self.connection_string = getattr(settings, 'AZURE_BLOB_CONNECTION_STRING', None)
        self.account_name = getattr(settings, 'AZURE_STORAGE_ACCOUNT', 'mindrobostorage001')
        self.container_recordings = "call-recordings"
        self.container_transcripts = "call-transcripts"
    
    async def upload_recording_from_url(self, call_id: str, recording_url: str) -> str | None:
        """Download recording from Retell URL and upload to Azure Blob."""
        if not self.connection_string:
            logger.warning("Azure Blob connection string not configured - skipping upload")
            return None
        
        try:
            # Download recording from Retell
            async with httpx.AsyncClient() as client:
                response = await client.get(recording_url, timeout=30.0)
                response.raise_for_status()
                audio_data = response.content
            
            # Upload to Azure Blob
            async with BlobServiceClient.from_connection_string(self.connection_string) as blob_service:
                blob_client = blob_service.get_blob_client(
                    container=self.container_recordings,
                    blob=f"{call_id}.mp3"
                )
                await blob_client.upload_blob(audio_data, overwrite=True)
                
                blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_recordings}/{call_id}.mp3"
                logger.info("Recording uploaded: %s", blob_url)
                return blob_url
        
        except Exception as e:
            logger.error("Failed to upload recording: %s", e)
            return None
    
    async def upload_transcript(self, call_id: str, transcript_data: dict) -> str | None:
        """Upload transcript JSON to Azure Blob."""
        if not self.connection_string:
            logger.warning("Azure Blob connection string not configured - skipping upload")
            return None
        
        try:
            transcript_json = json.dumps(transcript_data, indent=2).encode('utf-8')
            
            async with BlobServiceClient.from_connection_string(self.connection_string) as blob_service:
                blob_client = blob_service.get_blob_client(
                    container=self.container_transcripts,
                    blob=f"{call_id}.json"
                )
                await blob_client.upload_blob(transcript_json, overwrite=True, content_type='application/json')
                
                blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_transcripts}/{call_id}.json"
                logger.info("Transcript uploaded: %s", blob_url)
                return blob_url
        
        except Exception as e:
            logger.error("Failed to upload transcript: %s", e)
            return None


# Singleton instance
blob_service = BlobStorageService()
