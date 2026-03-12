"""Post-1 통계 엔진 테스트.

통계 계산 정확성, 필터링 동작, scaffold 출력 변경을 검증한다.

실행 방법:
  cd backend
  pytest tests/test_statistics.py -v --tb=short
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient

# ── 테스트 데이터 ──

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.0, 37.5],
            [127.1, 37.5],
            [127.1, 37.6],
            [127.0, 37.6],
            [127.0, 37.5],
        ]
    ],
}

# 대기질 수치 데이터 (최근 1년 이내)
AIR_EVIDENCES_RECENT = [
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "45",
        "numeric_value": 45.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "50",
        "numeric_value": 50.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=60)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "40",
        "numeric_value": 40.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=90)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM2.5_연평균",
        "value": "20",
        "numeric_value": 20.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM2.5_연평균",
        "value": "25",
        "numeric_value": 25.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=60)).isoformat(),
    },
]

# 2년 전 대기질 데이터 (기본 1년 필터에 걸려야 함)
AIR_EVIDENCES_OLD = [
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "100",
        "numeric_value": 100.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=800)).isoformat(),
    },
]

# 수질 수치 데이터 (최근 5년 이내)
WATER_EVIDENCES = [
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "2.0",
        "numeric_value": 2.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "3.0",
        "numeric_value": 3.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "4.0",
        "numeric_value": 4.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=300)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "COD",
        "value": "5.5",
        "numeric_value": 5.5,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat(),
    },
]

# 6년 전 수질 데이터 (기본 5년 필터에 걸려야 함)
WATER_EVIDENCES_OLD = [
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "10.0",
        "numeric_value": 10.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=2300)).isoformat(),
    },
]

# 비수치 생태 데이터 (통계 대상 아님)
ECOLOGY_NON_NUMERIC = [
    {
        "category": "ecology",
        "indicator": "비오톱_유형",
        "value": "자연림",
    },
    {
        "category": "ecology",
        "indicator": "녹지자연도",
        "value": "7등급",
    },
]

# 동일 날짜 시간별 대기 데이터 (일평균 집계 테스트용)
today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
AIR_HOURLY_SAME_DAY = [
    {
        "category": "air_quality",
        "indicator": "NO2_연평균",
        "value": "0.020",
        "numeric_value": 0.020,
        "unit": "ppm",
        "observed_at": f"{today_str}T09:00:00+00:00",
    },
    {
        "category": "air_quality",
        "indicator": "NO2_연평균",
        "value": "0.030",
        "numeric_value": 0.030,
        "unit": "ppm",
        "observed_at": f"{today_str}T15:00:00+00:00",
    },
    {
        "category": "air_quality",
        "indicator": "NO2_연평균",
        "value": "0.040",
        "numeric_value": 0.040,
        "unit": "ppm",
        "observed_at": f"{today_str}T21:00:00+00:00",
    },
]


# ── 헬퍼 ──

async def _create_project(client: AsyncClient) -> str:
    """테스트용 프로젝트 생성."""
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "통계 테스트 프로젝트",
            "description": "Post-1 통계 테스트",
            "project_type": "industrial",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_evidence(
    client: AsyncClient, project_id: str, ev: dict[str, Any]
) -> dict:
    """증거 데이터 생성."""
    payload = {"project_id": project_id, "screening_only": False, **ev}
    resp = await client.post("/api/v1/evidences", json=payload)
    assert resp.status_code == 201, f"증거 생성 실패: {resp.text}"
    return resp.json()


async def _create_evidences_batch(
    client: AsyncClient, project_id: str, evidences: list[dict]
) -> None:
    """여러 증거를 일괄 생성."""
    for ev in evidences:
        await _create_evidence(client, project_id, ev)


# ── 통계 계산 정확성 테스트 ──


@pytest.mark.asyncio
async def test_statistics_calculation_accuracy(client: AsyncClient):
    """기본 통계 계산(평균, 최대, 최소, 표준편차, 건수) 정확성 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)

    # years_filter=0으로 전체 기간 조회
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/water_quality?years_filter=0"
    )
    assert resp.status_code == 200
    stats = resp.json()

    # BOD 지표: 값 [2.0, 3.0, 4.0]
    bod_stats = next(
        (s for s in stats["indicator_stats"] if s["indicator"] == "BOD"), None
    )
    assert bod_stats is not None
    assert bod_stats["count"] == 3
    assert abs(bod_stats["mean"] - 3.0) < 0.001
    assert abs(bod_stats["max_value"] - 4.0) < 0.001
    assert abs(bod_stats["min_value"] - 2.0) < 0.001
    # 표준편차: sqrt(((2-3)^2 + (3-3)^2 + (4-3)^2) / 2) = 1.0
    assert abs(bod_stats["std_dev"] - 1.0) < 0.001

    # COD 지표: 값 [5.5]
    cod_stats = next(
        (s for s in stats["indicator_stats"] if s["indicator"] == "COD"), None
    )
    assert cod_stats is not None
    assert cod_stats["count"] == 1
    assert abs(cod_stats["mean"] - 5.5) < 0.001
    assert cod_stats["std_dev"] == 0.0  # 단일 값이면 표준편차 0


