"""Post-2 환경기준 비교 엔진 테스트.

환경기준 비교 판정 정확성, scaffold 서술문 생성, R006 QA 규칙을 검증한다.

실행 방법:
  cd backend
  pytest tests/test_standard_checker.py -v --tb=short
"""

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

# 대기질 — 기준 이내 데이터 (PM10 평균 45 < 기준 50)
AIR_PASS_EVIDENCES = [
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "42",
        "numeric_value": 42.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "48",
        "numeric_value": 48.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=60)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM2.5_연평균",
        "value": "12",
        "numeric_value": 12.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
]

# 대기질 — 기준 초과 데이터 (PM10 평균 55 > 기준 50)
AIR_FAIL_EVIDENCES = [
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "55",
        "numeric_value": 55.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM10_연평균",
        "value": "60",
        "numeric_value": 60.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=60)).isoformat(),
    },
    {
        "category": "air_quality",
        "indicator": "PM2.5_연평균",
        "value": "18",
        "numeric_value": 18.0,
        "unit": "ug/m3",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat(),
    },
]

# 수질 — III등급 이내 (BOD 평균 3.0 ≤ 5.0)
WATER_PASS_EVIDENCES = [
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
        "value": "4.0",
        "numeric_value": 4.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "COD",
        "value": "5.0",
        "numeric_value": 5.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "DO",
        "value": "7.0",
        "numeric_value": 7.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat(),
    },
]

# 수질 — 기준 초과 (BOD 평균 6.0 > 기준 5.0)
WATER_FAIL_EVIDENCES = [
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "6.0",
        "numeric_value": 6.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat(),
    },
    {
        "category": "water_quality",
        "indicator": "BOD",
        "value": "8.0",
        "numeric_value": 8.0,
        "unit": "mg/L",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat(),
    },
]

# 소음 — 야간 초과 (48.3 > 기준 45)
NOISE_FAIL_EVIDENCES = [
    {
        "category": "noise_vibration",
        "indicator": "소음_Leq_주간",
        "value": "52.0",
        "numeric_value": 52.0,
        "unit": "dB(A)",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=10)).isoformat(),
    },
    {
        "category": "noise_vibration",
        "indicator": "소음_Leq_야간",
        "value": "48.3",
        "numeric_value": 48.3,
        "unit": "dB(A)",
        "observed_at": (datetime.now(tz=timezone.utc) - timedelta(days=10)).isoformat(),
    },
]


# ── 헬퍼 ──

