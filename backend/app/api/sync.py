from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CommonQueryParams, get_db
from app.models import SyncTask
from app.schemas import ApiResponse, PaginatedResponse, SyncStatusSchema, SyncTaskSchema

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/trigger", response_model=ApiResponse[SyncTaskSchema])
async def trigger_sync(
    task_type: str = "full",
    triggered_by: Optional[str] = "manual",
    db: AsyncSession = Depends(get_db),
) -> Any:
    running_query = select(SyncTask).where(SyncTask.status.in_(["pending", "running"]))
    running_result = await db.execute(running_query)
    running = running_result.scalar_one_or_none()

    if running:
        raise HTTPException(status_code=400, detail="A sync task is already running")

    task = SyncTask(
        task_type=task_type,
        status="pending",
        triggered_by=triggered_by,
        started_at=datetime.now(UTC),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return ApiResponse(data=SyncTaskSchema.model_validate(task))


@router.get("/history", response_model=PaginatedResponse[SyncTaskSchema])
async def get_sync_history(
    commons: CommonQueryParams = Depends(),
    status: Optional[str] = Query(default=None, description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(SyncTask)
    if status:
        query = query.where(SyncTask.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset(commons.skip).limit(commons.limit).order_by(SyncTask.id.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    return PaginatedResponse(
        data=[SyncTaskSchema.model_validate(t) for t in tasks],
        meta={"skip": commons.skip, "limit": commons.limit, "total": total},
    )


@router.get("/status", response_model=ApiResponse[SyncStatusSchema])
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
) -> Any:
    current_query = (
        select(SyncTask)
        .where(SyncTask.status.in_(["pending", "running"]))
        .order_by(SyncTask.id.desc())
        .limit(1)
    )
    current_result = await db.execute(current_query)
    current_task = current_result.scalar_one_or_none()

    last_query = (
        select(SyncTask)
        .where(SyncTask.status.in_(["completed", "failed"]))
        .order_by(SyncTask.id.desc())
        .limit(1)
    )
    last_result = await db.execute(last_query)
    last_task = last_result.scalar_one_or_none()

    return ApiResponse(
        data=SyncStatusSchema(
            is_running=current_task is not None,
            current_task=SyncTaskSchema.model_validate(current_task) if current_task else None,
            last_completed=SyncTaskSchema.model_validate(last_task) if last_task else None,
        )
    )
