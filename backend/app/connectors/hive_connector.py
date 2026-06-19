import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class HiveTable:
    db_name: str
    table_name: str
    owner: Optional[str] = None
    create_time: Optional[int] = None
    location: Optional[str] = None
    table_type: Optional[str] = None
    partition_keys: List[Dict[str, str]] = field(default_factory=list)
    columns: List[Dict[str, str]] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)


@dataclass
class HivePartition:
    values: List[str]
    db_name: str
    table_name: str
    location: Optional[str] = None
    create_time: Optional[int] = None
    parameters: Dict[str, str] = field(default_factory=dict)


def _retry(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        str(e),
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


class HiveConnector:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        self.host = host or settings.HIVE_METASTORE_HOST
        self.port = port or settings.HIVE_METASTORE_PORT
        self._client = None
        self._transport = None
        self._connected = False
        logger.info("HiveConnector initialized for %s:%d", self.host, self.port)

    def _connect(self) -> None:
        if self._connected:
            return

        try:
            from thrift.transport import TSocket, TTransport
            from thrift.protocol import TBinaryProtocol
            from hive_metastore import ThriftHiveMetastore

            socket = TSocket.TSocket(self.host, self.port)
            socket.setTimeout(60000)
            self._transport = TTransport.TBufferedTransport(socket)
            protocol = TBinaryProtocol.TBinaryProtocol(self._transport)
            self._client = ThriftHiveMetastore.Client(protocol)
            self._transport.open()
            self._connected = True
            logger.info("Connected to Hive Metastore at %s:%d", self.host, self.port)
        except ImportError:
            logger.warning(
                "Hive Metastore thrift client not available. "
                "Install hive_metastore package or use mock mode."
            )
            self._connected = False
        except Exception as e:
            logger.error("Failed to connect to Hive Metastore: %s", str(e))
            self._connected = False
            raise

    def _close(self) -> None:
        if self._transport and self._connected:
            try:
                self._transport.close()
            except Exception as e:
                logger.warning("Error closing Hive Metastore connection: %s", str(e))
            finally:
                self._connected = False
                self._client = None
                self._transport = None

    def __enter__(self) -> "HiveConnector":
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._close()

    @_retry(max_retries=3)
    def get_all_databases(self) -> List[str]:
        logger.info("Fetching all databases from Hive Metastore")
        if not self._connected:
            self._connect()
        if not self._client:
            logger.warning("Hive client not connected, returning empty database list")
            return []
        try:
            databases = self._client.get_all_databases()
            logger.info("Found %d databases", len(databases))
            return databases
        except Exception as e:
            logger.error("Failed to fetch databases: %s", str(e))
            raise

    @_retry(max_retries=3)
    def get_all_tables(self, db_name: str) -> List[str]:
        logger.info("Fetching all tables from database: %s", db_name)
        if not self._connected:
            self._connect()
        if not self._client:
            logger.warning("Hive client not connected, returning empty table list")
            return []
        try:
            tables = self._client.get_all_tables(db_name)
            logger.info("Found %d tables in database %s", len(tables), db_name)
            return tables
        except Exception as e:
            logger.error("Failed to fetch tables for database %s: %s", db_name, str(e))
            raise

    @_retry(max_retries=3)
    def get_table(self, db_name: str, table_name: str) -> Optional[HiveTable]:
        logger.info("Fetching table: %s.%s", db_name, table_name)
        if not self._connected:
            self._connect()
        if not self._client:
            logger.warning("Hive client not connected, returning None for table")
            return None
        try:
            table = self._client.get_table(db_name, table_name)
            hive_table = HiveTable(
                db_name=db_name,
                table_name=table_name,
                owner=getattr(table, "owner", None),
                create_time=getattr(table, "createTime", None),
                location=table.sd.location if table.sd else None,
                table_type=getattr(table, "tableType", None),
                partition_keys=[
                    {"name": col.name, "type": col.type, "comment": getattr(col, "comment", "") or ""}
                    for col in getattr(table, "partitionKeys", [])
                ],
                columns=[
                    {
                        "name": col.name,
                        "type": col.type,
                        "comment": getattr(col, "comment", "") or "",
                    }
                    for col in (table.sd.cols if table.sd else [])
                ],
                parameters=dict(getattr(table, "parameters", {}) or {}),
            )
            logger.info("Retrieved table metadata for %s.%s", db_name, table_name)
            return hive_table
        except Exception as e:
            logger.error("Failed to fetch table %s.%s: %s", db_name, table_name, str(e))
            return None

    def get_table_schema(self, db_name: str, table_name: str) -> List[Dict[str, Any]]:
        logger.info("Fetching schema for table: %s.%s", db_name, table_name)
        table = self.get_table(db_name, table_name)
        if not table:
            return []
        schema = []
        for idx, col in enumerate(table.columns):
            schema.append(
                {
                    "column_name": col["name"],
                    "data_type": col["type"],
                    "comment": col.get("comment", ""),
                    "is_nullable": True,
                    "position": idx,
                }
            )
        logger.info("Retrieved %d columns for %s.%s", len(schema), db_name, table_name)
        return schema

    @_retry(max_retries=3)
    def get_partitions(self, db_name: str, table_name: str) -> List[HivePartition]:
        logger.info("Fetching partitions for table: %s.%s", db_name, table_name)
        if not self._connected:
            self._connect()
        if not self._client:
            logger.warning("Hive client not connected, returning empty partition list")
            return []
        try:
            partitions = self._client.get_partitions(db_name, table_name, -1)
            result = []
            for p in partitions:
                result.append(
                    HivePartition(
                        values=list(getattr(p, "values", [])),
                        db_name=db_name,
                        table_name=table_name,
                        location=p.sd.location if p.sd else None,
                        create_time=getattr(p, "createTime", None),
                        parameters=dict(getattr(p, "parameters", {}) or {}),
                    )
                )
            logger.info("Found %d partitions for %s.%s", len(result), db_name, table_name)
            return result
        except Exception as e:
            logger.error("Failed to fetch partitions for %s.%s: %s", db_name, table_name, str(e))
            return []

    def get_table_location(self, db_name: str, table_name: str) -> Optional[str]:
        logger.info("Fetching location for table: %s.%s", db_name, table_name)
        table = self.get_table(db_name, table_name)
        if not table:
            return None
        return table.location

    def get_partition_keys(self, db_name: str, table_name: str) -> List[str]:
        logger.info("Fetching partition keys for table: %s.%s", db_name, table_name)
        table = self.get_table(db_name, table_name)
        if not table:
            return []
        return [pk["name"] for pk in table.partition_keys]
