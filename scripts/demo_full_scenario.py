# -*- coding: utf-8 -*-
"""실사용 시나리오 전체 흐름 데모 (Final-1 최종판).

시나리오: "서울특별시 강남구 태양광 발전소 건설 프로젝트"

전체 흐름:
  1. 프로젝트 생성
  2. 데이터 수집
     a. 에어코리아 대기질 커넥터
     b. 수질 커넥터
     c. 토양측정망 커넥터 (Post-4)
     d. 기상청 ASOS 기후 커넥터 (Post-4)
     e. V-world 토지이용 커넥터 (Post-9)
     f. 국가유산청 문화재 커넥터 (Post-9)
     g. 소음·진동 수동 데이터
     h. 생태 수동 데이터
     i. 교통량 통계 커넥터 (Conn-1)
     j. 폐기물 통계 커넥터 (Conn-1)
  3. 유사사례 등록 및 매칭
  4. 섹션 플래너 충족도 확인
  4.5. 법령 반영 검증 (Reg-5)
     a. 평가 범위 조회 (power_plant)
     b. 필수 섹션 확인
     c. 서술문 법적 근거 포함 확인
     d. 환경기준 비교 법적 근거 열 확인
  5. 통계 엔진 실행 (Post-1)
  6. 환경기준 비교 실행 (Post-2)
  7. 초안 뼈대 + 서술문 생성 (Post-3, Pred-3 예측 포함)
  7.5. 영향 예측 실행 (Pred-1~2)
     a. 대기 확산 예측 (가우시안 플룸)
     b. 소음 전파 예측 (거리감쇠 + 차음벽)
     c. 수질 혼합 예측 (완전혼합)
  8. LLM 보강 실행 (Post-6, 선택)
  9. QA 실행 + R007/R008 법적 필수 항목 검증 (Reg-3)
  10. DOCX + PDF export (부록 + 영향 예측 포함, Post-5)
  11. 결과 요약 비교

사전 조건:
  - 백엔드 서버 실행 중: uvicorn app.main:app --reload (http://localhost:8000)
  - PostgreSQL + PostGIS 실행 중
  - backend/.env에 DATA_GO_KR_API_KEY 설정됨

사용법:
  python scripts/demo_full_scenario.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp949 인코딩 이슈 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

# 백엔드 서버 기본 URL
BASE_URL = os.getenv("DEMO_API_URL", "http://localhost:8000")

# 출력 파일 저장 경로
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


# ═══════════════════════════════════════════════════════════════
# 헬퍼 함수
# ═══════════════════════════════════════════════════════════════

def banner(title: str) -> None:
    """단계 구분 배너 출력."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def sub_banner(title: str) -> None:
    """하위 단계 배너 출력."""
    print()
    print(f"  ── {title} ──")


async def api_call(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json: dict | None = None,
    expected: int = 200,
    label: str = "",
) -> dict | bytes | None:
    """API 호출 공통 래퍼. 오류 시 상세 메시지를 출력한다."""
    url = f"{BASE_URL}{path}"
    resp = await client.request(method, url, json=json)

    if resp.status_code != expected:
        print(f"    [오류] {label or path}: HTTP {resp.status_code}")
        try:
            print(f"    상세: {resp.json()}")
        except Exception:
            print(f"    응답: {resp.text[:300]}")
        return None

    # 바이너리 응답 (DOCX/PDF)
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type:
        return resp.content

    return resp.json()


# ═══════════════════════════════════════════════════════════════
# 단계 1: 프로젝트 생성
# ═══════════════════════════════════════════════════════════════

# 강남구 일대 폴리곤 (실제 좌표 — 강남구 중심부 사각형 근사)
GANGNAM_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.0280, 37.4979],
            [127.0630, 37.4979],
            [127.0630, 37.5170],
            [127.0280, 37.5170],
            [127.0280, 37.4979],
        ]
    ],
}


async def step1_create_project(client: httpx.AsyncClient) -> str | None:
    """프로젝트 생성. 프로젝트 ID를 반환한다."""
    banner("단계 1: 프로젝트 생성")

    data = {
        "name": "강남구 태양광 발전소 환경영향평가",
        "description": "서울특별시 강남구 일대 태양광 발전소 건설에 따른 환경영향평가",
        "project_type": "power_plant",
        "geometry": GANGNAM_POLYGON,
    }

    result = await api_call(
        client, "POST", "/api/v1/projects",
        json=data, expected=201, label="프로젝트 생성",
    )
    if result is None:
        return None

    project_id = result["id"]
    print(f"    프로젝트 ID: {project_id}")
    print(f"    이름: {result['name']}")
    print(f"    유형: {result['project_type']}")
    print(f"    상태: {result['status']}")
    print(f"    생성일: {result['created_at']}")
    return project_id


# ═══════════════════════════════════════════════════════════════
# 단계 2: 데이터 수집
# ═══════════════════════════════════════════════════════════════

