# -*- coding: utf-8 -*-
"""실사용 시나리오 전체 흐름 데모.

시나리오: "서울특별시 강남구 태양광 발전소 건설 프로젝트"

전체 흐름:
  1. 프로젝트 생성
  2. 데이터 수집 (에어코리아 + 수질 커넥터 + 수동 증거)
  3. 유사사례 등록 및 매칭
  4. 섹션 플래너 충족도 확인
  5. 초안 뼈대 생성
  6. QA 실행
  7. DOCX/PDF Export

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

async def step2_collect_data(client: httpx.AsyncClient, project_id: str) -> bool:
    """에어코리아 + 수질 커넥터 + 수동 증거 추가."""
    banner("단계 2: 데이터 수집")

    success = True

    # 2-1. 에어코리아 커넥터
    sub_banner("2-1. 에어코리아 대기질 커넥터 — 측정소: 강남구")
    result = await api_call(
        client, "POST", "/api/v1/connectors/keco_air/collect",
        json={
            "project_id": project_id,
            "params": {
                "station_name": "강남구",
                "data_term": "DAILY",
            },
            "screening_only": False,
        },
        expected=200, label="에어코리아 수집",
    )
    if result:
        print(f"    상태: {result['status']}")
        print(f"    수집 건수: {result['evidence_count']}")
        if result.get("error_message"):
            print(f"    오류: {result['error_message']}")

    # 커넥터가 수집하는 지표명(PM10, PM2.5 등)과
    # 섹션 플래너 필수 지표명(PM10_연평균 등)이 다르므로 필수 지표를 수동 보충
    sub_banner("2-1b. 대기질 필수 지표(연평균) 수동 보충")
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

    # 2-2. 수질 커넥터
    sub_banner("2-2. 수질 커넥터 — 한강 수계 측정지점")
    result = await api_call(
        client, "POST", "/api/v1/connectors/water_info/collect",
        json={
            "project_id": project_id,
            "params": {
                "year": "2024",
                "pt_no": "1018A60",  # 한강 탄천 측정지점 (강남구 인근)
            },
            "screening_only": False,
        },
        expected=200, label="수질 수집",
    )
    if result:
        print(f"    상태: {result['status']}")
        print(f"    수집 건수: {result['evidence_count']}")
        if result.get("error_message"):
            print(f"    오류: {result['error_message']}")
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
        print(f"    수동 수질 데이터 {len(water_manual)}건 추가 완료")

    # 2-3. 수동 증거 추가: 소음 측정값 2건
    sub_banner("2-3. 수동 증거 — 소음 측정값 2건")
    noise_evidences = [
        {
            "category": "noise_vibration",
            "indicator": "소음_Leq_주간",
            "value": "62.5",
            "numeric_value": 62.5,
            "unit": "dB(A)",
            "observed_at": "2025-11-15T10:00:00",
        },
        {
            "category": "noise_vibration",
            "indicator": "소음_Leq_야간",
            "value": "48.3",
            "numeric_value": 48.3,
            "unit": "dB(A)",
            "observed_at": "2025-11-15T22:00:00",
        },
        {
            "category": "noise_vibration",
            "indicator": "진동_Lv_주간",
            "value": "55.0",
            "numeric_value": 55.0,
            "unit": "dB(V)",
            "observed_at": "2025-11-15T10:00:00",
        },
    ]
    for ev in noise_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"소음: {ev['indicator']}",
        )
        if result:
            print(f"    {ev['indicator']}: {ev['value']} {ev['unit']} — 등록 완료")

    # 2-4. 수동 증거 추가: 생태 관련 5건 (모든 필수 지표)
    sub_banner("2-4. 수동 증거 — 생태 조사 데이터 5건")
    ecology_evidences = [
        {
            "category": "ecology",
            "indicator": "식물상_종수",
            "value": "187",
            "numeric_value": 187.0,
            "unit": "종",
            "observed_at": "2025-10-01T00:00:00",
        },
        {
            "category": "ecology",
            "indicator": "동물상_종수",
            "value": "42",
            "numeric_value": 42.0,
            "unit": "종",
            "observed_at": "2025-10-01T00:00:00",
        },
        {
            "category": "ecology",
            "indicator": "법정보호종",
            "value": "1",
            "numeric_value": 1.0,
            "unit": "종",
            "observed_at": "2025-10-01T00:00:00",
        },
        {
            "category": "ecology",
            "indicator": "비오톱_유형",
            "value": "도시녹지",
            "observed_at": "2025-10-01T00:00:00",
        },
        {
            "category": "ecology",
            "indicator": "녹지자연도",
            "value": "5등급",
            "observed_at": "2025-10-01T00:00:00",
        },
    ]
    for ev in ecology_evidences:
        result = await api_call(
            client, "POST", "/api/v1/evidences",
            json={"project_id": project_id, "screening_only": False, **ev},
            expected=201, label=f"생태: {ev['indicator']}",
        )
        if result:
            print(f"    {ev['indicator']}: {ev['value']} — 등록 완료")

    # 증거 전체 건수 확인
    sub_banner("수집 결과 요약")
    resp = await api_call(
        client, "GET",
        f"/api/v1/evidences?project_id={project_id}&limit=1",
        label="증거 목록",
    )
    if resp:
        print(f"    총 증거 건수: {resp['total']}")

    return success


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

    # 유사사례 등록
    sub_banner("유사사례 등록")
    for case in SIMILAR_CASES:
        result = await api_call(
            client, "POST", "/api/v1/similar-cases",
            json=case, expected=201, label=f"유사사례: {case['name']}",
        )
        if result:
            print(f"    등록: {result['name']} (ID: {result['id'][:8]}...)")

    # 매칭 실행
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

async def step4_section_planner(client: httpx.AsyncClient, project_id: str) -> bool:
    """11개 섹션 충족도 확인."""
    banner("단계 4: 섹션 플래너 — 충족도 확인")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/status",
        label="섹션 상태",
    )
    if not result:
        return False

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

    # complete / partial / empty 카운트
    statuses = [s["status"] for s in sections]
    print()
    print(f"    완료: {statuses.count('complete')}개 | "
          f"부분: {statuses.count('partial')}개 | "
          f"미수집: {statuses.count('empty')}개")

    return True


# ═══════════════════════════════════════════════════════════════
# 단계 5: 초안 뼈대 생성
# ═══════════════════════════════════════════════════════════════

async def step5_scaffold(client: httpx.AsyncClient, project_id: str) -> bool:
    """전체 섹션 scaffold 생성."""
    banner("단계 5: 초안 뼈대 생성")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/sections/scaffold",
        label="초안 뼈대",
    )
    if not result:
        return False

    print(f"    생성 시각: {result['generated_at']}")
    print(f"    총 근거 데이터: {result['total_evidence_count']}건")
    print()

    for s in result.get("sections", []):
        entry_count = len(s.get("evidence_entries", []))
        status = "근거 있음" if entry_count > 0 else "미수집"
        print(f"    {s['order']:2d}. {s['title']:<12s}  {status} ({entry_count}건)")
        # 요약문 첫 줄만 표시
        summary_first = s.get("summary_text", "").split("\n")[0]
        if summary_first:
            print(f"        요약: {summary_first[:60]}...")

    return True


# ═══════════════════════════════════════════════════════════════
# 단계 6: QA 실행
# ═══════════════════════════════════════════════════════════════

async def step6_qa(client: httpx.AsyncClient, project_id: str) -> bool:
    """QA 규칙 엔진 실행."""
    banner("단계 6: QA 규칙 엔진 실행")

    result = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/qa",
        label="QA 실행",
    )
    if not result:
        return False

    summary = result.get("summary", {})
    print(f"    Export 가능: {'예' if result['export_ready'] else '아니오'}")
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
        if issue.get("indicators"):
            print(f"           관련 지표: {', '.join(issue['indicators'])}")

    return result["export_ready"]


# ═══════════════════════════════════════════════════════════════
# 단계 7: Export (DOCX + PDF)
# ═══════════════════════════════════════════════════════════════

async def step7_export(client: httpx.AsyncClient, project_id: str) -> tuple[str | None, str | None]:
    """DOCX 및 PDF 파일 생성 및 저장."""
    banner("단계 7: Export — DOCX + PDF")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docx_path = None
    pdf_path = None

    # DOCX Export
    sub_banner("DOCX 다운로드")
    content = await api_call(
        client, "POST",
        f"/api/v1/projects/{project_id}/export/docx",
        label="DOCX export",
    )
    if content and isinstance(content, bytes):
        docx_path = str(OUTPUT_DIR / f"demo_gangnam_solar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
        with open(docx_path, "wb") as f:
            f.write(content)
        print(f"    DOCX 파일 저장 완료: {docx_path}")
        print(f"    파일 크기: {len(content):,} bytes")
    elif content and isinstance(content, dict):
        print(f"    [오류] DOCX 생성 실패: {content}")

    # PDF Export
    sub_banner("PDF 다운로드")
    content = await api_call(
        client, "GET",
        f"/api/v1/projects/{project_id}/export/pdf",
        label="PDF export",
    )
    if content and isinstance(content, bytes):
        pdf_path = str(OUTPUT_DIR / f"demo_gangnam_solar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(content)
        print(f"    PDF 파일 저장 완료: {pdf_path}")
        print(f"    파일 크기: {len(content):,} bytes")

        # PDF 유효성 검증
        if content[:5] == b"%PDF-":
            print("    PDF 매직 바이트 확인: 유효")
        else:
            print("    [경고] PDF 매직 바이트 불일치")
    elif content and isinstance(content, dict):
        print(f"    [오류] PDF 생성 실패: {content}")

    return docx_path, pdf_path


# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EIA Draft Copilot — 실사용 시나리오 전체 흐름 데모           ║")
    print("║  시나리오: 서울특별시 강남구 태양광 발전소 건설 프로젝트       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  백엔드 URL: {BASE_URL}")
    print(f"  실행 시각: {datetime.now(tz=timezone.utc).isoformat()}")

    # 서버 연결 확인
    async with httpx.AsyncClient(timeout=30) as client:
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
        await step2_collect_data(client, project_id)

        # ── 단계 3: 유사사례 등록 및 매칭 ──
        await step3_similar_cases(client, project_id)

        # ── 단계 4: 섹션 플래너 ──
        await step4_section_planner(client, project_id)

        # ── 단계 5: 초안 뼈대 ──
        await step5_scaffold(client, project_id)

        # ── 단계 6: QA 실행 ──
        export_ready = await step6_qa(client, project_id)

        # ── 단계 7: Export ──
        if export_ready:
            docx_path, pdf_path = await step7_export(client, project_id)
        else:
            print()
            print("    [안내] Export가 차단되었습니다 (critical 이슈 미해결).")
            print("    critical 이슈를 해결한 후 다시 시도하세요.")
            docx_path, pdf_path = None, None

    # ── 최종 요약 ──
    banner("데모 실행 완료 — 최종 요약")
    print(f"    프로젝트 ID: {project_id}")
    print(f"    프로젝트명: 강남구 태양광 발전소 환경영향평가")
    print(f"    Export 가능: {'예' if export_ready else '아니오'}")
    if docx_path:
        print(f"    DOCX 파일: {docx_path}")
    if pdf_path:
        print(f"    PDF 파일:  {pdf_path}")
    if not docx_path and not pdf_path:
        print("    출력 파일: 없음 (Export 차단 또는 오류)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
