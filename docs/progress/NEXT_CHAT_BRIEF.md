# Next Chat Brief

## 마지막 완료 작업
**Pred-2: 소음 전파 + 수질 혼합 모델** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1: 예측 모듈 + 대기 확산 모델 ✅
- Pred-2: 소음 전파 + 수질 혼합 모델 ✅

## 완료된 작업 (Pred-2)

### 소음 전파 모델
- `prediction/noise_propagation.py`: 점음원/선음원 거리감쇠 + Maekawa 차음벽 회절
- 점음원: L(r) = Lw - 20·log10(r) - 11 (+지면반사, -대기흡수)
- 선음원: L(r) = Lw/m - 10·log10(r) - 8 (+지면반사, -대기흡수)
- 에너지 합산: L_total = 10·log10(10^(L1/10) + 10^(L2/10))
- 6지점(10m~500m) × 주간/야간 예측
- 환경기준: 주간 55dB(A), 야간 45dB(A)
- 사업유형별: power_plant=95dB, road=75dB/m(선음원), housing=90dB, industrial=100dB

### 수질 혼합 모델
- `prediction/water_mixing.py`: 완전혼합 희석 모델
- C_mix = (Q_river·C_river + Q_discharge·C_discharge) / (Q_river + Q_discharge)
- BOD, COD, SS, T-N, T-P 예측
- 방류수 수질기준(물환경보전법): BOD 30, COD 40, SS 30, T-N 60, T-P 8 (mg/L)
- 하천 환경기준(III등급): BOD 5, COD 7, SS 25, T-P 0.2 (mg/L)
- 사업유형별 방류량: power_plant=0.01, industrial=0.1, housing=0.05 (m³/s)

### API 확장
- 기존 예측 API 재사용 (POST /predict/{section_key}, GET /prediction-models)
- 배경 데이터 자동 추출: 소음(주간/야간 Leq), 수질(BOD, COD, SS, T-N, T-P)

### 테스트
- 82개 신규 테스트 (526개 전체 통과)

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

### 커넥터 (6종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |

### 테스트 (526개)
- test_prediction_noise_water.py (82), test_prediction.py (74), test_regulations.py (95)
- test_connectors.py (69), test_export_format.py (40+), test_narrative_generator.py (51)
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
pytest tests/ -v    # 526개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