@pytest.mark.asyncio
async def test_statistics_period_tracking(client: AsyncClient):
    """관측 기간(최초~최종 관측일) 추적 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/water_quality?years_filter=0"
    )
    assert resp.status_code == 200

    bod_stats = next(
        (s for s in resp.json()["indicator_stats"] if s["indicator"] == "BOD"), None
    )
    assert bod_stats is not None
    assert bod_stats["period_start"] is not None
    assert bod_stats["period_end"] is not None
    # period_start < period_end (300일 전 < 100일 전)
    assert bod_stats["period_start"] < bod_stats["period_end"]


@pytest.mark.asyncio
async def test_statistics_ignores_screening_only(client: AsyncClient):
    """screening_only=True 데이터는 통계에서 제외되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)
    # 스크리닝 전용 데이터 추가
    await _create_evidence(client, project_id, {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "99.0",
        "numeric_value": 99.0,
        "unit": "mg/L",
        "screening_only": True,
    })

    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/water_quality?years_filter=0"
    )
    assert resp.status_code == 200

    bod_stats = next(
        (s for s in resp.json()["indicator_stats"] if s["indicator"] == "BOD"), None
    )
    # 스크리닝 데이터(99.0)가 포함되지 않았으므로 건수 3, 평균 3.0
    assert bod_stats["count"] == 3
    assert abs(bod_stats["mean"] - 3.0) < 0.001


@pytest.mark.asyncio
async def test_statistics_ignores_non_numeric(client: AsyncClient):
    """numeric_value가 없는 데이터는 통계에서 제외되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, ECOLOGY_NON_NUMERIC)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/ecology?years_filter=0"
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_numeric_count"] == 0
    assert len(stats["indicator_stats"]) == 0


# ── 필터링 동작 테스트 ──


@pytest.mark.asyncio
async def test_air_default_filter_1year(client: AsyncClient):
    """대기 섹션: 기본 1년 필터로 오래된 데이터가 제외되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_EVIDENCES_RECENT)
    await _create_evidences_batch(client, project_id, AIR_EVIDENCES_OLD)

    # 기본 필터 (years_filter 미지정 → 대기는 1년)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/air_quality"
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["years_filter_applied"] == 1

    pm10 = next(
        (s for s in stats["indicator_stats"] if s["indicator"] == "PM10_연평균"), None
    )
    assert pm10 is not None
    # 최근 3건만 포함 (800일 전 데이터 제외)
    assert pm10["count"] == 3
    assert abs(pm10["mean"] - 45.0) < 0.001  # (45+50+40)/3 = 45


@pytest.mark.asyncio
async def test_air_filter_override_all(client: AsyncClient):
    """years_filter=0으로 전체 기간 조회 시 오래된 데이터도 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_EVIDENCES_RECENT)
    await _create_evidences_batch(client, project_id, AIR_EVIDENCES_OLD)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/air_quality?years_filter=0"
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["years_filter_applied"] is None

    pm10 = next(
        (s for s in stats["indicator_stats"] if s["indicator"] == "PM10_연평균"), None
    )
    # 오래된 100.0 포함하여 4건
    assert pm10["count"] == 4


@pytest.mark.asyncio
async def test_water_default_filter_5years(client: AsyncClient):
    """수질 섹션: 기본 5년 필터로 오래된 데이터가 제외되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES_OLD)

    # 기본 필터 (years_filter 미지정 → 수질은 5년)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/water_quality"
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["years_filter_applied"] == 5

    bod = next(
        (s for s in stats["indicator_stats"] if s["indicator"] == "BOD"), None
    )
    # 6년 전 데이터(10.0) 제외하여 3건
    assert bod["count"] == 3
    assert abs(bod["mean"] - 3.0) < 0.001


