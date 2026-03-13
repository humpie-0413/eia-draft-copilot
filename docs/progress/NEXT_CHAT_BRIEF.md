# Next Chat Brief

## 마지막 완료 작업
**Pred-1: 예측 모듈 기반 구조 + 대기 확산 모델** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1: 예측 모듈 + 대기 확산 모델 ✅

## 완료된 작업 (Pred-1)

### 예측 엔진 기반 구조
- `prediction/base.py`: BasePredictionModel 추상 클래스 (predict, get_required_inputs, get_model_info)
- `prediction/registry.py`: 모델 레지스트리 (section_key → model 매핑)
- PredictionResult: section_key, model_name, input_parameters, predictions, summary, assumptions, limitations

### 대기 확산 모델 (가우시안 플룸)
- `prediction/air_dispersion.py`: Pasquill-Gifford 확산계수 + 가우시안 플룸 지표면 농도 계산
- PM10, PM2.5, NO2, SO2에 대해 6지점(100m~5km) 예측
- 배경 농도(에어코리아) 합산 → 사업 후 예상 농도 → 환경기준 초과 판정
- 사업유형별 기본 배출량/굴뚝 높이 딕셔너리

### API 엔드포인트
- `POST /api/v1/projects/{id}/predict/{section_key}` — 예측 실행
- `GET /api/v1/prediction-models` — 모델 목록 + 입력 파라미터
- 배경 농도: evidence에서 연평균 대기 데이터 자동 추출
- 풍속: 기후 데이터에서 자동 추출, 없으면 기본값 3.0 m/s

### 테스트
- 74개 신규 테스트 (444개 전체 통과)

## 시스템 전체 현황

### 백엔드 서비스 (10개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| scope_service.py | 사업유형별 필수/권장/선택 평가 범위 판단 |
| draft_scaffold.py | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 + 법적 근거 자동 삽입 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 |
| export_service.py | DOCX/PDF 생성 + 법적 근거 열 + 필수 섹션 표시 |
| prediction/ | 예측 모듈 (가우시안 플룸 대기 확산 모델) |

### 예측 모델 (Pred-1)
| 모델 | 적용 섹션 | 설명 |
|------|----------|------|
| gaussian_plume | air_quality | 가우시안 플룸 대기 확산 (PM10, PM2.5, NO2, SO2) |

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

### 커넥터 (6종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |

### 테스트 (444개)
- test_prediction.py (74), test_regulations.py (95), test_connectors.py (69)
- test_export_format.py (40+), test_narrative_generator.py (51), test_llm_adapter.py (29)
- test_standard_checker.py (27), test_spec_alignment.py (23), test_statistics.py (16)
- test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

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
pytest tests/ -v    # 444개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
