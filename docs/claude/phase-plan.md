# EIA Draft Copilot — Phase Plan

## Phase 0: Project Scaffolding & Planning ✅
- [x] Git 저장소 초기화
- [x] 디렉토리 구조 생성
- [x] CLAUDE.md 작성
- [x] phase-plan.md 작성
- [x] NEXT_CHAT_BRIEF.md 작성
- [x] Next.js + TypeScript + Tailwind 프로젝트 설정
- [x] .gitignore, .env.example, tsconfig.json 등 설정 파일
- [x] 기본 레이아웃 및 랜딩 페이지 스캐폴딩
- [x] ESLint + Prettier 설정

## Phase 1: Project CRUD & Backend API ✅
- [x] FastAPI 백엔드 스캐폴딩 (`backend/`)
- [x] PostgreSQL + PostGIS DB 스키마 (projects 테이블)
- [x] Alembic 마이그레이션 설정 및 초기 마이그레이션
- [x] Project CRUD API 엔드포인트 (POST/GET/PATCH/DELETE)
- [x] GeoJSON 지오메트리 입력 및 검증 (geojson-pydantic)
- [x] Pydantic 스키마 기반 입력 검증 및 에러 핸들링
- [x] 통합 테스트 (pytest + httpx)

## Phase 1.5: Core Data Models & Document Parsing (이전 Phase 1)
- [ ] EIA 문서 구조 타입 정의 (섹션, 항목, 메타데이터)
- [ ] PDF/HWP 파일 업로드 및 텍스트 추출 API
- [ ] 참고문서 파싱 및 청크 분할 로직

## Phase 2: 공공데이터 커넥터 및 증거 수집 인프라 ✅
- [x] 공공데이터 커넥터 스켈레톤 (BaseConnector + 레지스트리)
- [x] data_sources 테이블 및 스키마 (소스 레지스트리)
- [x] source_snapshots 테이블 및 스키마 (raw payload JSONB 보존)
- [x] evidences 테이블 및 스키마 (정규화된 증거 + screening_only 분리)
- [x] Alembic 마이그레이션 002 (3개 테이블 + 인덱스)
- [x] CRUD 함수 (벌크 생성, 필터 조회 포함)
- [x] REST API 엔드포인트 (data-sources, evidences, snapshots)
- [x] 커넥터 스켈레톤: KecoAirConnector (대기질), WaterInfoConnector (수질)

## Phase 2.5: AI Integration (Claude API)
- [ ] Claude API 클라이언트 설정 (`@anthropic-ai/sdk`)
- [ ] EIA 섹션별 프롬프트 템플릿 설계
- [ ] 스트리밍 응답 처리 (Server-Sent Events)
- [ ] 컨텍스트 관리 (참고문서 + 이전 섹션 요약)

## Phase 3: Draft Editor UI
- [ ] 섹션 네비게이션 사이드바
- [ ] 리치 텍스트 에디터 (Tiptap 또는 Slate)
- [ ] AI 초안 생성 패널 (생성/수정/재생성)
- [ ] 인라인 AI 제안 및 수정 UI

## Phase 4: Review & Compliance Check
- [ ] 환경영향평가법 기반 체크리스트 엔진
- [ ] 섹션 완성도 검증 (필수 항목 누락 감지)
- [ ] 검토 코멘트 시스템
- [ ] 최종 보고서 내보내기 (PDF/DOCX)

## Phase 5: Deployment & Polish
- [ ] Vercel 배포 설정
- [ ] 환경변수 및 시크릿 관리
- [ ] 사용자 인증 (NextAuth.js)
- [ ] 성능 최적화 및 에러 핸들링
- [ ] 사용자 피드백 수집 및 반영

---

## Design Principles
1. **점진적 구현**: 각 Phase는 독립적으로 동작 가능한 단위
2. **AI-first**: AI 초안 생성이 핵심 워크플로우
3. **법규 준수**: 환경영향평가법 요건을 시스템에 내장
4. **사용자 주도**: AI는 제안하고, 최종 판단은 사용자가
