# Next Chat Brief

## 마지막 완료 작업
**Demo-3: 3종 시나리오 데모 스크립트** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1~Pred-3: 예측 모듈 통합 완료 ✅
- Conn-1~Conn-2: 커넥터 확장 완료 ✅
- Final-1~Final-2: 통합 검증 + 문서화 완료 ✅
- Demo-1~Demo-2: 통합 데모 + QA 해결 + Export 성공 ✅
- Doc-1: CLAUDE.md 전면 업데이트 ✅
- LLM-Enhancement: 서술문 품질 최종 개선 ✅
- GIS-1: GIS 공간 분석 및 도면 생성 ✅
- GIS-2: 프론트엔드 지도 시각화 ✅
- Demo-3: 3종 시나리오 데모 스크립트 ✅

## 완료된 작업 (Demo-3: 2026-03-15)

### 시나리오 1: 국도 우회도로 건설 — 경기 양평
- 파일: `scripts/demo_road_yangpyeong.py`
- 사업유형: road, 양평군 양평읍 (127.49°E, 37.49°N)
- 도로 형태 폴리곤 (폭 200m, 길이 2km)
- 커넥터 9종 + 수동 3종 (소음·진동, 생태 — 수달/원앙 2종, 경관 — 두물머리)
- 유사사례: 포천 국도 확장, 원주 우회도로, 충주 우회도로
- 예측: 소음(선음원 75dB), 대기(도로 분진 H=5m), 수질(혼합)

### 시나리오 2: 택지개발 신도시 — 세종시
- 파일: `scripts/demo_housing_sejong.py`
- 사업유형: housing, 세종시 조치원읍 (127.0°E, 36.6°N)
- 1km x 1km 사각형 폴리곤
- 커넥터 9종 + 수동 2종 (소음·진동, 생태 — 보호종 0, 도시녹지)
- 유사사례: 동탄 신도시, 오송 택지개발, 다산 택지개발
- 예측: 대기(건설 분진), 소음(건설 장비 90dB), 수질(방류량 0.03)

### 시나리오 3: 화력발전소 증설 — 충남 보령
- 파일: `scripts/demo_powerplant_boryeong.py`
- 사업유형: power_plant, 보령시 오천면 (126.5°E, 36.3°N)
- 500m x 500m 사각형 폴리곤
- 커넥터 9종 + 수동 3종 (소음·진동, 생태 — 간척지, 기후 보강 — 기상청 실패 시)
- 유사사례: 서천 화력, 영광 원자력, 삼척 화력
- 예측: 대기(굴뚝 80m, PM10/NO2/SO2 고배출), 소음(터빈 100dB), 수질(방류량 0.05)

### 공통 특징
- 기존 `demo_full_scenario.py` 미수정 (4번째 독립 스크립트)
- 11단계 동일 구조: 생성 → 수집 → 유사사례 → 섹션 → 법령 → 통계 → 기준비교 → 서술문 → 예측 → LLM → QA → GIS → Export → 요약
- 더미 데이터 절대 사용 금지 원칙 준수
- API 자동수집 / 수동입력 / 미수집 구분 표시
- output/ 폴더에 시나리오별 DOCX + PDF + GIS 도면 PNG

### 검증 결과
- 3개 스크립트 Python 구문 검증 통과
- 백엔드 644개 테스트 전체 통과

## 다음 작업 후보

### Phase Deploy: 배포 환경 구성
- Docker Compose 통합 (PostgreSQL+PostGIS, FastAPI, Next.js)
- CI/CD 파이프라인
- 환경 분리 (dev/staging/prod)

### Phase Portfolio: 포트폴리오 문서 정리
- GIS 도면 산출물 포함
- 데이터 파이프라인 아키텍처 다이어그램
- Before/After 서술문 비교

## 실행 방법
```bash
# 백엔드 서버 기동
cd backend && uvicorn app.main:app --reload

# 시나리오별 데모 실행
python scripts/demo_road_yangpyeong.py       # 시나리오 1: 양평 도로
python scripts/demo_housing_sejong.py         # 시나리오 2: 세종 택지
python scripts/demo_powerplant_boryeong.py    # 시나리오 3: 보령 발전소
python scripts/demo_full_scenario.py          # 기존 시나리오: 강남 태양광

# 테스트
cd backend && pytest tests/ -v    # 644개 테스트
```
