from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CommonQueryParams, get_db
from app.models import AssetColumn, AssetPartition, DataAsset
from app.schemas import (
    AssetBase,
    AssetColumnSchema,
    AssetDetail,
    AssetPartitionSchema,
    AssetSearchResult,
    PaginatedResponse,
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=PaginatedResponse[AssetBase])
async def list_assets(
    commons: CommonQueryParams = Depends(),
    source_type: Optional[str] = Query(default=None, description="按来源类型过滤"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(DataAsset)
    conditions = []

    if source_type:
        conditions.append(DataAsset.source_type == source_type)
    if commons.keyword:
        keyword = f"%{commons.keyword}%"
        conditions.append(
            or_(
                DataAsset.name.ilike(keyword),
                DataAsset.fully_qualified_name.ilike(keyword),
                DataAsset.description.ilike(keyword),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset(commons.skip).limit(commons.limit).order_by(DataAsset.id.desc())
    result = await db.execute(query)
    assets = result.scalars().all()

    return PaginatedResponse(
        data=[AssetBase.model_validate(a) for a in assets],
        meta={"skip": commons.skip, "limit": commons.limit, "total": total},
    )


@router.get("/search", response_model=PaginatedResponse[AssetSearchResult])
async def search_assets(
    commons: CommonQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not commons.keyword:
        return PaginatedResponse(
            data=[],
            meta={"skip": commons.skip, "limit": commons.limit, "total": 0},
        )

    keyword = f"%{commons.keyword}%"

    table_query = (
        select(DataAsset)
        .where(
            or_(
                DataAsset.name.ilike(keyword),
                DataAsset.fully_qualified_name.ilike(keyword),
                DataAsset.description.ilike(keyword),
            )
        )
    )

    column_query = (
        select(AssetColumn)
        .where(
            or_(
                AssetColumn.name.ilike(keyword),
                AssetColumn.comment.ilike(keyword),
            )
        )
        .options(selectinload(AssetColumn.asset))
    )

    table_result = await db.execute(table_query)
    column_result = await db.execute(column_query)

    table_matches = table_result.scalars().all()
    column_matches = column_result.scalars().all()

    search_results: list[AssetSearchResult] = []

    for asset in table_matches:
        matched_text = None
        if commons.keyword and commons.keyword.lower() in asset.name.lower():
            matched_text = asset.name
            matched_type = "table_name"
        elif commons.keyword and commons.keyword.lower() in asset.fully_qualified_name.lower():
            matched_text = asset.fully_qualified_name
            matched_type = "fq_name"
        else:
            matched_text = asset.description or ""
            matched_type = "table_comment"

        search_results.append(
            AssetSearchResult(
                id=asset.id,
                name=asset.name,
                fully_qualified_name=asset.fully_qualified_name,
                source_type=asset.source_type,
                storage_layer=asset.storage_layer,
                description=asset.description,
                total_size_bytes=asset.total_size_bytes,
                file_count=asset.file_count,
                matched_type=matched_type,
                matched_text=matched_text,
            )
        )

    seen_asset_ids = {a.id for a in table_matches}
    for col in column_matches:
        if col.asset_id in seen_asset_ids:
            continue
        seen_asset_ids.add(col.asset_id)
        matched_type = "column_name" if commons.keyword and commons.keyword.lower() in col.name.lower() else "column_comment"
        search_results.append(
            AssetSearchResult(
                id=col.asset.id,
                name=col.asset.name,
                fully_qualified_name=col.asset.fully_qualified_name,
                source_type=col.asset.source_type,
                storage_layer=col.asset.storage_layer,
                description=col.asset.description,
                total_size_bytes=col.asset.total_size_bytes,
                file_count=col.asset.file_count,
                matched_type=matched_type,
                matched_text=f"{col.name}: {col.comment or ''}",
            )
        )

    total = len(search_results)
    paged = search_results[commons.skip : commons.skip + commons.limit]

    return PaginatedResponse(
        data=paged,
        meta={"skip": commons.skip, "limit": commons.limit, "total": total},
    )


@router.get("/{asset_id}", response_model=AssetDetail)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = (
        select(DataAsset)
        .where(DataAsset.id == asset_id)
        .options(
            selectinload(DataAsset.columns),
            selectinload(DataAsset.partitions),
        )
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetDetail.model_validate(asset)


@router.get("/{asset_id}/columns", response_model=list[AssetColumnSchema])
async def get_asset_columns(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = (
        select(AssetColumn)
        .where(AssetColumn.asset_id == asset_id)
        .order_by(AssetColumn.ordinal_position.asc())
    )
    result = await db.execute(query)
    columns = result.scalars().all()
    return [AssetColumnSchema.model_validate(c) for c in columns]


@router.get("/{asset_id}/partitions", response_model=list[AssetPartitionSchema])
async def get_asset_partitions(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = (
        select(AssetPartition)
        .where(AssetPartition.asset_id == asset_id)
        .order_by(AssetPartition.name.asc())
    )
    result = await db.execute(query)
    partitions = result.scalars().all()
    return [AssetPartitionSchema.model_validate(p) for p in partitions]
