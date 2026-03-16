# EIA Draft Copilot — 배포 전 완성 Phase 계획

## 선택된 작업 영역
1. 영향 예측 모듈 (정형 수학 모델 기반)
2. 추가 커넥터 확장 (가능한 범위)

---

## Phase 로드맵

| Phase | 이름 | 핵심 목표 |
|-------|------|-----------|
| Pred-1 | 예측 모듈 기반 구축 | 예측 엔진 인터페이스 + 대기 확산 모델 |
| Pred-2 | 소음·수질 예측 모델 | 소음 전파 + 수질 혼합 모델 |
| Pred-3 | 예측 결과 통합 | scaffold/export에 예측 결과 반영, 서술문 생성 |
| Conn-1 | 추가 커넥터 조사·구현 | 교통/폐기물/경관 API 탐색 + 가능한 것 구현 |
| Final-1 | 통합 검증 + 문서화 | 전체 데모, 테스트, 문서 최종 업데이트 |

---

## Pred-1: 예측 모듈 기반 구축 + 대기 확산 모델

### 목표
영향 예측 엔진의 기반 구조를 만들고, 첫 번째 모델로 대기 확산 예측(가우시안 플룸)을 구현한다.

### 배경
가우시안 플룸 모델은 점 오염원(굴뚝 등)에서 배출된 대기오염물질의 확산을 예측하는 표준 모델이다.
공식: C(x,y,z) = (Q / (2π·u·σy·σz)) · exp(-y²/(2σy²)) · [exp(-(z-H)²/(2σz²)) + exp(-(z+H)²/(2σz²))]
- Q: 배출량 (g/s), u: 풍속 (m/s), H: 유효 굴뚝높이 (m)
- σy, σz: 수평/수직 확산계수 (Pasquill-Gifford 안정도 등급 기반)

### 프롬프트

```
CLAUDE.md, docs/progress/NEXT_CHAT_BRIEF.md, git status를 읽어라. 현재 상태를 요약한 뒤 Pred-1 (예측 모듈 기반 + 대기 확산 모델)만 수행하라. 모든 커밋 메시지, 주석, 문서는 한글로 작성하라. 사용자에게 허가를 묻지 말고, 에이전트 판단하에 프롬프트 범위 내 작업을 끝까지 완료하라.

Pred-1 범위:

1. 예측 엔진 기반 구조 (backend/app/services/prediction/)
   - __init__.py
   - base.py — BasePredictionModel 추상 클래스
     - predict(project, parameters) → PredictionResult
     - get_required_inputs() → 필요 입력 파라미터 목록
     - get_model_info() → 모델명, 설명, 적용 분야
   - registry.py — 모델 레지스트리 (section_key → model 매핑)
   - PredictionResult 스키마:
     - section_key, model_name, input_parameters
     - predictions: list[PredictionItem] (지점/거리별 예측값)
     - summary: 요약 텍스트
     - assumptions: 전제 조건 목록
     - limitations: 모델 한계 설명

2. 대기 확산 모델 (backend/app/services/prediction/air_dispersion.py)
   - 가우시안 플룸 모델 구현
   - 입력 파라미터:
     - emission_rate (Q): 오염물질 배출량 (g/s) — 사업 유형별 기본값 제공
     - stack_height (H): 굴뚝 높이 (m) — 기본값 제공
     - wind_speed (u): 풍속 (m/s) — 기후 커넥터 데이터 활용 가능
     - stability_class: 대기안정도 등급 (A~F, Pasquill-Gifford) — 기본값 D(중립)
   - Pasquill-Gifford 확산계수 σy, σz 계산 (안정도 등급별 경험식)
   - 출력: 풍하거리별(100m, 200m, 500m, 1km, 2km, 5km) 지표면 농도 예측
   - 기존 대기질 현황 데이터(에어코리아)와 예측 결과를 합산하여 사업 후 예상 농도 산출
   - PM10, PM2.5, NO2, SO2에 대해 각각 예측
   - 예측 결과를 환경기준과 비교하여 초과 여부 판정

3. 예측 API 엔드포인트
   - POST /api/v1/projects/{id}/predict/{section_key} — 예측 실행 (파라미터 입력)
   - GET /api/v1/projects/{id}/predictions — 저장된 예측 결과 조회
   - GET /api/v1/prediction-models — 사용 가능한 모델 목록

4. 예측 파라미터 기본값
   - 사업유형별 배출량 기본값 딕셔너리:
     - power_plant: PM10=0.5g/s, PM2.5=0.3g/s, NO2=1.0g/s, SO2=0.5g/s
     - industrial: PM10=1.0g/s, PM2.5=0.5g/s, NO2=2.0g/s, SO2=1.0g/s
     - (기타 유형은 power_plant의 50% 수준)
   - 기본 굴뚝높이: power_plant=50m, industrial=30m, 기타=20m
   - 풍속: 프로젝트의 기후 데이터에서 자동 추출, 없으면 기본값 3.0 m/s

5. 테스트 작성
   - 가우시안 플룸 계산 정확성 테스트 (알려진 값과 비교)
   - 확산계수 계산 테스트 (안정도 등급별)
   - API 엔드포인트 테스트
   - 기본값 적용 테스트

Pred-2 이후 작업은 착수하지 마라.
```

