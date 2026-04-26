from __future__ import annotations

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource

import urllib3
from typing import Any
import uuid
from datetime import datetime, timedelta, UTC

from object_move_mcp.config import CONFIG

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

def utcnow() -> datetime:
    return datetime.now(UTC)

def parse_minio_path(path: str) -> tuple[str, str]:
    """
    Input:  'bucket-name/path/to/object.png'
    Output: ('bucket-name', 'path/to/object.png')
    """
    if not path or "/" not in path:
        raise ValueError(f"Invalid MinIO path: {path!r}")

    bucket, object_name = path.split("/", 1)
    if not bucket or not object_name:
        raise ValueError(f"Invalid MinIO path: {path!r}")

    return bucket, object_name

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

def move_minio_object_from_temporary_to_permanent_store(
    *,
    source_path: str,
    target_bucket: str,
    ttl_days: int,
) -> dict[str, Any]:
    """
    Copy object from temp/trash bucket to permanent bucket.

    NOTE:
    - ttl_days/expires_at are stored in metadata only.
    - For automatic deletion you still need:
      1) bucket lifecycle policy, or
      2) background cleanup job.

    Returns:
    {
      "source_path": "...",
      "target_path": "...",
      "object_id": "...",
      "ttl_days": 30,
      "expires_at": "2026-05-01T12:00:00+00:00",
    }
    """

    client: Minio = get_minio_client()

    source_bucket, source_object_name = parse_minio_path(source_path)

    ensure_bucket(client, target_bucket)

    try:
        object_exists(client, source_bucket, source_object_name)
    except Exception as e:
        raise RuntimeError(f"Source object '{source_path}' does not exist. Error: {e}")
    
    # stat = client.stat_object(source_bucket, source_object_name)
    
    target_object_id, target_object_name = generate_unique_object_name(
                client=client,
                bucket_name=target_bucket,
                prefix=CONFIG.minio_prefix,
            )

    expires_at = utcnow() + timedelta(days=ttl_days)

    # source_obj = client.get_object(source_bucket, source_object_name)
    # try:
    #     client.put_object(
    #         bucket_name=target_bucket,
    #         object_name=target_object_name,
    #         data=source_obj,           
    #         # length=stat.size,
    #         # content_type=stat.content_type
    #         metadata={
    #             "expires_at": expires_at.isoformat(),
    #         },
    #     )
    # finally:
    #     source_obj.close()
    #     source_obj.release_conn()

    client.copy_object(
        bucket_name=target_bucket,
        object_name=target_object_name,
        source=CopySource(source_bucket, source_object_name),
        metadata={
            "expires_at": expires_at.isoformat(),
        },
        metadata_directive="REPLACE",
    )

    return {
        "object_id": target_object_id,
        "path": f"{target_bucket}/{target_object_name}",
    }