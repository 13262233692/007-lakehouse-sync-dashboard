import gc
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

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

    @property
    def name(self) -> str:
        return ",".join(self.values)

    @property
    def partition_values(self) -> str:
        return self.name


@dataclass
class PartitionBatch:
    partitions: List[HivePartition]
    batch_index: int
    total_batches: int
    has_more: bool
    memory_safe_estimate_bytes: int = 0


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
                        sleep_time = delay * (attempt + 1)
                        logger.info("Sleeping %.1fs before retry", sleep_time)
                        time.sleep(sleep_time)
                        gc.collect()
            raise last_exception
        return wrapper
    return decorator


class HiveConnector:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        batch_size: int = 100,
        max_partitions: Optional[int] = None,
        max_retries: int = 3,
    ) -> None:
        self.host = host or settings.HIVE_METASTORE_HOST
        self.port = port or settings.HIVE_METASTORE_PORT
        self.batch_size = batch_size
        self.max_partitions = max_partitions or settings.HIVE_MAX_PARTITIONS
        self.max_retries = max_retries
        self._client = None
        self._transport = None
        self._connected = False
        logger.info(
            "HiveConnector initialized for %s:%d (batch_size=%d, max_partitions=%s)",
            self.host, self.port, self.batch_size, self.max_partitions
        )

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
                gc.collect()

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

    @_retry(max_retries=3)
    def get_partition_names(
        self,
        db_name: str,
        table_name: str,
        max_parts: int = -1,
        partition_filter: Optional[str] = None,
    ) -> List[str]:
        logger.info(
            "Fetching partition names for %s.%s (max_parts=%s, filter=%s)",
            db_name, table_name, max_parts, partition_filter
        )
        if not self._connected:
            self._connect()
        if not self._client:
            logger.warning("Hive client not connected, returning empty partition name list")
            return []
        try:
            if partition_filter:
                names = self._client.get_partition_names_ps(
                    db_name, table_name, partition_filter, max_parts
                )
            else:
                names = self._client.get_partition_names(db_name, table_name, max_parts)
            logger.info("Found %d partition names for %s.%s", len(names), db_name, table_name)
            return names
        except Exception as e:
            logger.error(
                "Failed to fetch partition names for %s.%s: %s",
                db_name, table_name, str(e)
            )
            raise

    @_retry(max_retries=3)
    def get_partitions_by_names(
        self,
        db_name: str,
        table_name: str,
        partition_names: List[str],
    ) -> List[HivePartition]:
        logger.info(
            "Fetching %d partitions by names for %s.%s",
            len(partition_names), db_name, table_name
        )
        if not self._connected:
            self._connect()
        if not self._client or not partition_names:
            return []
        try:
            partitions = self._client.get_partitions_by_names(
                db_name, table_name, partition_names
            )
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
            logger.info("Retrieved %d partitions for %s.%s", len(result), db_name, table_name)
            return result
        except Exception as e:
            logger.error(
                "Failed to fetch partitions by names for %s.%s: %s",
                db_name, table_name, str(e)
            )
            raise

    @_retry(max_retries=3)
    def get_partition_by_name(
        self,
        db_name: str,
        table_name: str,
        partition_name: str,
    ) -> Optional[HivePartition]:
        if not self._connected:
            self._connect()
        if not self._client:
            return None
        try:
            values = partition_name.split(",") if partition_name else []
            partition = self._client.get_partition(db_name, table_name, values)
            return HivePartition(
                values=list(getattr(partition, "values", [])),
                db_name=db_name,
                table_name=table_name,
                location=partition.sd.location if partition.sd else None,
                create_time=getattr(partition, "createTime", None),
                parameters=dict(getattr(partition, "parameters", {}) or {}),
            )
        except Exception as e:
            logger.warning(
                "Failed to fetch single partition %s for %s.%s: %s",
                partition_name, db_name, table_name, str(e)
            )
            return None

    def _parse_date_from_partition_name(
        self,
        partition_name: str,
        partition_keys: List[str],
    ) -> Optional[date]:
        parts = partition_name.split("/") if "/" in partition_name else partition_name.split(",")
        date_parts = {}
        for part in parts:
            if "=" in part:
                key, _, value = part.partition("=")
                date_parts[key.strip()] = value.strip()

        for key in partition_keys:
            value = date_parts.get(key, "")
            if key.lower() in ("dt", "date", "partition_date", "day", "ds", "d"):
                try:
                    if len(value) == 8 and value.isdigit():
                        return datetime.strptime(value, "%Y%m%d").date()
                    elif len(value) == 10:
                        return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    continue
        return None

    def _build_date_filter(
        self,
        partition_keys: List[str],
        start_date: Optional[Union[date, datetime, str]],
        end_date: Optional[Union[date, datetime, str]],
    ) -> Optional[str]:
        if not start_date and not end_date:
            return None

        def _to_date(d: Optional[Union[date, datetime, str]]) -> Optional[date]:
            if d is None:
                return None
            if isinstance(d, str):
                for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(d, fmt).date()
                    except ValueError:
                        continue
                return None
            if isinstance(d, datetime):
                return d.date()
            return d

        start = _to_date(start_date)
        end = _to_date(end_date)

        dt_key = None
        for key in partition_keys:
            if key.lower() in ("dt", "date", "partition_date", "day", "ds", "d"):
                dt_key = key
                break

        if not dt_key:
            logger.warning("No date partition key found, cannot apply date filter")
            return None

        conditions = []
        if start:
            conditions.append(f"{dt_key} >= \"{start.strftime('%Y-%m-%d')}\"")
        if end:
            conditions.append(f"{dt_key} <= \"{end.strftime('%Y-%m-%d')}\"")

        return " AND ".join(conditions) if conditions else None

    def _apply_memory_protection(
        self,
        partition_names: List[str],
        db_name: str,
        table_name: str,
    ) -> List[str]:
        total = len(partition_names)
        if self.max_partitions and total > self.max_partitions:
            logger.warning(
                "Memory protection triggered: table %s.%s has %d partitions, "
                "exceeds limit %d. Only latest %d partitions will be synced",
                db_name, table_name, total, self.max_partitions, self.max_partitions
            )
            return partition_names[-self.max_partitions:]
        return partition_names

    def iter_partition_names_batched(
        self,
        db_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
        start_date: Optional[Union[date, datetime, str]] = None,
        end_date: Optional[Union[date, datetime, str]] = None,
        partition_keys: Optional[List[str]] = None,
    ) -> Generator[List[str], None, int]:
        logger.info(
            "Starting batched partition name iteration for %s.%s",
            db_name, table_name
        )

        if partition_keys is None:
            partition_keys = self.get_partition_keys(db_name, table_name)

        if not partition_keys:
            logger.info("Table %s.%s is not partitioned", db_name, table_name)
            yield from []
            return 0

        if start_date or end_date:
            partition_filter = self._build_date_filter(
                partition_keys, start_date, end_date
            )
            if partition_filter:
                logger.info("Using date filter: %s", partition_filter)

        all_names = self.get_partition_names(
            db_name, table_name, max_parts=-1, partition_filter=partition_filter
        )

        all_names = self._apply_memory_protection(all_names, db_name, table_name)

        total = len(all_names)
        logger.info("Total partitions to process: %d", total)

        for i in range(0, total, self.batch_size):
            batch = all_names[i:i + self.batch_size]
            yield batch

        return total

    def iter_partitions_batched(
        self,
        db_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
        start_date: Optional[Union[date, datetime, str]] = None,
        end_date: Optional[Union[date, datetime, str]] = None,
        partition_keys: Optional[List[str]] = None,
        batch_sleep: float = 0.1,
    ) -> Generator[PartitionBatch, None, int]:
        logger.info(
            "Starting batched partition iteration for %s.%s",
            db_name, table_name
        )

        if partition_keys is None:
            partition_keys = self.get_partition_keys(db_name, table_name)

        name_iter = self.iter_partition_names_batched(
            db_name, table_name,
            partition_filter=partition_filter,
            start_date=start_date, end_date=end_date,
            partition_keys=partition_keys,
        )

        total_batches = 0
        processed = 0
        all_batches = []

        for batch_names in name_iter:
            all_batches.append(batch_names)

        if not all_batches:
            logger.info("No partitions to process for %s.%s", db_name, table_name)
            yield from []
            return 0

        total_batches = len(all_batches)

        for batch_idx, batch_names in enumerate(all_batches):
            partitions = self.get_partitions_by_names(db_name, table_name, batch_names)

            estimated_mem = len(partitions) * 8192

            has_more = batch_idx < total_batches - 1

            batch = PartitionBatch(
                partitions=partitions,
                batch_index=batch_idx,
                total_batches=total_batches,
                has_more=has_more,
                memory_safe_estimate_bytes=estimated_mem,
            )

            yield batch

            processed += len(partitions)

            if has_more and batch_sleep > 0:
                time.sleep(batch_sleep)
                gc.collect()

        logger.info(
            "Completed iteration for %s.%s: %d partitions in %d batches",
            db_name, table_name, processed, total_batches
        )

        return processed

    def iter_partitions(
        self,
        db_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
        start_date: Optional[Union[date, datetime, str]] = None,
        end_date: Optional[Union[date, datetime, str]] = None,
        partition_keys: Optional[List[str]] = None,
        batch_sleep: float = 0.1,
    ) -> Generator[HivePartition, None, int]:
        batch_iter = self.iter_partitions_batched(
            db_name, table_name,
            partition_filter=partition_filter,
            start_date=start_date, end_date=end_date,
            partition_keys=partition_keys,
            batch_sleep=batch_sleep,
        )

        total = 0
        for batch in batch_iter:
            for partition in batch.partitions:
                yield partition
                total += 1
        return total

    def get_partitions(
        self,
        db_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
        start_date: Optional[Union[date, datetime, str]] = None,
        end_date: Optional[Union[date, datetime, str]] = None,
        partition_keys: Optional[List[str]] = None,
        batch_sleep: float = 0.1,
    ) -> List[HivePartition]:
        logger.warning(
            "get_partitions() called for %s.%s - for large tables "
            "use iter_partitions() to avoid OOM. "
            "Will use batched fetching internally but still loads all into memory.",
            db_name, table_name
        )

        all_partitions: List[HivePartition] = []
        for batch in self.iter_partitions_batched(
            db_name, table_name,
            partition_filter=partition_filter,
            start_date=start_date, end_date=end_date,
            partition_keys=partition_keys,
            batch_sleep=batch_sleep,
        ):
            all_partitions.extend(batch.partitions)
            logger.info(
                "Batch %d/%d: accumulated %d partitions",
                batch.batch_index + 1, batch.total_batches, len(all_partitions)
            )
        return all_partitions

    def get_partition_count(
        self,
        db_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
    ) -> int:
        names = self.get_partition_names(
            db_name, table_name, max_parts=-1, partition_filter=partition_filter
        )
        return len(names)
