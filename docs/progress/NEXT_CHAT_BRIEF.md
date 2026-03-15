# Next Chat Brief

## 마지막 완료 작업
**GIS-2: 프론트엔드 지도 시각화** ✅

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1~Pred-3: 예측 모듈 통합 완료 ✅
- Conn-1~Conn-2: 커넥터 확장 완료 ✅
- Final-1~Final-2: 통합 검증 + 문서화 완료 ✅
- Demo-1~Demo-2: 통합 데모 + QA 해결 + Export 성공 ✅
- Doc-1: CLAUDE.md 전면 업데이트 ✅
- LLM-Enhancement: 서술문 품질 최종 개선 ✅
- GIS-1: GIS 공간 분석 및 도면 생성 ✅
- GIS-2: 프론트엔드 지도 시각화 ✅

## 완료된 작업 (GIS-2: 2026-03-15)

### 의존성
- maplibre-gl 5.20.1 설치 (OpenFreeMap 무료 타일 — API 키 불필요)

### 기본 지도 컴포넌트 (`src/components/map/base-map.tsx`)
- MapLibre GL JS 래퍼 컴포넌트
- 프로젝트 geometry centroid 자동 계산 + bounds 맞춤
- 한국 중심 기본값: [127.0, 37.5], zoom 10
- 지도 컨트롤: 줌, 방위, 축척
- minimal 모드 (미니맵용)

### 레이어 시스템 (`src/components/map/use-map-layers.ts`)
- 사업 경계: 초록색 반투명 폴리곤 + 실선 (항상 표시)
- 1km 버퍼: 파란 점선 (토글)
- 5km 버퍼: 보라 점선 (토글)
- 대기측정소: 빨간 원 마커 + 이름 라벨 + 클릭 팝업 (토글)
- 수질측정소: 파란 원 마커 + 클릭 팝업 (토글)
- 소음측정소: 노란 원 마커 + 클릭 팝업 (토글)
- 문화재: 빨간 마커 + 문화재명 + 클릭 팝업 (토글)
- 용도지역: 용도별 색상 구분 (주거=노랑, 상업=빨강, 공업=보라, 녹지=초록, 토글)
- 클릭 팝업: 항목명, 유형, 이격거리, 메타데이터

### 레이어 컨트롤 (`src/components/map/layer-control.tsx`)
- 체크박스 토글 + 범례 색상 + 접기/펼치기

### 사업 경계 편집 도구 (`src/components/map/draw-tools.tsx`)
- 클릭으로 꼭짓점 추가, 더블클릭으로 완성
- 꼭짓점 드래그 편집 + 초기화/삭제
- 면적(㎡/km²) + 중심점 좌표 자동 계산
- GeoJSON Polygon → 프로젝트 geometry 저장

### 미니 지도 (`src/components/map/mini-map.tsx`)
- 소형 지도 (상호작용 비활성화)
- 사업 경계 + 포인트 마커

### 프로젝트 지도 페이지 (`/projects/[id]/map`)
- 전체 화면 지도 + 사이드 패널
- 사이드 패널: 프로젝트 정보, 경계 편집, 레이어 컨트롤
- 버퍼 내 규제 항목 목록 (이격거리)
- 정적 도면 다운로드 (5종)
- 네비게이션 링크

### API 클라이언트 (`src/lib/project-api.ts`)
- getProject() / updateProjectGeometry()

### 기존 페이지 연동
- 프로젝트 목록: "지도" 버튼 추가
- 초안 뼈대: "대화형 지도" 버튼 추가

### 빌드 결과
- TypeScript 타입 체크 통과
- Next.js 빌드 성공
- 백엔드 644개 테스트 전체 통과

## 다음 작업 후보

### Phase Deploy: 배포 환경 구성
- Docker Compose 통합 (PostgreSQL+PostGIS, FastAPI, Next.js)
- CI/CD 파이프라인
- 환경 분리 (dev/staging/prod)

### Phase Portfolio: 포트폴리오 문서 정리
- GIS 도면 산출물 포함
- 데이터 파이프라인 아키텍처 다이어그램
- Before/After 서술문 비교

## 시스템 전체 현황

### 백엔드 서비스 (13개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| scope_service.py | 사업유형별 필수/권장/선택 평가 범위 판단 |
| draft_scaffold.py | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback + 예측 결과 포함) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 + 한글 지표명 + 법적 근거 + 기준 대비 % + 저감방안 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 + 부분충족 WARNING |
| export_service.py | DOCX/PDF 생성 + 한글 지표명 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 + GIS 도면 삽입 |
| prediction/ | 예측 모듈 (대기 확산 + 소음 전파 + 수질 혼합) |
| llm/ | LLM 어댑터 (none / openai_paid / gemini_free) + 10규칙 전문가 프롬프트 |
| spatial_analysis.py | 버퍼 분석 + 규제 항목 중첩 탐색 |
| map_renderer.py | 5종 정적 도면 렌더링 |

### 프론트엔드 지도 컴포넌트 (6개)
| 컴포넌트 | 역할 |
|----------|------|
| base-map.tsx | MapLibre GL JS 래퍼 |
| use-map-layers.ts | 8개 레이어 관리 훅 |
| layer-control.tsx | 레이어 토글 패널 |
| draw-tools.tsx | 폴리곤 그리기/편집 |
| mini-map.tsx | 미니 지도 |
| /map/page.tsx | 전체 화면 지도 페이지 |

### API 엔드포인트 (18개 라우터)
- 기존 15개 라우터 (변경 없음)

### 테스트 (644개)
- 백엔드 전체 통과
- 프론트엔드 TypeScript + Next.js 빌드 통과

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정) — vworld.kr에서 별도 발급
- **국가유산청 API**: 키 불필요 (공개 API)
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:3000)
- **GIS 도면 생성**: matplotlib + geopandas + pyproj 설치 필요
- **대화형 지도**: maplibre-gl (프론트엔드, npm에 포함)

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
pytest tests/ -v    # 644개 테스트

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py
```
