import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors import HiveConnector, OSSConnector, TableStoreConnector
from app.models import (
    ColumnMeta,
    DataAsset,
    PartitionInfo,
    SyncHistory,
    get_session,
)
from app.utils import normalize_storage_path


logger = logging.getLogger(__name__)


_scheduler: Optional[AsyncIOScheduler] = None
_sync_service: Optional["SyncService"] = None


class SyncService:
    def __init__(self) -> None:
        self.hive = HiveConnector()
        self.oss = OSSConnector()
        self.ots = TableStoreConnector()
        logger.info("SyncService initialized")

    async def _create_sync_history(
        self,
        session: AsyncSession,
        source_type: str,
    ) -> SyncHistory:
        history = SyncHistory(
            source_type=source_type,
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(history)
        await session.commit()
        await session.refresh(history)
        return history

    async def _finish_sync_history(
        self,
        session: AsyncSession,
        history: SyncHistory,
        status: str,
        records_processed: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        history.status = status
        history.records_processed = records_processed
        history.error_message = error_message
        history.finished_at = datetime.utcnow()
        await session.commit()

    async def _upsert_asset(
        self,
        session: AsyncSession,
        source_type: str,
        name: str,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        storage_path: Optional[str] = None,
    ) -> DataAsset:
        normalized_path = normalize_storage_path(storage_path) if storage_path else None
        stmt = select(DataAsset).where(
            (DataAsset.source_type == source_type)
            & (
                (DataAsset.name == name)
                | (
                    (DataAsset.schema_name == schema_name)
                    & (DataAsset.table_name == table_name)
                    & (schema_name is not None)
                    & (table_name is not None)
                )
                | ((DataAsset.storage_path == normalized_path) & (normalized_path is not None))
            )
        )
        result = await session.execute(stmt)
        asset = result.scalar_one_or_none()
        if asset is None:
            asset = DataAsset(
                name=name,
                source_type=source_type,
                schema_name=schema_name,
                table_name=table_name,
                storage_path=normalized_path,
            )
            session.add(asset)
            await session.flush()
            logger.info("Created new data asset: %s (%s)", name, source_type)
        else:
            asset.name = name
            asset.schema_name = schema_name
            asset.table_name = table_name
            if normalized_path:
                asset.storage_path = normalized_path
            asset.last_sync_at = datetime.utcnow()
            logger.info("Updated existing data asset: %s (%s)", name, source_type)
        return asset

    async def sync_hive_metadata(self) -> Dict[str, Any]:
        logger.info("Starting Hive metadata sync")
        session_factory = get_session()
        async with session_factory() as session:
            history = await self._create_sync_history(session, "hive")
            records_processed = 0
            try:
                with self.hive:
                    databases = self.hive.get_all_databases()
                    for db in databases:
                        tables = self.hive.get_all_tables(db)
                        for table_name in tables:
                            try:
                                await self._sync_single_hive_table(session, db, table_name)
                                records_processed += 1
                            except Exception as e:
                                logger.error(
                                    "Error syncing hive table %s.%s: %s",
                                    db, table_name, str(e),
                                )
                await self._finish_sync_history(session, history, "success", records_processed)
                logger.info("Hive metadata sync completed: %d tables processed", records_processed)
                return {"status": "success", "records_processed": records_processed, "source": "hive"}
            except Exception as e:
                logger.error("Hive metadata sync failed: %s", str(e))
                await self._finish_sync_history(session, history, "failed", records_processed, str(e))
                return {"status": "failed", "records_processed": records_processed, "source": "hive", "error": str(e)}

    async def _sync_single_hive_table(
        self, session: AsyncSession, db_name: str, table_name: str
    ) -> None:
        table = self.hive.get_table(db_name, table_name)
        if not table:
            return
        asset = await self._upsert_asset(
            session,
            source_type="hive",
            name=f"{db_name}.{table_name}",
            schema_name=db_name,
            table_name=table_name,
            storage_path=table.location,
        )
        schema = self.hive.get_table_schema(db_name, table_name)
        if schema:
            await self._update_columns(session, asset.id, schema)
        partition_keys = self.hive.get_partition_keys(db_name, table_name)
        if partition_keys:
            asset.partition_key = ",".join(partition_keys)
            partitions = self.hive.get_partitions(db_name, table_name)
            await self._update_partitions(session, asset.id, partitions)
        try:
            total_size_param = table.parameters.get("totalSize") or table.parameters.get("numFiles")
            if total_size_param:
                asset.total_size_bytes = int(total_size_param)
            row_count = table.parameters.get("numRows")
            if row_count:
                asset.record_count = int(row_count)
            file_count = table.parameters.get("numFiles")
            if file_count:
                asset.file_count = int(file_count)
        except (ValueError, TypeError):
            pass
        await session.commit()

    async def _update_columns(
        self, session: AsyncSession, asset_id: int, schema: List[Dict[str, Any]]
    ) -> None:
        await session.execute(
            ColumnMeta.__table__.delete().where(ColumnMeta.asset_id == asset_id)
        )
        for col in schema:
            column_meta = ColumnMeta(
                asset_id=asset_id,
                column_name=col["column_name"],
                data_type=col["data_type"],
                comment=col.get("comment", ""),
                is_nullable=col.get("is_nullable", True),
                position=col.get("position", 0),
            )
            session.add(column_meta)

    async def _update_partitions(
        self, session: AsyncSession, asset_id: int, partitions: List[Any]
    ) -> None:
        await session.execute(
            PartitionInfo.__table__.delete().where(PartitionInfo.asset_id == asset_id)
        )
        for idx, p in enumerate(partitions):
            partition_name = ",".join(p.values) if hasattr(p, "values") else f"partition_{idx}"
            partition_value = ",".join(p.values) if hasattr(p, "values") else None
            location = getattr(p, "location", None)
            size_bytes = None
            record_count = None
            params = getattr(p, "parameters", {}) or {}
            try:
                total_size = params.get("totalSize")
                if total_size:
                    size_bytes = int(total_size)
                row_count = params.get("numRows")
                if row_count:
                    record_count = int(row_count)
            except (ValueError, TypeError):
                pass
            partition_info = PartitionInfo(
                asset_id=asset_id,
                partition_name=partition_name,
                partition_value=partition_value,
                location=location,
                size_bytes=size_bytes,
                record_count=record_count,
            )
            session.add(partition_info)

    async def sync_oss_metadata(self) -> Dict[str, Any]:
        logger.info("Starting OSS metadata sync")
        session_factory = get_session()
        async with session_factory() as session:
            history = await self._create_sync_history(session, "oss")
            records_processed = 0
            try:
                prefixes = self.oss.list_common_prefixes("")
                if not prefixes:
                    stats = self.oss.get_directory_size("")
                    await self._sync_oss_directory(session, "", stats)
                    records_processed = 1
                else:
                    for prefix in prefixes:
                        try:
                            stats = self.oss.get_directory_size(prefix)
                            await self._sync_oss_directory(session, prefix, stats)
                            records_processed += 1
                        except Exception as e:
                            logger.error("Error syncing OSS prefix %s: %s", prefix, str(e))
                await self._finish_sync_history(session, history, "success", records_processed)
                logger.info("OSS metadata sync completed: %d directories processed", records_processed)
                return {"status": "success", "records_processed": records_processed, "source": "oss"}
            except Exception as e:
                logger.error("OSS metadata sync failed: %s", str(e))
                await self._finish_sync_history(session, history, "failed", records_processed, str(e))
                return {"status": "failed", "records_processed": records_processed, "source": "oss", "error": str(e)}

    async def _sync_oss_directory(
        self, session: AsyncSession, prefix: str, stats: Dict[str, Any]
    ) -> None:
        name = prefix.rstrip("/") or "root"
        asset = await self._upsert_asset(
            session,
            source_type="oss",
            name=name,
            storage_path=prefix,
        )
        asset.total_size_bytes = stats.get("total_size_bytes", 0)
        asset.file_count = stats.get("file_count", 0)
        await session.commit()

    async def sync_tablestore_metadata(self) -> Dict[str, Any]:
        logger.info("Starting TableStore metadata sync")
        session_factory = get_session()
        async with session_factory() as session:
            history = await self._create_sync_history(session, "tablestore")
            records_processed = 0
            try:
                tables = self.ots.list_tables()
                for table_name in tables:
                    try:
                        await self._sync_single_tablestore_table(session, table_name)
                        records_processed += 1
                    except Exception as e:
                        logger.error(
                            "Error syncing TableStore table %s: %s",
                            table_name, str(e),
                        )
                await self._finish_sync_history(session, history, "success", records_processed)
                logger.info("TableStore metadata sync completed: %d tables processed", records_processed)
                return {"status": "success", "records_processed": records_processed, "source": "tablestore"}
            except Exception as e:
                logger.error("TableStore metadata sync failed: %s", str(e))
                await self._finish_sync_history(session, history, "failed", records_processed, str(e))
                return {"status": "failed", "records_processed": records_processed, "source": "tablestore", "error": str(e)}

    async def _sync_single_tablestore_table(
        self, session: AsyncSession, table_name: str
    ) -> None:
        schema = self.ots.get_table_schema(table_name)
        asset = await self._upsert_asset(
            session,
            source_type="tablestore",
            name=table_name,
            table_name=table_name,
        )
        if schema:
            await self._update_columns(session, asset.id, schema)
        row_count = self.ots.get_row_count(table_name)
        asset.record_count = row_count
        await session.commit()

    async def full_sync(self) -> Dict[str, Any]:
        logger.info("Starting full metadata sync")
        results = {}
        for sync_fn in [self.sync_hive_metadata, self.sync_oss_metadata, self.sync_tablestore_metadata]:
            source = sync_fn.__name__.replace("sync_", "").replace("_metadata", "")
            try:
                result = await sync_fn()
                results[source] = result
            except Exception as e:
                logger.error("Full sync step failed for %s: %s", source, str(e))
                results[source] = {"status": "failed", "error": str(e)}
        logger.info("Full sync completed: %s", results)
        return results


def get_sync_service() -> SyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    sync_service = get_sync_service()
    interval = settings.SYNC_INTERVAL_MINUTES

    async def scheduled_full_sync() -> None:
        logger.info("Scheduled full sync triggered")
        await sync_service.full_sync()

    _scheduler.add_job(
        scheduled_full_sync,
        "interval",
        minutes=interval,
        id="full_metadata_sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("APScheduler started with interval of %d minutes", interval)
    return _scheduler
