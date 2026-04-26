from minio import Minio
import urllib3
from screenshot_mcp.config import CONFIG
from minio.error import S3Error
import uuid
import io

def get_minio_client() -> Minio:
    if CONFIG.minio_secure:
        if CONFIG.minio_verify_ssl:
            http_client = urllib3.PoolManager(
                cert_reqs="CERT_REQUIRED",
                ca_certs=CONFIG.ca_cert_path,
            )
        else:
            urllib3.disable_warnings()
            http_client = urllib3.PoolManager(cert_reqs="CERT_NONE")

    return Minio(
        endpoint=CONFIG.minio_endpoint,
        access_key=CONFIG.minio_access_key,
        secret_key=CONFIG.minio_secret_key,
        secure=CONFIG.minio_secure,
        region=CONFIG.minio_region,
        http_client=http_client,
    )

def ensure_bucket(client: Minio, bucket_name: str) -> None:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name, location=CONFIG.minio_region)

def object_exists(client: Minio, bucket_name: str, object_name: str) -> bool:
    try:
        client.stat_object(bucket_name, object_name)
        return True
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchVersion", "NoSuchBucket"}:
            return False
        raise

def generate_unique_object_name(client: Minio, bucket_name: str, prefix: str) -> tuple[str, str]:
    while True:
        object_id = str(uuid.uuid4())
        object_name = f"{prefix}{object_id}.png"
        if not object_exists(client, bucket_name, object_name):
            return object_id, object_name

def upload_png_bytes(client: Minio, bucket_name: str, object_name: str, data: bytes) -> None:
    stream = io.BytesIO(data)
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=stream,
        length=len(data),
        content_type="image/png",
    )