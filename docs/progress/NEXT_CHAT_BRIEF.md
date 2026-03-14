# Next Chat Brief

## 마지막 완료 작업
**Final-1: 배포 전 최종 검증 (실제 API 연동)** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1: 예측 모듈 + 대기 확산 모델 ✅
- Pred-2: 소음 전파 + 수질 혼합 모델 ✅
- Pred-3: 예측 결과 통합 — ScaffoldSection + Export + API 스키마 ✅
- Conn-1: 추가 커넥터 확장 — 교통/폐기물 커넥터 + 미수집 서술문 개선 ✅
- Final-1: 배포 전 최종 검증 — 실제 API 연동 + 더미 데이터 제거 ✅

## 완료된 작업 (Final-1: 2026-03-14)

### 1. 전체 커넥터 실제 API 연동 검증
8종 커넥터 실제 API 호출 결과:
| 커넥터 | 결과 | 비고 |
|--------|------|------|
| 에어코리아 대기질 | 성공 | PM10=17, PM2.5=7 (강남구 실측) |
| 국립환경과학원 수질 DB | 성공 | BOD=0.6, COD=2.4 (위천5 실측) |
| 국립환경과학원 토양측정망 | 실패 | HTTP 500 (공공데이터포털 서버 장애) |
| 기상청 ASOS | 실패 | HTTP 403 (API 키 미승인, 별도 활용 신청 필요) |
| V-world 토지이용 | 실패 | VWORLD_API_KEY 미설정 |
| 국가유산청 문화재 | 성공 | 서울 숭례문 등 2301건 |
| 한국건설기술연구원 교통량 | 실패 | HTTP 404 (API 엔드포인트 폐지/변경) |
| 행정안전부 폐기물 | 성공 | 강남구 배출일정 데이터 수신 |

### 2. 더미 데이터 완전 제거
- 데모 스크립트에서 모든 수동 보충 데이터 제거 (air_required, water_supplement 등)
- 실패 커넥터의 수동 fallback 데이터 제거
- 수동 데이터는 소음·진동(현장 측정)과 생태(현장 조사)만 허용
- "더미 데이터 절대 사용 금지" 원칙 전면 적용

### 3. 폐기물 커넥터 normalize 수정
- 실제 API 응답 구조에 맞게 normalize 함수 업데이트
- 배출일정/관리 정보 추출: 관리부서, 배출방법, 배출요일 등
- 기존 배출량 추출 로직은 하위 호환성 유지

### 4. 테스트 결과
- 606개 전체 통과 (기존 605 + 신규 폐기물 배출일정 테스트 1)

### 5. 문서 최종 업데이트
- README.md: 커넥터 가용 현황, 606개 테스트
- docs/architecture.md: 예측 엔진, 커넥터 가용 현황
- docs/user-guide.md: API 키 별도 신청 안내
- docs/api-reference.md: 커넥터 엔드포인트, 예측 API
- docs/development.md: 커넥터/예측 모델 추가 방법

## 시스템 전체 현황

### 백엔드 서비스 (11개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| scope_service.py | 사업유형별 필수/권장/선택 평가 범위 판단 |
| draft_scaffold.py | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback + 예측 결과 포함) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 + 법적 근거 자동 삽입 + 예측 서술문 + 수동입력 가이드 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 |
| export_service.py | DOCX/PDF 생성 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 섹션 |
| prediction/ | 예측 모듈 (대기 확산 + 소음 전파 + 수질 혼합) |

### 커넥터 (8종 — 4종 가동, 4종 일시 비활성)
| 커넥터 키 | 대상 API | 상태 | 비고 |
|-----------|----------|------|------|
| `keco_air` | 에어코리아 대기오염정보 | 가동 | PM10, PM2.5 등 실측 |
| `water_info` | 국립환경과학원 수질 DB | 가동 | BOD, COD 등 실측 |
| `soil_info` | 국립환경과학원 토양측정망 | 비활성 | 서버 장애 (HTTP 500) |
| `kma_weather` | 기상청 ASOS 일자료 | 비활성 | 키 미승인 (HTTP 403) |
| `vworld_land_use` | V-world 2D데이터 | 비활성 | VWORLD_API_KEY 미설정 |
| `cultural_heritage` | 국가유산청 Open API | 가동 | 키 불필요 |
| `traffic_volume` | 한국건설기술연구원 교통량 | 비활성 | 엔드포인트 폐지 (HTTP 404) |
| `waste_stats` | 행정안전부 생활쓰레기배출정보 | 가동 | 배출일정/관리 데이터 |

### 테스트 (606개)
- test_connectors.py (96), test_pred3_integration.py (27), test_prediction_narrative.py (26)
- test_prediction_noise_water.py (82), test_prediction.py (74), test_regulations.py (95)
- test_export_format.py (40+), test_narrative_generator.py (51)
- test_llm_adapter.py (29), test_standard_checker.py (27), test_spec_alignment.py (23)
- test_statistics.py (16), test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정) — vworld.kr에서 별도 발급
- **기상청 ASOS**: 공공데이터포털에서 별도 활용 신청 필요
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
pytest tests/ -v    # 606개 테스트

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py
```

## 비활성 커넥터 활성화 방법
1. **토양측정망**: 공공데이터포털 API 서버 정상화 대기
2. **기상청 ASOS**: data.go.kr에서 "기상청_지상(종관, ASOS) 일자료 조회서비스" 활용 신청
3. **V-world**: vworld.kr 회원가입 → API 키 발급 → .env에 VWORLD_API_KEY 설정
4. **교통량**: 공공데이터포털에서 최신 API 엔드포인트 확인 후 connector 코드 업데이트

## 알려진 제한사항 및 향후 과제
- 프론트엔드 프로젝트 생성 폼 미구현 (API를 통해서만 생성 가능)
- 예측 모델은 간이 모델 — 정밀 모사에는 전문 소프트웨어 필요
- PROCEDURE_PENDING 상태 미구현 (외부 절차 연동 필요)
- spatialRelation, confidence 필드 미구현 (현재 작동에 영향 없음)
- Draft claim contract 미구현 (LLM 연동 심화 시 구현 예정)
- 실시간 협업, 테넌트 인증, 빌링 미지원 (MVP 비목표)
- 폐기물 커넥터는 배출량이 아닌 배출일정 데이터 제공 (환경부 폐기물발생 API 별도 연동 필요)
