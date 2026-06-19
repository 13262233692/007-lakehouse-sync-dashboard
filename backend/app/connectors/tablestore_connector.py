import logging
from typing import Any, Dict, List, Optional

from app.config import settings


logger = logging.getLogger(__name__)


class TableStoreConnector:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        instance_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.TABLESTORE_ENDPOINT
        self.access_key_id = access_key_id or settings.TABLESTORE_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or settings.TABLESTORE_ACCESS_KEY_SECRET
        self.instance_name = instance_name or settings.TABLESTORE_INSTANCE
        self._client = None
        logger.info("TableStoreConnector initialized for instance: %s", self.instance_name)

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import tablestore

            self._client = tablestore.OTSClient(
                self.endpoint,
                self.access_key_id,
                self.access_key_secret,
                self.instance_name,
            )
            logger.info("TableStore client initialized for instance: %s", self.instance_name)
        except ImportError:
            logger.warning("tablestore package not available")
            self._client = None
        except Exception as e:
            logger.error("Failed to create TableStore client: %s", str(e))
            self._client = None
            raise
        return self._client

    def list_tables(self) -> List[str]:
        logger.info("Listing all TableStore tables")
        client = self._get_client()
        if client is None:
            logger.warning("TableStore client not available, returning empty table list")
            return []
        try:
            tables = client.list_table()
            logger.info("Found %d TableStore tables", len(tables))
            return tables
        except Exception as e:
            logger.error("Failed to list TableStore tables: %s", str(e))
            raise

    def describe_table(self, table_name: str) -> Optional[Dict[str, Any]]:
        logger.info("Describing TableStore table: %s", table_name)
        client = self._get_client()
        if client is None:
            logger.warning("TableStore client not available, returning None")
            return None
        try:
            table_meta, table_options, reserved_throughput = client.describe_table(table_name)
            result: Dict[str, Any] = {
                "table_name": table_meta.table_name,
                "primary_keys": [],
                "defined_columns": [],
                "table_options": {},
            }
            for pk in table_meta.primary_key:
                result["primary_keys"].append(
                    {"name": pk[0], "type": pk[1]}
                )
            if table_meta.defined_columns:
                for col in table_meta.defined_columns:
                    result["defined_columns"].append(
                        {"name": col[0], "type": col[1]}
                    )
            if table_options:
                result["table_options"]["time_to_live"] = getattr(table_options, "time_to_live", None)
                result["table_options"]["max_versions"] = getattr(table_options, "max_versions", None)
                result["table_options"]["deviation_cell_version_in_sec"] = getattr(
                    table_options, "deviation_cell_version_in_sec", None
                )
            logger.info("Retrieved description for table %s", table_name)
            return result
        except Exception as e:
            logger.error("Failed to describe table %s: %s", table_name, str(e))
            return None

    def get_row_count(self, table_name: str, limit: int = 1000000) -> int:
        logger.info("Estimating row count for table: %s", table_name)
        client = self._get_client()
        if client is None:
            logger.warning("TableStore client not available, returning 0")
            return 0
        try:
            count = 0
            next_token = None
            while True:
                consumed, next_start_primary_key, rows, next_token = client.get_range(
                    table_name,
                    tablestore.Direction.FORWARD,
                    [],
                    None,
                    limit=min(limit, 5000),
                    next_token=next_token,
                )
                count += len(rows)
                if next_start_primary_key is None or count >= limit:
                    break
            logger.info("Estimated %d rows in table %s", count, table_name)
            return count
        except Exception as e:
            logger.error("Failed to get row count for table %s: %s", table_name, str(e))
            return 0

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        logger.info("Getting schema for table: %s", table_name)
        table_desc = self.describe_table(table_name)
        if not table_desc:
            return []
        schema = []
        for idx, pk in enumerate(table_desc["primary_keys"]):
            schema.append(
                {
                    "column_name": pk["name"],
                    "data_type": self._map_tablestore_type(pk["type"]),
                    "comment": "",
                    "is_nullable": False,
                    "position": idx,
                }
            )
        offset = len(schema)
        for idx, col in enumerate(table_desc["defined_columns"]):
            schema.append(
                {
                    "column_name": col["name"],
                    "data_type": self._map_tablestore_type(col["type"]),
                    "comment": "",
                    "is_nullable": True,
                    "position": offset + idx,
                }
            )
        logger.info("Retrieved %d columns for table %s", len(schema), table_name)
        return schema

    @staticmethod
    def _map_tablestore_type(ots_type: Any) -> str:
        type_mapping = {
            "INTEGER": "bigint",
            "STRING": "string",
            "BINARY": "binary",
            "DOUBLE": "double",
            "BOOLEAN": "boolean",
        }
        type_str = str(ots_type).split(".")[-1].upper() if ots_type else "STRING"
        return type_mapping.get(type_str, "string")
