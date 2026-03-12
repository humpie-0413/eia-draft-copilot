# Next Chat Brief

## 마지막 완료 작업
**Post-3: 초안 텍스트 생성기 고도화** ✅

## 완료된 작업 (Post-3)

### 서술문 템플릿 엔진
- `backend/app/services/narrative_generator.py`:
  - 대기질: 지표별 환경기준 비교 서술 + 초과 시 저감대책 언급
  - 수질: BOD/COD 병합 서술 + 등급 판정 + 기타 지표 서술
  - 소음·진동: 주간/야간 판정 + 진동 + 방음대책 서술
  - 생태: 식물상/동물상 종수 + 녹지자연도 + 법정보호종 서술
  - 범용: 토양/교통/폐기물 등 환경기준 없는 섹션
  - 미수집: "현장조사 및 자료 수집이 필요하다" 고정 서술문
  - LLM 미사용 결정적 템플릿 방식

### scaffold 서비스 개편
- narrative 필드 분리 (서술문 ↔ 통계 요약 분리)
- 상세 데이터 샘플 5건 제한 (나머지는 "별첨 참조")
- summary_text: 측정 현황 요약 테이블 + 비수치 데이터 + 샘플

### DOCX/PDF export 4부 구조
- 가. 현황 및 영향 분석 (서술문 본문)
- 나. 측정 현황 요약 (통계 테이블)
- 다. 환경기준 비교 (기준 비교 테이블)
- 라. 측정 데이터 (대표 샘플 5건 + "별첨 참조")

### 프론트엔드 업데이트
- 서술문 미리보기 영역 (좌측 강조 바 스타일)
- 원시 데이터 목록 접기/펼치기(collapsible) 전환
- SectionStatusCard 확장 상태 색상 추가

### 테스트
- `backend/tests/test_narrative_generator.py`: 28개 신규 테스트
- 전체 136개 테스트 통과

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

## 향후 작업 (Post-4+)
- Post-4: 추가 커넥터 (토양, 기후)
- Post-5: 문서 포맷 고도화
- Post-6: LLM adapter 연동
- Post-7: 통합 테스트 및 최종 데모

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
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
```

## 주요 파일 (Post-3 신규/수정)
- `backend/app/services/narrative_generator.py` — 서술문 템플릿 엔진 (신규)
- `backend/app/services/draft_scaffold.py` — scaffold 전면 개편 (수정)
- `backend/app/services/export_service.py` — DOCX/PDF 4부 구조 (수정)
- `backend/app/schemas/section.py` — narrative 필드 추가 (수정)
- `backend/app/api/v1/sections.py` — narrative 매핑 추가 (수정)
- `backend/tests/test_narrative_generator.py` — 테스트 28개 (신규)
- `src/types/section.ts` — narrative 필드 추가 (수정)
- `src/components/section/scaffold-section-view.tsx` — 서술문 UI (수정)
- `src/components/section/section-status-card.tsx` — 상태 색상 (수정)
