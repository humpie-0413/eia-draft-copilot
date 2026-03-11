# Next Chat Brief

## 마지막 완료 Phase
**Phase 2: 공공데이터 커넥터 및 증거 수집 인프라** ✅

## 완료된 작업 (Phase 2)
- `data_sources` 테이블: 공공데이터 소스 레지스트리 (connector_key 매핑)
- `source_snapshots` 테이블: 원시 응답 JSONB 보존 (raw_payload)
- `evidences` 테이블: 정규화된 증거 데이터 + screening_only 플래그
- Alembic 마이그레이션 002: 위 3개 테이블 + 인덱스 생성
- 각 모델별 CRUD 함수 (벌크 생성, 필터 조회 포함)
- 커넥터 스켈레톤 프레임워크:
  - `BaseConnector`: fetch → 스냅샷 저장 → normalize → 증거 저장 파이프라인
  - `KecoAirConnector`: 에어코리아 대기질 (PM10, PM2.5, O3 등)
  - `WaterInfoConnector`: 물환경정보시스템 수질 (BOD, COD, SS 등)
  - 커넥터 레지스트리 (connector_key → 인스턴스 매핑)
- REST API 엔드포인트:
  - `/api/v1/data-sources`: 소스 CRUD + 커넥터 목록
  - `/api/v1/evidences`: 증거 CRUD + screening_only/category 필터
  - `/api/v1/snapshots`: 스냅샷 CRUD (raw_payload 조회)

## 다음 작업: Phase 3 이후
- 커넥터 실제 API 호출 구현 (httpx 기반)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- Draft Editor UI
- 유사사례 검색, section planner

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- 커넥터 fetch()는 NotImplementedError — 실제 API 키 및 호출 로직은 미구현
- 마이그레이션 실행: `cd backend && alembic upgrade head`

## 백엔드 실행 방법
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
# API 문서: http://localhost:8000/docs
```

## 주요 파일
- `backend/app/models/data_source.py` — DataSource 모델
- `backend/app/models/source_snapshot.py` — SourceSnapshot 모델
- `backend/app/models/evidence.py` — Evidence 모델
- `backend/app/schemas/evidence.py` — Evidence 스키마 + EvidenceCategory enum
- `backend/app/connectors/base.py` — BaseConnector 추상 클래스
- `backend/app/connectors/registry.py` — 커넥터 레지스트리
- `backend/app/connectors/keco_air.py` — 대기질 커넥터 스켈레톤
- `backend/app/connectors/water_info.py` — 수질 커넥터 스켈레톤
- `backend/app/api/v1/evidences.py` — Evidence API 엔드포인트
- `backend/alembic/versions/002_create_evidence_tables.py` — 마이그레이션 002