---

## Pred-2: 소음 전파 + 수질 혼합 모델

### 목표
소음 거리감쇠 모델과 수질 희석 모델을 추가 구현한다.

### 배경
- 소음: 점음원 거리감쇠 공식 L(r) = Lw - 20·log10(r) - 11 (자유음장), 반사보정, 차음벽 효과
- 수질: 완전혼합 희석 모델 C_mix = (Q_river·C_river + Q_discharge·C_discharge) / (Q_river + Q_discharge)

### 프롬프트

```
CLAUDE.md, docs/progress/NEXT_CHAT_BRIEF.md, git status를 읽어라. 현재 상태를 요약한 뒤 Pred-2 (소음 전파 + 수질 혼합 모델)만 수행하라. 모든 커밋 메시지, 주석, 문서는 한글로 작성하라. 사용자에게 허가를 묻지 말고, 에이전트 판단하에 프롬프트 범위 내 작업을 끝까지 완료하라.

Pred-2 범위:

1. 소음 전파 모델 (backend/app/services/prediction/noise_propagation.py)
   - 점음원 거리감쇠 모델:
     L(r) = Lw - 20·log10(r) - 11 (자유음장 점음원)
     여기서 Lw: 음원 음향파워레벨 (dB), r: 거리 (m)
   - 선음원(도로) 감쇠: L(r) = Lw/m - 10·log10(r) - 8
   - 보정 요소:
     - 지면 반사 보정: +3 dB (반사면 위)
     - 대기 흡수: -α·r/1000 (α ≈ 0.005 dB/m, 주파수 의존)
     - 차음벽 효과: 프레넬 수(N) 기반 Maekawa 회절 감쇠 (선택적 입력)
   - 입력 파라미터:
     - source_type: point(점음원) 또는 line(선음원/도로)
     - sound_power_level (Lw): 음원 레벨 (dB) — 사업유형별 기본값
     - barrier_height: 차음벽 높이 (m, 0이면 없음)
     - receiver_height: 수음점 높이 (m, 기본값 1.2m)
   - 출력: 거리별(10m, 20m, 50m, 100m, 200m, 500m) 예측 소음도
   - 기존 소음 현황 + 예측 소음을 에너지 합산: L_total = 10·log10(10^(L1/10) + 10^(L2/10))
   - 환경기준 비교 (주간/야간)
   - 사업유형별 기본값:
     - power_plant: Lw=95dB (점음원)
     - road: Lw/m=75dB/m (선음원)
     - housing: Lw=90dB (건설장비, 점음원)
     - industrial: Lw=100dB (점음원)

2. 수질 혼합 모델 (backend/app/services/prediction/water_mixing.py)
   - 완전혼합 희석 모델:
     C_mix = (Q_river · C_river + Q_discharge · C_discharge) / (Q_river + Q_discharge)
   - 입력 파라미터:
     - river_flow (Q_river): 하천 유량 (m³/s) — 수동 입력 또는 기본값
     - discharge_flow (Q_discharge): 방류량 (m³/s) — 사업유형별 기본값
     - discharge_concentration: 방류수 오염물질 농도 (mg/L) — 방류수 수질기준 적용
     - 방류수 수질기준: BOD 30mg/L, COD 40mg/L, SS 30mg/L, T-N 60mg/L, T-P 8mg/L (물환경보전법 시행규칙)
   - 기존 수질 현황(평균값)을 C_river로 사용
   - 출력: 혼합 후 예상 농도 (BOD, COD, SS, T-N, T-P)
   - 환경기준(등급) 비교
   - 사업유형별 기본값:
     - power_plant: Q_discharge=0.01 m³/s
     - industrial: Q_discharge=0.1 m³/s
     - housing: Q_discharge=0.05 m³/s

3. 두 모델 모두 BasePredictionModel 상속, registry 등록

4. 테스트 작성
   - 소음 감쇠 계산 정확성 (알려진 거리-감쇠 관계)
   - 에너지 합산 정확성
   - 수질 혼합 계산 정확성
   - 차음벽 효과 테스트
   - API 테스트

Pred-3 이후 작업은 착수하지 마라.
```

