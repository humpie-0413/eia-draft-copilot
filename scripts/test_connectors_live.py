# -*- coding: utf-8 -*-
"""커넥터 실제 API 연동 검증 스크립트.

에어코리아 대기질 + 수질 DB + 토양측정망 + 기상청 ASOS +
V-world 토지이용 + 국가유산청 문화재 커넥터를 실제 API로 호출하여
데이터가 정상 수신되는지 확인한다.

사용법:
    python scripts/test_connectors_live.py
"""

import asyncio
import os
import sys
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

# ──────────────────────────────────────────────────
# 에어코리아 대기질 커넥터 검증
# ──────────────────────────────────────────────────

AIRKOREA_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"


async def test_airkorea():
    """에어코리아 API 실제 호출 검증."""
    print("=" * 60)
    print("[에어코리아 대기질 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        print("  ERROR: DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "stationName": "종로구",
        "dataTerm": "DAILY",
        "pageNo": "1",
        "numOfRows": "10",
        "ver": "1.3",
    }

    print(f"  요청 URL: {AIRKOREA_URL}")
    print(f"  측정소명: {params['stationName']}")
    print(f"  조회 기간: {params['dataTerm']}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(AIRKOREA_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

        data = response.json()

        # 응답 구조 확인
        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")

        print(f"  API 결과코드: {result_code}")
        print(f"  API 결과메시지: {result_msg}")

        if result_code != "00":
            print("  ERROR: API 오류 응답")
            return False

        body = resp.get("body", {})
        total_count = body.get("totalCount", 0)
        items = body.get("items", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            print("  WARNING: 수신 데이터 없음")
            return False

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
            return True
        else:
            # 통신장애 시간대일 수 있지만 API 자체는 정상 동작
            print()
            print("  WARNING: PM10/PM2.5 값이 모두 '-'이지만 API 연결은 정상")
            print("  (실시간 데이터가 일시적으로 '-'일 수 있음)")
            # API 연결 자체는 성공이므로 True 반환
            return True

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# 국립환경과학원 수질 DB 커넥터 검증
# ──────────────────────────────────────────────────

WATER_QUALITY_URL = "http://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList"


async def test_water_quality():
    """국립환경과학원 수질 DB API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[국립환경과학원 수질 DB 커넥터 검증 -- 물환경 수질측정망]")
    print("=" * 60)

    if not API_KEY:
        print("  ERROR: DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    # 낙동강 수계 측정지점, 최근 연도
    params = {
        "serviceKey": API_KEY,
        "resultType": "json",
        "year": "2023",
        "ptNoList": "2008A40",
        "pageNo": "1",
        "numOfRows": "5",
    }

    print(f"  요청 URL: {WATER_QUALITY_URL}")
    print(f"  조회 연도: {params['year']}")
    print(f"  측정지점: {params['ptNoList']}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(WATER_QUALITY_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

        data = response.json()

        # 응답 구조 확인 -- 래퍼가 getWaterMeasuringList
        result = data.get("getWaterMeasuringList", {})
        header = result.get("header", {})
        code = header.get("code")
        message = header.get("message")

        print(f"  API 결과코드: {code}")
        print(f"  API 결과메시지: {message}")

        if code != "00":
            print("  ERROR: API 오류 응답")
            return False

        total_count = result.get("totalCount", 0)
        items = result.get("item", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            print("  WARNING: 수신 데이터 없음")
            return False

        # 샘플 데이터 출력
        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]
        print(f"    측정지점코드: {sample.get('PT_NO')}")
        print(f"    측정지점명: {sample.get('PT_NM')}")
        print(f"    측정일: {sample.get('WMCYMD')}")

        def strip_val(v):
            return str(v).strip() if v is not None else ""

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

        # BOD, COD 값 존재 확인
        bod = sample.get("ITEM_BOD")
        has_data = bod is not None and strip_val(bod) != ""

        if has_data:
            print()
            print("  SUCCESS: 국립환경과학원 수질 DB API 연동 성공")
            return True
        else:
            print()
            print("  WARNING: BOD/COD 값이 비어있습니다")
            return False

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# 국립환경과학원 토양측정망 커넥터 검증
# ──────────────────────────────────────────────────

SOIL_MEASURING_URL = "http://apis.data.go.kr/1480523/SoilMeasuringService/getSoilMeasuringList"


async def test_soil_measuring():
    """국립환경과학원 토양측정망 API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[국립환경과학원 토양측정망 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        print("  ERROR: DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    params = {
        "serviceKey": API_KEY,
        "resultType": "json",
        "year": "2023",
        "pageNo": "1",
        "numOfRows": "5",
    }

    print(f"  요청 URL: {SOIL_MEASURING_URL}")
    print(f"  조회 연도: {params['year']}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(SOIL_MEASURING_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

        data = response.json()

        # 응답 구조 확인
        result = data.get("getSoilMeasuringList", {})
        header = result.get("header", {})
        code = header.get("code")
        message = header.get("message")

        print(f"  API 결과코드: {code}")
        print(f"  API 결과메시지: {message}")

        if code != "00":
            print("  ERROR: API 오류 응답")
            return False

        total_count = result.get("totalCount", 0)
        items = result.get("item", [])

        print(f"  총 데이터 건수: {total_count}")
        print(f"  수신 건수: {len(items)}")

        if not items:
            print("  WARNING: 수신 데이터 없음")
            return False

        # 샘플 데이터 출력
        print()
        print("  [샘플 데이터 (첫 번째 항목)]")
        sample = items[0]
        print(f"    측정지점코드: {sample.get('PT_NO')}")
        print(f"    측정지점명: {sample.get('PT_NM')}")
        print(f"    측정일: {sample.get('MEASURE_DT')}")

        def strip_val(v):
            return str(v).strip() if v is not None else ""

        print(f"    Cd: {strip_val(sample.get('ITEM_CD'))} mg/kg")
        print(f"    Cu: {strip_val(sample.get('ITEM_CU'))} mg/kg")
        print(f"    Pb: {strip_val(sample.get('ITEM_PB'))} mg/kg")
        print(f"    Zn: {strip_val(sample.get('ITEM_ZN'))} mg/kg")
        print(f"    Ni: {strip_val(sample.get('ITEM_NI'))} mg/kg")
        print(f"    Cr6+: {strip_val(sample.get('ITEM_CR6'))} mg/kg")
        print(f"    pH: {strip_val(sample.get('ITEM_PH'))}")
        print(f"    유기물함량: {strip_val(sample.get('ITEM_OM'))} %")

        # raw_payload 구조 확인
        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    getSoilMeasuringList.header: {header}")
        print(f"    item 필드: {list(sample.keys())[:15]}")

        print()
        print("  SUCCESS: 토양측정망 API 연동 성공")
        return True

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# 기상청 ASOS 커넥터 검증
# ──────────────────────────────────────────────────

KMA_ASOS_URL = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"


async def test_kma_asos():
    """기상청 ASOS API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[기상청 종관기상관측(ASOS) 커넥터 검증]")
    print("=" * 60)

    if not API_KEY:
        print("  ERROR: DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

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

    print(f"  요청 URL: {KMA_ASOS_URL}")
    print(f"  관측소: 서울(108)")
    print(f"  조회 기간: {params['startDt']}~{params['endDt']}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(KMA_ASOS_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

        data = response.json()

        # 응답 구조 확인
        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")

        print(f"  API 결과코드: {result_code}")
        print(f"  API 결과메시지: {result_msg}")

        if result_code != "00":
            print("  ERROR: API 오류 응답")
            return False

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
            print("  WARNING: 수신 데이터 없음")
            return False

        # 샘플 데이터 출력
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

        # raw_payload 구조 확인
        print()
        print("  [raw_payload 구조]")
        print(f"    최상위 키: {list(data.keys())}")
        print(f"    response.header: {header}")
        print(f"    response.body 키: {list(body.keys())}")
        print(f"    item 필드: {list(sample.keys())[:15]}")

        print()
        print("  SUCCESS: 기상청 ASOS API 연동 성공")
        return True

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# V-world 토지이용 커넥터 검증
# ──────────────────────────────────────────────────

VWORLD_API_KEY = os.getenv("VWORLD_API_KEY", "")
VWORLD_URL = "https://api.vworld.kr/req/data"


async def test_vworld_land_use():
    """V-world 토지이용 API 실제 호출 검증."""
    print()
    print("=" * 60)
    print("[V-world 토지이용 커넥터 검증]")
    print("=" * 60)

    if not VWORLD_API_KEY:
        print("  ERROR: VWORLD_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

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

    print(f"  요청 URL: {VWORLD_URL}")
    print(f"  좌표: ({lng}, {lat})")
    print()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(VWORLD_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

        data = response.json()
        status = data.get("response", {}).get("status", "")
        print(f"  API 상태: {status}")

        if status != "OK":
            error = data.get("response", {}).get("error", {})
            print(f"  ERROR: {error}")
            return False

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
        return True

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# 국가유산청 문화재 커넥터 검증
# ──────────────────────────────────────────────────

HERITAGE_URL = "https://www.khs.go.kr/cha/SearchKindOpenapiList.do"


async def test_cultural_heritage():
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

    print(f"  요청 URL: {HERITAGE_URL}")
    print(f"  시도코드: {params['ccbaCtcd']} (서울)")
    print()

    try:
        import xml.etree.ElementTree as ET

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(HERITAGE_URL, params=params)

        print(f"  HTTP 상태코드: {response.status_code}")

        if response.status_code != 200:
            print("  ERROR: HTTP 오류 응답")
            print(f"  응답 본문: {response.text[:500]}")
            return False

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
        return True

    except Exception as e:
        print(f"  ERROR: 예외 발생 -- {type(e).__name__}: {e}")
        return False


# ──────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────

async def main():
    print("커넥터 실제 API 연동 검증 시작")
    print(f"API 키 설정 여부: {'설정됨' if API_KEY else '미설정'}")
    print()

    air_ok = await test_airkorea()
    water_ok = await test_water_quality()
    soil_ok = await test_soil_measuring()
    kma_ok = await test_kma_asos()
    vworld_ok = await test_vworld_land_use()
    heritage_ok = await test_cultural_heritage()

    print()
    print("=" * 60)
    print("[검증 결과 요약]")
    print("=" * 60)
    print(f"  에어코리아 대기질: {'SUCCESS' if air_ok else 'FAILED'}")
    print(f"  국립환경과학원 수질 DB: {'SUCCESS' if water_ok else 'FAILED'}")
    print(f"  국립환경과학원 토양측정망: {'SUCCESS' if soil_ok else 'FAILED'}")
    print(f"  기상청 ASOS: {'SUCCESS' if kma_ok else 'FAILED'}")
    print(f"  V-world 토지이용: {'SUCCESS' if vworld_ok else 'FAILED'}")
    print(f"  국가유산청 문화재: {'SUCCESS' if heritage_ok else 'FAILED'}")
    print()

    all_ok = air_ok and water_ok and soil_ok and kma_ok and vworld_ok and heritage_ok
    if all_ok:
        print("  전체 검증 통과")
    else:
        print("  일부 검증 실패 -- 위 로그를 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
