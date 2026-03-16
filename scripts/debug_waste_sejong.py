# -*- coding: utf-8 -*-
"""세종시 폐기물 데이터 검색 — 다양한 검색어로 시도."""

import json
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
base_url = "http://apis.data.go.kr/1741000/household_waste_info/info"

# 세종시 다양한 검색어
search_terms = ["세종", "세종시", "세종특별자치시", "세종특별자치", "조치원"]

for term in search_terms:
    with httpx.Client(timeout=30) as client:
        resp = client.get(base_url, params={
            "serviceKey": DATA_GO_KR_KEY,
            "returnType": "json",
            "pageNo": "1",
            "numOfRows": "3",
            "cond[SGG_NM::LIKE]": term,
        })
        data = resp.json()
        body = data.get("response", {}).get("body", {})
        total = body.get("totalCount", 0)
        items = body.get("items", {}).get("item", [])
        if items:
            sgg_names = set(i.get("SGG_NM", "") for i in items)
            ctpv_names = set(i.get("CTPV_NM", "") for i in items)
            print(f"  '{term}' → totalCount={total}, SGG_NM={sgg_names}, CTPV_NM={ctpv_names}")
        else:
            print(f"  '{term}' → totalCount={total} (데이터 없음)")

# CTPV_NM (시도명) 검색도 시도
print("\n--- CTPV_NM 검색 ---")
for term in ["세종", "세종특별자치시"]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(base_url, params={
            "serviceKey": DATA_GO_KR_KEY,
            "returnType": "json",
            "pageNo": "1",
            "numOfRows": "3",
            "cond[CTPV_NM::LIKE]": term,
        })
        data = resp.json()
        body = data.get("response", {}).get("body", {})
        total = body.get("totalCount", 0)
        items = body.get("items", {}).get("item", [])
        if items:
            sgg_names = set(i.get("SGG_NM", "") for i in items)
            ctpv_names = set(i.get("CTPV_NM", "") for i in items)
            print(f"  CTPV_NM LIKE '{term}' → totalCount={total}, SGG_NM={sgg_names}, CTPV_NM={ctpv_names}")
        else:
            print(f"  CTPV_NM LIKE '{term}' → totalCount={total} (데이터 없음)")
