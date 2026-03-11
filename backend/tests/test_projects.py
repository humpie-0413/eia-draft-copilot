"""Project CRUD API 통합 테스트.

실행 전 PostgreSQL + PostGIS가 필요합니다:
  createdb eia_copilot_test
  psql eia_copilot_test -c "CREATE EXTENSION IF NOT EXISTS postgis"

  cd backend && pytest tests/ -v
"""
import pytest
from httpx import AsyncClient

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [126.9780, 37.5665],
            [126.9790, 37.5665],
            [126.9790, 37.5675],
            [126.9780, 37.5675],
            [126.9780, 37.5665],
        ]
    ],
}


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "테스트 도로 사업",
            "description": "서울~세종 고속도로",
            "project_type": "road",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "테스트 도로 사업"
    assert data["status"] == "draft"
    assert data["project_type"] == "road"
    assert data["geometry"]["type"] == "Polygon"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_project_minimal(client: AsyncClient):
    """name만으로 생성 가능 (geometry, description 선택)."""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "최소 프로젝트"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "최소 프로젝트"
    assert data["geometry"] is None


@pytest.mark.asyncio
async def test_create_project_validation_error(client: AsyncClient):
    """name 없이 생성 시 422 에러."""
    resp = await client.post("/api/v1/projects", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    # 2개 생성
    await client.post("/api/v1/projects", json={"name": "프로젝트 A"})
    await client.post("/api/v1/projects", json={"name": "프로젝트 B"})

    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "조회 테스트"})
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "조회 테스트"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "수정 전", "project_type": "road"},
    )
    project_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "name": "수정 후",
            "status": "in_progress",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "수정 후"
    assert data["status"] == "in_progress"
    assert data["geometry"]["type"] == "Polygon"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "삭제 대상"})
    project_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 204

    # 삭제 후 조회 시 404
    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404