---

## Pred-3: 예측 결과 통합 (scaffold/export/UI)

### 목표
예측 결과를 scaffold, DOCX/PDF export, 프론트엔드에 반영한다. 서술문에 영향 예측 파트를 추가한다.

### 프롬프트

```
CLAUDE.md, docs/progress/NEXT_CHAT_BRIEF.md, git status를 읽어라. 현재 상태를 요약한 뒤 Pred-3 (예측 결과 통합)만 수행하라. 모든 커밋 메시지, 주석, 문서는 한글로 작성하라. 사용자에게 허가를 묻지 말고, 에이전트 판단하에 프롬프트 범위 내 작업을 끝까지 완료하라.

Pred-3 범위:

1. scaffold 서비스 확장
   - 기존 4부 구조에 "영향 예측" 파트 추가:
     1.1 현황 및 영향 분석 (서술문)
     1.2 측정 현황 요약 (통계 테이블)
     1.3 환경기준 비교 (기준 비교 테이블)
     **1.4 영향 예측 (NEW)**
     1.5 측정 데이터 (샘플 5건)
   - 예측 파트에 포함할 내용:
     - 예측 모델명, 입력 파라미터, 전제 조건
     - 거리별/지점별 예측 결과 테이블
     - 예측 결과 + 현황 합산값
     - 환경기준 비교 판정

2. 서술문 생성 확장 (narrative_generator.py)
   - 대기질 영향 예측 서술문:
     "가우시안 플룸 모델을 적용하여 대기오염물질 확산을 예측한 결과, 사업지 경계(100m 지점)에서 PM10 기여농도는 {값} ug/m3으로 예측되었다. 현황 농도({현황값} ug/m3)와 합산 시 {합산값} ug/m3으로 환경정책기본법 시행령 별표 제1호에 따른 대기환경기준({기준값} ug/m3) {판정}이다."
   - 소음 영향 예측 서술문:
     "점음원 거리감쇠 모델을 적용하여 소음 전파를 예측한 결과, 가장 가까운 수음점({거리}m)에서 예측 소음도는 {값} dB(A)이다. 현황 소음({현황값} dB(A))과 에너지 합산 시 {합산값} dB(A)로 {판정}."
   - 수질 영향 예측 서술문:
     "완전혼합 희석 모델을 적용하여 방류수 혼합 후 수질을 예측한 결과, BOD {값} mg/L, COD {값} mg/L로 하천 생활환경기준 {등급} 수준이다."
   - 예측이 없는 섹션: "본 분야에 대한 영향 예측은 별도 전문 분석이 필요하다."

3. DOCX/PDF export 수정
   - 예측 결과가 있는 섹션에 "X.4 영향 예측" 하위 섹션 추가
   - 예측 결과 테이블: 지점/거리 | 기여농도 | 현황 | 합산 | 기준 | 판정
   - 전제 조건 및 모델 한계를 "※ 참고" 문단으로 추가
   - 기존 측정 데이터는 X.5로 밀림

4. 프론트엔드
   - 프로젝트별 "영향 예측" 페이지 추가 (/projects/[id]/predictions)
   - 섹션별 예측 모델 선택 + 파라미터 입력 폼
   - 기본값 자동 채움 (사업유형 + 기후 데이터 기반)
   - 예측 실행 버튼 → 결과 테이블 + 차트(거리-농도 그래프)
   - 초안 뼈대 화면에 예측 결과 미리보기 영역 추가

5. 테스트 작성
   - scaffold에 예측 결과 포함 테스트
   - 서술문 생성 테스트
   - DOCX 구조 검증 (X.4 영향 예측 존재)

Conn-1 이후 작업은 착수하지 마라.
```

---

## Conn-1: 추가 커넥터 확장

### 목표
교통/폐기물/경관 3개 미수집 섹션 중 공공 API로 자동화 가능한 것을 구현한다.

### 프롬프트