async def step2_collect_data(client: httpx.AsyncClient, project_id: str) -> dict:
    """10개 경로로 데이터 수집: 커넥터 8종 + 수동 2종."""
    banner("단계 2: 데이터 수집 (커넥터 8종 + 수동 2종)")

    stats = {"connectors": {}, "manual": {}}

    # 2-a. 에어코리아 커넥터
    sub_banner("2-a. 에어코리아 대기질 커넥터 — 측정소: 강남구")
    result = await api_call(
        client, "POST", "/api/v1/connectors/keco_air/collect",
        json={
            "project_id": project_id,
            "params": {"station_name": "강남구", "data_term": "DAILY"},
            "screening_only": False,
        },
        expected=200, label="에어코리아 수집",
    )
    if result:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["keco_air"] = result["evidence_count"]
        if result.get("error_message"):
            print(f"    오류: {result['error_message']}")

    # 대기질 필수 지표(연평균) 수동 보충
    sub_banner("2-a2. 대기질 필수 지표(연평균) 수동 보충")
    air_required = [
        {"category": "air_quality", "indicator": "PM10_연평균", "value": "42", "numeric_value": 42.0, "unit": "ug/m3"},
        {"category": "air_quality", "indicator": "PM2.5_연평균", "value": "21", "numeric_value": 21.0, "unit": "ug/m3"},
        {"category": "air_quality", "indicator": "NO2_연평균", "value": "0.030", "numeric_value": 0.030, "unit": "ppm"},
        {"category": "air_quality", "indicator": "SO2_연평균", "value": "0.003", "numeric_value": 0.003, "unit": "ppm"},
        {"category": "air_quality", "indicator": "CO_연평균", "value": "0.4", "numeric_value": 0.4, "unit": "ppm"},
        {"category": "air_quality", "indicator": "O3_연평균", "value": "0.028", "numeric_value": 0.028, "unit": "ppm"},
    ]
    for ev in air_required:
        await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"대기질 보충: {ev['indicator']}",
        )
    print(f"    대기질 필수 지표 {len(air_required)}건 보충 완료")

    # 2-b. 수질 커넥터
    sub_banner("2-b. 수질 커넥터 — 한강 수계 측정지점")
    result = await api_call(
        client, "POST", "/api/v1/connectors/water_info/collect",
        json={
            "project_id": project_id,
            "params": {"year": "2024", "pt_no": "1018A60"},
            "screening_only": False,
        },
        expected=200, label="수질 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["water_info"] = result["evidence_count"]
    else:
        if result:
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
        print("    [경고] 수질 수집 실패/부족 — 수동 수질 데이터로 보충합니다.")

    # 2-b2. 수질 필수 지표 수동 보충 (커넥터 데이터가 오래된 경우 대비)
    sub_banner("2-b2. 수질 필수 지표 수동 보충")
    water_supplement = [
        {"category": "water_quality", "indicator": "BOD", "value": "1.8", "numeric_value": 1.8, "unit": "mg/L"},
        {"category": "water_quality", "indicator": "COD", "value": "3.5", "numeric_value": 3.5, "unit": "mg/L"},
        {"category": "water_quality", "indicator": "SS", "value": "8.2", "numeric_value": 8.2, "unit": "mg/L"},
        {"category": "water_quality", "indicator": "T-N", "value": "2.1", "numeric_value": 2.1, "unit": "mg/L"},
        {"category": "water_quality", "indicator": "T-P", "value": "0.04", "numeric_value": 0.04, "unit": "mg/L"},
        {"category": "water_quality", "indicator": "DO", "value": "9.2", "numeric_value": 9.2, "unit": "mg/L"},
    ]
    for ev in water_supplement:
        await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"수질 보충: {ev['indicator']}",
        )
    stats["connectors"].setdefault("water_info", 0)
    print(f"    수질 필수 지표 {len(water_supplement)}건 보충 완료")

    # 2-c. 토양측정망 커넥터 (Post-4)
    sub_banner("2-c. 토양측정망 커넥터 — 서울특별시")
    result = await api_call(
        client, "POST", "/api/v1/connectors/soil_info/collect",
        json={
            "project_id": project_id,
            "params": {"year": "2023", "sido": "서울특별시"},
            "screening_only": False,
        },
        expected=200, label="토양측정망 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["soil_info"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 토양 커넥터 실패 — 수동 토양 데이터로 대체합니다.")
        soil_manual = [
            {"category": "soil", "indicator": "Pb", "value": "12.5", "numeric_value": 12.5, "unit": "mg/kg"},
            {"category": "soil", "indicator": "Cd", "value": "0.8", "numeric_value": 0.8, "unit": "mg/kg"},
            {"category": "soil", "indicator": "pH", "value": "6.5", "numeric_value": 6.5, "unit": ""},
            {"category": "soil", "indicator": "유기물함량", "value": "3.2", "numeric_value": 3.2, "unit": "%"},
        ]
        for ev in soil_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 토양: {ev['indicator']}",
            )
        stats["connectors"]["soil_info"] = len(soil_manual)
        print(f"    수동 토양 데이터 {len(soil_manual)}건 추가 완료")

    # 2-d. 기상청 ASOS 기후 커넥터 (Post-4)
    sub_banner("2-d. 기상청 ASOS 기후 커넥터 — 서울(108)")
    result = await api_call(
        client, "POST", "/api/v1/connectors/kma_weather/collect",
        json={
            "project_id": project_id,
            "params": {
                "stn_id": "108",
                "start_dt": "20240101",
                "end_dt": "20241231",
            },
            "screening_only": False,
        },
        expected=200, label="기상청 ASOS 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["kma_weather"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 기후 커넥터 실패 — 수동 기후 데이터로 대체합니다.")
        climate_manual = [
            {"category": "climate", "indicator": "평균기온", "value": "13.2", "numeric_value": 13.2, "unit": "\u2103"},
            {"category": "climate", "indicator": "강수량", "value": "1394", "numeric_value": 1394.0, "unit": "mm"},
            {"category": "climate", "indicator": "평균풍속", "value": "2.3", "numeric_value": 2.3, "unit": "m/s"},
        ]
        for ev in climate_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 기후: {ev['indicator']}",
            )
        stats["connectors"]["kma_weather"] = len(climate_manual)
        print(f"    수동 기후 데이터 {len(climate_manual)}건 추가 완료")

    # 2-e. V-world 토지이용 커넥터 (Post-9)
    sub_banner("2-e. V-world 토지이용 커넥터 — 강남구 중심점")
    result = await api_call(
        client, "POST", "/api/v1/connectors/vworld_land_use/collect",
        json={
            "project_id": project_id,
            "params": {"lng": "127.0455", "lat": "37.5075"},
            "screening_only": False,
        },
        expected=200, label="V-world 토지이용 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["vworld_land_use"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 토지이용 커넥터 실패 — 수동 토지이용 데이터로 대체합니다.")
        land_use_manual = [
            {"category": "land_use", "indicator": "용도지역구분", "value": "제2종일반주거지역, 일반상업지역"},
            {"category": "land_use", "indicator": "용도지구", "value": "미관지구"},
            {"category": "land_use", "indicator": "지목", "value": "대"},
        ]
        for ev in land_use_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 토지이용: {ev['indicator']}",
            )
        stats["connectors"]["vworld_land_use"] = len(land_use_manual)
        print(f"    수동 토지이용 데이터 {len(land_use_manual)}건 추가 완료")

    # 2-f. 국가유산청 문화재 커넥터 (Post-9)
    sub_banner("2-f. 국가유산청 문화재 커넥터 — 강남구 중심점 반경 1km")
    result = await api_call(
        client, "POST", "/api/v1/connectors/cultural_heritage/collect",
        json={
            "project_id": project_id,
            "params": {"lng": "127.0455", "lat": "37.5075"},
            "screening_only": False,
        },
        expected=200, label="국가유산청 문화재 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["cultural_heritage"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 문화재 커넥터 실패 — 수동 문화재 데이터로 대체합니다.")
        heritage_manual = [
            {"category": "cultural_heritage", "indicator": "문화재명", "value": "봉은사"},
            {"category": "cultural_heritage", "indicator": "이격거리", "value": "850", "numeric_value": 850.0, "unit": "m"},
        ]
        for ev in heritage_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 문화재: {ev['indicator']}",
            )
        stats["connectors"]["cultural_heritage"] = len(heritage_manual)
        print(f"    수동 문화재 데이터 {len(heritage_manual)}건 추가 완료")

    # 2-g. 수동 증거 — 소음·진동 3건
    sub_banner("2-g. 수동 증거 — 소음·진동 3건")
    noise_evidences = [
        {"category": "noise_vibration", "indicator": "소음_Leq_주간", "value": "62.5", "numeric_value": 62.5, "unit": "dB(A)", "observed_at": "2025-11-15T10:00:00"},
        {"category": "noise_vibration", "indicator": "소음_Leq_야간", "value": "48.3", "numeric_value": 48.3, "unit": "dB(A)", "observed_at": "2025-11-15T22:00:00"},
        {"category": "noise_vibration", "indicator": "진동_Lv_주간", "value": "55.0", "numeric_value": 55.0, "unit": "dB(V)", "observed_at": "2025-11-15T10:00:00"},
    ]
    for ev in noise_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"소음: {ev['indicator']}",
        )
        if result:
            print(f"    {ev['indicator']}: {ev['value']} {ev['unit']} — 등록 완료")
    stats["manual"]["noise_vibration"] = len(noise_evidences)

    # 2-h. 수동 증거 — 생태 5건
    sub_banner("2-h. 수동 증거 — 생태 조사 데이터 5건")
    ecology_evidences = [
        {"category": "ecology", "indicator": "식물상_종수", "value": "187", "numeric_value": 187.0, "unit": "종", "observed_at": "2025-10-01T00:00:00"},
        {"category": "ecology", "indicator": "동물상_종수", "value": "42", "numeric_value": 42.0, "unit": "종", "observed_at": "2025-10-01T00:00:00"},
        {"category": "ecology", "indicator": "법정보호종", "value": "1", "numeric_value": 1.0, "unit": "종", "observed_at": "2025-10-01T00:00:00"},
        {"category": "ecology", "indicator": "비오톱_유형", "value": "도시녹지", "observed_at": "2025-10-01T00:00:00"},
        {"category": "ecology", "indicator": "녹지자연도", "value": "5등급", "observed_at": "2025-10-01T00:00:00"},
    ]
    for ev in ecology_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"생태: {ev['indicator']}",
        )
        if result:
            print(f"    {ev['indicator']}: {ev['value']} — 등록 완료")
    stats["manual"]["ecology"] = len(ecology_evidences)

    # 2-i. 교통량 통계 커넥터 (Conn-1)
    sub_banner("2-i. 교통량 통계 커넥터 — 서울 일반국도")
    result = await api_call(
        client, "POST", "/api/v1/connectors/traffic_volume/collect",
        json={
            "project_id": project_id,
            "params": {"year": "2024", "dtype": "2"},
            "screening_only": False,
        },
        expected=200, label="교통량 통계 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["traffic_volume"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 교통량 커넥터 실패 — 수동 교통 데이터로 대체합니다.")
        traffic_manual = [
            {"category": "traffic", "indicator": "교통량_현황", "value": "15420", "numeric_value": 15420.0, "unit": "대/일"},
            {"category": "traffic", "indicator": "도로등급", "value": "일반국도"},
            {"category": "traffic", "indicator": "도로명", "value": "강남대로"},
        ]
        for ev in traffic_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 교통: {ev['indicator']}",
            )
        stats["connectors"]["traffic_volume"] = len(traffic_manual)
        print(f"    수동 교통 데이터 {len(traffic_manual)}건 추가 완료")

    # 2-j. 폐기물 통계 커넥터 (Conn-1)
    sub_banner("2-j. 폐기물 통계 커넥터 — 강남구")
    result = await api_call(
        client, "POST", "/api/v1/connectors/waste_stats/collect",
        json={
            "project_id": project_id,
            "params": {"region": "강남구"},
            "screening_only": False,
        },
        expected=200, label="폐기물 통계 수집",
    )
    if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["waste_stats"] = result["evidence_count"]
    else:
        if result:
            msg = result.get("error_message", "")
            print(f"    상태: {result.get('status')}, 수집 건수: {result.get('evidence_count', 0)}")
            if msg:
                print(f"    오류: {msg}")
        print("    [경고] 폐기물 커넥터 실패 — 수동 폐기물 데이터로 대체합니다.")
        waste_manual = [
            {"category": "waste", "indicator": "생활폐기물_발생량", "value": "1250", "numeric_value": 1250.0, "unit": "톤/일"},
            {"category": "waste", "indicator": "음식물쓰레기_발생량", "value": "320", "numeric_value": 320.0, "unit": "톤/일"},
            {"category": "waste", "indicator": "재활용_발생량", "value": "480", "numeric_value": 480.0, "unit": "톤/일"},
        ]
        for ev in waste_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 폐기물: {ev['indicator']}",
            )
        stats["connectors"]["waste_stats"] = len(waste_manual)
        print(f"    수동 폐기물 데이터 {len(waste_manual)}건 추가 완료")

    # 수집 결과 요약
    sub_banner("수집 결과 요약")
    resp = await api_call(
        client, "GET",
        f"/api/v1/evidences?project_id={project_id}&limit=1",
        label="증거 목록",
    )
    if resp:
        total = resp["total"]
        stats["total"] = total
        print(f"    총 증거 건수: {total}")
        for k, v in stats["connectors"].items():
            print(f"      커넥터 [{k}]: {v}건")
        for k, v in stats["manual"].items():
            print(f"      수동 [{k}]: {v}건")

    return stats


