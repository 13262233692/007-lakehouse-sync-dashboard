from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ApiResponse
from app.services.lineage_service import LineageService


router = APIRouter(prefix="/lineage", tags=["Lineage"])

_lineage_service: Optional[LineageService] = None


def get_lineage_service() -> LineageService:
    global _lineage_service
    if _lineage_service is None:
        _lineage_service = LineageService()
    return _lineage_service


@router.get("/force-graph", response_model=ApiResponse)
async def get_force_graph(
    force_refresh: bool = Query(
        default=False,
        description="Force refresh lineage cache"
    ),
):
    try:
        service = get_lineage_service()
        data = service.get_force_graph_data(force_refresh=force_refresh)
        return ApiResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dag", response_model=ApiResponse)
async def get_dag(
    force_refresh: bool = Query(
        default=False,
        description="Force refresh lineage cache"
    ),
):
    try:
        service = get_lineage_service()
        dag = service.build_lineage_dag(force_refresh=force_refresh)
        return ApiResponse(data=dag.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refresh-delays", response_model=ApiResponse)
async def get_refresh_delays(
    force_refresh: bool = Query(
        default=False,
        description="Force refresh lineage cache"
    ),
):
    try:
        service = get_lineage_service()
        dag = service.build_lineage_dag(force_refresh=force_refresh)
        delays = service.calculate_refresh_delays(dag)
        return ApiResponse(data=delays)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_fqn:path}", response_model=ApiResponse)
async def get_node_subgraph(
    node_fqn: str,
    depth: int = Query(default=3, ge=1, le=10),
):
    try:
        service = get_lineage_service()
        dag = service.build_lineage_dag()
        if node_fqn not in dag.nodes:
            raise HTTPException(status_code=404, detail=f"Node not found: {node_fqn}")
        subgraph = dag.get_subgraph(node_fqn, depth=depth)
        return ApiResponse(data=subgraph.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
