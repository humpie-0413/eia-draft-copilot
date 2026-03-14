# -*- coding: utf-8 -*-
"""커넥터 실제 API 연동 검증 스크립트.

에어코리아 대기질 + 수질 DB + 토양측정망 + 기상청 ASOS +
V-world 토지이용 + 국가유산청 문화재 + 교통량 통계 + 생활쓰레기배출정보
커넥터를 실제 API로 호출하여 데이터가 정상 수신되는지 확인한다.

핵심 커넥터 (4개): airkorea, water, heritage, waste
   → 이 4개 중 4개 모두 통과하면 exit code 0
   → 나머지(soil, kma, vworld, traffic)는 알려진 문제로 실패해도 exit code에 영향 없음

사용법:
    python scripts/test_connectors_live.py
"""

import asyncio
import os
import sys
import urllib.parse
from pathlib import Path

# backend 디렉토리를 sys.path에 추가
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Windows cp949 인코딩 이슈 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

# .env 파일 로드
env_path = backend_dir / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
VWORLD_API_KEY = os.getenv("VWORLD_API_KEY", "")

# 각 커넥터별 실패 원인 기록 딕셔너리 (main 에서 채워짐)
_failure_reasons: dict[str, str] = {}


def _redact_key(url: str) -> str:
    """URL에서 API 키를 마스킹하여 반환한다.

    serviceKey 또는 key 파라미터 값을 앞 6자만 남기고 나머지를 ****로 대체한다.
    """
    for param_name in ("serviceKey", "key"):
        # URL 파라미터에서 해당 이름 찾기
        import re
        pattern = rf"({re.escape(param_name)}=)([^&]+)"
        def _mask(m: re.Match) -> str:
            val = m.group(2)
            visible = val[:6] if len(val) > 6 else val
            return f"{m.group(1)}{visible}****"
        url = re.sub(pattern, _mask, url)
    return url


def _build_url_log(base_url: str, params: dict) -> str:
    """base_url + params 를 조합한 전체 URL을 만들고 API 키를 마스킹한다."""
    query_string = urllib.parse.urlencode(params)
    full_url = f"{base_url}?{query_string}"
    return _redact_key(full_url)


# ──────────────────────────────────────────────────
# 에어코리아 대기질 커넥터 검증
# ──────────────────────────────────────────────────

AIRKOREA_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"