# ═══════════════════════════════════════════════════════════════
# 단계 3: 유사사례 등록 및 매칭
# ═══════════════════════════════════════════════════════════════

SIMILAR_CASES = [
    {
        "name": "경기도 화성시 태양광 발전단지 환경영향평가",
        "description": "화성시 남양읍 일대 50MW급 태양광 발전단지 조성사업",
        "project_type": "power_plant",
        "location": {"type": "Point", "coordinates": [126.95, 37.20]},
        "area_sqm": 320000.0,
        "summary": "농경지 전환 태양광 단지 조성. 대기질 영향 미미, 생태계 완충지대 설정 권고.",
        "key_findings": {
            "대기질": "공사 중 비산먼지 관리 필요, 운영 시 영향 없음",
            "수질": "우수 유출 관리 계획 수립",
            "생태": "조류 충돌 방지 시설 설치 권고",
        },
        "evidence_categories": ["air_quality", "water_quality", "ecology"],
    },
    {
        "name": "충남 당진시 태양광 발전소 환경영향평가",
        "description": "당진시 해안 간척지 100MW급 태양광 발전소",
        "project_type": "power_plant",
        "location": {"type": "Point", "coordinates": [126.65, 36.90]},
        "area_sqm": 580000.0,
        "summary": "간척지 태양광 발전소. 해양 생태 영향 중점 평가, 조류 이동 경로 분석.",
        "key_findings": {
            "대기질": "비산먼지 저감 대책 이행",
            "수질": "해수 유입 방지 및 담수 수질 관리",
            "생태": "철새 도래지 인접 — 계절별 모니터링 의무화",
            "소음": "인버터 소음 기준 이내",
        },
        "evidence_categories": ["air_quality", "water_quality", "ecology", "noise_vibration"],
    },
    {
        "name": "전남 해남군 풍력·태양광 복합 발전단지",
        "description": "해남군 해안지역 풍력 30MW + 태양광 20MW 복합 발전단지",
        "project_type": "power_plant",
        "location": {"type": "Point", "coordinates": [126.60, 34.55]},
        "area_sqm": 450000.0,
        "summary": "복합 재생에너지 단지. 소음진동 중점 평가, 경관 시뮬레이션 수행.",
        "key_findings": {
            "소음진동": "풍력 발전기 저주파 소음 영향 평가",
            "경관": "조망점 10개소 경관 영향 분석",
            "생태": "해안 습지 보전 구역 회피 설계",
        },
        "evidence_categories": ["noise_vibration", "ecology", "landscape"],
    },
]


async def step3_similar_cases(client: httpx.AsyncClient, project_id: str) -> bool:
    """유사사례 등록 + 매칭 실행."""
    banner("단계 3: 유사사례 등록 및 매칭")

    sub_banner("유사사례 등록")
    for case in SIMILAR_CASES:
        result = await api_call(
            client, "POST", "/api/v1/similar-cases",
            json=case, expected=201, label=f"유사사례: {case['name']}",
        )
        if result:
            print(f"    등록: {result['name']} (ID: {result['id'][:8]}...)")

    sub_banner("매칭 실행")
    result = await api_call(
        client, "GET",
        f"/api/v1/similar-cases/match/{project_id}?top_k=5",
        label="유사사례 매칭",
    )
    if result:
        print(f"    매칭 결과 수: {result['total']}")
        for i, match in enumerate(result.get("matches", []), 1):
            sc = match["similar_case"]
            print(f"    {i}. {sc['name']}")
            print(f"       종합 유사도: {match['overall_score']:.2f}")
            print(f"       사업유형: {match['type_score']:.2f} | "
                  f"위치: {match['location_score']:.2f} | "
                  f"규모: {match['scale_score']:.2f} | "
                  f"분야: {match['category_score']:.2f}")
        return True

    return False