```
CLAUDE.md, docs/progress/NEXT_CHAT_BRIEF.md, git status를 읽어라. 현재 상태를 요약한 뒤 Conn-1 (추가 커넥터 확장)만 수행하라. 모든 커밋 메시지, 주석, 문서는 한글로 작성하라. 사용자에게 허가를 묻지 말고, 에이전트 판단하에 프롬프트 범위 내 작업을 끝까지 완료하라.

Conn-1 범위:

현재 미수집 3개 섹션(교통, 폐기물, 경관)에 대해 공공 API를 조사하고 가능한 것을 구현한다.

1. 교통 — 부분 자동화 시도
   - 국가교통DB(KTDB) 또는 도로교통공단 교통량 API 조사 (data.go.kr 검색)
   - API가 존재하면:
     - 커넥터 구현 (BaseConnector 상속)
     - 사업지 인근 주요 도로 교통량(AADT) 수집
     - 수집 지표: 도로명, 교통량(대/일), 도로 등급
   - API가 없거나 사업지 특화 데이터 불가능하면:
     - 지역별 교통통계 수준이라도 수집 시도
     - 최종적으로 불가하면 수동 입력 유지 확정 + 수동 입력 가이드 강화

2. 폐기물 — 자동화 가능성 낮음
   - 환경부 폐기물 통계 API 조사 (data.go.kr)
   - 지역별 폐기물 발생량 통계가 있으면 커넥터 구현
   - 없으면 수동 입력 유지 확정 + 권장 지표 가이드:
     - 건설폐기물 예상 발생량 (m³/일)
     - 생활폐기물 예상 발생량 (톤/일)
     - 지정폐기물 발생 여부

3. 경관 — 자동화 불가
   - 경관은 현장 시각 조사 필수이므로 API 자동화 불가 확정
   - 수동 입력 가이드 강화:
     - 주요 조망점 유무
     - 스카이라인 영향 여부
     - 경관 등급 (1~5등급)
     - 주요 경관 자원 (산, 하천, 역사경관 등)
   - 프론트엔드 수동 입력 폼에 경관 전용 필드 추가

4. 미수집 섹션 서술문 개선
   - 수동 입력 유지 확정된 섹션의 서술문 개선:
     - 기존: "본 분야에 대한 현황 데이터가 수집되지 않았다."
     - 변경: "본 분야는 현장조사 및 전문가 판단이 필요한 항목으로, 자동 수집 대상에 해당하지 않는다. 아래 항목에 대한 수동 입력이 필요하다: {권장 지표 목록}"

5. 각 커넥터:
   - 실제 API 호출 테스트 (가능한 경우)
   - 단위 테스트
   - scripts/test_connectors_live.py 업데이트
   - 프론트엔드 커넥터 목록 업데이트

Final-1 이후 작업은 착수하지 마라.
```

---

## Final-1: 통합 검증 + 문서화

### 프롬프트

```
CLAUDE.md, docs/progress/NEXT_CHAT_BRIEF.md, git status를 읽어라. 현재 상태를 요약한 뒤 Final-1 (통합 검증 + 문서화)만 수행하라. 모든 커밋 메시지, 주석, 문서는 한글로 작성하라. 사용자에게 허가를 묻지 말고, 에이전트 판단하에 프롬프트 범위 내 작업을 끝까지 완료하라.

Final-1 범위:

1. 데모 스크립트 최종 업데이트 (scripts/demo_full_scenario.py)
   - 기존 강남구 태양광 시나리오 확장:
     a. 전체 커넥터 수집 (기존 6종 + 추가된 것)
     b. 영향 예측 실행 (대기 확산, 소음 전파, 수질 혼합)
     c. 예측 결과 포함 scaffold 확인
     d. QA 실행 (R001~R008 + 예측 관련 검증)
     e. DOCX + PDF export (영향 예측 포함)
   - 각 단계별 콘솔 출력
   - 최종 비교 요약: 전체 섹션 상태, 예측 포함 여부, QA 결과

2. 전체 테스트 실행
   - pytest 전체 통과 확인
   - 실패 시 수정

3. 문서 최종 업데이트
   - README.md: 영향 예측 모듈, 추가 커넥터 반영
   - docs/architecture.md: 예측 엔진 구조, 모델 목록
   - docs/user-guide.md: 영향 예측 사용법, 파라미터 설명
   - docs/api-reference.md: 예측 API 엔드포인트
   - docs/development.md: 새 예측 모델 추가 방법, 새 커넥터 추가 방법
   - docs/progress/WORKLOG.md: Pred-1~Pred-3, Conn-1, Final-1 이력

4. 프로젝트 전체 현황 문서 업데이트
   - 전체 Phase 이력 정리
   - 현재 시스템 구성 최신화
   - 알려진 제한사항 및 향후 과제

5. output/ 폴더에 최종 DOCX + PDF 생성

이것이 배포 전 완성 Phase의 마지막 단계이다.
```

---

## 진행 규칙 (기존과 동일)
1. 한 세션에 한 Phase만 진행
2. Phase 전환 시 새 채팅
3. 커밋 시점은 Claude Code 에이전트가 자체 판단
4. 결과 요약 제공 → 분석 → 다음 프롬프트 제공
