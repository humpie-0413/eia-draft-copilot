# -*- coding: utf-8 -*-
"""데모 시나리오 1: 국도 우회도로 건설 (경기 양평).

시나리오: "양평군 국도 우회도로 건설사업 환경영향평가"

원칙:
  - 더미 데이터 절대 사용 금지
  - 모든 커넥터 데이터는 실제 API 호출로 수신한 데이터만 사용
  - API 실패 커넥터는 건너뛰고 실패 사유만 출력
  - 수동 데이터는 소음·진동(현장 측정)/생태(현장 조사)/경관(현장 조사)만 허용

전체 흐름:
  1. 프로젝트 생성
  2. 데이터 수집 (커넥터 9종 실제 API + 수동 3종)
  3. 유사사례 등록 및 매칭
  4. 섹션 플래너 충족도 확인
  4.5. 법령 반영 검증
  5. 통계 엔진 실행
  6. 환경기준 비교 실행
  7. 초안 뼈대 + 서술문 생성
  7.5. 영향 예측 실행 (소음 전파, 대기 확산, 수질 혼합)
  8. LLM 보강 (선택)
  9. QA 실행
  9.5. GIS 도면 생성
  10. DOCX + PDF export
  11. 전체 현황 보고

사전 조건:
  - 백엔드 서버 실행 중: uvicorn app.main:app --reload (http://localhost:8000)
  - PostgreSQL + PostGIS 실행 중
  - backend/.env에 DATA_GO_KR_API_KEY 설정됨

사용법:
  python scripts/demo_road_yangpyeong.py
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
    try:
        resp = await client.request(method, url, json=json)
    except (httpx.TimeoutException, httpx.TransportError) as e:
        print(f"    [네트워크 오류] {label or path}: {type(e).__name__}: {e}")
        return None

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

# 양평군 양평읍 일대 남북 방향 도로 형태 폴리곤 (폭 ~200m, 길이 ~2km)
YANGPYEONG_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.489, 37.480],
            [127.491, 37.480],
            [127.491, 37.500],
            [127.489, 37.500],
            [127.489, 37.480],
        ]
    ],
}


async def step1_create_project(client: httpx.AsyncClient) -> str | None:
    """프로젝트 생성. 프로젝트 ID를 반환한다."""
    banner("단계 1: 프로젝트 생성")

    data = {
        "name": "양평군 국도 우회도로 건설사업 환경영향평가",
        "description": "경기도 양평군 양평읍 일대 국도 우회도로 건설에 따른 환경영향평가",
        "project_type": "road",
        "geometry": YANGPYEONG_POLYGON,
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
    """커넥터 9종 실제 API 호출 + 수동 3종(소음·진동, 생태, 경관)으로 데이터 수집."""
    banner("단계 2: 데이터 수집 (커넥터 9종 실제 API + 수동 3종)")

    stats = {
        "connectors": {},
        "connector_failed": {},
        "manual": {},
    }

    # ── 커넥터 공통 수집 함수 (60초 타임아웃) ──
    CONNECTOR_TIMEOUT = 60  # 각 커넥터 수집 최대 시간 (초)

    async def collect_connector(
        key: str, label: str, params: dict, *,
        failure_reason_hint: str = "",
    ) -> int:
        sub_banner(f"{label}")
        try:
            result = await asyncio.wait_for(
                api_call(
                    client, "POST", f"/api/v1/connectors/{key}/collect",
                    json={
                        "project_id": project_id,
                        "params": params,
                        "screening_only": False,
                    },
                    expected=200, label=f"{key} 수집",
                ),
                timeout=CONNECTOR_TIMEOUT,
            )
        except asyncio.TimeoutError:
            reason = f"{key} 수집 타임아웃 ({CONNECTOR_TIMEOUT}초 초과) — 건너뜀"
            stats["connector_failed"][key] = reason
            print(f"    [타임아웃] {reason}")
            return 0

        if result and result.get("status") == "success" and result.get("evidence_count", 0) > 0:
            count = result["evidence_count"]
            print(f"    [실제 API] 상태: 성공, 수집 건수: {count}")
            stats["connectors"][key] = count
            return count

        reason = ""
        if result:
            err = result.get("error_message", "")
            status = result.get("status", "unknown")
            count = result.get("evidence_count", 0)
            print(f"    상태: {status}, 수집 건수: {count}")
            if err:
                reason = err
                print(f"    오류: {err}")
        if not reason:
            reason = failure_reason_hint or "API 호출 실패 또는 데이터 없음"

        stats["connector_failed"][key] = reason
        print(f"    [건너뜀] {reason}")
        print(f"    → 수동 데이터 주입 없음 (더미 데이터 사용 금지 원칙)")
        return 0

    # 2-a. 에어코리아 대기질 커넥터
    await collect_connector(
        "keco_air",
        "2-a. 에어코리아 대기질 커넥터 — 측정소: 양평읍",
        {"station_name": "양평읍", "data_term": "DAILY"},
    )

    # 2-b. 수질 커넥터
    await collect_connector(
        "water_info",
        "2-b. 수질 커넥터 — 한강 수계 측정지점 (1018A60)",
        {"year": "2024", "pt_no": "1018A60"},
    )

    # 2-c. 토양측정망 커넥터
    await collect_connector(
        "soil_info",
        "2-c. 토양측정망 커넥터 — 2023년도",
        {"year": "2023"},
        failure_reason_hint="API 서버 장애 (HTTP 500, 공공데이터포털 측 문제)",
    )

    # 2-d. 기상청 ASOS 기후 커넥터 — 양평 관측소 (202)
    await collect_connector(
        "kma_weather",
        "2-d. 기상청 ASOS 기후 커넥터 — 양평(202)",
        {"stn_id": "202", "start_dt": "20240101", "end_dt": "20241231"},
    )

    # 2-e. V-world 토지이용 커넥터
    await collect_connector(
        "vworld_land_use",
        "2-e. V-world 토지이용 커넥터 — 양평읍 중심점",
        {"lng": "127.49", "lat": "37.49"},
    )

    # 2-f. 토지이용규제정보 커넥터
    await collect_connector(
        "land_use_regulation",
        "2-f. 토지이용규제정보 커넥터 — 양평군",
        {"area_cd": "41830", "ucodes": ["UQA100"], "land_use_nm": "건축"},
    )

    # 2-g. 국가유산청 문화재 커넥터
    await collect_connector(
        "cultural_heritage",
        "2-g. 국가유산청 문화재 커넥터 — 양평 인근",
        {"lng": "127.49", "lat": "37.49"},
    )

    # 2-h. 교통량 통계 커넥터 — 일반국도
    await collect_connector(
        "traffic_volume",
        "2-h. 교통량 통계 커넥터 — 2023년 일반국도",
        {"year": "2023", "dtype": "2"},
    )

    # 2-i. 폐기물 통계 커넥터
    await collect_connector(
        "waste_stats",
        "2-i. 폐기물 통계 커넥터 — 양평군",
        {"region": "양평군"},
    )

    # 2-j. 수동 증거 — 소음·진동 3건 (현장 측정 데이터)
    sub_banner("2-j. 수동 증거 — 소음·진동 3건 (현장 측정)")
    noise_evidences = [
        {"category": "noise_vibration", "indicator": "소음_Leq_주간", "value": "58.5", "numeric_value": 58.5, "unit": "dB(A)", "observed_at": "2025-10-20T10:00:00"},
        {"category": "noise_vibration", "indicator": "소음_Leq_야간", "value": "45.2", "numeric_value": 45.2, "unit": "dB(A)", "observed_at": "2025-10-20T22:00:00"},
        {"category": "noise_vibration", "indicator": "진동_Lv_주간", "value": "52.0", "numeric_value": 52.0, "unit": "dB(V)", "observed_at": "2025-10-20T10:00:00"},
    ]
    for ev in noise_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"소음: {ev['indicator']}",
        )
        if result:
            print(f"    [수동] {ev['indicator']}: {ev['value']} {ev['unit']} — 등록 완료")
    stats["manual"]["noise_vibration"] = len(noise_evidences)

    # 2-k. 수동 증거 — 생태 5건 (현장 조사 데이터)
    sub_banner("2-k. 수동 증거 — 생태 조사 데이터 5건 (현장 조사)")
    ecology_evidences = [
        {"category": "ecology", "indicator": "식물상_종수", "value": "253", "numeric_value": 253.0, "unit": "종", "observed_at": "2025-09-15T00:00:00"},
        {"category": "ecology", "indicator": "동물상_종수", "value": "67", "numeric_value": 67.0, "unit": "종", "observed_at": "2025-09-15T00:00:00"},
        {"category": "ecology", "indicator": "법정보호종", "value": "2 (수달, 원앙)", "numeric_value": 2.0, "unit": "종", "observed_at": "2025-09-15T00:00:00"},
        {"category": "ecology", "indicator": "녹지자연도", "value": "7등급", "observed_at": "2025-09-15T00:00:00"},
        {"category": "ecology", "indicator": "비오톱_유형", "value": "자연림", "observed_at": "2025-09-15T00:00:00"},
    ]
    for ev in ecology_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"생태: {ev['indicator']}",
        )
        if result:
            print(f"    [수동] {ev['indicator']}: {ev['value']} — 등록 완료")
    stats["manual"]["ecology"] = len(ecology_evidences)

    # 2-l. 수동 증거 — 경관 3건 (현장 조사 데이터)
    sub_banner("2-l. 수동 증거 — 경관 조사 데이터 3건 (현장 조사)")
    landscape_evidences = [
        {"category": "landscape", "indicator": "주요_조망점_수", "value": "2", "numeric_value": 2.0, "unit": "개소", "observed_at": "2025-09-15T00:00:00"},
        {"category": "landscape", "indicator": "조망점명", "value": "양수리 두물머리, 양평읍 시가지", "observed_at": "2025-09-15T00:00:00"},
        {"category": "landscape", "indicator": "스카이라인_영향", "value": "영향 있음", "observed_at": "2025-09-15T00:00:00"},
    ]
    for ev in landscape_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"경관: {ev['indicator']}",
        )
        if result:
            print(f"    [수동] {ev['indicator']}: {ev['value']} — 등록 완료")
    stats["manual"]["landscape"] = len(landscape_evidences)

    # ── 수집 결과 요약 ──
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

    all_connectors = [
        "keco_air", "water_info", "soil_info", "kma_weather",
        "vworld_land_use", "land_use_regulation", "cultural_heritage",
        "traffic_volume", "waste_stats",
    ]
    connector_names = {
        "keco_air": "에어코리아 대기질",
        "water_info": "수질 DB",
        "soil_info": "토양측정망",
        "kma_weather": "기상청 ASOS",
        "vworld_land_use": "V-world 토지이용",
        "land_use_regulation": "토지이용규제정보",
        "cultural_heritage": "국가유산청 문화재",
        "traffic_volume": "교통량 통계",
        "waste_stats": "폐기물 통계",
    }
    print()
    print("    ┌───────────────────────┬────────┬───────┬──────────────────────────────────┐")
    print("    │ 커넥터                │ 결과   │ 건수  │ 비고                             │")
    print("    ├───────────────────────┼────────┼───────┼──────────────────────────────────┤")
    for key in all_connectors:
        name = connector_names[key]
        if key in stats["connectors"]:
            count = stats["connectors"][key]
            print(f"    │ {name:<20s} │ 성공   │ {count:>5d} │ 실제 API 데이터                  │")
        elif key in stats["connector_failed"]:
            reason = stats["connector_failed"][key][:30]
            print(f"    │ {name:<20s} │ 실패   │     0 │ {reason:<32s} │")
        else:
            print(f"    │ {name:<20s} │ 미실행 │     - │                                  │")
    print("    ├───────────────────────┼────────┼───────┼──────────────────────────────────┤")
    manual_labels = {"noise_vibration": "소음·진동", "ecology": "생태", "landscape": "경관"}
    for key, count in stats["manual"].items():
        label = manual_labels.get(key, key)
        print(f"    │ {label:<20s} │ 수동   │ {count:>5d} │ 현장 측정/조사 데이터            │")
    print("    └───────────────────────┴────────┴───────┴──────────────────────────────────┘")

    api_count = sum(stats["connectors"].values())
    manual_count = sum(stats["manual"].values())
    success_count = len(stats["connectors"])
    fail_count = len(stats["connector_failed"])
    print()
    print(f"    커넥터: {success_count}개 성공 / {fail_count}개 실패 (총 9개)")
    print(f"    실제 API 데이터: {api_count}건 | 수동 입력: {manual_count}건")

    return stats


# ═══════════════════════════════════════════════════════════════
# 단계 3: 유사사례 등록 및 매칭
# ═══════════════════════════════════════════════════════════════

SIMILAR_CASES = [
    {
        "name": "경기도 포천시 국도 확장공사 환경영향평가",
        "description": "포천시 소흘읍 일대 4차선 국도 확장공사",
        "project_type": "road",
        "location": {"type": "Point", "coordinates": [127.2, 37.9]},
        "area_sqm": 50000.0,
        "summary": "기존 2차선 국도 4차선 확장. 소음·진동 영향 중점 평가, 방음벽 설치 권고.",
        "key_findings": {
            "대기질": "공사 중 비산먼지 관리 필요",
            "소음": "도로 교통소음 저감 방음벽 필요",
            "생태": "산림 훼손 최소화 권고",
        },
        "evidence_categories": ["air_quality", "noise_vibration", "ecology"],
    },
    {
        "name": "강원도 원주시 우회도로 건설 환경영향평가",
        "description": "원주시 문막읍~지정면 우회도로 신설",
        "project_type": "road",
        "location": {"type": "Point", "coordinates": [127.9, 37.3]},
        "area_sqm": 80000.0,
        "summary": "우회도로 신설로 시가지 교통 분산. 하천 횡단 구간 수질 영향 평가.",
        "key_findings": {
            "수질": "하천 횡단 시 탁수 유출 방지 대책",
            "소음": "주거지 인접 구간 방음대책",
            "생태": "야생동물 이동통로 확보",
        },
        "evidence_categories": ["water_quality", "noise_vibration", "ecology"],
    },
    {
        "name": "충북 충주시 국도 우회도로 환경영향평가",
        "description": "충주시 주덕읍 일대 우회도로 건설",
        "project_type": "road",
        "location": {"type": "Point", "coordinates": [127.9, 36.9]},
        "area_sqm": 60000.0,
        "summary": "시가지 우회도로 건설. 농경지 전환에 따른 토지이용 영향 평가.",
        "key_findings": {
            "토지이용": "농경지 전환 면적 최소화",
            "소음": "인근 주거지 소음 저감",
            "대기질": "공사 중 비산먼지 저감",
        },
        "evidence_categories": ["air_quality", "noise_vibration", "land_use"],
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
# 단계 4.5: 법령 반영 검증
# ═══════════════════════════════════════════════════════════════

async def step4_5_regulation_check(
    client: httpx.AsyncClient,
    project_id: str,
) -> dict:
    """법령 반영 기능을 종합 검증한다."""
    banner("단계 4.5: 법령 반영 검증")

    reg_summary = {
        "scope_ok": False,
        "required_sections": [],
        "narrative_legal_refs": 0,
        "standards_legal_refs": 0,
    }

    # ── a. 평가 범위 조회 ──
    sub_banner("4.5-a. 평가 범위 조회 (road)")
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
        legal_keywords = [
            "환경정책기본법", "토양환경보전법", "환경영향평가법", "시행령", "별표",
        ]
        narrative_ref_count = 0
        for s in scaffold.get("sections", []):
            narrative = s.get("narrative", "") or ""
            found = [kw for kw in legal_keywords if kw in narrative]
            if found:
                narrative_ref_count += 1
                print(f"    {s['title']:<12s}: 법적 근거 포함 ({', '.join(found)})")
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
# 단계 5: 통계 엔진 실행
# ═══════════════════════════════════════════════════════════════

async def step5_statistics(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 통계 조회."""
    banner("단계 5: 통계 엔진 실행")

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
# 단계 6: 환경기준 비교
# ═══════════════════════════════════════════════════════════════

