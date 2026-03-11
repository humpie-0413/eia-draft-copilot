# Next Chat Brief

## 마지막 완료 Phase
**Phase 1: Project CRUD & Backend API** ✅

## 완료된 작업
- FastAPI 백엔드 프로젝트 구조 생성 (`backend/`)
- PostgreSQL + PostGIS 기반 `projects` 테이블 스키마
- Alembic 마이그레이션 설정 + 초기 마이그레이션 (001)
- Project CRUD REST API: `POST/GET/PATCH/DELETE /api/v1/projects`
- GeoJSON 지오메트리 입력 (Point, Polygon, MultiPolygon) 및 PostGIS 저장
- Pydantic v2 스키마: ProjectCreate, ProjectRead, ProjectUpdate, ProjectList
- ProjectStatus / ProjectType enum 정의
- CORS 설정 (Next.js 프론트엔드 연동 대비)
- pytest + httpx 통합 테스트 9개

## 다음 작업: Phase 1.5 — Document Parsing
1. EIA 문서 구조 타입 정의 (섹션, 항목, 메타데이터)
2. PDF 파일 업로드 API 라우트
3. 텍스트 추출 유틸리티
4. 참고문서 파싱 및 청크 분할 로직

## 주의사항
- PostgreSQL + PostGIS가 로컬에 설치되어 있어야 테스트 실행 가능
- `backend/.env`를 `.env.example` 기준으로 설정 필요
- Phase 2(AI 연동), 증거 수집, 커넥터 등은 미착수 상태

## 백엔드 실행 방법
```bash
cd backend
pip install -r requirements.txt
# DB 마이그레이션
alembic upgrade head
# 개발 서버
uvicorn app.main:app --reload
# API 문서: http://localhost:8000/docs
```

## 참고 파일
- `CLAUDE.md` — 프로젝트 컨벤션 및 기술 스택
- `docs/claude/phase-plan.md` — 전체 Phase 계획
- `backend/app/api/v1/projects.py` — Project API 엔드포인트
- `backend/app/models/project.py` — SQLAlchemy 모델
- `backend/app/schemas/project.py` — Pydantic 스키마
