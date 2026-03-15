# Next Chat Brief

## 마지막 완료 작업
**LLM-Enhancement: 서술문 품질 최종 개선** ✅

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

## 완료된 작업 (LLM-Enhancement: 2026-03-15)

### 지표 한글명 매핑 모듈
- `backend/app/data/indicator_names.py` — 28개 지표 한글 매핑 + 저감방안 매핑
- 대기(PM10→미세먼지, NO₂→이산화질소 등), 수질(BOD, COD 등), 토양(Cd, Pb 등), 소음(Leq 주간/야간)

### 서술문 템플릿 전면 개선
- 8개 전용 + 1개 범용 서술문 생성기 전면 개선
- 한글 지표명, 기준 대비 %, 적합 묶음/초과 분리, 종합 판단문, 「」법률명, 저감방안
- 범용 서술문 FAIL 판정 버그 수정 (legal_basis 미설정 시 초과 미감지)

### LLM 프롬프트 고도화
- openai_adapter.py, gemini_adapter.py: 10개 규칙 전문가 프롬프트

### Export/Scaffold 한글 지표명
- DOCX/PDF 8개소 + scaffold 2개소에 한글 지표명 적용

### 테스트
- 616개 전체 통과 (기존 612 + 신규 4)

## 다음 작업 후보

### Phase GIS-1: GIS 공간 분석 및 도면 생성
- PostGIS 기반 버퍼 분석 (ST_Buffer 1km/5km)
- 사업 경계 기준 규제 항목 중첩 분석 (ST_Intersection)
- geopandas + matplotlib 기반 정적 도면 렌더링 (위치도, 토지이용현황도, 생태자연도, 대기질 측정소, 문화재 분포도, 소음 등고선도)
- 도면을 DOCX/PDF에 자동 삽입
- SHP/GeoJSON 파일 업로드 지원

### Phase GIS-2: 프론트엔드 지도 시각화
- MapLibre GL JS 기반 대화형 지도
- 레이어 토글 (용도지역, 측정소, 문화재, 버퍼 등)
- 사업 경계 그리기/편집 도구

### Phase Deploy: 배포 환경 구성
- Docker Compose 통합, CI/CD, 환경 분리

### Phase Portfolio: 포트폴리오 문서 정리
- GIS 도면 산출물, 아키텍처 다이어그램, Before/After 비교

## 시스템 전체 현황

### 백엔드 서비스 (11개)
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
| export_service.py | DOCX/PDF 생성 + 한글 지표명 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 섹션 |
| prediction/ | 예측 모듈 (대기 확산 + 소음 전파 + 수질 혼합) |
| llm/ | LLM 어댑터 (none / openai_paid / gemini_free) + 10규칙 전문가 프롬프트 |

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

### 테스트 (616개)
- test_connectors.py (102), test_pred3_integration.py (27), test_prediction_narrative.py (26)
- test_prediction_noise_water.py (82), test_prediction.py (74), test_regulations.py (95)
- test_export_format.py (40+), test_narrative_generator.py (55)
- test_llm_adapter.py (29), test_standard_checker.py (27), test_spec_alignment.py (23)
- test_statistics.py (16), test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정) — vworld.kr에서 별도 발급
- **국가유산청 API**: 키 불필요 (공개 API)
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:3000)

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
pytest tests/ -v    # 616개 테스트

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py
```
