import io
import tempfile
from contextlib import contextmanager
from pathlib import Path

import boto3
from django.conf import settings

class ArtifactStorageError(RuntimeError):
    pass

def _clean_key(key):
    return str(key).strip("/").replace("\\", "/")

def _s3_client():
    kwargs = {}
    if settings.ARTIFACT_S3_REGION:
        kwargs["region_name"] = settings.ARTIFACT_S3_REGION
    if settings.ARTIFACT_S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.ARTIFACT_S3_ENDPOINT_URL
    if settings.ARTIFACT_S3_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.ARTIFACT_S3_ACCESS_KEY_ID
    if settings.ARTIFACT_S3_SECRET_ACCESS_KEY:
        kwargs["aws_secret_access_key"] = settings.ARTIFACT_S3_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)

def artifact_uri(key):
    key = _clean_key(key)
    if settings.ARTIFACT_STORAGE_BACKEND == "S3":
        full = _clean_key(f"{settings.ARTIFACT_S3_PREFIX}/{key}")
        return f"s3://{settings.ARTIFACT_S3_BUCKET}/{full}"
    return str((Path(settings.ARTIFACT_LOCAL_ROOT) / key).resolve())

def put_bytes(key, data, content_type=None):
    key = _clean_key(key)
    if settings.ARTIFACT_STORAGE_BACKEND == "S3":
        if not settings.ARTIFACT_S3_BUCKET:
            raise ArtifactStorageError("ARTIFACT_S3_BUCKET no está configurado.")
        full = _clean_key(f"{settings.ARTIFACT_S3_PREFIX}/{key}")
        kwargs = {"Bucket": settings.ARTIFACT_S3_BUCKET, "Key": full, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        _s3_client().put_object(**kwargs)
        return f"s3://{settings.ARTIFACT_S3_BUCKET}/{full}"
    path = Path(settings.ARTIFACT_LOCAL_ROOT) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path.resolve())

def put_file(key, source_path, content_type=None):
    return put_bytes(key, Path(source_path).read_bytes(), content_type)

def get_bytes(uri):
    if str(uri).startswith("s3://"):
        without = str(uri)[5:]
        bucket, key = without.split("/", 1)
        obj = _s3_client().get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    return Path(uri).read_bytes()

def exists(uri):
    try:
        if str(uri).startswith("s3://"):
            without = str(uri)[5:]
            bucket, key = without.split("/", 1)
            _s3_client().head_object(Bucket=bucket, Key=key)
            return True
        return Path(uri).exists()
    except Exception:
        return False

def delete(uri):
    if str(uri).startswith("s3://"):
        without = str(uri)[5:]
        bucket, key = without.split("/", 1)
        _s3_client().delete_object(Bucket=bucket, Key=key)
        return
    path = Path(uri)
    if path.exists() and path.is_file():
        path.unlink()

@contextmanager
def materialize(uri, suffix=""):
    if not str(uri).startswith("s3://"):
        yield Path(uri)
        return
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(get_bytes(uri))
        tmp_path = Path(tmp.name)
    try:
        yield tmp_path
    finally:
        tmp_path.unlink(missing_ok=True)

def healthcheck():
    backend = settings.ARTIFACT_STORAGE_BACKEND
    if backend == "S3":
        if not settings.ARTIFACT_S3_BUCKET:
            return {"ok": False, "backend": "S3", "detail": "bucket_not_configured"}
        try:
            _s3_client().head_bucket(Bucket=settings.ARTIFACT_S3_BUCKET)
            return {"ok": True, "backend": "S3"}
        except Exception as exc:
            return {"ok": False, "backend": "S3", "detail": exc.__class__.__name__}
    root = Path(settings.ARTIFACT_LOCAL_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "backend": "LOCAL", "root": str(root)}
