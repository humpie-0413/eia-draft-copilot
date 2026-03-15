# Next Chat Brief

## 마지막 완료 작업
**GIS-1: GIS 공간 분석 및 도면 생성** ✅

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

## 완료된 작업 (GIS-1: 2026-03-15)

### 공간 분석 서비스 (`backend/app/services/spatial_analysis.py`)
- PostGIS → shapely + pyproj 기반 버퍼 생성 (EPSG:4326 → 5179 → buffer → 4326)
- 1km/5km 버퍼 GeoJSON 생성 + 면적(km²) 계산
- evidence 좌표 기반 중첩 분석 (측정소, 문화재, 생태조사지점 거리 계산)
- Haversine 거리 계산 함수

### 도면 렌더링 서비스 (`backend/app/services/map_renderer.py`)
- matplotlib + shapely 기반 5종 정적 도면 생성 (A4 가로, 150 DPI)
- 사업대상지 위치도: 사업 경계 + 1km/5km 버퍼 + 측정소/문화재 마커
- 토지이용현황도: 용도지역별 색상 구분 (주거/상업/공업/녹지)
- 환경측정소 분포도: 대기(빨간 △), 수질(파란 ○), 소음(노란 □) 분류
- 소음 예측 등고선도: 주간/야간 기준선 + 농도 등고면 + 음원 표시
- 대기확산 예측도: 가우시안 플룸 등고면 + 기준 초과 영역 + 풍향 화살표
- 한글 폰트 자동 감지 (맑은 고딕 / 나눔고딕)
- 방위표, 축척, 범례 자동 삽입

### API 엔드포인트 (`backend/app/api/v1/spatial.py`)
- `GET /projects/{id}/spatial/buffer?radius=1000` — 버퍼 GeoJSON
- `GET /projects/{id}/spatial/overlay?radius=1000` — 버퍼 내 규제 항목
- `GET /projects/{id}/maps` — 사용 가능한 도면 목록
- `GET /projects/{id}/maps/{map_type}` — 도면 PNG 반환
  - map_type: location, land_use, monitoring_stations, noise_contour, air_dispersion

### DOCX/PDF 도면 자동 삽입
- 표지 다음: 사업대상지 위치도 (그림 0-1)
- 제1장 대기질: 환경측정소 분포도 + 대기확산 예측도
- 제4장 소음·진동: 소음 예측 등고선도
- 제6장 토지이용: 토지이용현황도
- python-docx `add_picture()` + reportlab `Image` 삽입
- 이미지 크기: 15cm, 캡션 자동 부여 (그림 X-Y. 제목)

### 프론트엔드 (`src/app/projects/[id]/maps/page.tsx`)
- 5종 도면 그리드 표시
- 전체 화면 모달 + PNG 다운로드
- 초안 뼈대 페이지에 "GIS 도면" 버튼 추가

### 의존성 추가
- matplotlib>=3.9.0, geopandas>=1.0.0, pyproj>=3.6.0

### 데모 스크립트 업데이트
- 단계 9.5: 버퍼 분석 → 중첩 분석 → 5종 도면 생성 → output/maps/ 저장
- 단계 11 요약에 GIS 도면 현황 추가

### 테스트
- 644개 전체 통과 (기존 616 + 신규 28)
- test_spatial_maps.py: Haversine(4) + Buffer(4) + Overlay(4) + MapRenderer(7) + Interpolation(5) + Model(4)

## 다음 작업 후보

### Phase GIS-2: 프론트엔드 지도 시각화
- MapLibre GL JS 기반 대화형 지도
- 레이어 토글 (용도지역, 측정소, 문화재, 버퍼 등)
- 사업 경계 그리기/편집 도구

### Phase Deploy: 배포 환경 구성
- Docker Compose 통합, CI/CD, 환경 분리

### Phase Portfolio: 포트폴리오 문서 정리
- GIS 도면 산출물, 아키텍처 다이어그램, Before/After 비교

## 시스템 전체 현황

### 백엔드 서비스 (13개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| scope_service.py | 사업유형별 필수/권장/선택 평가 범위 판단 |
| draft_scaffold.py | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback + 예측 결과 포함) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 + 한글 지표명 + 법적 근거 + 기준 대비 % + 저감방안 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 + 부분충족 WARNING |
| export_service.py | DOCX/PDF 생성 + 한글 지표명 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 + **GIS 도면 삽입** |
| prediction/ | 예측 모듈 (대기 확산 + 소음 전파 + 수질 혼합) |
| llm/ | LLM 어댑터 (none / openai_paid / gemini_free) + 10규칙 전문가 프롬프트 |
| **spatial_analysis.py** | 버퍼 분석 + 규제 항목 중첩 탐색 (신규) |
| **map_renderer.py** | 5종 정적 도면 렌더링 (신규) |

### API 엔드포인트 (18개 라우터)
- 기존 14개 + spatial (버퍼/중첩/도면) 1개 = 15개 라우터

### 커넥터 (9종 — 6종 가동, 3종 일시 비활성)
| 커넥터 키 | 대상 API | 상태 | 비고 |
|-----------|----------|------|------|
| `keco_air` | 에어코리아 대기오염정보 | 가동 | PM10_연평균 등 6개 지표 |
| `water_info` | 국립환경과학원 수질 DB | 가동 | BOD, COD 등 실측 |
| `soil_info` | 국립환경과학원 토양측정망 | 비활성 | 서버 장애 (HTTP 500) |
| `kma_weather` | 기상청 ASOS 일자료 | 비활성 | 서버 장애 (HTTP 500) |
| `vworld_land_use` | V-world 2D데이터 | 가동 | LT_C_UQ111 용도지역 |
| `land_use_regulation` | 국토교통부 토지이용규제정보서비스 | 가동 | 행위제한 정보 |
| `cultural_heritage` | 국가유산청 Open API | 비활성 | 네트워크 오류 (일시적) |
| `traffic_volume` | 한국건설기술연구원 교통량 | 가동 | vt_yearly 엔드포인트 |
| `waste_stats` | 행정안전부 생활쓰레기배출정보 | 가동 | 배출일정/관리 데이터 |

### 테스트 (644개)
- test_connectors.py (102), test_pred3_integration.py (27), test_prediction_narrative.py (26)
- test_prediction_noise_water.py (82), test_prediction.py (74), test_regulations.py (95)
- test_export_format.py (40+), test_narrative_generator.py (55)
- test_llm_adapter.py (29), test_standard_checker.py (27), test_spec_alignment.py (23)
- test_statistics.py (16), test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)
- **test_spatial_maps.py (28)** (신규)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정) — vworld.kr에서 별도 발급
- **국가유산청 API**: 키 불필요 (공개 API)
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:3000)
- **GIS 도면 생성**: matplotlib + geopandas + pyproj 설치 필요

## 실행 방법
```bash
# 프론트엔드
npm run dev    # http://localhost:3000

# 백엔드
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000

# 테스트
cd backend
pytest tests/ -v    # 644개 테스트

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py
```
