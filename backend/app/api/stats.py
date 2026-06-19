from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import AssetPartition, DataAsset, StorageTrend
from app.schemas import (
    ApiResponse,
    OverviewStats,
    SourceBreakdownItem,
    StorageLayerStats,
    TreeNode,
    TrendPoint,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=ApiResponse[OverviewStats])
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
) -> Any:
    total_size_query = select(func.coalesce(func.sum(DataAsset.total_size_bytes), 0))
    total_tables_query = select(func.count(DataAsset.id))
    total_files_query = select(func.coalesce(func.sum(DataAsset.file_count), 0))

    total_size_result = await db.execute(total_size_query)
    total_tables_result = await db.execute(total_tables_query)
    total_files_result = await db.execute(total_files_query)

    total_size = total_size_result.scalar_one()
    total_tables = total_tables_result.scalar_one()
    total_files = total_files_result.scalar_one()

    layer_query = (
        select(
            DataAsset.storage_layer,
            func.coalesce(func.sum(DataAsset.total_size_bytes), 0).label("total_size"),
            func.count(DataAsset.id).label("total_tables"),
            func.coalesce(func.sum(DataAsset.file_count), 0).label("total_files"),
        )
        .group_by(DataAsset.storage_layer)
    )
    layer_result = await db.execute(layer_query)
    layers = layer_result.all()

    storage_layers: list[StorageLayerStats] = []
    for row in layers:
        size = row.total_size or 0
        percentage = round((size / total_size * 100) if total_size > 0 else 0.0, 2)
        storage_layers.append(
            StorageLayerStats(
                name=row.storage_layer,
                total_size_bytes=size,
                total_tables=row.total_tables or 0,
                total_files=row.total_files or 0,
                percentage=percentage,
            )
        )

    return ApiResponse(
        data=OverviewStats(
            total_size_bytes=total_size,
            total_tables=total_tables,
            total_files=total_files,
            storage_layers=storage_layers,
        )
    )


@router.get("/tree", response_model=ApiResponse[list[TreeNode]])
async def get_tree_data(
    db: AsyncSession = Depends(get_db),
) -> Any:
    assets_query = select(DataAsset).options()
    partitions_query = select(AssetPartition)

    assets_result = await db.execute(assets_query)
    partitions_result = await db.execute(partitions_query)

    assets = assets_result.scalars().all()
    partitions = partitions_result.scalars().all()

    partitions_by_asset: dict[int, list] = defaultdict(list)
    for p in partitions:
        partitions_by_asset[p.asset_id].append(p)

    layer_map: dict[str, TreeNode] = {}
    for asset in assets:
        layer_name = asset.storage_layer
        if layer_name not in layer_map:
            layer_map[layer_name] = TreeNode(
                name=layer_name, type="storage_layer", children=[]
            )
        layer_node = layer_map[layer_name]

        db_name = asset.database_name or "(default)"
        db_node = next(
            (c for c in layer_node.children if c.name == db_name and c.type == "database"),
            None,
        )
        if db_node is None:
            db_node = TreeNode(name=db_name, type="database", children=[])
            layer_node.children.append(db_node)

        table_node = TreeNode(
            name=asset.name,
            type="table",
            size_bytes=asset.total_size_bytes,
            file_count=asset.file_count,
            children=[],
        )

        for p in partitions_by_asset.get(asset.id, []):
            table_node.children.append(
                TreeNode(
                    name=p.name,
                    type="partition",
                    size_bytes=p.size_bytes,
                    file_count=p.file_count,
                    children=[],
                )
            )
            table_node.size_bytes += p.size_bytes
            table_node.file_count += p.file_count

        db_node.children.append(table_node)
        db_node.size_bytes += table_node.size_bytes
        db_node.file_count += table_node.file_count
        layer_node.size_bytes += table_node.size_bytes
        layer_node.file_count += table_node.file_count

    return ApiResponse(data=list(layer_map.values()))


@router.get("/trend", response_model=ApiResponse[list[TrendPoint]])
async def get_trend_data(
    db: AsyncSession = Depends(get_db),
) -> Any:
    today = date.today()
    date_list = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]

    trend_query = (
        select(
            StorageTrend.stat_date,
            func.coalesce(func.sum(StorageTrend.total_size_bytes), 0).label("total_size"),
            func.coalesce(func.sum(StorageTrend.total_files), 0).label("total_files"),
            func.coalesce(func.sum(StorageTrend.total_tables), 0).label("total_tables"),
        )
        .where(StorageTrend.stat_date.in_(date_list))
        .group_by(StorageTrend.stat_date)
    )
    trend_result = await db.execute(trend_query)
    rows = {row.stat_date: row for row in trend_result.all()}

    trends: list[TrendPoint] = []
    for d in date_list:
        row = rows.get(d)
        if row:
            trends.append(
                TrendPoint(
                    stat_date=d,
                    total_size_bytes=row.total_size or 0,
                    total_files=row.total_files or 0,
                    total_tables=row.total_tables or 0,
                )
            )
        else:
            trends.append(
                TrendPoint(
                    stat_date=d,
                    total_size_bytes=0,
                    total_files=0,
                    total_tables=0,
                )
            )

    return ApiResponse(data=trends)


@router.get("/source-breakdown", response_model=ApiResponse[list[SourceBreakdownItem]])
async def get_source_breakdown(
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = (
        select(
            DataAsset.source_type,
            func.coalesce(func.sum(DataAsset.total_size_bytes), 0).label("total_size"),
            func.count(DataAsset.id).label("total_tables"),
            func.coalesce(func.sum(DataAsset.file_count), 0).label("total_files"),
        )
        .group_by(DataAsset.source_type)
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[SourceBreakdownItem] = []
    for row in rows:
        items.append(
            SourceBreakdownItem(
                source_type=row.source_type,
                total_size_bytes=row.total_size or 0,
                total_tables=row.total_tables or 0,
                total_files=row.total_files or 0,
            )
        )

    return ApiResponse(data=items)
