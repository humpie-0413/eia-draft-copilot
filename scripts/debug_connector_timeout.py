# -*- coding: utf-8 -*-
"""커넥터 타임아웃 근본 원인 진단 스크립트.

각 문제 커넥터(수질, 기상청, 폐기물)에 대해 직접 API를 호출하여
응답 시간을 측정하고, numOfRows 변경에 따른 영향을 확인한다.
V-world 세종/보령 좌표 실패 원인도 함께 진단한다.

사용법:
  cd backend && python ../scripts/debug_connector_timeout.py
"""

import os
import sys
import time

# Windows cp949 인코딩 이슈 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# backend/.env에서 API 키를 읽기 위해 dotenv 사용
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
ENV_FILE = BACKEND_DIR / ".env"

# dotenv 로드
api_keys = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            api_keys[k.strip()] = v.strip().strip('"').strip("'")

DATA_GO_KR_KEY = api_keys.get("DATA_GO_KR_API_KEY", "")
VWORLD_KEY = api_keys.get("VWORLD_API_KEY", "")

if not DATA_GO_KR_KEY:
    print("[오류] DATA_GO_KR_API_KEY를 backend/.env에서 찾을 수 없습니다.")
    sys.exit(1)

import httpx


def banner(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_api(label: str, url: str, params: dict, timeout: int = 30) -> dict | None:
    """동기 HTTP GET 호출로 응답 시간과 상태를 측정한다."""
    print(f"\n  [{label}]")
    print(f"    URL: {url}")
    print(f"    numOfRows: {params.get('numOfRows', params.get('num_of_rows', 'N/A'))}")
    print(f"    timeout: {timeout}초")

    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=params)
            elapsed = time.time() - start
            print(f"    응답시간: {elapsed:.1f}초")
            print(f"    상태코드: {resp.status_code}")
            print(f"    응답크기: {len(resp.content):,} bytes")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # 응답 구조 요약
                    if isinstance(data, dict):
                        top_keys = list(data.keys())[:5]
                        print(f"    응답 키: {top_keys}")
                    return data
                except Exception:
                    print(f"    응답 (text): {resp.text[:200]}")
                    return None
            else:
                print(f"    응답 (text): {resp.text[:300]}")
                return None
    except httpx.TimeoutException as e:
        elapsed = time.time() - start
        print(f"    [타임아웃] {elapsed:.1f}초 후 타임아웃: {e}")
        return None
    except Exception as e:
        elapsed = time.time() - start
        print(f"    [오류] {elapsed:.1f}초: {type(e).__name__}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 1. 수질 커넥터 (water_info) 진단
# ═══════════════════════════════════════════════════════════════

def test_water_info():
    banner("1. 수질 커넥터 (water_info) — 국립환경과학원 수질 DB")

    base_url = "http://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList"

    # 3개 시나리오의 측정지점
    stations = {
        "양평 (1018A60)": "1018A60",
        "세종 (3008A20)": "3008A20",
        "보령 (4008A10)": "4008A10",
    }

    for scenario, pt_no in stations.items():
        print(f"\n  ── {scenario} ──")

        # numOfRows=10 테스트
        data = test_api(
            f"수질 {scenario} numOfRows=10",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "resultType": "json",
                "year": "2024",
                "ptNoList": pt_no,
                "pageNo": "1",
                "numOfRows": "10",
            },
            timeout=30,
        )
        if data:
            result = data.get("getWaterMeasuringList", {})
            total = result.get("totalCount", "?")
            items = result.get("item", [])
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")

        # numOfRows=100 테스트 (현재 코드 설정)
        data = test_api(
            f"수질 {scenario} numOfRows=100",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "resultType": "json",
                "year": "2024",
                "ptNoList": pt_no,
                "pageNo": "1",
                "numOfRows": "100",
            },
            timeout=60,
        )
        if data:
            result = data.get("getWaterMeasuringList", {})
            total = result.get("totalCount", "?")
            items = result.get("item", [])
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")


# ═══════════════════════════════════════════════════════════════
# 2. 기상청 ASOS (kma_weather) 진단
# ═══════════════════════════════════════════════════════════════

def test_kma_weather():
    banner("2. 기상청 ASOS (kma_weather) — 종관기상관측")

    base_url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

    # 3개 시나리오의 관측소
    stations = {
        "양평 (202)": "202",
        "대전 (133)": "133",
        "보령 (235)": "235",
    }

    for scenario, stn_id in stations.items():
        print(f"\n  ── {scenario} ──")

        # numOfRows=10, 1개월 기간
        data = test_api(
            f"기상청 {scenario} numOfRows=10, 1개월",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "DAY",
                "startDt": "20240101",
                "endDt": "20240131",
                "stnIds": stn_id,
                "pageNo": "1",
                "numOfRows": "10",
            },
            timeout=30,
        )
        if data:
            body = data.get("response", {}).get("body", {})
            total = body.get("totalCount", "?")
            items_wrapper = body.get("items", {})
            items = items_wrapper.get("item", []) if isinstance(items_wrapper, dict) else items_wrapper
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")

        # numOfRows=999, 1년 기간 (현재 코드 설정 — 문제 원인 의심)
        data = test_api(
            f"기상청 {scenario} numOfRows=999, 1년",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "DAY",
                "startDt": "20240101",
                "endDt": "20241231",
                "stnIds": stn_id,
                "pageNo": "1",
                "numOfRows": "999",
            },
            timeout=60,
        )
        if data:
            body = data.get("response", {}).get("body", {})
            total = body.get("totalCount", "?")
            items_wrapper = body.get("items", {})
            items = items_wrapper.get("item", []) if isinstance(items_wrapper, dict) else items_wrapper
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")

        # numOfRows=100으로 제한 테스트
        data = test_api(
            f"기상청 {scenario} numOfRows=100, 1년",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "DAY",
                "startDt": "20240101",
                "endDt": "20241231",
                "stnIds": stn_id,
                "pageNo": "1",
                "numOfRows": "100",
            },
            timeout=60,
        )
        if data:
            body = data.get("response", {}).get("body", {})
            total = body.get("totalCount", "?")
            items_wrapper = body.get("items", {})
            items = items_wrapper.get("item", []) if isinstance(items_wrapper, dict) else items_wrapper
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")


