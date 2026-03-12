# -*- coding: utf-8 -*-
"""실사용 시나리오 전체 흐름 데모 (Post-7 최종판).

시나리오: "서울특별시 강남구 태양광 발전소 건설 프로젝트"

전체 흐름:
  1. 프로젝트 생성
  2. 데이터 수집
     a. 에어코리아 대기질 커넥터
     b. 수질 커넥터
     c. 토양측정망 커넥터 (Post-4)
     d. 기상청 ASOS 기후 커넥터 (Post-4)
     e. 소음·진동 수동 데이터
     f. 생태 수동 데이터
  3. 유사사례 등록 및 매칭
  4. 섹션 플래너 충족도 확인
  5. 통계 엔진 실행 (Post-1)
  6. 환경기준 비교 실행 (Post-2)
  7. 초안 뼈대 + 서술문 생성 (Post-3)
  8. LLM 보강 실행 (Post-6, 선택)
  9. QA 실행
  10. DOCX + PDF export (부록 포함, Post-5)
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
    """6개 경로로 데이터 수집: 커넥터 4종 + 수동 2종."""
    banner("단계 2: 데이터 수집 (커넥터 4종 + 수동 2종)")

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
    if result:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["water_info"] = result["evidence_count"]
    else:
        print("    [경고] 수질 수집 실패 — 수동 수질 데이터로 대체합니다.")
        water_manual = [
            {"category": "water_quality", "indicator": "BOD", "value": "1.8", "numeric_value": 1.8, "unit": "mg/L"},
            {"category": "water_quality", "indicator": "COD", "value": "3.5", "numeric_value": 3.5, "unit": "mg/L"},
            {"category": "water_quality", "indicator": "SS", "value": "8.2", "numeric_value": 8.2, "unit": "mg/L"},
            {"category": "water_quality", "indicator": "T-N", "value": "2.1", "numeric_value": 2.1, "unit": "mg/L"},
            {"category": "water_quality", "indicator": "T-P", "value": "0.04", "numeric_value": 0.04, "unit": "mg/L"},
            {"category": "water_quality", "indicator": "DO", "value": "9.2", "numeric_value": 9.2, "unit": "mg/L"},
        ]
        for ev in water_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 수질: {ev['indicator']}",
            )
        stats["connectors"]["water_info"] = len(water_manual)
        print(f"    수동 수질 데이터 {len(water_manual)}건 추가 완료")

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
    if result:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["soil_info"] = result["evidence_count"]
        if result.get("error_message"):
            print(f"    오류: {result['error_message']}")
    else:
        print("    [경고] 토양 커넥터 실패 — 수동 토양 데이터로 대체합니다.")
        soil_manual = [
            {"category": "soil", "indicator": "납(Pb)", "value": "12.5", "numeric_value": 12.5, "unit": "mg/kg"},
            {"category": "soil", "indicator": "카드뮴(Cd)", "value": "0.8", "numeric_value": 0.8, "unit": "mg/kg"},
            {"category": "soil", "indicator": "유류오염(TPH)", "value": "180", "numeric_value": 180.0, "unit": "mg/kg"},
            {"category": "soil", "indicator": "pH", "value": "6.5", "numeric_value": 6.5, "unit": "-"},
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
    if result:
        print(f"    상태: {result['status']}, 수집 건수: {result['evidence_count']}")
        stats["connectors"]["kma_weather"] = result["evidence_count"]
        if result.get("error_message"):
            print(f"    오류: {result['error_message']}")
    else:
        print("    [경고] 기후 커넥터 실패 — 수동 기후 데이터로 대체합니다.")
        climate_manual = [
            {"category": "climate", "indicator": "기온_연평균", "value": "13.2", "numeric_value": 13.2, "unit": "℃"},
            {"category": "climate", "indicator": "강수량_연평균", "value": "1394", "numeric_value": 1394.0, "unit": "mm"},
            {"category": "climate", "indicator": "풍향·풍속", "value": "서풍 2.3m/s", "numeric_value": 2.3, "unit": "m/s"},
        ]
        for ev in climate_manual:
            await api_call(
                client, "POST", "/api/v1/evidences",
                json={"project_id": project_id, "screening_only": False, **ev},
                expected=201, label=f"수동 기후: {ev['indicator']}",
            )
        stats["connectors"]["kma_weather"] = len(climate_manual)
        print(f"    수동 기후 데이터 {len(climate_manual)}건 추가 완료")

    # 2-e. 수동 증거 — 소음·진동 3건
    sub_banner("2-e. 수동 증거 — 소음·진동 3건")
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

    # 2-f. 수동 증거 — 생태 5건
    sub_banner("2-f. 수동 증거 — 생태 조사 데이터 5건")
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
    for s in result.get("sections", []):
        entry_count = len(s.get("evidence_entries", []))
        has_narrative = bool(s.get("narrative"))
        has_summary = bool(s.get("summary_text"))
        scaffold_summary[s["section_key"]] = {
            "evidence_count": entry_count,
            "has_narrative": has_narrative,
            "has_summary": has_summary,
        }

        status_parts = []
        if entry_count > 0:
            status_parts.append(f"근거 {entry_count}건")
        else:
            status_parts.append("미수집")
        if has_narrative:
            status_parts.append("서술문 있음")
        if has_summary:
            status_parts.append("통계 요약 있음")

        print(f"    {s['order']:2d}. {s['title']:<12s}  {' | '.join(status_parts)}")

        # 서술문 첫 2줄 미리보기
        narrative = s.get("narrative", "")
        if narrative:
            lines = [l for l in narrative.split("\n") if l.strip()][:2]
            for line in lines:
                print(f"        {line[:70]}")

    narrative_sections = sum(1 for v in scaffold_summary.values() if v["has_narrative"])
    print()
    print(f"    서술문 존재 섹션: {narrative_sections} / {len(scaffold_summary)}")

    return scaffold_summary


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

    return {
        "export_ready": export_ready,
        "critical": summary.get("critical_count", 0),
        "warning": summary.get("warning_count", 0),
        "info": summary.get("info_count", 0),
        "total": summary.get("total", 0),
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
    stats_summary: dict,
    check_summary: dict,
    scaffold_summary: dict,
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
    print(f"  │ 커넥터 수집: {connector_total}건 (4개 커넥터)")
    print(f"  │ 수동 입력: {manual_total}건 + 연평균 보충 6건")
    print(f"  │ 커넥터: {', '.join(collect_stats.get('connectors', {}).keys())}")
    print()

    # 섹션 상태
    print("  ┌─ 섹션 플래너 ───────────────────────────────────")
    print(f"  │ 데이터 있는 섹션: {section_summary.get('complete', 0) + section_summary.get('partial', 0)}개 "
          f"(완료 {section_summary.get('complete', 0)} + 부분 {section_summary.get('partial', 0)})")
    print(f"  │ 미수집 섹션: {section_summary.get('empty', 0)}개")
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
    print(f"  │ 서술문 존재 섹션: {narrative_count}개")
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
    print("  ┌─ MVP vs Post-MVP 기능 비교 ─────────────────────")
    print("  │")
    print("  │  기능                 │ MVP (Phase 6)  │ Post-MVP      ")
    print("  │  ─────────────────────┼────────────────┼───────────────")
    print("  │  커넥터 수             │ 2개            │ 4개           ")
    print("  │  통계 엔진             │ 미구현         │ 지표별 기술통계")
    print("  │  환경기준 비교         │ 미구현         │ 대기/수질/소음 ")
    print("  │  서술문 생성           │ 미구현         │ 템플릿 기반    ")
    print("  │  LLM 보강             │ 미구현         │ 3종 adapter   ")
    print("  │  문서 포맷             │ 기본 DOCX      │ 표지+목차+부록 ")
    print("  │  PDF 출력             │ 미구현         │ reportlab 기반 ")
    print("  │  수동 입력 가이드      │ 미구현         │ 10개 분야 안내 ")
    print("  │")
    print("  └─────────────────────────────────────────────────")
    print()


# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  EIA Draft Copilot — Post-MVP 통합 데모 (Post-7)                ║")
    print("║  시나리오: 서울특별시 강남구 태양광 발전소 건설 프로젝트            ║")
    print("║  범위: Phase 0~6 + Post-1~Post-7 전체 기능                      ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
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

        # ── 단계 5: 통계 엔진 (Post-1) ──
        stats_summary = await step5_statistics(client, project_id)

        # ── 단계 6: 환경기준 비교 (Post-2) ──
        check_summary = await step6_standards_check(client, project_id)

        # ── 단계 7: 초안 뼈대 + 서술문 (Post-3) ──
        scaffold_summary = await step7_scaffold(client, project_id)

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
        stats_summary=stats_summary,
        check_summary=check_summary,
        scaffold_summary=scaffold_summary,
        llm_summary=llm_summary,
        qa_summary=qa_summary,
        export_result=export_result,
    )


if __name__ == "__main__":
    asyncio.run(main())
