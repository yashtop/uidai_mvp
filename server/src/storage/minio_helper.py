# server/src/storage/minio_helper.py
"""
MinIO helper with organized structure for multi-agent system
"""
import logging
from pathlib import Path
from typing import Optional
from minio import Minio
from minio.error import S3Error

from ..config import config

log = logging.getLogger(__name__)

class MinIOManager:
    """Manages MinIO artifact storage with organized structure"""
    
    def __init__(self):
        if not config.MINIO_ENABLED:
            self.client = None
            return
        
        self.client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE
        )
        self.bucket = config.MINIO_BUCKET
        
        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                log.info(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            log.error(f"MinIO bucket error: {e}")
    
    def upload_artifact(
        self, 
        run_id: str, 
        local_path: Path, 
        artifact_type: str,
        test_creation_mode: str = "ai"
    ) -> Optional[str]:
        """
        Upload artifact with organized structure
        
        Structure:
        /{run_id}/
            /discovery/
                screenshots/
                network_logs/
            /recording/          # Only for record/hybrid mode
                recorded_test.py
                recording_video.webm
            /generation/
                /ai_generated/   # AI-generated tests
                /recorded/       # User-recorded tests
            /execution/
                screenshots/
                videos/
                traces/
            /healing/
                patches/
        
        Args:
            run_id: Run identifier
            local_path: Local file path
            artifact_type: Type of artifact (discovery|recording|generation|execution|healing)
            test_creation_mode: ai|record|hybrid
        
        Returns:
            Object path in MinIO or None if failed
        """
        if not self.client:
            return None
        
        try:
            filename = local_path.name
            
            # Build object path based on type
            if artifact_type == "recording":
                object_path = f"{run_id}/recording/{filename}"
            elif artifact_type == "generation":
                # Separate AI-generated vs recorded tests
                if "recorded" in filename or test_creation_mode == "record":
                    object_path = f"{run_id}/generation/recorded/{filename}"
                else:
                    object_path = f"{run_id}/generation/ai_generated/{filename}"
            else:
                object_path = f"{run_id}/{artifact_type}/{filename}"
            
            # Upload
            self.client.fput_object(
                self.bucket,
                object_path,
                str(local_path)
            )
            
            log.info(f"Uploaded to MinIO: {object_path}")
            return object_path
            
        except S3Error as e:
            log.error(f"MinIO upload failed: {e}")
            return None
    
    def upload_directory(
        self, 
        run_id: str, 
        local_dir: Path, 
        artifact_type: str,
        test_creation_mode: str = "ai"
    ) -> int:
        """Upload entire directory"""
        if not self.client or not local_dir.exists():
            return 0
        
        count = 0
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                result = self.upload_artifact(run_id, file_path, artifact_type, test_creation_mode)
                if result:
                    count += 1
        
        return count
    
    def get_artifact_url(self, run_id: str, artifact_path: str) -> Optional[str]:
        """Get presigned URL for artifact"""
        if not self.client:
            return None
        
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                artifact_path,
                expires=3600  # 1 hour
            )
            return url
        except S3Error as e:
            log.error(f"Failed to generate URL: {e}")
            return None

# Global instance
minio_manager = MinIOManager()