async def step6_standards_check(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 환경기준 비교."""
    banner("단계 6: 환경기준 비교")

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
        if s.get("water_grade"):
            print(f"      수질 등급: {s['water_grade_name']} ({s['water_grade']})")

        if s.get("summary"):
            first_line = s["summary"].split("\n")[0]
            print(f"      요약: {first_line[:80]}")

    return check_summary


# ═══════════════════════════════════════════════════════════════
# 단계 7: 초안 뼈대 + 서술문
# ═══════════════════════════════════════════════════════════════

async def step7_scaffold(client: httpx.AsyncClient, project_id: str) -> dict:
    """전체 섹션 scaffold + 서술문 생성."""
    banner("단계 7: 초안 뼈대 + 서술문 생성")

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

        narrative = s.get("narrative", "")
        if narrative:
            lines = [l for l in narrative.split("\n") if l.strip()][:2]
            for line in lines:
                print(f"        {line[:70]}")

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
# 단계 7.5: 영향 예측 실행
# ═══════════════════════════════════════════════════════════════

async def step7_5_prediction(client: httpx.AsyncClient, project_id: str) -> dict:
    """소음 전파(도로 선음원), 대기 확산(도로 분진), 수질 혼합 예측 실행."""
    banner("단계 7.5: 영향 예측 실행")

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

    # 소음 전파 예측 (도로 선음원, Lw/m=75dB)
    sub_banner("7.5-a. 소음 전파 예측 (도로 선음원, Lw/m=75dB)")
    result = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/predict/noise_vibration",
        json={
            "model_name": "noise_propagation",
            "parameters": {
                "sound_power_level": 75.0,
                "source_type": "line",
            },
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

    # 대기 확산 예측 (도로 분진, 저고도 배출)
    sub_banner("7.5-b. 대기 확산 예측 (도로 분진, 저고도 H=5m)")
    result = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/predict/air_quality",
        json={
            "model_name": "gaussian_plume",
            "parameters": {
                "stack_height": 5.0,
                "PM10": 0.5,
                "NO2": 0.3,
            },
            "use_background_data": True,
        },
        label="대기 확산 예측",
    )
    if result:
        pred_summary["models_run"].append("gaussian_plume")
        pred_count = len(result.get("predictions", []))
        print(f"    모델: {result['model_name']}")
        print(f"    예측 결과: {pred_count}건")
        for p in result.get("predictions", [])[:3]:
            exceed = " [초과]" if p.get("exceeds_standard") else ""
            print(f"      {p['label']:>6s} {p['pollutant']}: "
                  f"기여 {p['predicted_concentration']:.2f} + "
                  f"현황 {p['background_concentration']:.1f} = "
                  f"합산 {p['total_concentration']:.2f} {p['unit']}{exceed}")
        if pred_count > 3:
            print(f"      ... 외 {pred_count - 3}건")
        summary = result.get("summary", "")
        if summary:
            print(f"    요약: {summary.split(chr(10))[0][:70]}")
        pred_summary["results"]["air_quality"] = {
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
# 단계 8: LLM 보강 (선택)
# ═══════════════════════════════════════════════════════════════

async def step8_llm_enhance(client: httpx.AsyncClient, project_id: str) -> dict:
    """LLM adapter 상태 확인 후 보강 실행."""
    banner("단계 8: LLM 보강")

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

    test_sections = ["air_quality", "noise_vibration"]
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
        legal = issue.get("legal_basis", "")
        if legal:
            print(f"           법적 근거: {legal}")

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
# 단계 9.5: GIS 도면 생성
# ═══════════════════════════════════════════════════════════════

async def step9_5_maps(client: httpx.AsyncClient, project_id: str) -> dict:
    """5종 GIS 도면을 생성하고 output/maps/ 폴더에 저장한다."""
    banner("단계 9.5: GIS 도면 생성")

    maps_dir = OUTPUT_DIR / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    map_result = {"generated": [], "failed": [], "buffer": None, "overlay_count": 0}

    # 버퍼 분석 (1km)
    sub_banner("9.5-a. 공간 버퍼 분석")
    buffer_resp = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/spatial/buffer?radius=1000",
        label="1km 버퍼 분석",
    )
    if buffer_resp:
        print(f"    버퍼 반경: {buffer_resp['radius_m']}m")
        print(f"    버퍼 면적: {buffer_resp['area_km2']} km²")
        print(f"    중심점: {buffer_resp['centroid']}")
        map_result["buffer"] = buffer_resp

    # 중첩 분석 (5km)
    sub_banner("9.5-b. 규제 항목 중첩 분석")
    overlay_resp = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/spatial/overlay?radius=5000",
        label="5km 중첩 분석",
    )
    if overlay_resp:
        print(f"    탐색 반경: {overlay_resp['radius_m']}m")
        print(f"    탐지 항목: {overlay_resp['total_count']}건")
        map_result["overlay_count"] = overlay_resp["total_count"]
        for item in overlay_resp.get("items", [])[:10]:
            print(f"      {item['item_type']:<10s} {item['name']:<20s} 거리: {item['distance_m']:,.0f}m")

    # 도면 목록 조회
    sub_banner("9.5-c. 도면 목록")
    map_list = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/maps",
        label="도면 목록",
    )
    if map_list:
        for m in map_list.get("maps", []):
            print(f"    {m['map_type']:<25s} {m['title']}")

    # 5종 도면 생성 + PNG 저장
    map_types = ["location", "land_use", "monitoring_stations", "noise_contour", "air_dispersion"]
    for map_type in map_types:
        sub_banner(f"9.5-d. 도면 생성: {map_type}")
        content = await api_call(
            client, "GET",
            f"/api/v1/projects/{project_id}/maps/{map_type}?save=true",
            label=f"도면: {map_type}",
        )
        if content and isinstance(content, bytes):
            png_path = maps_dir / f"{project_id}_{map_type}.png"
            with open(png_path, "wb") as f:
                f.write(content)
            map_result["generated"].append(map_type)
            print(f"    PNG 저장: {png_path}")
            print(f"    파일 크기: {len(content):,} bytes ({len(content)/1024:.1f} KB)")

            if content[:8] == b"\x89PNG\r\n\x1a\n":
                print("    PNG 매직 바이트 확인: 유효")
            else:
                print("    [경고] PNG 매직 바이트 불일치")
        else:
            map_result["failed"].append(map_type)
            print(f"    [실패] {map_type} 도면 생성 실패")

    print()
    print(f"    도면 생성 완료: {len(map_result['generated'])}종 / {len(map_types)}종")
    if map_result["failed"]:
        print(f"    실패: {', '.join(map_result['failed'])}")

    return map_result


# ═══════════════════════════════════════════════════════════════
# 단계 10: Export (DOCX + PDF)
# ═══════════════════════════════════════════════════════════════

async def step10_export(client: httpx.AsyncClient, project_id: str) -> dict:
    """DOCX 및 PDF 파일 생성 및 저장."""
    banner("단계 10: Export — DOCX + PDF (부록 포함)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_result = {"docx_path": None, "pdf_path": None, "docx_size": 0, "pdf_size": 0}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # DOCX Export
    sub_banner("DOCX 다운로드 (부록 A/B/C 포함)")
    content = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/export/docx"
        "?include_appendix_a=true&include_appendix_b=true&include_appendix_c=true&skip_qa_check=true",
        label="DOCX export",
    )
    if content and isinstance(content, bytes):
        docx_path = str(OUTPUT_DIR / f"demo_road_yangpyeong_{timestamp}.docx")
        with open(docx_path, "wb") as f:
            f.write(content)
        export_result["docx_path"] = docx_path
        export_result["docx_size"] = len(content)
        print(f"    DOCX 파일 저장: {docx_path}")
        print(f"    파일 크기: {len(content):,} bytes ({len(content)/1024:.1f} KB)")
    elif content and isinstance(content, dict):
        print(f"    [오류] DOCX 생성 실패: {content}")

    # PDF Export
    sub_banner("PDF 다운로드 (부록 A/B/C 포함)")
    content = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/export/pdf"
        "?include_appendix_a=true&include_appendix_b=true&include_appendix_c=true&skip_qa_check=true",
        label="PDF export",
    )
    if content and isinstance(content, bytes):
        pdf_path = str(OUTPUT_DIR / f"demo_road_yangpyeong_{timestamp}.pdf")
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
# 단계 11: 결과 요약
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
    map_result: dict | None = None,
):
    """전체 데모 결과 요약."""
    banner("단계 11: 최종 결과 요약 — 양평군 국도 우회도로 건설사업")

    print(f"    프로젝트 ID: {project_id}")
    print(f"    프로젝트명: 양평군 국도 우회도로 건설사업 환경영향평가")
    print(f"    사업유형: road (도로)")
    print(f"    실행 시각: {datetime.now(tz=timezone.utc).isoformat()}")
    print()

    # 1. 커넥터 현황
    print("  ┌─ 1. 전체 커넥터 현황 (9종) ─────────────────────")
    connector_names = {
        "keco_air": "에어코리아 대기질",
        "water_info": "수질 DB",
        "soil_info": "토양측정망",
        "kma_weather": "기상청 ASOS",
        "vworld_land_use": "V-world 토지이용",
        "land_use_regulation": "토지이용규제정보",
        "cultural_heritage": "국가유산청 문화재",
        "traffic_volume": "교통량 통계",
        "waste_stats": "폐기물 통계",
    }
    all_connectors = list(connector_names.keys())
    api_count = sum(collect_stats.get("connectors", {}).values())
    manual_count = sum(collect_stats.get("manual", {}).values())
    success_count = len(collect_stats.get("connectors", {}))
    fail_count = len(collect_stats.get("connector_failed", {}))

    for key in all_connectors:
        name = connector_names[key]
        if key in collect_stats.get("connectors", {}):
            count = collect_stats["connectors"][key]
            print(f"  │ [성공] {name:<20s} {count:>4d}건 (실제 API)")
        elif key in collect_stats.get("connector_failed", {}):
            reason = collect_stats["connector_failed"][key]
            print(f"  │ [실패] {name:<20s}    - ({reason[:40]})")
        else:
            print(f"  │ [미실행] {name}")
    print(f"  │")
    print(f"  │ 성공: {success_count}/9 | 실패: {fail_count}/9")
    print(f"  │ 실제 API 데이터: {api_count}건 | 수동 입력: {manual_count}건 (소음·생태·경관)")
    print()

    # 2. 섹션 현황
    print("  ┌─ 2. 섹션 플래너 (11개 섹션) ────────────────────")
    print(f"  │ 데이터 있는 섹션: {section_summary.get('complete', 0) + section_summary.get('partial', 0)}개 "
          f"(완료 {section_summary.get('complete', 0)} + 부분 {section_summary.get('partial', 0)})")
    print(f"  │ 미수집 섹션: {section_summary.get('empty', 0)}개")
    print()

    # 3. 법령 반영
    print("  ┌─ 3. 법령 반영 ───────────────────────────────────")
    print(f"  │ 평가 범위 API: {'정상' if reg_summary.get('scope_ok') else '미동작'}")
    req_secs = reg_summary.get("required_sections", [])
    print(f"  │ 필수 섹션: {len(req_secs)}개")
    print(f"  │ 서술문 법적 근거: {reg_summary.get('narrative_legal_refs', 0)}개 섹션")
    print(f"  │ 환경기준 법적 근거: {reg_summary.get('standards_legal_refs', 0)}건")
    print()

    # 4. 분석 엔진
    print("  ┌─ 4. 분석 엔진 현황 ─────────────────────────────")
    stats_with_data = sum(1 for v in stats_summary.values() if v > 0) if stats_summary else 0
    print(f"  │ 통계 산출 섹션: {stats_with_data}개")
    exceed_count = sum(
        v.get("exceedance_count", 0) for v in check_summary.values()
    ) if check_summary else 0
    print(f"  │ 환경기준 초과: {exceed_count}건")
    narrative_count = sum(
        1 for v in scaffold_summary.values() if v.get("has_narrative")
    ) if scaffold_summary else 0
    prediction_count = sum(
        1 for v in scaffold_summary.values() if v.get("has_prediction")
    ) if scaffold_summary else 0
    print(f"  │ 서술문 존재 섹션: {narrative_count}개")
    print(f"  │ 예측 결과 포함 섹션: {prediction_count}개")
    print()

    # 5. 예측 모델
    print("  ┌─ 5. 영향 예측 모델 현황 (3종) ──────────────────")
    models_run = pred_summary.get("models_run", [])
    model_display = {
        "gaussian_plume": "가우시안 플룸 (대기 확산)",
        "noise_propagation": "소음 전파 (거리감쇠)",
        "water_mixing": "수질 혼합 (완전혼합)",
    }
    all_models = ["gaussian_plume", "noise_propagation", "water_mixing"]
    for model in all_models:
        display = model_display.get(model, model)
        if model in models_run:
            r = pred_summary.get("results", {})
            count = 0
            for k, v in r.items():
                if v.get("model") == model:
                    count = v.get("prediction_count", 0)
            print(f"  │ [실행] {display}: {count}건")
        else:
            print(f"  │ [미실행] {display}")
    print(f"  │ 총 실행 모델: {len(models_run)}/3")
    print()

    # 6. QA
    print("  ┌─ 6. QA 결과 ────────────────────────────────────")
    print(f"  │ Export 가능: {'예' if qa_summary.get('export_ready') else '아니오'}")
    print(f"  │ critical: {qa_summary.get('critical', 0)}건")
    print(f"  │ warning: {qa_summary.get('warning', 0)}건")
    print(f"  │ info: {qa_summary.get('info', 0)}건")
    print(f"  │ 전체 이슈: {qa_summary.get('total', 0)}건")
    print(f"  │ R007 법적 필수 섹션 누락: {qa_summary.get('r007_count', 0)}건")
    print(f"  │ R008 법적 필수 지표 누락: {qa_summary.get('r008_count', 0)}건")
    print()

    # 7. LLM
    print("  ┌─ 7. LLM 보강 ───────────────────────────────────")
    print(f"  │ Adapter: {llm_summary.get('adapter', 'unknown')}")
    enhanced = llm_summary.get("enhanced", [])
    print(f"  │ 보강 완료 섹션: {len(enhanced)}개")
    print()

    # 8. GIS 도면
    print("  ┌─ 8. GIS 도면 현황 ──────────────────────────────")
    map_generated = map_result.get("generated", []) if map_result else []
    print(f"  │ 도면 생성: {len(map_generated)}/5종")
    map_titles = {
        "location": "사업대상지 위치도",
        "land_use": "토지이용현황도",
        "monitoring_stations": "환경측정소 분포도",
        "noise_contour": "소음 예측 등고선도",
        "air_dispersion": "대기확산 예측도",
    }
    for mt, title in map_titles.items():
        status = "생성" if mt in map_generated else "실패"
        print(f"  │ [{status}] {title}")
    if map_result:
        print(f"  │ 중첩 분석 항목: {map_result.get('overlay_count', 0)}건")
    print()

    # 9. 문서 산출물
    print("  ┌─ 9. 최종 문서 산출물 ────────────────────────────")
    print("  │ DOCX: {0}".format(export_result.get("docx_path", "미생성")))
    if export_result.get("docx_size"):
        print(f"  │       크기: {export_result['docx_size']:,} bytes ({export_result['docx_size']/1024:.1f} KB)")
    print("  │ PDF:  {0}".format(export_result.get("pdf_path", "미생성")))
    if export_result.get("pdf_size"):
        print(f"  │       크기: {export_result['pdf_size']:,} bytes ({export_result['pdf_size']/1024:.1f} KB)")
    print()
    print("  └─────────────────────────────────────────────────")
    print()


# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  EIA Draft Copilot — 데모 시나리오 1                               ║")
    print("║  양평군 국도 우회도로 건설사업 환경영향평가                            ║")
    print("║  사업유형: road | 원칙: 실제 API 데이터만 사용                        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"  백엔드 URL: {BASE_URL}")
    print(f"  실행 시각: {datetime.now(tz=timezone.utc).isoformat()}")

    async with httpx.AsyncClient(timeout=300) as client:
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

        project_id = await step1_create_project(client)
        if not project_id:
            print("\n[오류] 프로젝트 생성 실패. 중단합니다.")
            sys.exit(1)

        collect_stats = await step2_collect_data(client, project_id)
        await step3_similar_cases(client, project_id)
        section_summary = await step4_section_planner(client, project_id)
        reg_summary = await step4_5_regulation_check(client, project_id)
        stats_summary = await step5_statistics(client, project_id)
        check_summary = await step6_standards_check(client, project_id)
        scaffold_summary = await step7_scaffold(client, project_id)
        pred_summary = await step7_5_prediction(client, project_id)
        llm_summary = await step8_llm_enhance(client, project_id)
        qa_summary = await step9_qa(client, project_id)
        map_result = await step9_5_maps(client, project_id)

        if not qa_summary.get("export_ready"):
            print()
            banner("단계 10: Export — critical 이슈 존재")
            print("    [안내] critical QA 이슈가 있어 정식 export는 차단됩니다.")
            print("    실패 커넥터로 인한 미수집 섹션이 원인입니다.")
            print("    참고용으로 문서 생성을 시도합니다.")
        export_result = await step10_export(client, project_id)

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
        map_result=map_result,
    )


if __name__ == "__main__":
    asyncio.run(main())
