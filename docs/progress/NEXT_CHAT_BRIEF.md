# Next Chat Brief

## 마지막 완료 작업
**커넥터 실제 API 연동** ✅

## 완료된 작업 (커넥터 연동)

### 백엔드
- 에어코리아 대기질 커넥터 (`backend/app/connectors/keco_air.py`):
  - 공공데이터포털 에어코리아 대기오염정보 API 실제 연동 (httpx)
  - PM10, PM2.5, O3, NO2, SO2, CO 6개 지표 수집
  - API 키 환경변수 처리 (DATA_GO_KR_API_KEY)
  - fetch → raw_payload 스냅샷 저장 → normalize → evidence 벌크 저장
  - 에러 처리 (API 키 미설정, 측정소명 누락, API 오류 응답, 통신장애 값)
- 물환경정보시스템 수질 커넥터 (`backend/app/connectors/water_info.py`):
  - 물환경정보시스템 수질측정정보 API 실제 연동 (httpx)
  - BOD, COD, SS, DO, T-N, T-P 6개 지표 수집
  - 측정지점별·기간별 조회
  - YYYYMMDD 날짜 변환, 빈 값/None 건너뛰기
- 커넥터 수집 API (`backend/app/api/v1/connectors.py`):
  - GET /api/v1/connectors — 커넥터 목록
  - POST /api/v1/connectors/{connector_key}/collect — 수집 실행
  - 데이터 소스 자동 등록
  - 수집 결과 요약 응답 (status, evidence_count, error_message)
- Pydantic 스키마 (`backend/app/schemas/connector.py`):
  - CollectRequest, CollectResult
- 환경 설정 (`backend/app/config.py`):
  - DATA_GO_KR_API_KEY, CONNECTOR_TIMEOUT 설정 추가
- 테스트 (`backend/tests/test_connectors.py`):
  - 에어코리아 커넥터: normalize 7개 + fetch 4개 테스트
  - 물환경정보 커넥터: normalize 6개 + fetch 3개 테스트
  - 레지스트리 4개 + API 엔드포인트 3개 테스트 (총 27개)

### 프론트엔드
- TypeScript 타입 (`src/types/connector.ts`):
  - ConnectorInfo, CollectRequest, CollectResult
- API 클라이언트 (`src/lib/connector-api.ts`):
  - listConnectors, collectData
- 컴포넌트 (`src/components/evidence/collect-data-dialog.tsx`):
  - 데이터 수집 다이얼로그 (커넥터 선택, 파라미터 입력, 수집 실행, 결과 표시)
  - 커넥터별 동적 파라미터 폼 (에어코리아: 측정소명/기간, 수질: 지점코드/시작일/종료일)
  - 로딩 상태, 성공/실패 표시
- 페이지 수정 (`src/app/projects/[id]/evidences/page.tsx`):
  - "데이터 수집" 버튼 추가
  - 수집 완료 시 증거 목록 자동 새로고침

### 설정
- `.env.example` — DATA_GO_KR_API_KEY, CONNECTOR_TIMEOUT 추가
- `CLAUDE.md` — API 키 발급 안내 추가

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅
- Phase 5: 섹션 플래너 + 초안 뼈대 ✅
- Phase 6: QA 규칙 엔진 + Export Gate + DOCX 출력 ✅ (MVP 완료)

## 향후 작업 (Phase 7+)
- Vercel 배포 설정
- 사용자 인증 (NextAuth.js)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 성능 최적화 및 에러 핸들링

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- python-docx 설치 필요: `pip install python-docx>=1.1.0`
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
```

## 주요 파일
### 커넥터 연동 신규/수정 파일
- `backend/app/connectors/keco_air.py` — 에어코리아 대기질 커넥터 (실제 연동)
- `backend/app/connectors/water_info.py` — 물환경정보시스템 수질 커넥터 (실제 연동)
- `backend/app/api/v1/connectors.py` — 커넥터 수집 API 엔드포인트
- `backend/app/schemas/connector.py` — 수집 요청/결과 스키마
- `backend/app/config.py` — API 키 환경변수 추가
- `backend/app/main.py` — connectors 라우터 등록
- `backend/.env.example` — API 키 변수 추가
- `backend/tests/test_connectors.py` — 연동 테스트 27개
- `src/types/connector.ts` — TypeScript 커넥터 타입
- `src/lib/connector-api.ts` — 커넥터 API 클라이언트
- `src/components/evidence/collect-data-dialog.tsx` — 데이터 수집 다이얼로그
- `src/app/projects/[id]/evidences/page.tsx` — 수집 버튼 추가
