# Next Chat Brief

## 마지막 완료 작업
**Post-5: 문서 포맷 고도화** ✅

## 완료된 작업 (Post-5)

### DOCX 템플릿 전면 개편
- 표지: "환경영향평가서 초안" + 사업명 + 사업유형(한글) + 위치(centroid 좌표) + 작성일 + "EIA Draft Copilot으로 작성"
- 목차: 테이블 형태 — 제N장 + 제목 + 충족도 상태(완료/미비/미수집) + 증거 건수 + 부록 목차
- 머리말: 사업명(좌) + "환경영향평가서 초안"(우) + 구분선
- 꼬리말: 페이지 번호(중앙) + 구분선
- 섹션 번호: "제1장 대기질" → "1.1 현황" → "1.2 측정" → "1.3 기준비교" → "1.4 데이터"

### 테이블 디자인 개선
- 헤더 배경 연한 파란(#D6E4F0), 교차 행 배경(#F5F5F7)
- 환경기준 초과 시 해당 행 배경 연한 빨간(#FDE0DC)
- 열 너비 조정 (지표명 넓게, 수치 좁게)

### 부록 3종
- 부록 A: 상세 측정 데이터 (섹션별 최대 50건)
- 부록 B: 유사사례 매칭 결과 (유사도 점수 + 요약)
- 부록 C: QA 검사 결과 (이슈 목록, critical 빨간 배경)

### PDF 동일 적용
- reportlab PDF에도 동일 구조 (머리말/꼬리말, 테이블 색상, 부록)

### API 변경
- Export 옵션 쿼리 파라미터 (부록 포함 여부)
- GET /export/preview: 문서 구조 미리보기 엔드포인트

### 프론트엔드
- ExportPreviewPanel: 문서 구조 트리 + 부록 옵션 체크박스
- ExportButton에 옵션 전달 통합

### 테스트
- 40개 신규 테스트 (test_export_format.py)
- 전체 201개 테스트 통과

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
- Post-5: 문서 포맷 고도화 ✅

## 향후 작업 (Post-6+)
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

## 주요 파일 (Post-5 신규/수정)
- `backend/app/services/export_service.py` — DOCX/PDF 전면 개편 (수정)
- `backend/app/api/v1/export.py` — 옵션 파라미터 + 미리보기 API (수정)
- `backend/tests/test_export_format.py` — 40개 신규 테스트 (신규)
- `src/types/export.ts` — ExportPreview/ExportOptions 타입 (신규)
- `src/lib/qa-api.ts` — 미리보기 API + 옵션 지원 (수정)
- `src/components/qa/export-preview.tsx` — 문서 구조 미리보기 (신규)
- `src/components/qa/export-button.tsx` — 옵션 통합 (수정)
