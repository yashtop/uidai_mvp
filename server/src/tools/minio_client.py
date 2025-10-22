# server/src/tools/minio_client.py
import os
import logging
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

log = logging.getLogger(__name__)

# Default values (safe local defaults); prefer to set via env in production
_DEFAULT_MINIO_ENDPOINT = "127.0.0.1:9001"

# Read raw env (user may provide host:port OR full URL like https://host:9000/prefix)
_RAW_MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", _DEFAULT_MINIO_ENDPOINT)
_MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
_MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
# Optional: explicit override; if not set we infer from scheme in endpoint (https -> secure)
_MINIO_SECURE_ENV = os.getenv("MINIO_SECURE", None)
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uidai-artifacts")

_client: Minio | None = None


def _normalize_minio_endpoint(raw: str, secure_env: str | None):
    """
    Accepts:
      - 'host:9000'
      - 'http://host:9000'
      - 'https://host:9000'
      - 'http://host:9000/some/path'  (will strip the path)
    Returns (host_port, secure_bool)
    """
    if not raw:
        raise ValueError("MINIO_ENDPOINT is empty")

    # If raw contains scheme, urlparse will parse netloc; otherwise we force a // prefix
    parsed = urlparse(raw) if "://" in raw else urlparse(f"//{raw}", scheme="")

    # Determine host:port
    host_port = parsed.netloc or parsed.path  # when no scheme, path holds host:port

    # If there is a path (and netloc present) warn and strip it
    if parsed.netloc and parsed.path and parsed.path not in ("", "/"):
        log.warning(
            "MINIO_ENDPOINT '%s' contains a path '%s' - MinIO endpoint should be host[:port]. "
            "Stripping the path for SDK compatibility.",
            raw,
            parsed.path,
        )

    # Decide secure flag: env override has priority, else infer from scheme
    if secure_env is not None:
        se = str(secure_env).lower()
        if se in ("1", "true", "yes"):
            secure = True
        elif se in ("0", "false", "no"):
            secure = False
        else:
            # unknown value, fallback to inference
            secure = parsed.scheme == "https"
    else:
        secure = parsed.scheme == "https"

    if not host_port:
        raise ValueError(f"Could not determine host:port from MINIO_ENDPOINT '{raw}'")

    # final sanity remove trailing slashes
    host_port = host_port.rstrip("/")

    return host_port, bool(secure)


def get_client() -> Minio | None:
    """
    Returns a cached Minio client or None if MinIO not configured.
    Accepts MINIO_ENDPOINT as either 'host:port' or 'http(s)://host:port[/path]'.
    """
    global _client
    if _client is not None:
        return _client

    # quick check: fail fast if auth missing
    if not (_RAW_MINIO_ENDPOINT and _MINIO_ACCESS_KEY and _MINIO_SECRET_KEY):
        log.warning("MinIO not configured (MINIO_ENDPOINT / AUTH missing). Uploads will be skipped.")
        return None

    try:
        endpoint, secure = _normalize_minio_endpoint(_RAW_MINIO_ENDPOINT, _MINIO_SECURE_ENV)
    except Exception as e:
        log.exception("Invalid MINIO_ENDPOINT (%s): %s", _RAW_MINIO_ENDPOINT, e)
        return None

    log.info("Creating MinIO client with endpoint=%s secure=%s", endpoint, secure)

    try:
        _client = Minio(
            endpoint=endpoint,
            access_key=_MINIO_ACCESS_KEY,
            secret_key=_MINIO_SECRET_KEY,
            secure=secure,
        )
    except Exception:
        log.exception("Failed creating MinIO client (check endpoint/credentials).")
        return None

    # ensure bucket exists (idempotent). Don't fail hard — just log.
    try:
        if not _client.bucket_exists(MINIO_BUCKET):
            _client.make_bucket(MINIO_BUCKET)
            log.info("Created missing MinIO bucket: %s", MINIO_BUCKET)
    except Exception:
        log.exception("Failed to ensure MinIO bucket '%s' exists; uploads may still fail.", MINIO_BUCKET)

    return _client


def _object_key_for_path(run_id: str, local_path: Path) -> str:
    """
    store under key: <runId>/<relative path from /tmp/uidai_runs/<runId>> or fallback to file name
    """
    try:
        rel = local_path.relative_to(Path("/tmp/uidai_runs") / run_id)
    except Exception:
        # fallback: use file name only
        rel = local_path.name
    return f"{run_id}/{Path(rel).as_posix()}"


def upload_file(run_id: str, local_path: str, content_type: str = None) -> str | None:
    """
    Upload single file. Returns object key on success (e.g. <runId>/path) or None
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
    except Exception as e:
        log.exception("Unexpected MinIO upload_file error: %s", e)
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