# ═══════════════════════════════════════════════════════════════
# 단계 4: 섹션 플래너 확인
# ═══════════════════════════════════════════════════════════════

async def step4_section_planner(client: httpx.AsyncClient, project_id: str) -> dict:
    """11개 섹션 충족도 확인."""
    banner("단계 4: 섹션 플래너 — 충족도 확인")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/status",
        label="섹션 상태",
    )
    if not result:
        return {}

    sections = result.get("sections", [])
    print(f"    총 섹션 수: {result['total_sections']}")
    print()

    status_emoji = {"complete": "[완료]", "partial": "[부분]", "empty": "[미수집]"}

    for s in sections:
        status = s["status"]
        mark = status_emoji.get(status, status)
        ratio = s["coverage_ratio"]
        print(
            f"    {s['order']:2d}. {s['title']:<12s}  {mark:<8s}  "
            f"충족도: {ratio:.0%}  ({s['fulfilled_count']}/{s['required_count']})"
        )

    statuses = [s["status"] for s in sections]
    summary = {
        "complete": statuses.count("complete"),
        "partial": statuses.count("partial"),
        "empty": statuses.count("empty"),
    }
    print()
    print(f"    완료: {summary['complete']}개 | "
          f"부분: {summary['partial']}개 | "
          f"미수집: {summary['empty']}개")

    return summary


# ═══════════════════════════════════════════════════════════════
# 단계 4.5: 법령 반영 검증 (Reg-5)
# ═══════════════════════════════════════════════════════════════

async def step4_5_regulation_check(
    client: httpx.AsyncClient,
    project_id: str,
) -> dict:
    """법령 반영 기능을 종합 검증한다.

    Reg-1~Reg-4에서 구현한 기능들이 정상 동작하는지 확인:
    a. 평가 범위 조회 (power_plant 유형 기반)
    b. 필수 섹션 목록 확인
    c. 서술문에 법적 근거 포함 여부 확인
    d. 환경기준 비교 테이블에 법적 근거 열 존재 확인
    """
    banner("단계 4.5: 법령 반영 검증 (Reg-5)")

    reg_summary = {
        "scope_ok": False,
        "required_sections": [],
        "narrative_legal_refs": 0,
        "standards_legal_refs": 0,
    }

    # ── a. 평가 범위 조회 ──
    sub_banner("4.5-a. 평가 범위 조회 (power_plant)")
    scope = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/assessment-scope",
        label="평가 범위",
    )
    if scope:
        reg_summary["scope_ok"] = True
        print(f"    사업유형: {scope['type_name']} ({scope['project_type']})")
        print(f"    법적 근거: {scope['legal_basis']}")
        print(f"    필수 섹션: {scope['required_count']}개")
        print(f"    권장 섹션: {scope['recommended_count']}개")
        print(f"    선택 섹션: {scope['optional_count']}개")
        print()

        required = [s for s in scope["sections"] if s["scope"] == "required"]
        recommended = [s for s in scope["sections"] if s["scope"] == "recommended"]
        optional = [s for s in scope["sections"] if s["scope"] == "optional"]

        reg_summary["required_sections"] = [s["section_key"] for s in required]

        print("    필수 섹션 목록:")
        for s in required:
            ind_count = len(s.get("required_indicators", []))
            print(f"      - {s['title']} ({s['section_key']}): 필수 지표 {ind_count}개")
        if recommended:
            print("    권장 섹션:")
            for s in recommended:
                print(f"      - {s['title']} ({s['section_key']})")
        if optional:
            print("    선택 섹션:")
            for s in optional:
                print(f"      - {s['title']} ({s['section_key']})")

    # ── b. 섹션 상태에 scope 필드 확인 ──
    sub_banner("4.5-b. 섹션 상태 scope 필드 확인")
    status_result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/status",
        label="섹션 상태 + scope",
    )
    if status_result:
        sections = status_result.get("sections", [])
        scope_found = 0
        for s in sections:
            scope_val = s.get("scope", "")
            if scope_val:
                scope_found += 1
            scope_label = {"required": "필수", "recommended": "권장", "optional": "선택"}.get(scope_val, "-")
            print(f"    {s['order']:2d}. {s['title']:<12s}  [{scope_label}]  {s['status']}")
        print(f"\n    scope 정보 존재 섹션: {scope_found}/{len(sections)}")

    # ── c. 서술문 법적 근거 포함 확인 ──
    sub_banner("4.5-c. 서술문 법적 근거 포함 확인")
    scaffold = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/scaffold",
        label="초안 뼈대 (법적 근거 검증)",
    )
    if scaffold:
        # 법적 근거 키워드 패턴
        legal_keywords = [
            "환경정책기본법",
            "토양환경보전법",
            "환경영향평가법",
            "시행령",
            "별표",
        ]
        narrative_ref_count = 0
        for s in scaffold.get("sections", []):
            narrative = s.get("narrative", "") or ""
            found = [kw for kw in legal_keywords if kw in narrative]
            if found:
                narrative_ref_count += 1
                print(f"    {s['title']:<12s}: 법적 근거 포함 ({', '.join(found)})")
                # 첫 줄 미리보기
                first_legal = ""
                for line in narrative.split("\n"):
                    if any(kw in line for kw in legal_keywords):
                        first_legal = line.strip()[:80]
                        break
                if first_legal:
                    print(f"        예시: {first_legal}")
            else:
                if narrative and "수집" not in narrative:
                    print(f"    {s['title']:<12s}: 서술문 있음, 법적 근거 없음")

        reg_summary["narrative_legal_refs"] = narrative_ref_count
        print(f"\n    법적 근거 포함 서술문: {narrative_ref_count}개 섹션")

    # ── d. 환경기준 비교 법적 근거 열 확인 ──
    sub_banner("4.5-d. 환경기준 비교 법적 근거 열 확인")
    standards = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/standards-check",
        label="환경기준 비교 (법적 근거 열)",
    )
    if standards:
        legal_ref_count = 0
        for s in standards.get("sections", []):
            for ind in s.get("indicators", []):
                legal = ind.get("legal_basis", "")
                if legal:
                    legal_ref_count += 1
        reg_summary["standards_legal_refs"] = legal_ref_count
        print(f"    환경기준 비교 지표 중 법적 근거 포함: {legal_ref_count}건")

        # 대표 예시 출력
        for s in standards.get("sections", []):
            for ind in s.get("indicators", []):
                legal = ind.get("legal_basis", "")
                if legal and ind.get("standard_value") is not None:
                    print(f"    예시: {ind['indicator']} — {legal}")
                    break
            if any(ind.get("legal_basis") for ind in s.get("indicators", [])):
                break

    # ── 검증 요약 ──
    sub_banner("법령 반영 검증 요약")
    checks = [
        ("평가 범위 API 동작", reg_summary["scope_ok"]),
        ("필수 섹션 식별", len(reg_summary["required_sections"]) > 0),
        ("서술문 법적 근거 포함", reg_summary["narrative_legal_refs"] > 0),
        ("환경기준 법적 근거 열", reg_summary["standards_legal_refs"] > 0),
    ]
    all_pass = True
    for label, ok in checks:
        mark = "✓" if ok else "✗"
        print(f"    {mark} {label}")
        if not ok:
            all_pass = False

    print()
    if all_pass:
        print("    법령 반영 검증 통과")
    else:
        print("    [경고] 일부 검증 항목 미통과 — 상세 확인 필요")

    return reg_summary