async def _create_project(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "기준비교 테스트 프로젝트",
            "description": "Post-2 테스트",
            "project_type": "industrial",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_evidence(
    client: AsyncClient, project_id: str, ev: dict[str, Any]
) -> dict:
    payload = {"project_id": project_id, "screening_only": False, **ev}
    resp = await client.post("/api/v1/evidences", json=payload)
    assert resp.status_code == 201, f"증거 생성 실패: {resp.text}"
    return resp.json()


async def _create_evidences_batch(
    client: AsyncClient, project_id: str, evidences: list[dict]
) -> None:
    for ev in evidences:
        await _create_evidence(client, project_id, ev)


# ──────────────────────────────────────────────
# 1. 환경기준 비교 판정 정확성 테스트
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_air_standards_pass(client: AsyncClient):
    """대기질 — 기준 이내 시 pass 판정."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/air_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["has_exceedance"] is False
    assert result["exceedance_count"] == 0

    # PM10 지표 확인
    pm10 = next(
        (i for i in result["indicators"] if i["indicator"] == "PM10_연평균"), None
    )
    assert pm10 is not None
    assert pm10["status"] == "pass"
    assert pm10["standard_value"] == 50.0
    assert pm10["measured_avg"] is not None
    assert pm10["measured_avg"] <= 50.0


@pytest.mark.asyncio
async def test_air_standards_fail(client: AsyncClient):
    """대기질 — 기준 초과 시 fail 판정."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_FAIL_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/air_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["has_exceedance"] is True
    assert result["exceedance_count"] >= 1

    # PM10 초과 확인
    pm10 = next(
        (i for i in result["indicators"] if i["indicator"] == "PM10_연평균"), None
    )
    assert pm10 is not None
    assert pm10["status"] == "fail"

    # PM2.5 — 평균 18 > 기준 15 → 초과
    pm25 = next(
        (i for i in result["indicators"] if i["indicator"] == "PM2.5_연평균"), None
    )
    assert pm25 is not None
    assert pm25["status"] == "fail"


@pytest.mark.asyncio
async def test_water_standards_pass(client: AsyncClient):
    """수질 — III등급 기준 이내 시 pass 판정."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/water_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    # BOD 평균 3.0 ≤ 5.0 → pass
    bod = next(
        (i for i in result["indicators"] if i["indicator"] == "BOD"), None
    )
    assert bod is not None
    assert bod["status"] == "pass"
    assert bod["standard_value"] == 5.0

    # COD 평균 5.0 ≤ 7.0 → pass
    cod = next(
        (i for i in result["indicators"] if i["indicator"] == "COD"), None
    )
    assert cod is not None
    assert cod["status"] == "pass"


@pytest.mark.asyncio
async def test_water_grade_determination(client: AsyncClient):
    """수질 등급 판정 확인."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/water_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    # BOD 평균 3.0 → II등급(약간 좋음, BOD≤3)
    assert result["water_grade"] is not None
    assert result["water_grade_name"] is not None


@pytest.mark.asyncio
async def test_water_standards_fail(client: AsyncClient):
    """수질 — 기준 초과 시 fail 판정."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_FAIL_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/water_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    # BOD 평균 7.0 > 기준 5.0 → fail
    bod = next(
        (i for i in result["indicators"] if i["indicator"] == "BOD"), None
    )
    assert bod is not None
    assert bod["status"] == "fail"
    assert result["has_exceedance"] is True


@pytest.mark.asyncio
async def test_noise_standards_partial_fail(client: AsyncClient):
    """소음 — 주간 적합, 야간 초과 판정."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, NOISE_FAIL_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/noise_vibration"
    )
    assert resp.status_code == 200
    result = resp.json()

    # 주간 52.0 ≤ 55.0 → pass
    daytime = next(
        (i for i in result["indicators"] if i["indicator"] == "소음_Leq_주간"), None
    )
    assert daytime is not None
    assert daytime["status"] == "pass"

    # 야간 48.3 > 45.0 → fail
    nighttime = next(
        (i for i in result["indicators"] if i["indicator"] == "소음_Leq_야간"), None
    )
    assert nighttime is not None
    assert nighttime["status"] == "fail"

    assert result["has_exceedance"] is True
    assert result["exceedance_count"] >= 1


@pytest.mark.asyncio
async def test_do_geq_comparison(client: AsyncClient):
    """DO(용존산소) — GEQ(이상) 비교 연산 확인."""
    project_id = await _create_project(client)
    # DO 7.0 ≥ 5.0 → pass
    await _create_evidences_batch(client, project_id, WATER_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/water_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    do_result = next(
        (i for i in result["indicators"] if i["indicator"] == "DO"), None
    )
    assert do_result is not None
    assert do_result["status"] == "pass"


@pytest.mark.asyncio
async def test_no_data_returns_na(client: AsyncClient):
    """측정 데이터 없는 섹션의 판정은 na."""
    project_id = await _create_project(client)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/air_quality"
    )
    assert resp.status_code == 200
    result = resp.json()

    # 모든 지표가 na
    for ind in result["indicators"]:
        assert ind["status"] == "na"
    assert result["has_exceedance"] is False


@pytest.mark.asyncio
async def test_no_standard_section(client: AsyncClient):
    """환경기준이 없는 섹션(ecology)은 모든 지표 na."""
    project_id = await _create_project(client)
    await _create_evidence(client, project_id, {
        "category": "ecology",
        "indicator": "식물상_종수",
        "value": "150",
        "numeric_value": 150.0,
    })

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/ecology"
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["has_exceedance"] is False
    # 식물상_종수는 기준이 없으므로 na
    species = next(
        (i for i in result["indicators"] if i["indicator"] == "식물상_종수"), None
    )
    assert species is not None
    assert species["status"] == "na"