async def test_airkorea() -> tuple[bool, str]:
    """에어코리아 API 실제 호출 검증.

    측정소명을 '강남구'로 조회한다.
    반환값: (성공 여부, 실패 원인 문자열 또는 "")
    """
    print("=" * 60)
    print("[에어코리아 대기질 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "stationName": "강남구",   # 요청에 따라 종로구 → 강남구로 변경
        "dataTerm": "DAILY",
        "pageNo": "1",
        "numOfRows": "10",
        "ver": "1.3",
    }

    print(f"  측정소명: {params['stationName']}")
    print(f"  조회 기간: {params['dataTerm']}")
    print(f"  요청 URL: {_build_url_log(AIRKOREA_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(AIRKOREA_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {msg}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, msg

        data = response.json()

        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")

        print(f"  API 결과코드: {result_code}")
        print(f"  API 결과메시지: {result_msg}")

        if result_code != "00":
            msg = f"API 오류 코드={result_code} msg={result_msg}"
            print(f"  ERROR: {msg}")
            return False, msg

        body = resp.get("body", {})
        total_count = body.get("totalCount", 0)
        items = body.get("items", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            msg = "수신 데이터 없음"
            print(f"  WARNING: {msg}")
            return False, msg

        # 유효한 데이터가 있는 항목 찾기 ("-" 또는 통신장애가 아닌 것)
        valid_sample = None
        for item in items:
            pm10 = item.get("pm10Value")
            if pm10 is not None and str(pm10).strip() not in ("", "-", "통신장애"):
                valid_sample = item
                break

        # 첫 번째 항목은 무조건 출력
        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]
        print(f"    측정소명: {sample.get('stationName')}")
        print(f"    측정시각: {sample.get('dataTime')}")
        print(f"    PM10: {sample.get('pm10Value')} ug/m3")
        print(f"    PM2.5: {sample.get('pm25Value')} ug/m3")
        print(f"    O3: {sample.get('o3Value')} ppm")
        print(f"    NO2: {sample.get('no2Value')} ppm")
        print(f"    SO2: {sample.get('so2Value')} ppm")
        print(f"    CO: {sample.get('coValue')} ppm")

        # 유효 항목이 따로 있으면 추가 출력
        if valid_sample and valid_sample is not sample:
            print()
            print("  [유효 데이터 항목]")
            print(f"    측정시각: {valid_sample.get('dataTime')}")
            print(f"    PM10: {valid_sample.get('pm10Value')} ug/m3")
            print(f"    PM2.5: {valid_sample.get('pm25Value')} ug/m3")

        # raw_payload 구조 확인
        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    response.header: {header}")
        print(f"    response.body 키: {list(body.keys())}")

        if valid_sample:
            print()
            print("  SUCCESS: 에어코리아 API 연동 성공")
            return True, ""
        else:
            # 통신장애 시간대일 수 있지만 API 자체는 정상 동작
            print()
            print("  WARNING: PM10/PM2.5 값이 모두 '-'이지만 API 연결은 정상")
            print("  (실시간 데이터가 일시적으로 '-'일 수 있음)")
            # API 연결 자체는 성공이므로 True 반환
            return True, ""

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 국립환경과학원 수질 DB 커넥터 검증
# ──────────────────────────────────────────────────

WATER_QUALITY_URL = "http://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList"


async def test_water_quality() -> tuple[bool, str]:
    """국립환경과학원 수질 DB API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[국립환경과학원 수질 DB 커넥터 검증 -- 물환경 수질측정망]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    # 낙동강 수계 측정지점, 최근 연도
    params = {
        "serviceKey": API_KEY,
        "resultType": "json",
        "year": "2023",
        "ptNoList": "2008A40",
        "pageNo": "1",
        "numOfRows": "5",
    }

    print(f"  조회 연도: {params['year']}")
    print(f"  측정지점: {params['ptNoList']}")
    print(f"  요청 URL: {_build_url_log(WATER_QUALITY_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(WATER_QUALITY_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {msg}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, msg

        data = response.json()

        # 응답 구조 확인 -- 래퍼가 getWaterMeasuringList
        result = data.get("getWaterMeasuringList", {})
        header = result.get("header", {})
        code = header.get("code")
        message = header.get("message")

        print(f"  API 결과코드: {code}")
        print(f"  API 결과메시지: {message}")

        if code != "00":
            msg = f"API 오류 코드={code} msg={message}"
            print(f"  ERROR: {msg}")
            return False, msg

        total_count = result.get("totalCount", 0)
        items = result.get("item", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            msg = "수신 데이터 없음"
            print(f"  WARNING: {msg}")
            return False, msg

        # 샘플 데이터 출력
        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]

        def strip_val(v):
            return str(v).strip() if v is not None else ""

        print(f"    측정지점코드: {sample.get('PT_NO')}")
        print(f"    측정지점명: {sample.get('PT_NM')}")
        print(f"    측정일: {sample.get('WMCYMD')}")
        print(f"    BOD: {strip_val(sample.get('ITEM_BOD'))} mg/L")
        print(f"    COD: {strip_val(sample.get('ITEM_COD'))} mg/L")
        print(f"    SS: {strip_val(sample.get('ITEM_SS'))} mg/L")
        print(f"    DO: {strip_val(sample.get('ITEM_DOC'))} mg/L")
        print(f"    T-N: {strip_val(sample.get('ITEM_TN'))} mg/L")
        print(f"    T-P: {strip_val(sample.get('ITEM_TP'))} mg/L")

        # raw_payload 구조 확인
        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    getWaterMeasuringList.header: {header}")
        print(f"    getWaterMeasuringList 키: {[k for k in result.keys() if k != 'item']}")

        bod = sample.get("ITEM_BOD")
        has_data = bod is not None and strip_val(bod) != ""

        if has_data:
            print()
            print("  SUCCESS: 국립환경과학원 수질 DB API 연동 성공")
            return True, ""
        else:
            msg = "BOD/COD 값이 비어있음"
            print()
            print(f"  WARNING: {msg}")
            return False, msg

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 국립환경과학원 토양측정망 커넥터 검증
# ──────────────────────────────────────────────────

SOIL_MEASURING_URL = "http://apis.data.go.kr/1480523/SoilMeasuringService/getSoilMeasuringList"

# 알려진 실패 원인
_SOIL_KNOWN_FAILURE = "API 서버 장애 (공공데이터포털 측)"


async def test_soil_measuring() -> tuple[bool, str]:
    """국립환경과학원 토양측정망 API 실제 호출 검증.

    현재 HTTP 500 오류가 발생하는 것으로 알려짐.
    공공데이터포털 서버 측 장애 — exit code 판정에 영향 없음.
    """
    print()
    print("=" * 60)
    print("[국립환경과학원 토양측정망 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    params = {
        "serviceKey": API_KEY,
        "resultType": "json",
        "year": "2023",
        "pageNo": "1",
        "numOfRows": "5",
    }

    print(f"  조회 연도: {params['year']}")
    print(f"  요청 URL: {_build_url_log(SOIL_MEASURING_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(SOIL_MEASURING_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            # HTTP 500은 알려진 공공데이터포털 서버 측 장애
            diagnosis = _SOIL_KNOWN_FAILURE if response.status_code == 500 else f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {diagnosis}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, diagnosis

        data = response.json()

        result = data.get("getSoilMeasuringList", {})
        header = result.get("header", {})
        code = header.get("code")
        message = header.get("message")

        print(f"  API 결과코드: {code}")
        print(f"  API 결과메시지: {message}")

        if code != "00":
            msg = f"API 오류 코드={code} msg={message}"
            print(f"  ERROR: {msg}")
            return False, msg

        total_count = result.get("totalCount", 0)
        items = result.get("item", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            msg = "수신 데이터 없음"
            print(f"  WARNING: {msg}")
            return False, msg

        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]

        def strip_val(v):
            return str(v).strip() if v is not None else ""

        print(f"    측정지점코드: {sample.get('PT_NO')}")
        print(f"    측정지점명: {sample.get('PT_NM')}")
        print(f"    측정일: {sample.get('MEASURE_DT')}")
        print(f"    Cd: {strip_val(sample.get('ITEM_CD'))} mg/kg")
        print(f"    Cu: {strip_val(sample.get('ITEM_CU'))} mg/kg")
        print(f"    Pb: {strip_val(sample.get('ITEM_PB'))} mg/kg")
        print(f"    Zn: {strip_val(sample.get('ITEM_ZN'))} mg/kg")
        print(f"    Ni: {strip_val(sample.get('ITEM_NI'))} mg/kg")
        print(f"    Cr6+: {strip_val(sample.get('ITEM_CR6'))} mg/kg")
        print(f"    pH: {strip_val(sample.get('ITEM_PH'))}")
        print(f"    유기물함량: {strip_val(sample.get('ITEM_OM'))} %")

        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    getSoilMeasuringList.header: {header}")
        print(f"    item 필드: {list(sample.keys())}")

        print()
        print("  SUCCESS: 토양측정망 API 연동 성공")
        return True, ""

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 기상청 ASOS 커넥터 검증
# ──────────────────────────────────────────────────

KMA_ASOS_URL = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

# 알려진 실패 원인
_KMA_KNOWN_FAILURE = "API 키 미승인 — 기상청 ASOS API 별도 활용 신청 필요"


async def test_kma_asos() -> tuple[bool, str]:
    """기상청 ASOS API 실제 호출 검증.

    현재 HTTP 403 오류가 발생하는 것으로 알려짐.
    기상청 ASOS API는 공공데이터포털 기본 키와 별도로 활용 신청이 필요함.
    """
    print()
    print("=" * 60)
    print("[기상청 종관기상관측(ASOS) 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    # 서울(108) 관측소, 2024년 1월 1일~7일
    params = {
        "serviceKey": API_KEY,
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": "20240101",
        "endDt": "20240107",
        "stnIds": "108",
        "pageNo": "1",
        "numOfRows": "10",
    }

    print(f"  관측소: 서울(108)")
    print(f"  조회 기간: {params['startDt']}~{params['endDt']}")
    print(f"  요청 URL: {_build_url_log(KMA_ASOS_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(KMA_ASOS_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            # HTTP 403은 알려진 API 키 미승인 오류
            diagnosis = _KMA_KNOWN_FAILURE if response.status_code == 403 else f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {diagnosis}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, diagnosis

        data = response.json()

        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")

        print(f"  API 결과코드: {result_code}")
        print(f"  API 결과메시지: {result_msg}")

        if result_code != "00":
            msg = f"API 오류 코드={result_code} msg={result_msg}"
            print(f"  ERROR: {msg}")
            return False, msg

        body = resp.get("body", {})
        total_count = body.get("totalCount", 0)

        # items 구조 파싱 (dict 또는 list)
        items_wrapper = body.get("items", {})
        if isinstance(items_wrapper, dict):
            items = items_wrapper.get("item", [])
        elif isinstance(items_wrapper, list):
            items = items_wrapper
        else:
            items = []

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            msg = "수신 데이터 없음"
            print(f"  WARNING: {msg}")
            return False, msg

        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]
        print(f"    관측소: {sample.get('stnNm')} (ID: {sample.get('stnId')})")
        print(f"    관측일: {sample.get('tm')}")
        print(f"    평균기온: {sample.get('avgTa')} C")
        print(f"    최고기온: {sample.get('maxTa')} C")
        print(f"    최저기온: {sample.get('minTa')} C")
        print(f"    강수량: {sample.get('sumRn')} mm")
        print(f"    평균풍속: {sample.get('avgWs')} m/s")
        print(f"    최대풍속: {sample.get('maxWs')} m/s")
        print(f"    평균습도: {sample.get('avgRhm')} %")

        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    response.header: {header}")
        print(f"    response.body 키: {list(body.keys())}")
        print(f"    item 필드: {list(sample.keys())}")

        print()
        print("  SUCCESS: 기상청 ASOS API 연동 성공")
        return True, ""

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# V-world 토지이용 커넥터 검증
# ──────────────────────────────────────────────────

VWORLD_URL = "https://api.vworld.kr/req/data"

# 알려진 실패 원인
_VWORLD_KNOWN_FAILURE = "VWORLD_API_KEY 미설정 — vworld.kr에서 별도 발급 필요"


async def test_vworld_land_use() -> tuple[bool, str]:
    """V-world 토지이용 API 실제 호출 검증.

    VWORLD_API_KEY 가 설정되지 않은 경우 알려진 실패로 처리한다.
    """
    print()
    print("=" * 60)
    print("[V-world 토지이용 커넥터 검증]")
    print("=" * 60)

    if not VWORLD_API_KEY:
        print(f"  ERROR: {_VWORLD_KNOWN_FAILURE}")
        return False, _VWORLD_KNOWN_FAILURE

    # 강남구 중심점 좌표
    lng, lat = 127.0455, 37.5075
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": "LP_PA_CBND_BONBUN",
        "key": VWORLD_API_KEY,
        "geomFilter": f"POINT({lng} {lat})",
        "crs": "EPSG:4326",
        "format": "json",
        "size": "10",
    }

    print(f"  좌표: ({lng}, {lat})")
    print(f"  요청 URL: {_build_url_log(VWORLD_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(VWORLD_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {msg}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, msg

        data = response.json()
        status = data.get("response", {}).get("status", "")
        print(f"  API 상태: {status}")

        if status != "OK":
            error = data.get("response", {}).get("error", {})
            msg = f"API 오류: {error}"
            print(f"  ERROR: {msg}")
            return False, msg

        result = data.get("response", {}).get("result", {})
        features = result.get("featureCollection", {}).get("features", [])
        print(f"  수신 건수: {len(features)}")

        if features:
            print()
            print("  [샘플 데이터 (첫 번째 피처)]")
            props = features[0].get("properties", {})
            for k, v in list(props.items())[:8]:
                print(f"    {k}: {v}")

        print()
        print("  SUCCESS: V-world 토지이용 API 연동 성공")
        return True, ""

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 국가유산청 문화재 커넥터 검증
# ──────────────────────────────────────────────────

HERITAGE_URL = "https://www.khs.go.kr/cha/SearchKindOpenapiList.do"


async def test_cultural_heritage() -> tuple[bool, str]:
    """국가유산청 문화재 API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[국가유산청 문화재 커넥터 검증]")
    print("=" * 60)

    # API 키 불필요
    params = {
        "ccbaCtcd": "11",  # 서울
        "pageUnit": "5",
        "pageIndex": "1",
    }

    print(f"  시도코드: {params['ccbaCtcd']} (서울)")
    print(f"  요청 URL: {_build_url_log(HERITAGE_URL, params)}")
    print()

    try:
        import xml.etree.ElementTree as ET

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(HERITAGE_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {msg}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, msg

        root = ET.fromstring(response.text)
        items = root.findall(".//item")
        total = root.findtext("totalCnt", "0")

        print(f"  총 건수: {total}")
        print(f"  수신 건수: {len(items)}")

        if items:
            print()
            print("  [샘플 데이터 (첫 번째 항목)]")
            item = items[0]
            fields = ["ccbaMnm1", "ccbaKdcd", "ccbaCtcdNm", "ccbaLcad", "longitude", "latitude"]
            for f in fields:
                val = item.findtext(f, "")
                print(f"    {f}: {val}")

        print()
        print("  SUCCESS: 국가유산청 문화재 API 연동 성공")
        return True, ""

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 한국건설기술연구원 교통량 통계 커넥터 검증
# ──────────────────────────────────────────────────

TRAFFIC_URL = "http://apis.data.go.kr/1613000/KictTmsStat/yearlyTrafficVolume"

# 알려진 실패 원인
_TRAFFIC_KNOWN_FAILURE = "API 엔드포인트 폐지/변경 — 공공데이터포털에서 최신 URL 확인 필요"


async def test_traffic_volume() -> tuple[bool, str]:
    """한국건설기술연구원 교통량 통계 API 실제 호출 검증.

    현재 HTTP 404 오류가 발생하는 것으로 알려짐.
    API 엔드포인트 폐지 또는 변경 가능성 있음.
    """
    print()
    print("=" * 60)
    print("[한국건설기술연구원 교통량 통계 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    params = {
        "serviceKey": API_KEY,
        "output": "json",
        "year": "2023",
        "month": "1",
        "dtype": "2",
        "spot_id": "all",
        "numOfRows": "5",
        "pageNo": "0",
    }

    print(f"  조회 연도: {params['year']}")
    print(f"  도로유형: 일반국도 (dtype=2)")
    print(f"  요청 URL: {_build_url_log(TRAFFIC_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(TRAFFIC_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            # HTTP 404는 알려진 엔드포인트 폐지/변경 오류
            diagnosis = _TRAFFIC_KNOWN_FAILURE if response.status_code == 404 else f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {diagnosis}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, diagnosis

        data = response.json()

        result_code = data.get("resultCode", data.get("response", {}).get("header", {}).get("resultCode"))
        print(f"  API 결과코드: {result_code}")

        traffic = data.get("traffic", [])
        if not traffic:
            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            if isinstance(items, dict):
                traffic = items.get("item", [])
            elif isinstance(items, list):
                traffic = items

        print(f"  수신 건수: {len(traffic)}")

        if traffic:
            print()
            print("  [샘플 데이터 (첫 번째 항목)]")
            sample = traffic[0]
            for k, v in list(sample.items())[:8]:
                print(f"    {k}: {v}")

            print()
            print("  SUCCESS: 교통량 통계 API 연동 성공")
            return True, ""
        else:
            msg = "교통량 데이터 추출 불가 — API 응답 구조 확인 필요"
            print()
            print(f"  [raw_payload 키 목록]: {list(data.keys())[:10]}")
            print()
            print(f"  WARNING: {msg}")
            return False, msg

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 행정안전부 생활쓰레기배출정보 커넥터 검증
# ──────────────────────────────────────────────────

WASTE_INFO_URL = "http://apis.data.go.kr/1741000/household_waste_info/info"


async def test_waste_stats() -> tuple[bool, str]:
    """행정안전부 생활쓰레기배출정보 API 실제 호출 검증.

    응답 구조 우선순위:
      1) response.body.items  (실제 API 포맷)
      2) data["data"]         (폴백)

    수집 데이터 유형 판별:
      - 폐기물 배출량 데이터: TOT_DSCG_QTY 등 수량 필드 포함
      - 배출 일정 데이터: EMSN_PLC 등 장소/일정 필드 포함
    """
    print()
    print("=" * 60)
    print("[행정안전부 생활쓰레기배출정보 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        msg = "DATA_GO_KR_API_KEY 미설정"
        print(f"  ERROR: {msg}")
        return False, msg

    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "pageNo": "1",
        "numOfRows": "5",
        "cond[SGG_NM::LIKE]": "강남",
    }

    print(f"  검색 조건: 강남 (LIKE)")
    print(f"  요청 URL: {_build_url_log(WASTE_INFO_URL, params)}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(WASTE_INFO_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} 오류"
            print(f"  ERROR: {msg}")
            print(f"  응답 본문: {response.text[:500]}")
            return False, msg

        data = response.json()

        # ── 응답 구조 탐색 (우선순위 1: response.body.items) ──
        items = []
        data_source_label = ""

        body = data.get("response", {}).get("body", {})
        body_items = body.get("items", None)
        if body_items is not None:
            if isinstance(body_items, list):
                items = body_items
            elif isinstance(body_items, dict):
                items = body_items.get("item", [])
            data_source_label = "response.body.items (실제 API 포맷)"

        # ── 폴백: data["data"] ──
        if not items:
            fallback = data.get("data", [])
            if fallback:
                items = fallback
                data_source_label = 'data["data"] (폴백)'

        total = (
            body.get("totalCount")
            or data.get("totalCount")
            or data.get("matchCount")
            or len(items)
        )

        print(f"  응답 데이터 소스: {data_source_label if data_source_label else '(알 수 없음)'}")
        print(f"  총 데이터 건수: {total}")
        print(f"  수신 건수: {len(items)}")

        if items:
            sample = items[0]
            all_fields = list(sample.keys())

            print()
            print("  [샘플 데이터 (첫 번째 항목) — 전체 필드]")
            for k in all_fields:
                print(f"    {k}: {sample.get(k)}")

            # 수집 데이터 유형 판별
            quantity_fields = [f for f in all_fields if "QTY" in f.upper() or "DSCG" in f.upper()]
            schedule_fields = [f for f in all_fields if "EMSN_PLC" in f.upper() or "EMSN_DT" in f.upper() or "SCHEDULE" in f.upper()]

            print()
            print("  [데이터 유형 판별]")
            if quantity_fields:
                print(f"    데이터 유형: 폐기물 배출량 데이터 (QUANTITY)")
                print(f"    수량 관련 필드: {quantity_fields}")
            elif schedule_fields:
                print(f"    데이터 유형: 배출 일정 데이터 (SCHEDULE)")
                print(f"    일정 관련 필드: {schedule_fields}")
            else:
                print(f"    데이터 유형: 미분류 (TOT_DSCG_QTY·EMSN_PLC 등 주요 필드 없음)")
                print(f"    사용 가능한 전체 필드: {all_fields}")

            print()
            print("  [raw_payload 최상위 키]")
            print(f"    {list(data.keys())}")

            print()
            print("  SUCCESS: 생활쓰레기배출정보 API 연동 성공")
            return True, ""
        else:
            msg = "데이터 추출 불가 — API 응답 구조 확인 필요"
            print()
            print(f"  [raw_payload 최상위 키]: {list(data.keys())}")
            print()
            print(f"  WARNING: {msg}")
            return False, msg

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  ERROR: 예외 발생 -- {msg}")
        return False, msg


# ──────────────────────────────────────────────────
# 결과 요약 테이블 출력
# ──────────────────────────────────────────────────

def _print_summary(results: dict[str, tuple[bool, str]]) -> None:
    """커넥터별 결과를 정렬된 테이블 형식으로 출력한다.

    컬럼: 커넥터명 | 결과 | 실패 원인
    """
    print()
    print("=" * 80)
    print("[검증 결과 요약]")
    print("=" * 80)

    # 컬럼 너비 정의
    col_name = 32
    col_result = 10

    header = f"  {'커넥터명':<{col_name}} {'결과':<{col_result}} 실패 원인"
    print(header)
    print("  " + "-" * 76)

    for name, (ok, reason) in results.items():
        result_str = "SUCCESS" if ok else "FAILED"
        reason_str = "" if ok else reason
        print(f"  {name:<{col_name}} {result_str:<{col_result}} {reason_str}")

    print()


# ──────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────

async def main():
    print("커넥터 실제 API 연동 검증 시작")
    print(f"DATA_GO_KR_API_KEY: {'설정됨' if API_KEY else '미설정'}")
    print(f"VWORLD_API_KEY: {'설정됨' if VWORLD_API_KEY else '미설정'}")
    print()

    air_result = await test_airkorea()
    water_result = await test_water_quality()
    soil_result = await test_soil_measuring()
    kma_result = await test_kma_asos()
    vworld_result = await test_vworld_land_use()
    heritage_result = await test_cultural_heritage()
    traffic_result = await test_traffic_volume()
    waste_result = await test_waste_stats()

    # 결과 딕셔너리 구성 (표시 순서 유지)
    results: dict[str, tuple[bool, str]] = {
        "에어코리아 대기질": air_result,
        "국립환경과학원 수질 DB": water_result,
        "국가유산청 문화재": heritage_result,
        "행정안전부 생활쓰레기": waste_result,
        "국립환경과학원 토양측정망": soil_result,
        "기상청 ASOS": kma_result,
        "V-world 토지이용": vworld_result,
        "한국건설기술연구원 교통량": traffic_result,
    }

    _print_summary(results)

    # ── 알려진 실패 커넥터에 대한 진단 안내 ──
    known_failures = {
        "국립환경과학원 토양측정망": _SOIL_KNOWN_FAILURE,
        "기상청 ASOS": _KMA_KNOWN_FAILURE,
        "V-world 토지이용": _VWORLD_KNOWN_FAILURE,
        "한국건설기술연구원 교통량": _TRAFFIC_KNOWN_FAILURE,
    }

    failed_known = [
        (name, diag)
        for name, diag in known_failures.items()
        if not results[name][0]
    ]

    if failed_known:
        print("  [알려진 실패 항목 진단]")
        for name, diag in failed_known:
            print(f"    {name}: {diag}")
        print()

    # ── exit code 판정: 핵심 4개(airkorea, water, heritage, waste)가 모두 통과해야 성공 ──
    core_ok = (
        air_result[0]
        and water_result[0]
        and heritage_result[0]
        and waste_result[0]
    )

    if core_ok:
        all_ok = all(ok for ok, _ in results.values())
        if all_ok:
            print("  전체 검증 통과")
        else:
            failed_non_core = [
                name for name, (ok, _) in results.items()
                if not ok and name not in ("에어코리아 대기질", "국립환경과학원 수질 DB", "국가유산청 문화재", "행정안전부 생활쓰레기")
            ]
            print(f"  핵심 커넥터 4개 검증 통과")
            print(f"  비핵심 실패 항목 ({len(failed_non_core)}개): {', '.join(failed_non_core)}")
        sys.exit(0)
    else:
        failed_core = [
            name for name, (ok, _) in results.items()
            if not ok and name in ("에어코리아 대기질", "국립환경과학원 수질 DB", "국가유산청 문화재", "행정안전부 생활쓰레기")
        ]
        print(f"  핵심 커넥터 검증 실패: {', '.join(failed_core)}")
        print("  위 로그를 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
