# Next Chat Brief

## 마지막 완료 작업
**CLAUDE.md 통합 로드맵 반영** ✅ (2026-03-16)

## 현재 상태
- 커넥터 안정 가동: 2/9 (에어코리아, 토지이용규제)
- 커넥터 타임아웃 미해결: 수질DB, 기상청 ASOS
- V-world 세종/보령 좌표 문제 미해결
- 양평 시나리오만 Export 가능, 세종/보령은 Export 불가 (critical QA)
- 649개 테스트 전체 통과

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
- Demo-3: 3종 시나리오 데모 스크립트 ✅
- Deploy: 배포 환경 구성 ✅
- Phase 4: 3종 시나리오 실행 검증 ✅
- Bugfix-6: 6건 버그 수정 ✅

## 다음 작업 순서
1. **Connector-Fix**: 커넥터 안정화 (최우선) — 수질/기상 타임아웃 디버깅, V-world 좌표 문제
2. **Wind-AERMOD**: 풍배도 + AERMOD 입력 생성 — 실무자 즉시 가치 높음
3. **Spatial-Advanced**: 공간 분석 고도화 — DEM, 토지피복도, 지적도
4. **HWP-Export**: HWP 출력 — 한국 실무 필수
5. **Map-Enhancement**: GIS 도면 사용자 친화성 개선
6. **Portfolio**: 포트폴리오 문서 정리

## 주의사항
- curl 사용 금지 (python urllib 사용)
- 더미 데이터 절대 사용 금지
- 커밋 메시지, 주석, 문서는 한글로 작성

## 미해결 이슈
- 수질 커넥터 타임아웃 근본 해결 필요
- 기상청 ASOS 타임아웃 근본 해결 필요
- V-world 세종/보령 좌표 문제
- 폐기물/교통 지역별 안정성
- 토양측정망 외부 서버 장애 (수정 불가)
- "연평균의 연평균" 중복 표현 확인

## 실행 방법
```bash
# Docker 실행 (권장)
cp .env.docker.example .env
# .env 파일에 API 키 설정 후:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up     # 개발
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d  # 운영

# 로컬 실행
cd backend && uvicorn app.main:app --reload
npm run dev

# 테스트
cd backend && pytest tests/ -v    # 649개 테스트

# 3종 시나리오 데모 (백엔드 서버 실행 후)
python scripts/demo_road_yangpyeong.py
python scripts/demo_housing_sejong.py
python scripts/demo_powerplant_boryeong.py
```
