import logging
from typing import Any, Dict, List, Optional

from app.config import settings


logger = logging.getLogger(__name__)


class OSSConnector:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.OSS_ENDPOINT
        self.access_key_id = access_key_id or settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or settings.OSS_ACCESS_KEY_SECRET
        self.bucket_name = bucket_name or settings.OSS_BUCKET
        self._auth = None
        self._bucket = None
        self._service = None
        logger.info("OSSConnector initialized for bucket: %s", self.bucket_name)

    def _init_auth(self) -> None:
        if self._auth is not None:
            return
        try:
            import oss2

            self._auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            logger.info("OSS auth initialized")
        except ImportError:
            logger.warning("oss2 package not available")
            self._auth = None
        except Exception as e:
            logger.error("Failed to initialize OSS auth: %s", str(e))
            self._auth = None
            raise

    def _get_service(self):
        if self._service is not None:
            return self._service
        self._init_auth()
        if self._auth is None:
            return None
        try:
            import oss2

            self._service = oss2.Service(self._auth, self.endpoint)
            logger.info("OSS service initialized for endpoint: %s", self.endpoint)
        except Exception as e:
            logger.error("Failed to create OSS service: %s", str(e))
            self._service = None
            raise
        return self._service

    def _get_bucket(self):
        if self._bucket is not None:
            return self._bucket
        self._init_auth()
        if self._auth is None:
            return None
        try:
            import oss2

            self._bucket = oss2.Bucket(self._auth, self.endpoint, self.bucket_name)
            logger.info("OSS bucket initialized: %s", self.bucket_name)
        except Exception as e:
            logger.error("Failed to create OSS bucket client: %s", str(e))
            self._bucket = None
            raise
        return self._bucket

    def list_buckets(self) -> List[str]:
        logger.info("Listing all OSS buckets")
        service = self._get_service()
        if service is None:
            logger.warning("OSS service not available, returning empty bucket list")
            return []
        try:
            result = service.list_buckets()
            bucket_names = [b.name for b in result.buckets]
            logger.info("Found %d OSS buckets", len(bucket_names))
            return bucket_names
        except Exception as e:
            logger.error("Failed to list OSS buckets: %s", str(e))
            raise

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        logger.info("Listing OSS objects with prefix: %s", prefix)
        bucket = self._get_bucket()
        if bucket is None:
            logger.warning("OSS bucket not available, returning empty object list")
            return []
        objects = []
        try:
            for obj in oss2.ObjectIteratorV2(bucket, prefix=prefix, max_keys=max_keys):
                objects.append(
                    {
                        "key": obj.key,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                        "type": obj.type,
                    }
                )
            logger.info("Found %d OSS objects with prefix: %s", len(objects), prefix)
            return objects
        except Exception as e:
            logger.error("Failed to list OSS objects with prefix %s: %s", prefix, str(e))
            raise

    def get_object_size(self, key: str) -> Optional[int]:
        logger.info("Getting size for OSS object: %s", key)
        bucket = self._get_bucket()
        if bucket is None:
            logger.warning("OSS bucket not available, returning None for object size")
            return None
        try:
            meta = bucket.head_object(key)
            size = meta.content_length
            logger.info("Object %s size: %d bytes", key, size)
            return size
        except Exception as e:
            logger.error("Failed to get size for object %s: %s", key, str(e))
            return None

    def get_directory_size(self, prefix: str = "") -> Dict[str, Any]:
        logger.info("Calculating directory size for prefix: %s", prefix)
        bucket = self._get_bucket()
        if bucket is None:
            logger.warning("OSS bucket not available, returning empty directory stats")
            return {"total_size_bytes": 0, "file_count": 0}

        total_size = 0
        file_count = 0
        try:
            for obj in oss2.ObjectIteratorV2(bucket, prefix=prefix):
                total_size += obj.size or 0
                file_count += 1
            result = {"total_size_bytes": total_size, "file_count": file_count}
            logger.info(
                "Directory %s: %d files, %d bytes",
                prefix,
                file_count,
                total_size,
            )
            return result
        except Exception as e:
            logger.error("Failed to calculate directory size for %s: %s", prefix, str(e))
            raise

    def list_common_prefixes(self, prefix: str = "", delimiter: str = "/") -> List[str]:
        logger.info("Listing common prefixes with prefix: %s", prefix)
        bucket = self._get_bucket()
        if bucket is None:
            logger.warning("OSS bucket not available, returning empty prefix list")
            return []
        prefixes = []
        try:
            for p in oss2.ObjectIteratorV2(bucket, prefix=prefix, delimiter=delimiter):
                if isinstance(p, oss2.models.SimplifiedObjectInfo):
                    continue
                prefixes.append(p)
            logger.info("Found %d common prefixes under %s", len(prefixes), prefix)
            return prefixes
        except Exception as e:
            logger.error("Failed to list common prefixes for %s: %s", prefix, str(e))
            raise