@pytest.mark.asyncio
async def test_aggregate_daily(client: AsyncClient):
    """일평균 집계 옵션 동작 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_HOURLY_SAME_DAY)

    # 집계 없이: 3건 그대로
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/air_quality?years_filter=0&aggregate_daily=false"
    )
    assert resp.status_code == 200
    no2_raw = next(
        (s for s in resp.json()["indicator_stats"] if s["indicator"] == "NO2_연평균"),
        None,
    )
    assert no2_raw is not None
    assert no2_raw["count"] == 3

    # 일평균 집계: 같은 날짜이므로 1건 (0.02+0.03+0.04)/3 = 0.03
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/air_quality?years_filter=0&aggregate_daily=true"
    )
    assert resp.status_code == 200
    no2_agg = next(
        (s for s in resp.json()["indicator_stats"] if s["indicator"] == "NO2_연평균"),
        None,
    )
    assert no2_agg is not None
    assert no2_agg["count"] == 1
    assert abs(no2_agg["mean"] - 0.03) < 0.001


# ── API 에러 처리 테스트 ──


@pytest.mark.asyncio
async def test_statistics_project_not_found(client: AsyncClient):
    """존재하지 않는 프로젝트 요청 시 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/projects/{fake_id}/statistics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_statistics_section_not_found(client: AsyncClient):
    """존재하지 않는 섹션 요청 시 404."""
    project_id = await _create_project(client)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics/nonexistent_section"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_statistics_empty_project(client: AsyncClient):
    """증거가 없는 프로젝트의 통계는 0건."""
    project_id = await _create_project(client)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics?years_filter=0"
    )
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_numeric_count"] == 0


# ── scaffold 출력 변경 테스트 ──


@pytest.mark.asyncio
async def test_scaffold_contains_stats_table(client: AsyncClient):
    """scaffold summary_text에 통계 요약 테이블이 포함되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/water_quality"
    )
    assert resp.status_code == 200
    scaffold = resp.json()

    summary = scaffold["summary_text"]

    # 통계 요약 테이블 헤더 확인
    assert "측정 현황 요약" in summary
    # Post-2 이후: 환경기준이 있는 섹션은 기준+판정 열 포함
    assert "지표명" in summary
    assert "평균" in summary
    assert "건수" in summary

    # BOD 지표 행 확인
    assert "BOD" in summary

    # 상세 데이터 확인
    assert "측정 데이터" in summary


@pytest.mark.asyncio
async def test_scaffold_detail_sample_limit(client: AsyncClient):
    """scaffold 상세 데이터 부록이 최대 10건으로 제한되는지 검증."""
    project_id = await _create_project(client)

    # 15건의 대기질 데이터 생성
    for i in range(15):
        await _create_evidence(client, project_id, {
            "category": "air_quality",
            "indicator": "PM10_연평균",
            "value": str(30 + i),
            "numeric_value": 30.0 + i,
            "unit": "ug/m3",
            "observed_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=i)
            ).isoformat(),
        })

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/air_quality"
    )
    assert resp.status_code == 200
    scaffold = resp.json()

    summary = scaffold["summary_text"]
    # "외 10건은 별첨 참조" 표시 확인
    assert "별첨 참조" in summary


@pytest.mark.asyncio
async def test_scaffold_non_numeric_separate(client: AsyncClient):
    """비수치 데이터가 통계 테이블과 분리되어 표시되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, ECOLOGY_NON_NUMERIC)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/ecology"
    )
    assert resp.status_code == 200
    scaffold = resp.json()

    summary = scaffold["summary_text"]
    # 비수치 데이터 섹션 확인
    assert "비수치 데이터" in summary
    assert "자연림" in summary
    assert "7등급" in summary


@pytest.mark.asyncio
async def test_scaffold_empty_section(client: AsyncClient):
    """증거가 없는 섹션은 '데이터가 없습니다' 메시지."""
    project_id = await _create_project(client)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/soil"
    )
    assert resp.status_code == 200
    scaffold = resp.json()
    # Post-3: 미수집 섹션의 서술문은 narrative 필드에 위치
    assert scaffold["summary_text"] == ""
    assert "수집되지 않았다" in scaffold["narrative"]


# ── 전체 프로젝트 통계 API 테스트 ──


@pytest.mark.asyncio
async def test_project_statistics_multi_section(client: AsyncClient):
    """전체 프로젝트 통계에서 여러 섹션이 집계되는지 검증."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_EVIDENCES_RECENT)
    await _create_evidences_batch(client, project_id, WATER_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/statistics?years_filter=0"
    )
    assert resp.status_code == 200
    stats = resp.json()

    # 대기 5건 + 수질 4건 = 9건
    assert stats["total_numeric_count"] == 9

    section_keys = [s["section_key"] for s in stats["sections"]]
    # 데이터가 있는 섹션에 통계가 포함
    air = next(s for s in stats["sections"] if s["section_key"] == "air_quality")
    assert air["total_numeric_count"] == 5

    water = next(s for s in stats["sections"] if s["section_key"] == "water_quality")
    assert water["total_numeric_count"] == 4
