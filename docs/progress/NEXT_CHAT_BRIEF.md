# Next Chat Brief

## 마지막 완료 Phase
**Phase 0: Project Scaffolding & Planning** ✅

## 완료된 작업
- Git 저장소 클론 및 초기화
- 디렉토리 구조 생성 (`src/app`, `src/components`, `src/lib`, `src/types`, `docs/`)
- CLAUDE.md 작성 (프로젝트 개요, 기술 스택, 컨벤션)
- phase-plan.md 작성 (Phase 0~5 로드맵)
- Next.js 14 + TypeScript + Tailwind CSS 프로젝트 설정
- 기본 레이아웃 (`layout.tsx`) 및 랜딩 페이지 (`page.tsx`) 생성
- ESLint 설정
- .gitignore, .env.example 설정

## 다음 작업: Phase 1 — Core Data Models & Document Parsing
1. `src/types/`에 EIA 문서 구조 타입 정의
2. PDF 파일 업로드 API 라우트 (`src/app/api/upload/`)
3. 텍스트 추출 유틸리티 (`src/lib/parser.ts`)
4. 로컬 스토리지 기반 프로젝트 CRUD

## 주의사항
- Phase 1은 AI 연동 없이 데이터 파이프라인만 구축
- HWP 파싱은 복잡도가 높으므로 PDF 우선 구현
- 타입 정의 시 환경영향평가서 실제 목차 구조 참고 필요

## 참고 파일
- `CLAUDE.md` — 프로젝트 컨벤션 및 기술 스택
- `docs/claude/phase-plan.md` — 전체 Phase 계획
