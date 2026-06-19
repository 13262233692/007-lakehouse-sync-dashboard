import gc
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors import HiveConnector, OSSConnector, TableStoreConnector
from app.connectors.hive_connector import HivePartition, PartitionBatch
from app.database import AsyncSessionLocal, get_session
from app.models import (
    AssetColumn,
    AssetPartition,
    DataAsset,
    SyncTask,
    StorageTrend,
)
from app.utils import normalize_storage_path


logger = logging.getLogger(__name__)


_scheduler: Optional[AsyncIOScheduler] = None
_sync_service: Optional["SyncService"] = None


class SyncService:
    def __init__(self) -> None:
        self.hive = HiveConnector(
            batch_size=settings.HIVE_BATCH_SIZE,
            max_partitions=settings.HIVE_MAX_PARTITIONS,
        )
        self.oss = OSSConnector()
        self.ots = TableStoreConnector()
        self.batch_sleep = settings.HIVE_BATCH_SLEEP
        logger.info(
            "SyncService initialized (hive_batch_size=%d, hive_max_partitions=%d)",
            settings.HIVE_BATCH_SIZE, settings.HIVE_MAX_PARTITIONS
        )

    async def _create_sync_history(
        self,
        session: AsyncSession,
        source_type: str,
    ) -> SyncTask:
        history = SyncTask(
            task_type=source_type,
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
        history: SyncTask,
        status: str,
        records_processed: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        history.status = status
        history.processed_assets = records_processed
        history.error_message = error_message
        history.completed_at = datetime.utcnow()
        await session.commit()

    async def _upsert_asset(
        self,
        session: AsyncSession,
        source_type: str,
        name: str,
        fully_qualified_name: str,
        storage_layer: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        storage_path: Optional[str] = None,
        table_type: Optional[str] = None,
        location: Optional[str] = None,
        format: Optional[str] = None,
        description: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> DataAsset:
        normalized_path = normalize_storage_path(storage_path) if storage_path else None
        stmt = select(DataAsset).where(
            (DataAsset.source_type == source_type)
            & (DataAsset.fully_qualified_name == fully_qualified_name)
        )
        result = await session.execute(stmt)
        asset = result.scalar_one_or_none()
        if asset is None:
            asset = DataAsset(
                name=name,
                fully_qualified_name=fully_qualified_name,
                source_type=source_type,
                storage_layer=storage_layer,
                database_name=database_name,
                schema_name=schema_name,
                table_name=table_name,
                location=location,
                format=format,
                description=description,
                owner=owner,
                last_updated_at=datetime.utcnow(),
            )
            session.add(asset)
            await session.flush()
            logger.info("Created new data asset: %s (%s)", fully_qualified_name, source_type)
        else:
            asset.name = name
            asset.database_name = database_name
            asset.schema_name = schema_name
            asset.table_name = table_name
            asset.location = location or asset.location
            asset.format = format or asset.format
            asset.description = description or asset.description
            asset.owner = owner or asset.owner
            asset.last_updated_at = datetime.utcnow()
            logger.info("Updated existing data asset: %s (%s)", fully_qualified_name, source_type)
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
                await self._finish_sync_history(session, history, "completed", records_processed)
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

        fully_qualified_name = f"hive.{db_name}.{table_name}"
        asset = await self._upsert_asset(
            session,
            source_type="hive",
            name=table_name,
            fully_qualified_name=fully_qualified_name,
            storage_layer="hive",
            database_name=db_name,
            schema_name=db_name,
            table_name=table_name,
            storage_path=table.location,
            table_type=table.table_type,
            location=table.location,
            format=table.parameters.get("serialization.lib"),
            description=table.parameters.get("comment"),
            owner=table.owner,
        )

        schema = self.hive.get_table_schema(db_name, table_name)
        if schema:
            await self._update_columns(session, asset.id, schema)
            asset.column_count = len(schema)

        partition_keys = self.hive.get_partition_keys(db_name, table_name)
        if partition_keys:
            asset.partition_count = await self._update_partitions_streaming(
                session, asset.id, db_name, table_name, partition_keys
            )
        else:
            asset.partition_count = 0

        try:
            total_size_param = table.parameters.get("totalSize")
            if total_size_param:
                asset.total_size_bytes = int(total_size_param)
            row_count = table.parameters.get("numRows")
            if row_count:
                asset.row_count = int(row_count)
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
            AssetColumn.__table__.delete().where(AssetColumn.asset_id == asset_id)
        )
        for col in schema:
            column_meta = AssetColumn(
                asset_id=asset_id,
                name=col["column_name"],
                data_type=col["data_type"],
                comment=col.get("comment", ""),
                is_nullable=col.get("is_nullable", True),
                is_partition=False,
                ordinal_position=col.get("position", 0),
            )
            session.add(column_meta)

    async def _update_partitions_streaming(
        self,
        session: AsyncSession,
        asset_id: int,
        db_name: str,
        table_name: str,
        partition_keys: List[str],
    ) -> int:
        logger.info(
            "Starting streaming partition sync for %s.%s (asset_id=%d)",
            db_name, table_name, asset_id
        )

        partition_count_result = await session.execute(
            select(func.count(AssetPartition.id))
            .where(AssetPartition.asset_id == asset_id)
        )
        existing_count = partition_count_result.scalar_one() or 0
        logger.info(
            "Found %d existing partitions for asset_id=%d",
            existing_count, asset_id
        )

        total_processed = 0
        total_size = 0
        total_files = 0

        try:
            partition_count = self.hive.get_partition_count(db_name, table_name)
            logger.info(
                "Table %s.%s has %d total partitions in Hive Metastore",
                db_name, table_name, partition_count
            )

            if partition_count > settings.HIVE_MAX_PARTITIONS:
                logger.warning(
                    "Large table detected: %s.%s has %d partitions (limit=%d). "
                    "Using incremental sync for last %d days.",
                    db_name, table_name, partition_count,
                    settings.HIVE_MAX_PARTITIONS,
                    settings.HIVE_MAX_PARTITIONS
                )
                start_date = datetime.utcnow() - timedelta(days=min(partition_count, 365))
                end_date = datetime.utcnow()
            else:
                start_date = None
                end_date = None

            batch_iter = self.hive.iter_partitions_batched(
                db_name, table_name,
                partition_keys=partition_keys,
                start_date=start_date,
                end_date=end_date,
                batch_sleep=self.batch_sleep,
            )

            for batch in batch_iter:
                batch_size = len(batch.partitions)
                logger.info(
                    "Processing partition batch %d/%d for %s.%s: %d partitions "
                    "(estimated mem: %s)",
                    batch.batch_index + 1, batch.total_batches,
                    db_name, table_name, batch_size,
                    bytes_to_human(batch.memory_safe_estimate_bytes)
                )

                await self._process_partition_batch(
                    session, asset_id, batch.partitions
                )

                total_processed += batch_size
                for p in batch.partitions:
                    try:
                        total_size += int(p.parameters.get("totalSize", 0) or 0)
                        total_files += int(p.parameters.get("numFiles", 0) or 0)
                    except (ValueError, TypeError):
                        pass

                if batch.batch_index % 10 == 0 and batch.has_more:
                    logger.info(
                        "Progress: %d/%d partitions processed for %s.%s",
                        total_processed, partition_count, db_name, table_name
                    )

                gc.collect()

        except Exception as e:
            logger.error(
                "Error during streaming partition sync for %s.%s: %s",
                db_name, table_name, str(e), exc_info=True
            )
            raise

        logger.info(
            "Completed streaming partition sync for %s.%s: "
            "processed %d partitions, total_size=%s, total_files=%d",
            db_name, table_name, total_processed,
            bytes_to_human(total_size), total_files
        )

        if total_processed > 0:
            update_stmt = (
                DataAsset.__table__.update()
                .where(DataAsset.id == asset_id)
                .values(
                    total_size_bytes=total_size,
                    file_count=total_files,
                    partition_count=total_processed,
                    last_updated_at=datetime.utcnow(),
                )
            )
            await session.execute(update_stmt)

        return total_processed

    async def _process_partition_batch(
        self,
        session: AsyncSession,
        asset_id: int,
        partitions: List[HivePartition],
    ) -> None:
        partition_names = [p.name for p in partitions]

        if not partition_names:
            return

        delete_stmt = (
            AssetPartition.__table__.delete()
            .where(AssetPartition.asset_id == asset_id)
            .where(AssetPartition.name.in_(partition_names))
        )
        delete_result = await session.execute(delete_stmt)
        deleted = delete_result.rowcount or 0
        if deleted > 0:
            logger.debug("Deleted %d existing partitions for upsert", deleted)

        for p in partitions:
            partition_name = p.name
            partition_value = p.partition_values
            location = p.location
            size_bytes = None
            row_count = None
            file_count = None

            params = p.parameters or {}
            try:
                total_size = params.get("totalSize")
                if total_size:
                    size_bytes = int(total_size)
                row_count = params.get("numRows")
                if row_count:
                    row_count = int(row_count)
                num_files = params.get("numFiles")
                if num_files:
                    file_count = int(num_files)
            except (ValueError, TypeError):
                pass

            partition_info = AssetPartition(
                asset_id=asset_id,
                name=partition_name,
                value=partition_value,
                size_bytes=size_bytes or 0,
                file_count=file_count or 0,
                row_count=row_count,
                location=location,
                created_at=datetime.fromtimestamp(p.create_time) if p.create_time else None,
                last_modified_at=datetime.fromtimestamp(p.create_time) if p.create_time else None,
            )
            session.add(partition_info)

        await session.commit()

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
                await self._finish_sync_history(session, history, "completed", records_processed)
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
        fully_qualified_name = f"oss.{name}"
        asset = await self._upsert_asset(
            session,
            source_type="oss",
            name=name,
            fully_qualified_name=fully_qualified_name,
            storage_layer="oss",
            storage_path=prefix,
            location=prefix,
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
                await self._finish_sync_history(session, history, "completed", records_processed)
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
        fully_qualified_name = f"tablestore.{table_name}"
        asset = await self._upsert_asset(
            session,
            source_type="tablestore",
            name=table_name,
            fully_qualified_name=fully_qualified_name,
            storage_layer="tablestore",
            table_name=table_name,
        )
        if schema:
            await self._update_columns(session, asset.id, schema)
            asset.column_count = len(schema)
        row_count = self.ots.get_row_count(table_name)
        asset.row_count = row_count
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
