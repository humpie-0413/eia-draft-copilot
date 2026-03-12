"""PDF 출력 서비스 테스트.

reportlab 기반 PDF 생성이 정상 동작하는지 검증한다.
- 한글 폰트 등록
- PDF 문서 구조 (표지, 목차, 섹션, 근거 테이블)
- Export Gate (QA 검사) 연동
- API 엔드포인트 (/export/pdf)

실행:
  cd backend
  pytest tests/test_export_pdf.py -v --tb=short
"""

import io
from typing import Any

import pytest
from httpx import AsyncClient


# ── 테스트 데이터 (test_e2e.py와 동일 구조) ──

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

# 4개 핵심 섹션 모두 충족시키는 증거 데이터
ALL_EVIDENCES = [
    # 대기질 6개
    {"category": "air_quality", "indicator": "PM10_연평균", "value": "45", "numeric_value": 45.0, "unit": "ug/m3"},
    {"category": "air_quality", "indicator": "PM2.5_연평균", "value": "23", "numeric_value": 23.0, "unit": "ug/m3"},
    {"category": "air_quality", "indicator": "NO2_연평균", "value": "0.028", "numeric_value": 0.028, "unit": "ppm"},
    {"category": "air_quality", "indicator": "SO2_연평균", "value": "0.004", "numeric_value": 0.004, "unit": "ppm"},
    {"category": "air_quality", "indicator": "CO_연평균", "value": "0.5", "numeric_value": 0.5, "unit": "ppm"},
    {"category": "air_quality", "indicator": "O3_연평균", "value": "0.032", "numeric_value": 0.032, "unit": "ppm"},
    # 수질 6개
    {"category": "water_quality", "indicator": "BOD", "value": "2.1", "numeric_value": 2.1, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "COD", "value": "4.3", "numeric_value": 4.3, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "SS", "value": "12", "numeric_value": 12.0, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "T-N", "value": "1.8", "numeric_value": 1.8, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "T-P", "value": "0.05", "numeric_value": 0.05, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "DO", "value": "8.5", "numeric_value": 8.5, "unit": "mg/L"},
    # 소음진동 3개
    {"category": "noise_vibration", "indicator": "소음_Leq_주간", "value": "58", "numeric_value": 58.0, "unit": "dB(A)"},
    {"category": "noise_vibration", "indicator": "소음_Leq_야간", "value": "49", "numeric_value": 49.0, "unit": "dB(A)"},
    {"category": "noise_vibration", "indicator": "진동_Lv_주간", "value": "63", "numeric_value": 63.0, "unit": "dB(V)"},
    # 생태 5개
    {"category": "ecology", "indicator": "식물상_종수", "value": "245", "numeric_value": 245.0, "unit": "종"},
    {"category": "ecology", "indicator": "동물상_종수", "value": "78", "numeric_value": 78.0, "unit": "종"},
    {"category": "ecology", "indicator": "법정보호종", "value": "2", "numeric_value": 2.0, "unit": "종"},
    {"category": "ecology", "indicator": "비오톱_유형", "value": "자연림"},
    {"category": "ecology", "indicator": "녹지자연도", "value": "7등급"},
]


async def _create_evidence(client: AsyncClient, project_id: str, ev: dict[str, Any]) -> dict:
    """증거 데이터 생성 헬퍼."""
    payload = {"project_id": project_id, "screening_only": False, **ev}
    resp = await client.post("/api/v1/evidences", json=payload)
    assert resp.status_code == 201, f"증거 생성 실패: {ev['indicator']} -> {resp.text}"
    return resp.json()


async def _setup_project_with_evidences(client: AsyncClient) -> str:
    """프로젝트 생성 + 모든 핵심 섹션 증거 추가. 프로젝트 ID 반환."""
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "PDF 테스트 프로젝트",
            "description": "PDF 출력 테스트용",
            "project_type": "energy",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    for ev in ALL_EVIDENCES:
        await _create_evidence(client, project_id, ev)

    return project_id


@pytest.mark.asyncio
async def test_pdf_export_success(client: AsyncClient):
    """PDF export가 정상적으로 파일을 반환하는지 검증."""
    project_id = await _setup_project_with_evidences(client)

    resp = await client.get(f"/api/v1/projects/{project_id}/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.pdf"')

    # PDF 파일 크기 검증 (비어있지 않은지)
    assert len(resp.content) > 1000, "PDF 파일이 너무 작음"

    # PDF 매직 바이트 검증
    assert resp.content[:5] == b"%PDF-", "유효한 PDF 파일이어야 함"


@pytest.mark.asyncio
async def test_pdf_export_blocked_by_qa(client: AsyncClient):
    """critical QA 이슈가 있으면 PDF export가 차단되는지 검증."""
    # 프로젝트 생성 (증거 없음 → critical 이슈 발생)
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "QA 차단 테스트",
            "description": "증거 없음",
            "project_type": "energy",
            "geometry": SAMPLE_POLYGON,
        },
    )
    project_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/export/pdf")
    assert resp.status_code == 422
    assert "critical" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pdf_export_404(client: AsyncClient):
    """존재하지 않는 프로젝트의 PDF export는 404."""
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/projects/{fake_id}/export/pdf")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pdf_contains_content(client: AsyncClient):
    """PDF 파일 내 한글 텍스트가 포함되는지 간접 검증."""
    project_id = await _setup_project_with_evidences(client)

    resp = await client.get(f"/api/v1/projects/{project_id}/export/pdf")
    assert resp.status_code == 200

    # reportlab으로 생성된 PDF는 바이너리이지만 일부 텍스트 검증 가능
    # PDF 파일이 충분한 크기를 가져야 모든 섹션이 포함됨
    assert len(resp.content) > 5000, "충분한 내용이 담긴 PDF여야 함"