# ═══════════════════════════════════════════════════════════════
# 단계 5: 통계 엔진 실행 (Post-1)
# ═══════════════════════════════════════════════════════════════

async def step5_statistics(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 통계 조회."""
    banner("단계 5: 통계 엔진 실행 (Post-1)")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/statistics",
        label="통계 엔진",
    )
    if not result:
        return {}

    print(f"    생성 시각: {result['generated_at']}")
    print(f"    총 수치 데이터: {result['total_numeric_count']}건")
    print()

    stats_summary = {}
    for s in result.get("sections", []):
        indicator_count = len(s.get("indicator_stats", []))
        total_count = s.get("total_numeric_count", 0)
        stats_summary[s["section_key"]] = indicator_count
        if indicator_count > 0:
            print(f"    {s['title']:<12s}: 지표 {indicator_count}개, 수치 데이터 {total_count}건")
            for ind in s.get("indicator_stats", [])[:3]:
                unit_str = f" {ind['unit']}" if ind.get("unit") else ""
                print(f"      - {ind['indicator']}: 평균 {ind['mean']:.2f}{unit_str} "
                      f"(최소 {ind['min_value']}, 최대 {ind['max_value']}, {ind['count']}건)")
            if indicator_count > 3:
                print(f"      ... 외 {indicator_count - 3}개 지표")

    return stats_summary


# ═══════════════════════════════════════════════════════════════
# 단계 6: 환경기준 비교 (Post-2)
# ═══════════════════════════════════════════════════════════════

async def step6_standards_check(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 환경기준 비교."""
    banner("단계 6: 환경기준 비교 (Post-2)")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/standards-check",
        label="환경기준 비교",
    )
    if not result:
        return {}

    total_exceedance = result.get("total_exceedance_count", 0)
    print(f"    생성 시각: {result['generated_at']}")
    print(f"    전체 기준 초과 건수: {total_exceedance}")
    print()

    check_summary = {}
    for s in result.get("sections", []):
        has = s.get("has_exceedance", False)
        exc_count = s.get("exceedance_count", 0)
        check_summary[s["section_key"]] = {
            "has_exceedance": has,
            "exceedance_count": exc_count,
        }

        indicators = s.get("indicators", [])
        if not indicators:
            continue

        status_label = "초과 있음" if has else "적합"
        print(f"    {s['title']:<12s}: {status_label}")
        for ind in indicators:
            if ind.get("standard_value") is not None:
                std_unit = ind.get("standard_unit", "")
                status_text = "적합" if ind["status"] == "pass" else "초과"
                mark = "✓" if ind["status"] == "pass" else "✗"
                print(f"      {mark} {ind['indicator']}: "
                      f"기준 {ind['standard_value']} {std_unit}, "
                      f"측정 평균 {ind.get('measured_avg', '-')}, "
                      f"판정 {status_text}")
        # 수질 등급
        if s.get("water_grade"):
            print(f"      수질 등급: {s['water_grade_name']} ({s['water_grade']})")

        if s.get("summary"):
            first_line = s["summary"].split("\n")[0]
            print(f"      요약: {first_line[:80]}")

    return check_summary


# ═══════════════════════════════════════════════════════════════
# 단계 7: 초안 뼈대 + 서술문 (Post-3)
# ═══════════════════════════════════════════════════════════════

