# -*- coding: utf-8 -*-
"""폐기물 API 응답 구조 상세 분석 + V-world 세종 좌표 탐색."""

import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
ENV_FILE = BACKEND_DIR / ".env"

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


def main():
    print("=" * 70)
    print("  폐기물 API 응답 구조 상세 분석")
    print("=" * 70)

    base_url = "http://apis.data.go.kr/1741000/household_waste_info/info"

    for region in ["양평군", "세종시", "보령시", "세종특별자치시", "보령"]:
        print(f"\n--- {region} ---")
        with httpx.Client(timeout=30) as client:
            resp = client.get(base_url, params={
                "serviceKey": DATA_GO_KR_KEY,
                "returnType": "json",
                "pageNo": "1",
                "numOfRows": "5",
                "cond[SGG_NM::LIKE]": region,
            })
            print(f"  상태: {resp.status_code}, 크기: {len(resp.content)} bytes")
            try:
                data = resp.json()
                # 전체 구조 출력 (최대 2000자)
                formatted = json.dumps(data, ensure_ascii=False, indent=2)
                if len(formatted) > 2000:
                    print(f"  응답 (처음 2000자):\n{formatted[:2000]}...")
                else:
                    print(f"  응답:\n{formatted}")
            except Exception as e:
                print(f"  JSON 파싱 실패: {e}")
                print(f"  원본 (처음 500자): {resp.text[:500]}")

    # V-world 세종시 좌표 탐색
    print("\n" + "=" * 70)
    print("  V-world 세종시 좌표 탐색 (세종시청/행복도시 일대)")
    print("=" * 70)

    if not VWORLD_KEY:
        print("  [건너뜀] VWORLD_API_KEY 미설정")
        return

    # 세종시 주요 좌표 후보
    sejong_coords = [
        ("세종시청", "127.2494", "36.5101"),
        ("세종 행복도시 중심", "127.0612", "36.5039"),
        ("세종 조치원", "127.0015", "36.6009"),
        ("세종 첫마을", "127.0556", "36.4867"),
        ("세종 나성동", "127.0784", "36.5147"),
    ]

    boryeong_coords = [
        ("보령시청", "126.6126", "36.3335"),
        ("보령 시내", "126.6122", "36.3340"),
        ("보령 대천", "126.5880", "36.3219"),
        ("보령 명천동", "126.5963", "36.3461"),
    ]

    base_url = "https://api.vworld.kr/req/data"

    for label, lng, lat in sejong_coords + boryeong_coords:
        with httpx.Client(timeout=15) as client:
            resp = client.get(base_url, params={
                "service": "data",
                "request": "GetFeature",
                "data": "LT_C_UQ111",
                "key": VWORLD_KEY,
                "domain": "",
                "geomFilter": f"POINT({lng} {lat})",
                "crs": "EPSG:4326",
                "format": "json",
                "size": "100",
            })
            data = resp.json()
            resp_data = data.get("response", {})
            status = resp_data.get("status", "")
            if status == "OK":
                features = resp_data.get("result", {}).get("featureCollection", {}).get("features", [])
                zones = [f.get("properties", {}).get("uname", "") for f in features]
                print(f"  {label} ({lng}, {lat}): OK — {len(features)}건 {zones}")
            else:
                print(f"  {label} ({lng}, {lat}): {status}")


if __name__ == "__main__":
    main()
