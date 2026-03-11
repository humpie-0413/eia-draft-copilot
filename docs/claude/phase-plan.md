# EIA Draft Copilot — Phase Plan

## Phase 0: Project Scaffolding & Planning ← 현재
- [x] Git 저장소 초기화
- [x] 디렉토리 구조 생성
- [x] CLAUDE.md 작성
- [x] phase-plan.md 작성
- [x] NEXT_CHAT_BRIEF.md 작성
- [x] Next.js + TypeScript + Tailwind 프로젝트 설정
- [x] .gitignore, .env.example, tsconfig.json 등 설정 파일
- [x] 기본 레이아웃 및 랜딩 페이지 스캐폴딩
- [x] ESLint + Prettier 설정

## Phase 1: Core Data Models & Document Parsing
- [ ] EIA 문서 구조 타입 정의 (섹션, 항목, 메타데이터)
- [ ] PDF/HWP 파일 업로드 및 텍스트 추출 API
- [ ] 참고문서 파싱 및 청크 분할 로직
- [ ] 로컬 스토리지 기반 프로젝트 저장/불러오기

## Phase 2: AI Integration (Claude API)
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