async def step7_scaffold(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 scaffold + 서술문 생성."""
    banner("단계 7: 초안 뼈대 + 서술문 생성 (Post-3)")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/scaffold",
        label="초안 뼈대",
    )
    if not result:
        return {}

    print(f"    생성 시각: {result['generated_at']}")
    print(f"    총 근거 데이터: {result['total_evidence_count']}건")
    print()

    scaffold_summary = {}
    prediction_count = 0
    for s in result.get("sections", []):
        entry_count = len(s.get("evidence_entries", []))
        has_narrative = bool(s.get("narrative"))
        has_summary = bool(s.get("summary_text"))
        has_prediction = bool(s.get("prediction_result"))
        has_pred_narrative = bool(s.get("prediction_narrative"))
        scaffold_summary[s["section_key"]] = {
            "evidence_count": entry_count,
            "has_narrative": has_narrative,
            "has_summary": has_summary,
            "has_prediction": has_prediction,
        }
        if has_prediction:
            prediction_count += 1

        status_parts = []
        if entry_count > 0:
            status_parts.append(f"근거 {entry_count}건")
        else:
            status_parts.append("미수집")
        if has_narrative:
            status_parts.append("서술문 있음")
        if has_summary:
            status_parts.append("통계 요약 있음")
        if has_prediction:
            model_name = s["prediction_result"].get("model_name", "")
            status_parts.append(f"예측: {model_name}")

        print(f"    {s['order']:2d}. {s['title']:<12s}  {' | '.join(status_parts)}")

        # 서술문 첫 2줄 미리보기
        narrative = s.get("narrative", "")
        if narrative:
            lines = [l for l in narrative.split("\n") if l.strip()][:2]
            for line in lines:
                print(f"        {line[:70]}")

        # 예측 서술문 첫 줄 미리보기
        if has_pred_narrative:
            pred_lines = [l for l in s["prediction_narrative"].split("\n") if l.strip()]
            if pred_lines:
                print(f"        [예측] {pred_lines[0][:70]}")

    narrative_sections = sum(1 for v in scaffold_summary.values() if v["has_narrative"])
    print()
    print(f"    서술문 존재 섹션: {narrative_sections} / {len(scaffold_summary)}")
    print(f"    예측 결과 포함 섹션: {prediction_count}개")

    return scaffold_summary


# ═══════════════════════════════════════════════════════════════
# 단계 7.5: 영향 예측 실행 (Pred-1~2)
# ═══════════════════════════════════════════════════════════════

async def step7_5_prediction(client: httpx.AsyncClient, project_id: str) -> dict:
    """대기 확산, 소음 전파, 수질 혼합 예측 실행."""
    banner("단계 7.5: 영향 예측 실행 (Pred-1~2)")

    # 예측 모델 목록 조회
    sub_banner("등록된 예측 모델 목록")
    models = await api_call(
        client, "GET", "/api/v1/prediction-models",
        label="예측 모델 목록",
    )
    if models:
        for m in models:
            print(f"    {m['name']:<25s} {m['display_name']}")
            print(f"        적용 섹션: {', '.join(m['applicable_sections'])}")
            input_count = len(m.get("required_inputs", []))
            print(f"        입력 파라미터: {input_count}개")

    pred_summary = {"models_run": [], "results": {}}

    # 대기 확산 예측 (가우시안 플룸)
    sub_banner("7.5-a. 대기 확산 예측 (가우시안 플룸)")
    result = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/predict/air_quality",
        json={
            "model_name": "gaussian_plume",
            "parameters": {},
            "use_background_data": True,
        },
        label="대기 확산 예측",
    )
    if result:
        pred_summary["models_run"].append("gaussian_plume")
        pred_count = len(result.get("predictions", []))
        print(f"    모델: {result['model_name']}")
        print(f"    예측 결과: {pred_count}건")
        # 대표 결과 3건 출력
        for p in result.get("predictions", [])[:3]:
            exceed = " [초과]" if p.get("exceeds_standard") else ""
            print(f"      {p['label']:>6s} {p['pollutant']}: "
                  f"기여 {p['predicted_concentration']:.2f} + "
                  f"현황 {p['background_concentration']:.1f} = "
                  f"합산 {p['total_concentration']:.2f} {p['unit']}{exceed}")
        if pred_count > 3:
            print(f"      ... 외 {pred_count - 3}건")
        # 요약문 첫 줄
        summary = result.get("summary", "")
        if summary:
            print(f"    요약: {summary.split(chr(10))[0][:70]}")
        pred_summary["results"]["air_quality"] = {
            "model": result["model_name"],
            "prediction_count": pred_count,
        }

    # 소음 전파 예측
    sub_banner("7.5-b. 소음 전파 예측 (거리감쇠 + 차음벽)")
    result = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/predict/noise_vibration",
        json={
            "model_name": "noise_propagation",
            "parameters": {},
            "use_background_data": True,
        },
        label="소음 전파 예측",
    )
    if result:
        pred_summary["models_run"].append("noise_propagation")
        pred_count = len(result.get("predictions", []))
        print(f"    모델: {result['model_name']}")
        print(f"    예측 결과: {pred_count}건")
        for p in result.get("predictions", [])[:4]:
            exceed = " [초과]" if p.get("exceeds_standard") else ""
            print(f"      {p['label']:>6s} {p['pollutant']}: "
                  f"합산 {p['total_concentration']:.1f} {p['unit']}{exceed}")
        if pred_count > 4:
            print(f"      ... 외 {pred_count - 4}건")
        summary = result.get("summary", "")
        if summary:
            print(f"    요약: {summary.split(chr(10))[0][:70]}")
        pred_summary["results"]["noise_vibration"] = {
            "model": result["model_name"],
            "prediction_count": pred_count,
        }

    # 수질 혼합 예측
    sub_banner("7.5-c. 수질 혼합 예측 (완전혼합)")
    result = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/predict/water_quality",
        json={
            "model_name": "water_mixing",
            "parameters": {},
            "use_background_data": True,
        },
        label="수질 혼합 예측",
    )
    if result:
        pred_summary["models_run"].append("water_mixing")
        pred_count = len(result.get("predictions", []))
        print(f"    모델: {result['model_name']}")
        print(f"    예측 결과: {pred_count}건")
        for p in result.get("predictions", []):
            exceed = " [초과]" if p.get("exceeds_standard") else ""
            std_str = f", 기준 {p['standard_value']}" if p.get("standard_value") else ""
            print(f"      {p['pollutant']}: "
                  f"혼합 후 {p['total_concentration']:.3f} {p['unit']}"
                  f"{std_str}{exceed}")
        summary = result.get("summary", "")
        if summary:
            print(f"    요약: {summary.split(chr(10))[0][:70]}")
        pred_summary["results"]["water_quality"] = {
            "model": result["model_name"],
            "prediction_count": pred_count,
        }

    # 예측 요약
    sub_banner("영향 예측 요약")
    print(f"    실행된 모델: {len(pred_summary['models_run'])}개 "
          f"({', '.join(pred_summary['models_run'])})")
    total_preds = sum(
        r.get("prediction_count", 0) for r in pred_summary["results"].values()
    )
    print(f"    총 예측 결과: {total_preds}건")

    return pred_summary


# ═══════════════════════════════════════════════════════════════
# 단계 8: LLM 보강 (Post-6, 선택)
# ═══════════════════════════════════════════════════════════════

async def step8_llm_enhance(client: httpx.AsyncClient, project_id: str) -> dict:
    """LLM adapter 상태 확인 후 보강 실행 (adapter가 none이 아닌 경우)."""
    banner("단계 8: LLM 보강 (Post-6)")

    # LLM 상태 확인
    status_result = await api_call(
        client, "GET", "/api/v1/llm/status",
        label="LLM 상태",
    )
    if not status_result:
        return {"adapter": "unknown", "enhanced": []}

    adapter = status_result["adapter"]
    available = status_result["available"]
    print(f"    현재 adapter: {adapter}")
    print(f"    사용 가능: {'예' if available else '아니오'}")
    print(f"    OpenAI 키: {'설정됨' if status_result['openai_key_set'] else '미설정'}")
    print(f"    Google 키: {'설정됨' if status_result['google_key_set'] else '미설정'}")

    llm_summary = {"adapter": adapter, "enhanced": []}

    if adapter == "none":
        print()
        print("    [안내] LLM_ADAPTER=none — 보강을 건너뜁니다.")
        print("    LLM 보강을 사용하려면 .env에서 LLM_ADAPTER를 변경하세요:")
        print("      LLM_ADAPTER=openai_paid + OPENAI_API_KEY=...")
        print("      LLM_ADAPTER=gemini_free + GOOGLE_API_KEY=...")
        return llm_summary

    # 대기질, 수질 섹션에 대해 보강 시도
    test_sections = ["air_quality", "water_quality"]
    for section_key in test_sections:
        sub_banner(f"LLM 보강: {section_key}")
        result = await api_call(
            client, "POST",
            f"/api/v1/llm/projects/{project_id}/enhance",
            json={"section_key": section_key},
            label=f"LLM 보강: {section_key}",
        )
        if result:
            is_fb = result.get("is_fallback", False)
            adapter_used = result.get("adapter_used", "")
            print(f"    adapter: {adapter_used}, fallback: {is_fb}")
            if not is_fb:
                enhanced = result.get("enhanced_narrative", "")
                first_line = enhanced.split("\n")[0] if enhanced else ""
                print(f"    보강 결과 첫 줄: {first_line[:70]}")
                llm_summary["enhanced"].append(section_key)
            else:
                print("    fallback — 원본 그대로 반환됨")

    return llm_summary


# ═══════════════════════════════════════════════════════════════
# 단계 9: QA 실행
# ═══════════════════════════════════════════════════════════════

async def step9_qa(client: httpx.AsyncClient, project_id: str) -> dict:
    """QA 규칙 엔진 실행."""
    banner("단계 9: QA 규칙 엔진 실행")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/qa",
        label="QA 실행",
    )
    if not result:
        return {"export_ready": False}

    summary = result.get("summary", {})
    export_ready = result["export_ready"]

    print(f"    Export 가능: {'예' if export_ready else '아니오'}")
    print(f"    심각(critical): {summary.get('critical_count', 0)}건")
    print(f"    경고(warning): {summary.get('warning_count', 0)}건")
    print(f"    참고(info): {summary.get('info_count', 0)}건")
    print(f"    전체 이슈: {summary.get('total', 0)}건")
    print()

    issues = result.get("issues", [])
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

    severity_label = {"critical": "[심각]", "warning": "[경고]", "info": "[참고]"}
    for issue in issues:
        sev = severity_label.get(issue["severity"], issue["severity"])
        print(f"    {sev} [{issue['rule_id']}] {issue['title']}")
        print(f"           {issue['message']}")
        # R007/R008은 법적 근거 표시
        legal = issue.get("legal_basis", "")
        if legal:
            print(f"           법적 근거: {legal}")

    # R007/R008 법적 필수 항목 규칙 동작 확인
    r007_issues = [i for i in issues if i["rule_id"] == "R007"]
    r008_issues = [i for i in issues if i["rule_id"] == "R008"]
    print()
    print(f"    R007 (법적 필수 섹션 누락): {len(r007_issues)}건")
    print(f"    R008 (법적 필수 지표 누락): {len(r008_issues)}건")
    if r007_issues:
        for r in r007_issues:
            print(f"      → {r['section_key']}: {r['title']}")
    if r008_issues:
        for r in r008_issues:
            print(f"      → {r['section_key']}: {r['title']}")

    return {
        "export_ready": export_ready,
        "critical": summary.get("critical_count", 0),
        "warning": summary.get("warning_count", 0),
        "info": summary.get("info_count", 0),
        "total": summary.get("total", 0),
        "r007_count": len(r007_issues),
        "r008_count": len(r008_issues),
    }


# ═══════════════════════════════════════════════════════════════
# 단계 10: Export (DOCX + PDF, 부록 포함)
# ═══════════════════════════════════════════════════════════════

async def step10_export(client: httpx.AsyncClient, project_id: str) -> dict:
    """DOCX 및 PDF 파일 생성 및 저장 (부록 A/B/C 포함)."""
    banner("단계 10: Export — DOCX + PDF (부록 포함)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_result = {"docx_path": None, "pdf_path": None, "docx_size": 0, "pdf_size": 0}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # DOCX Export (부록 포함)
    sub_banner("DOCX 다운로드 (부록 A/B/C 포함)")
    content = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/export/docx"
        "?include_appendix_a=true&include_appendix_b=true&include_appendix_c=true",
        label="DOCX export",
    )
    if content and isinstance(content, bytes):
        docx_path = str(OUTPUT_DIR / f"demo_gangnam_solar_{timestamp}.docx")
        with open(docx_path, "wb") as f:
            f.write(content)
        export_result["docx_path"] = docx_path
        export_result["docx_size"] = len(content)
        print(f"    DOCX 파일 저장: {docx_path}")
        print(f"    파일 크기: {len(content):,} bytes ({len(content)/1024:.1f} KB)")
    elif content and isinstance(content, dict):
        print(f"    [오류] DOCX 생성 실패: {content}")

    # PDF Export (부록 포함)
    sub_banner("PDF 다운로드 (부록 A/B/C 포함)")
    content = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/export/pdf"
        "?include_appendix_a=true&include_appendix_b=true&include_appendix_c=true",
        label="PDF export",
    )
    if content and isinstance(content, bytes):
        pdf_path = str(OUTPUT_DIR / f"demo_gangnam_solar_{timestamp}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(content)
        export_result["pdf_path"] = pdf_path
        export_result["pdf_size"] = len(content)
        print(f"    PDF 파일 저장: {pdf_path}")
        print(f"    파일 크기: {len(content):,} bytes ({len(content)/1024:.1f} KB)")

        if content[:5] == b"%PDF-":
            print("    PDF 매직 바이트 확인: 유효")
        else:
            print("    [경고] PDF 매직 바이트 불일치")
    elif content and isinstance(content, dict):
        print(f"    [오류] PDF 생성 실패: {content}")

    # 문서 구조 미리보기
    sub_banner("문서 구조 미리보기")
    preview = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/export/preview",
        label="문서 미리보기",
    )
    if preview:
        print(f"    프로젝트명: {preview['project_name']}")
        print(f"    사업유형: {preview.get('project_type', '-')}")
        print(f"    총 증거: {preview['total_evidence']}건")
        print(f"    유사사례: {preview['similar_case_count']}건")
        print(f"    QA 이슈: {preview['qa_issue_count']}건")
        print(f"    Export 가능: {'예' if preview['export_ready'] else '아니오'}")
        print()
        for s in preview.get("sections", []):
            state_label = {"complete": "완료", "partial": "미비", "empty": "미수집"}.get(s["state"], s["state"])
            extras = []
            if s["has_stats"]:
                extras.append("통계")
            if s["has_standards"]:
                extras.append("기준비교")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            print(f"      {s['title']:<12s}: {state_label} ({s['evidence_count']}건){extra_str}")

    return export_result


# ═══════════════════════════════════════════════════════════════
# 단계 11: 결과 요약 비교
# ═══════════════════════════════════════════════════════════════

def step11_summary(
    project_id: str,
    collect_stats: dict,
    section_summary: dict,
    reg_summary: dict,
    stats_summary: dict,
    check_summary: dict,
    scaffold_summary: dict,
    pred_summary: dict,
    llm_summary: dict,
    qa_summary: dict,
    export_result: dict,
):
    """전체 데모 결과 요약 및 기능 비교."""
    banner("단계 11: 최종 결과 요약")

    print(f"    프로젝트 ID: {project_id}")
    print(f"    프로젝트명: 강남구 태양광 발전소 환경영향평가")
    print()

    # 데이터 수집 현황
    print("  ┌─ 데이터 수집 현황 ─────────────────────────────")
    total_evidence = collect_stats.get("total", 0)
    connector_total = sum(collect_stats.get("connectors", {}).values())
    manual_total = sum(collect_stats.get("manual", {}).values())
    print(f"  │ 총 증거 건수: {total_evidence}")
    connector_count = len(collect_stats.get("connectors", {}))
    print(f"  │ 커넥터 수집: {connector_total}건 ({connector_count}개 커넥터)")
    print(f"  │ 수동 입력: {manual_total}건 + 연평균 보충 6건")
    print(f"  │ 커넥터: {', '.join(collect_stats.get('connectors', {}).keys())}")
    print()

    # 섹션 상태
    print("  ┌─ 섹션 플래너 ───────────────────────────────────")
    print(f"  │ 데이터 있는 섹션: {section_summary.get('complete', 0) + section_summary.get('partial', 0)}개 "
          f"(완료 {section_summary.get('complete', 0)} + 부분 {section_summary.get('partial', 0)})")
    print(f"  │ 미수집 섹션: {section_summary.get('empty', 0)}개")
    print()

    # 법령 반영 (Reg-1~Reg-5)
    print("  ┌─ 법령 반영 (Reg-1~Reg-5) ──────────────────────")
    print(f"  │ 평가 범위 API: {'정상' if reg_summary.get('scope_ok') else '미동작'}")
    req_secs = reg_summary.get("required_sections", [])
    print(f"  │ 필수 섹션: {len(req_secs)}개{f' ({', '.join(req_secs[:5])})' if req_secs else ''}")
    print(f"  │ 서술문 법적 근거: {reg_summary.get('narrative_legal_refs', 0)}개 섹션")
    print(f"  │ 환경기준 법적 근거: {reg_summary.get('standards_legal_refs', 0)}건")
    print(f"  │ R007 법적 필수 섹션 누락: {qa_summary.get('r007_count', 0)}건")
    print(f"  │ R008 법적 필수 지표 누락: {qa_summary.get('r008_count', 0)}건")
    print()

    # 통계 엔진
    print("  ┌─ 통계 엔진 (Post-1) ────────────────────────────")
    stats_with_data = sum(1 for v in stats_summary.values() if v > 0) if stats_summary else 0
    print(f"  │ 통계 산출 섹션: {stats_with_data}개")
    print()

    # 환경기준 비교
    print("  ┌─ 환경기준 비교 (Post-2) ────────────────────────")
    sections_with_check = sum(
        1 for v in check_summary.values()
        if v.get("exceedance_count", 0) >= 0 and v != {}
    ) if check_summary else 0
    exceed_count = sum(
        v.get("exceedance_count", 0) for v in check_summary.values()
    ) if check_summary else 0
    print(f"  │ 기준 비교 수행 섹션: {sections_with_check}개")
    print(f"  │ 기준 초과 건수: {exceed_count}")
    print()

    # 서술문 생성
    print("  ┌─ 서술문 생성 (Post-3) ──────────────────────────")
    narrative_count = sum(
        1 for v in scaffold_summary.values() if v.get("has_narrative")
    ) if scaffold_summary else 0
    prediction_count = sum(
        1 for v in scaffold_summary.values() if v.get("has_prediction")
    ) if scaffold_summary else 0
    print(f"  │ 서술문 존재 섹션: {narrative_count}개")
    print(f"  │ 예측 결과 포함 섹션: {prediction_count}개")
    print()

    # 영향 예측
    print("  ┌─ 영향 예측 (Pred-1~2) ──────────────────────────")
    models_run = pred_summary.get("models_run", [])
    print(f"  │ 실행된 모델: {len(models_run)}개")
    for model in models_run:
        r = pred_summary.get("results", {})
        for k, v in r.items():
            if v.get("model") == model:
                print(f"  │   {model}: {v.get('prediction_count', 0)}건 ({k})")
    print()

    # LLM 보강
    print("  ┌─ LLM 보강 (Post-6) ─────────────────────────────")
    print(f"  │ Adapter: {llm_summary.get('adapter', 'unknown')}")
    enhanced = llm_summary.get("enhanced", [])
    print(f"  │ 보강 완료 섹션: {len(enhanced)}개{f' ({', '.join(enhanced)})' if enhanced else ''}")
    print()

    # QA
    print("  ┌─ QA 결과 ───────────────────────────────────────")
    print(f"  │ Export 가능: {'예' if qa_summary.get('export_ready') else '아니오'}")
    print(f"  │ critical: {qa_summary.get('critical', 0)} | "
          f"warning: {qa_summary.get('warning', 0)} | "
          f"info: {qa_summary.get('info', 0)}")
    print()

    # Export
    print("  ┌─ 문서 출력 (Post-5 포맷) ───────────────────────")
    print(f"  │ DOCX: {export_result.get('docx_path', '없음')}")
    if export_result.get("docx_size"):
        print(f"  │       크기: {export_result['docx_size']:,} bytes ({export_result['docx_size']/1024:.1f} KB)")
    print(f"  │ PDF:  {export_result.get('pdf_path', '없음')}")
    if export_result.get("pdf_size"):
        print(f"  │       크기: {export_result['pdf_size']:,} bytes ({export_result['pdf_size']/1024:.1f} KB)")
    print(f"  │ 문서 구조: 표지 + 목차 + 본문 11섹션 + 부록 A/B/C")
    print()

    # 기능 비교 표
    print("  ┌─ MVP → Post-MVP → 법령 → 예측·커넥터 기능 비교 ──")
    print("  │")
    print("  │  기능                 │ MVP (Phase 6)  │ Post-MVP       │ 법령 (Reg)     │ 최종 (Final)")
    print("  │  ─────────────────────┼────────────────┼────────────────┼────────────────┼──────────────")
    print("  │  커넥터 수             │ 2개            │ 6개            │ 6개            │ 8개(+교통,폐기물)")
    print("  │  통계 엔진             │ 미구현         │ 지표별 기술통계 │ (동일)         │ (동일)       ")
    print("  │  환경기준 비교         │ 미구현         │ 대기/수질/소음  │ +법적 근거 열   │ (동일)       ")
    print("  │  서술문 생성           │ 미구현         │ 템플릿 기반     │ +법적 근거 인용 │ +교통/폐기물 ")
    print("  │  영향 예측             │ 미구현         │ 미구현          │ 미구현          │ 3종 모델     ")
    print("  │  QA 규칙              │ 6개            │ 6개            │ 8개(+R007,R008)│ 8개(동일)    ")
    print("  │  평가 범위 판단        │ 미구현         │ 미구현          │ 12개 사업유형   │ (동일)       ")
    print("  │  법령 데이터           │ 없음           │ 없음           │ 3개 모듈       │ (동일)       ")
    print("  │  LLM 보강             │ 미구현         │ 3종 adapter    │ (동일)         │ (동일)       ")
    print("  │  문서 포맷             │ 기본 DOCX      │ 표지+목차+부록  │ +필수 섹션 표시 │ +영향 예측   ")
    print("  │  PDF 출력             │ 미구현         │ reportlab 기반  │ (동일)         │ +영향 예측   ")
    print("  │")
    print("  └─────────────────────────────────────────────────")
    print()


# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  EIA Draft Copilot — 최종 통합 데모 (Final-1)                      ║")
    print("║  시나리오: 서울특별시 강남구 태양광 발전소 건설 프로젝트                ║")
    print("║  범위: Phase 0~6 + Post + Reg + Pred-1~3 + Conn-1 전체 기능       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"  백엔드 URL: {BASE_URL}")
    print(f"  실행 시각: {datetime.now(tz=timezone.utc).isoformat()}")

    # 서버 연결 확인
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print(f"\n  [오류] 백엔드 서버 헬스 체크 실패: HTTP {resp.status_code}")
                print("  백엔드 서버가 실행 중인지 확인하세요.")
                sys.exit(1)
            print(f"  서버 상태: {resp.json()}")
        except httpx.ConnectError:
            print(f"\n  [오류] 백엔드 서버에 연결할 수 없습니다: {BASE_URL}")
            print("  다음 명령으로 서버를 실행하세요:")
            print("    cd backend && uvicorn app.main:app --reload")
            sys.exit(1)

        # ── 단계 1: 프로젝트 생성 ──
        project_id = await step1_create_project(client)
        if not project_id:
            print("\n[오류] 프로젝트 생성 실패. 중단합니다.")
            sys.exit(1)

        # ── 단계 2: 데이터 수집 ──
        collect_stats = await step2_collect_data(client, project_id)

        # ── 단계 3: 유사사례 등록 및 매칭 ──
        await step3_similar_cases(client, project_id)

        # ── 단계 4: 섹션 플래너 ──
        section_summary = await step4_section_planner(client, project_id)

        # ── 단계 4.5: 법령 반영 검증 (Reg-5) ──
        reg_summary = await step4_5_regulation_check(client, project_id)

        # ── 단계 5: 통계 엔진 (Post-1) ──
        stats_summary = await step5_statistics(client, project_id)

        # ── 단계 6: 환경기준 비교 (Post-2) ──
        check_summary = await step6_standards_check(client, project_id)

        # ── 단계 7: 초안 뼈대 + 서술문 (Post-3, Pred-3 예측 포함) ──
        scaffold_summary = await step7_scaffold(client, project_id)

        # ── 단계 7.5: 영향 예측 (Pred-1~2) ──
        pred_summary = await step7_5_prediction(client, project_id)

        # ── 단계 8: LLM 보강 (Post-6) ──
        llm_summary = await step8_llm_enhance(client, project_id)

        # ── 단계 9: QA 실행 ──
        qa_summary = await step9_qa(client, project_id)

        # ── 단계 10: Export ──
        if qa_summary.get("export_ready"):
            export_result = await step10_export(client, project_id)
        else:
            print()
            banner("단계 10: Export — 건너뜀")
            print("    [안내] Export가 차단되었습니다 (critical 이슈 미해결).")
            print("    critical 이슈를 해결한 후 다시 시도하세요.")
            export_result = {}

    # ── 단계 11: 최종 요약 비교 ──
    step11_summary(
        project_id=project_id,
        collect_stats=collect_stats,
        section_summary=section_summary,
        reg_summary=reg_summary,
        stats_summary=stats_summary,
        check_summary=check_summary,
        scaffold_summary=scaffold_summary,
        pred_summary=pred_summary,
        llm_summary=llm_summary,
        qa_summary=qa_summary,
        export_result=export_result,
    )


if __name__ == "__main__":
    asyncio.run(main())