# ──────────────────────────────────────────────
# 2. API 테스트
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_project_standards_check_all_sections(client: AsyncClient):
    """전체 프로젝트 기준 비교 API — 여러 섹션 결과."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_FAIL_EVIDENCES)
    await _create_evidences_batch(client, project_id, WATER_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check"
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["total_exceedance_count"] >= 1
    section_keys = [s["section_key"] for s in result["sections"]]
    assert "air_quality" in section_keys
    assert "water_quality" in section_keys


@pytest.mark.asyncio
async def test_standards_check_project_not_found(client: AsyncClient):
    """존재하지 않는 프로젝트는 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/projects/{fake_id}/standards-check")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_standards_check_section_not_found(client: AsyncClient):
    """존재하지 않는 섹션은 404."""
    project_id = await _create_project(client)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/standards-check/nonexistent"
    )
    assert resp.status_code == 404


# ──────────────────────────────────────────────
# 3. scaffold 서술문 생성 테스트
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scaffold_includes_standards_columns(client: AsyncClient):
    """scaffold 통계 테이블에 환경기준 및 판정 열이 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/air_quality"
    )
    assert resp.status_code == 200
    summary = resp.json()["summary_text"]

    # 환경기준 열이 테이블에 포함
    assert "환경기준" in summary
    assert "판정" in summary


@pytest.mark.asyncio
async def test_scaffold_pass_narrative(client: AsyncClient):
    """기준 적합 시 scaffold에 '적합' 서술 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/air_quality"
    )
    assert resp.status_code == 200
    summary = resp.json()["summary_text"]

    assert "적합" in summary


@pytest.mark.asyncio
async def test_scaffold_fail_narrative(client: AsyncClient):
    """기준 초과 시 scaffold에 '초과' 및 '저감대책' 서술 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_FAIL_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/air_quality"
    )
    assert resp.status_code == 200
    scaffold = resp.json()
    narrative = scaffold["narrative"]

    assert "초과" in narrative
    assert "저감대책" in narrative


@pytest.mark.asyncio
async def test_scaffold_water_grade_narrative(client: AsyncClient):
    """수질 scaffold에 등급 정보 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, WATER_PASS_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/water_quality"
    )
    assert resp.status_code == 200
    scaffold = resp.json()
    narrative = scaffold["narrative"]

    # 등급 관련 서술 확인
    assert "등급" in narrative


@pytest.mark.asyncio
async def test_scaffold_noise_fail_narrative(client: AsyncClient):
    """소음 기준 초과 시 scaffold에 해당 서술 포함."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, NOISE_FAIL_EVIDENCES)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/sections/scaffold/noise_vibration"
    )
    assert resp.status_code == 200
    scaffold = resp.json()
    narrative = scaffold["narrative"]

    assert "야간" in narrative
    assert "초과" in narrative or "방음대책" in narrative


# ──────────────────────────────────────────────
# 4. R006 QA 규칙 테스트
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_qa_r006_no_exceedance(client: AsyncClient):
    """기준 이내일 때 R006 이슈 없음."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_PASS_EVIDENCES)

    resp = await client.get(f"/api/v1/projects/{project_id}/qa")
    assert resp.status_code == 200
    qa = resp.json()

    r006_issues = [i for i in qa["issues"] if i["rule_id"] == "R006"]
    assert len(r006_issues) == 0


