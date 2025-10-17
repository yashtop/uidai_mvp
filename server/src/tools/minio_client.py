# server/src/tools/minio_client.py
import os
import logging
from pathlib import Path
from minio import Minio
from minio.error import S3Error

log = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "true").lower() in ("1", "true", "yes")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uidai-artifacts")

_client = None

def get_client():
    global _client
    if _client is None:
        if not (MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY):
            log.warning("MinIO not configured (MINIO_ENDPOINT/AUTH missing). Uploads will be skipped.")
            return None
        _client = Minio(endpoint=MINIO_ENDPOINT,
                        access_key=MINIO_ACCESS_KEY,
                        secret_key=MINIO_SECRET_KEY,
                        secure=MINIO_SECURE)
        # ensure bucket exists (idempotent)
        try:
            if not _client.bucket_exists(MINIO_BUCKET):
                _client.make_bucket(MINIO_BUCKET)
        except Exception as e:
            log.exception("Failed to ensure MinIO bucket exists: %s", e)
            # return client anyway; upload functions will handle errors
    return _client

def _object_key_for_path(run_id: str, local_path: Path) -> str:
    # store under bucket key: uidai-artifacts/<runId>/<relative path from /tmp/uidai_runs/<runId>>
    try:
        rel = local_path.relative_to(Path("/tmp/uidai_runs") / run_id)
    except Exception:
        # fallback: use file name only
        rel = local_path.name
    return f"{run_id}/{rel.as_posix()}"

def upload_file(run_id: str, local_path: str, content_type: str = None) -> str | None:
    """
    Upload single file. Returns object path on success (e.g. uidai-artifacts/<runId>/path) or None
    """
    client = get_client()
    if client is None:
        return None
    lp = Path(local_path)
    if not lp.exists() or not lp.is_file():
        log.warning("upload_file: path not found or not a file: %s", local_path)
        return None
    key = _object_key_for_path(run_id, lp)
    try:
        client.fput_object(MINIO_BUCKET, key, str(lp))
        log.info("Uploaded %s -> s3://%s/%s", lp, MINIO_BUCKET, key)
        return key
    except S3Error as e:
        log.exception("MinIO upload_file error: %s", e)
        return None

def upload_dir(run_id: str, local_dir: str) -> list:
    """
    Uploads all files under local_dir recursively. Returns list of uploaded keys.
    """
    client = get_client()
    if client is None:
        return []
    uploaded = []
    p = Path(local_dir)
    if not p.exists():
        log.warning("upload_dir: dir not found: %s", local_dir)
        return uploaded
    for f in p.rglob("*"):
        if f.is_file():
            key = _object_key_for_path(run_id, f)
            try:
                client.fput_object(MINIO_BUCKET, key, str(f))
                uploaded.append(key)
            except Exception as e:
                log.exception("Failed to upload %s: %s", f, e)
    log.info("Completed upload_dir %s -> %d objects", local_dir, len(uploaded))
    return uploaded