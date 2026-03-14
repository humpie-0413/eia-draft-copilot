# Next Chat Brief

## 마지막 완료 작업
**Conn-1: 추가 커넥터 확장 (교통/폐기물)** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1: 예측 모듈 + 대기 확산 모델 ✅
- Pred-2: 소음 전파 + 수질 혼합 모델 ✅
- Pred-3: 예측 결과 통합 — ScaffoldSection + Export + API 스키마 ✅
- Conn-1: 추가 커넥터 확장 — 교통/폐기물 커넥터 + 미수집 서술문 개선 ✅

## 완료된 작업 (Conn-1)

### 신규 커넥터 (2종)
1. `TrafficVolumeConnector` — 한국건설기술연구원 교통량 통계 (AADT, 도로등급, 도로명)
2. `WasteStatsConnector` — 행정안전부 생활쓰레기배출정보 (생활폐기물, 음식물, 재활용)

### 수동 입력 확정 (3개 섹션)
- 경관: 현장 시각 조사 필수 → API 자동화 불가
- 생태: 현장 생태 조사 필수
- 소음·진동: 현장 측정 필수

### 서술문 개선
- 미수집 섹션: "자동 수집 대상에 해당하지 않는다. 수동 입력이 필요하다" + 권장 지표 안내
- 교통 전용 서술문: AADT + 도로명 + 도로등급 기반
- 폐기물 전용 서술문: 생활/음식물/재활용/건설폐기물 기반

### 섹션 플래너 필수 지표 갱신
- traffic: 교통량_현황, 도로등급, 도로명
- waste: 생활폐기물_발생량, 건설폐기물_발생량, 지정폐기물_여부
- landscape: 주요_조망점, 스카이라인_영향, 경관_등급, 주요_경관자원

### 테스트
- 26개 신규 테스트 (605개 전체 통과)

## 시스템 전체 현황

### 백엔드 서비스 (10개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| scope_service.py | 사업유형별 필수/권장/선택 평가 범위 판단 |
| draft_scaffold.py | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 + 법적 근거 자동 삽입 + 수동입력 가이드 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 |
| export_service.py | DOCX/PDF 생성 + 법적 근거 열 + 필수 섹션 표시 |
| prediction/ | 예측 모듈 (대기 확산 + 소음 전파 + 수질 혼합) |

### 예측 모델 (Pred-1~2)
| 모델 | 적용 섹션 | 설명 |
|------|----------|------|
| gaussian_plume | air_quality | 가우시안 플룸 대기 확산 (PM10, PM2.5, NO2, SO2) |
| noise_propagation | noise_vibration | 점/선음원 거리감쇠 + 차음벽 (주간/야간) |
| water_mixing | water_quality | 완전혼합 희석 (BOD, COD, SS, T-N, T-P) |

### QA 규칙 (8개)
| 규칙 | 설명 | 심각도 |
|------|------|--------|
| R001 | 섹션 증거 없음 (동적 심각도) | critical/warning |
| R002 | 필수 지표 누락 (동적 심각도) | critical/warning |
| R003 | 충족도 50% 미만 | warning |
| R004 | 근거 없는 완료 상태 | critical |
| R005 | 단일 근거 지표 | info |
| R006 | 환경기준 초과 | warning |
| R007 | 법적 필수 섹션 누락 (사업유형 기반) | critical |
| R008 | 법적 필수 지표 누락 (사업유형 기반) | warning |

### 법령 데이터 (Reg-1~Reg-4)
| 파일 | 역할 |
|------|------|
| regulations/legal_references.py | 환경기준별 법적 근거 매핑 |
| regulations/required_items.py | 사업유형별 필수 평가 항목 (12개 유형) |
| regulations/area_classifications.py | 소음 지역구분별 기준 차등 |

### 커넥터 (8종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |
| `traffic_volume` | 한국건설기술연구원 교통량 통계 | 교통량_현황(AADT), 도로등급, 도로명 |
| `waste_stats` | 행정안전부 생활쓰레기배출정보 | 생활폐기물_발생량, 음식물쓰레기_발생량, 재활용_발생량 |

### 테스트 (605개)
- test_connectors.py (95), test_pred3_integration.py (27), test_prediction_narrative.py (26)
- test_prediction_noise_water.py (82), test_prediction.py (74), test_regulations.py (95)
- test_export_format.py (40+), test_narrative_generator.py (51)
- test_llm_adapter.py (29), test_standard_checker.py (27), test_spec_alignment.py (23)
- test_statistics.py (16), test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정)
- **국가유산청 API**: 키 불필요 (공개 API)
- **LLM adapter 사용 시** (선택):
  - `LLM_ADAPTER=openai_paid` + `OPENAI_API_KEY=...`
  - `LLM_ADAPTER=gemini_free` + `GOOGLE_API_KEY=...`
  - 기본값 `LLM_ADAPTER=none` → LLM 없이 동작
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
pytest tests/ -v    # 605개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