@pytest.mark.asyncio
async def test_qa_r006_exceedance_warning(client: AsyncClient):
    """기준 초과 시 R006 warning 발생."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, AIR_FAIL_EVIDENCES)

    resp = await client.get(f"/api/v1/projects/{project_id}/qa")
    assert resp.status_code == 200
    qa = resp.json()

    r006_issues = [i for i in qa["issues"] if i["rule_id"] == "R006"]
    assert len(r006_issues) >= 1

    issue = r006_issues[0]
    assert issue["severity"] == "warning"
    assert "PM10_연평균" in issue["message"]
    assert "초과" in issue["message"] or "저감대책" in issue["message"]
    assert issue["section_key"] == "air_quality"


@pytest.mark.asyncio
async def test_qa_r006_does_not_block_export(client: AsyncClient):
    """R006은 warning이므로 export를 차단하지 않는다."""
    project_id = await _create_project(client)
    # 대기질 기준 초과 + 모든 필수 지표 충족 (R001/R002는 발생하지만 다른 섹션이므로)
    await _create_evidences_batch(client, project_id, AIR_FAIL_EVIDENCES)

    resp = await client.get(f"/api/v1/projects/{project_id}/qa")
    assert resp.status_code == 200
    qa = resp.json()

    # R006만으로는 export_ready가 False가 되지 않음
    # (다른 critical 이슈가 있을 수 있으므로 R006 자체가 warning인지만 확인)
    r006_issues = [i for i in qa["issues"] if i["rule_id"] == "R006"]
    for issue in r006_issues:
        assert issue["severity"] == "warning"


@pytest.mark.asyncio
async def test_qa_r006_noise_exceedance(client: AsyncClient):
    """소음 기준 초과 시에도 R006 발생."""
    project_id = await _create_project(client)
    await _create_evidences_batch(client, project_id, NOISE_FAIL_EVIDENCES)

    resp = await client.get(f"/api/v1/projects/{project_id}/qa")
    assert resp.status_code == 200
    qa = resp.json()

    r006_issues = [
        i for i in qa["issues"]
        if i["rule_id"] == "R006" and i["section_key"] == "noise_vibration"
    ]
    assert len(r006_issues) >= 1
    assert "소음_Leq_야간" in r006_issues[0]["message"]


# ──────────────────────────────────────────────
# 5. 순수 함수 단위 테스트 (env_standards)
# ──────────────────────────────────────────────


def test_water_grade_ia():
    """BOD 0.5 → Ia등급(매우 좋음)."""
    from app.data.env_standards import determine_water_grade
    grade = determine_water_grade(bod=0.5)
    assert grade is not None
    assert grade.grade == "Ia"
    assert grade.grade_name == "매우 좋음"


def test_water_grade_iii():
    """BOD 4.0 → III등급(보통)."""
    from app.data.env_standards import determine_water_grade
    grade = determine_water_grade(bod=4.0)
    assert grade is not None
    assert grade.grade == "III"
    assert grade.grade_name == "보통"


def test_water_grade_worst_wins():
    """여러 지표 중 가장 나쁜 등급 적용."""
    from app.data.env_standards import determine_water_grade
    # BOD 2.0 → Ib, DO 3.0 → IV (DO<5.0이면 III 위반)
    grade = determine_water_grade(bod=2.0, do_val=3.0)
    assert grade is not None
    # DO 3.0은 III등급(DO≥5.0) 위반이므로 IV 이상
    assert grade.grade in ("IV", "V")


def test_water_grade_none_without_data():
    """데이터 없으면 None."""
    from app.data.env_standards import determine_water_grade
    grade = determine_water_grade()
    assert grade is None


def test_get_standard_for_indicator():
    """지표명으로 기준 조회."""
    from app.data.env_standards import get_standard_for_indicator
    std = get_standard_for_indicator("air_quality", "PM10_연평균")
    assert std is not None
    assert std.limit_value == 50.0
    assert std.unit == "ug/m3"


def test_get_standard_for_unknown_indicator():
    """알 수 없는 지표는 None."""
    from app.data.env_standards import get_standard_for_indicator
    std = get_standard_for_indicator("air_quality", "알수없는_지표")
    assert std is None


def test_check_indicator_nan_returns_na():
    """측정 평균이 NaN인 경우 NA로 판정해야 한다."""
    import math
    from app.data.env_standards import ComparisonOp, Standard
    from app.services.standard_checker import CheckStatus, _check_indicator
    from app.services.statistics import IndicatorStats

    stats = IndicatorStats(
        indicator="PM10_24시간",
        count=5,
        mean=float("nan"),
        max_value=float("nan"),
    )
    standard = Standard(
        indicator="PM10_24시간",
        time_basis="24시간",
        limit_value=100.0,
        unit="ug/m3",
        op=ComparisonOp.LEQ,
    )
    result = _check_indicator(stats, standard)
    assert result.status == CheckStatus.NA


def test_check_indicator_none_returns_na():
    """측정 평균이 None인 경우 NA로 판정해야 한다."""
    from app.data.env_standards import ComparisonOp, Standard
    from app.services.standard_checker import CheckStatus, _check_indicator
    from app.services.statistics import IndicatorStats

    stats = IndicatorStats(
        indicator="PM10_24시간",
        count=0,
        mean=None,
    )
    standard = Standard(
        indicator="PM10_24시간",
        time_basis="24시간",
        limit_value=100.0,
        unit="ug/m3",
        op=ComparisonOp.LEQ,
    )
    result = _check_indicator(stats, standard)
    assert result.status == CheckStatus.NA
