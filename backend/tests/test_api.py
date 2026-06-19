import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.config import settings
from app.database import Base, AsyncSessionLocal, engine
from app.main import create_app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def test_client():
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    test_engine = engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_health_check(test_client):
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_assets_empty(test_client):
    response = await test_client.get("/api/assets")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"] == []
    assert data["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_get_asset_not_found(test_client):
    response = await test_client.get("/api/assets/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_asset_columns_empty(test_client):
    response = await test_client.get("/api/assets/999/columns")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_asset_partitions_empty(test_client):
    response = await test_client.get("/api/assets/999/partitions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_assets_no_keyword(test_client):
    response = await test_client.get("/api/assets/search")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_stats_overview(test_client):
    response = await test_client.get("/api/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["total_size_bytes"] == 0
    assert data["data"]["total_tables"] == 0
    assert data["data"]["total_files"] == 0


@pytest.mark.asyncio
async def test_stats_tree(test_client):
    response = await test_client.get("/api/stats/tree")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_stats_trend(test_client):
    response = await test_client.get("/api/stats/trend")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 30


@pytest.mark.asyncio
async def test_stats_source_breakdown(test_client):
    response = await test_client.get("/api/stats/source-breakdown")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_sync_status(test_client):
    response = await test_client.get("/api/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["is_running"] is False


@pytest.mark.asyncio
async def test_sync_history_empty(test_client):
    response = await test_client.get("/api/sync/history")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_sync_trigger(test_client):
    response = await test_client.post("/api/sync/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "pending"
    assert data["data"]["task_type"] == "full"