# ═══════════════════════════════════════════════════════════════
# 3. 폐기물 (waste_stats) 진단
# ═══════════════════════════════════════════════════════════════

def test_waste_stats():
    banner("3. 폐기물 (waste_stats) — 생활쓰레기배출정보")

    base_url = "http://apis.data.go.kr/1741000/household_waste_info/info"

    # 3개 시나리오의 지역
    regions = {
        "양평군": "양평군",
        "세종시": "세종시",
        "보령시": "보령시",
    }

    for scenario, region in regions.items():
        print(f"\n  ── {scenario} ──")

        # numOfRows=10 테스트 (현재 코드 설정)
        data = test_api(
            f"폐기물 {scenario} numOfRows=10",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "returnType": "json",
                "pageNo": "1",
                "numOfRows": "10",
                "cond[SGG_NM::LIKE]": region,
            },
            timeout=30,
        )
        if data:
            total = data.get("totalCount", data.get("matchCount", "?"))
            items = data.get("data", [])
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")

        # numOfRows=5 테스트
        data = test_api(
            f"폐기물 {scenario} numOfRows=5",
            base_url,
            {
                "serviceKey": DATA_GO_KR_KEY,
                "returnType": "json",
                "pageNo": "1",
                "numOfRows": "5",
                "cond[SGG_NM::LIKE]": region,
            },
            timeout=30,
        )
        if data:
            total = data.get("totalCount", data.get("matchCount", "?"))
            items = data.get("data", [])
            print(f"    totalCount: {total}, 반환 items: {len(items) if isinstance(items, list) else 'N/A'}")


# ═══════════════════════════════════════════════════════════════
# 4. V-world 세종/보령 실패 진단
# ═══════════════════════════════════════════════════════════════

def test_vworld():
    banner("4. V-world 토지이용 — 세종/보령 좌표 진단")

    if not VWORLD_KEY:
        print("  [건너뜀] VWORLD_API_KEY가 설정되지 않았습니다.")
        return

    base_url = "https://api.vworld.kr/req/data"

    # 3개 시나리오의 좌표
    coords = {
        "양평 (127.49, 37.49)": ("127.49", "37.49"),
        "세종 (127.0, 36.6)": ("127.0", "36.6"),
        "보령 (126.5, 36.3)": ("126.5", "36.3"),
        # 더 구체적인 좌표 테스트
        "세종 구체적 (127.0090, 36.5040)": ("127.0090", "36.5040"),
        "보령 구체적 (126.6126, 36.3335)": ("126.6126", "36.3335"),
    }

    for scenario, (lng, lat) in coords.items():
        print(f"\n  ── {scenario} ──")

        for data_type in ["LT_C_UQ111", "LT_C_LHBLPN"]:
            data = test_api(
                f"V-world {data_type} {scenario}",
                base_url,
                {
                    "service": "data",
                    "request": "GetFeature",
                    "data": data_type,
                    "key": VWORLD_KEY,
                    "domain": "",
                    "geomFilter": f"POINT({lng} {lat})",
                    "crs": "EPSG:4326",
                    "format": "json",
                    "size": "100",
                },
                timeout=15,
            )
            if data:
                resp = data.get("response", {})
                status = resp.get("status", "")
                if status == "OK":
                    features = resp.get("result", {}).get("featureCollection", {}).get("features", [])
                    print(f"    status: OK, features: {len(features)}")
                else:
                    print(f"    status: {status}")
                    record = resp.get("record", {})
                    if record:
                        print(f"    record: {record}")


# ═══════════════════════════════════════════════════════════════
# 요약
# ═══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  커넥터 타임아웃 근본 원인 진단                                      ║")
    print("║  수질 / 기상청 / 폐기물 / V-world                                   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  API 키 존재: DATA_GO_KR={'예' if DATA_GO_KR_KEY else '아니오'}, VWORLD={'예' if VWORLD_KEY else '아니오'}")

    test_water_info()
    test_kma_weather()
    test_waste_stats()
    test_vworld()

    banner("진단 완료 — 요약")
    print("""
  확인 사항:
  1. 수질(water_info): numOfRows=100 vs 10 응답 시간 차이
  2. 기상청(kma_weather): numOfRows=999 → 제한 필요 여부
  3. 폐기물(waste_stats): 세종시/보령시 타임아웃 원인
  4. V-world: 세종/보령 좌표 정밀도 문제 여부
""")


if __name__ == "__main__":
    main()
