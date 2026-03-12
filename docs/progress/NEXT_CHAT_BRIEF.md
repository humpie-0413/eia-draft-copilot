# Next Chat Brief

## 마지막 완료 작업
**Post-4: 추가 커넥터 (토양, 기후) + 수동 입력 가이드** ✅

## 완료된 작업 (Post-4)

### 토양측정망 커넥터
- `backend/app/connectors/soil_info.py`:
  - 국립환경과학원 토양측정망 정보 조회 API 연동
  - Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 8개 지표
  - 연도별·측정지점별 조회
  - BaseConnector 상속, fetch → snapshot → normalize → evidence 파이프라인

### 기상청 ASOS 커넥터
- `backend/app/connectors/kma_weather.py`:
  - 기상청 지상(종관, ASOS) 일자료 조회서비스 API 연동
  - 평균기온, 최고기온, 최저기온, 강수량, 평균풍속, 최대풍속, 평균습도 7개 지표
  - 관측소 번호 + 기간(YYYYMMDD) 기반 조회

### 수동 입력 가이드 강화
- 10개 분야별 권장 지표 목록을 증거 추가 폼에 안내 표시
- 클릭 시 지표명 자동 입력, 데이터 출처 힌트 제공
- 커넥터 자동 수집 가능 분야는 별도 안내

### 프론트엔드 업데이트
- 데이터 수집 다이얼로그에 토양/기후 커넥터 파라미터 추가
- 수동 추가 폼에 권장 지표 안내 UI (클릭 가능 배지)

### 테스트
- 토양 커넥터 12개 + 기상청 커넥터 13개 = 25개 신규 테스트
- 전체 161개 테스트 통과

### 기타
- `.env.example` 추가 (4개 커넥터 API 키 안내)
- `scripts/test_connectors_live.py` 토양/기후 검증 추가

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅
- Phase 5: 섹션 플래너 + 초안 뼈대 ✅
- Phase 6: QA 규칙 엔진 + Export Gate + DOCX/PDF 출력 ✅ (MVP 완료)
- Post-0.5: 스펙 정렬 ✅
- Post-1: 데이터 전처리 및 통계 엔진 ✅
- Post-2: 환경기준 비교 엔진 ✅
- Post-3: 초안 텍스트 생성기 고도화 ✅
- Post-4: 추가 커넥터 (토양, 기후) + 수동 입력 가이드 ✅

## 향후 작업 (Post-5+)
- Post-5: 문서 포맷 고도화
- Post-6: LLM adapter 연동
- Post-7: 통합 테스트 및 최종 데모

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
  - 에어코리아 대기오염정보, 국립환경과학원 수질 DB, 토양측정망, 기상청 ASOS 공유
- python-docx 설치 필요: `pip install python-docx>=1.1.0`
- reportlab 설치 필요: `pip install reportlab>=4.0.0`
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:8000)

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
pytest tests/ -v

# 데모 실행 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```

## 커넥터 현황 (4개)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |

## 주요 파일 (Post-4 신규/수정)
- `backend/app/connectors/soil_info.py` — 토양측정망 커넥터 (신규)
- `backend/app/connectors/kma_weather.py` — 기상청 ASOS 커넥터 (신규)
- `backend/app/connectors/registry.py` — 4개 커넥터 등록 (수정)
- `backend/tests/test_connectors.py` — 25개 테스트 추가 (수정)
- `scripts/test_connectors_live.py` — 토양/기후 검증 추가 (수정)
- `src/components/evidence/evidence-form-dialog.tsx` — 권장 지표 안내 (수정)
- `src/components/evidence/collect-data-dialog.tsx` — 커넥터 파라미터 (수정)
- `backend/.env.example` — 환경변수 예제 (신규)
