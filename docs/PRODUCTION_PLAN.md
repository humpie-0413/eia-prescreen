# EIA Pre-Screen 실무 확장 계획

> 작성일: 2026-03-31 | 기반: PROJECT_AUDIT.md 전수조사 결과

---

## 목표

- **현재**: 포트폴리오 수준의 사전검토 보조 도구 (운영 준비도 ~92%)
- **목표**: 환경영향평가 대행업체가 실무에 사용할 수 있는 수준

---

## 확장 방향 4개 축

| 축 | 현재 상태 | 목표 상태 |
|---|----------|----------|
| 1. 데이터 완결성 | 20개 항목 중 11개 완전, 4개 부분, 5개 미보유 (55%) | 20개 항목 90%+ 커버 |
| 2. 법령 최신성 | YAML 규칙 64개 (수동 관리) | 개정 자동 감지 + 관리자 반영 |
| 3. 보고서 전문성 | 6장 18섹션 초안 | 가이드라인 21항목 초안 + 전문 서식 |
| 4. 운영 안정성 | 인메모리 + JSON 파일 | DB 영속화, 사용자 관리, 감사 로그 |

---

## 우선순위 기준

```
              높은 임팩트
                  │
    ┌─────────────┼─────────────┐
    │  P1: 즉시   │  P2: 다음   │
    │  (축1,4)    │  (축2)      │
    ├─────────────┼─────────────┤
    │  P3: 여유   │  P4: 보류   │
    │  (축3)      │             │
    └─────────────┼─────────────┘
                  │
              낮은 임팩트
    쉬운 구현 ←───┼───→ 어려운 구현
```

- 공공 API 존재 → 우선
- 기존 커넥터 패턴 재사용 가능 → 우선
- DB 없이도 동작하는 현재 아키텍처 유지

---

## Step별 실행 계획

### Phase A: 운영 안정성 (3일)

#### Step A-1: 문서 정합성 수정 (0.5일)

**목표**: 전수조사에서 발견된 문서 불일치 일괄 수정

**수정 대상 파일**:
- `README.md` — 수치 업데이트, 데모 시나리오 삭제, 커넥터/엔드포인트 수 갱신
- `.env.example` — DEMO_MODE 설명 갱신 ("커넥터 오류 무시 + 빈 데이터" 명시)
- `CLAUDE.md` — ITERATION_PLAN_V2.md 참조 제거, report.py/regulation.py 라우터 제거, 수치 갱신 (89건, 174개, 6,104 청크 등)
- `data/demo/` — 잔존 디렉토리 완전 삭제
- E2E 테스트 9개 파일 — `?scenario=yangpyeong` 쿼리 파라미터 제거 (24곳)

**수락 기준**:
- 모든 문서 수치가 실제 코드와 일치
- `data/demo/` 존재하지 않음
- E2E 테스트에서 scenario 참조 0건
- `pnpm build` + `pytest` 통과

**프롬프트**:
```
전수조사(docs/PROJECT_AUDIT.md) 6장에 정리된 P2 이슈 8건을 모두 수정해줘.
README.md, .env.example, CLAUDE.md의 수치를 실제 코드 기준으로 갱신하고,
data/demo/ 디렉토리 삭제, E2E 테스트의 scenario 파라미터 제거.
수정 후 pnpm build + pytest 실행하여 통과 확인.
```

---

#### Step A-2: Docker 프로덕션 모드 (0.5일)

**목표**: docker-compose.yml을 프로덕션 실행 모드로 전환

**수정 대상 파일**:
- `docker-compose.yml` — dev 모드 → prod 모드 (command 제거로 Dockerfile CMD 사용)
- `docker-compose.dev.yml` (신규) — 개발용 오버라이드 (--reload, pnpm dev)
- `backend/Dockerfile` — non-root 사용자 추가, HEALTHCHECK 추가
- `frontend/Dockerfile` — non-root 사용자 추가, HEALTHCHECK 추가

**수락 기준**:
- `docker compose up` → 프로덕션 모드 (no --reload, node server.js)
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` → 개발 모드
- 헬스체크 3개 서비스 모두 healthy

**프롬프트**:
```
docker-compose.yml을 프로덕션 모드로 전환해줘.
1. backend: --reload 제거, Dockerfile CMD 사용
2. frontend: pnpm dev → Dockerfile CMD(node server.js) 사용
3. 개발용 docker-compose.dev.yml 분리 (--reload, pnpm dev)
4. backend/frontend Dockerfile에 non-root 사용자 + HEALTHCHECK 추가
5. docker compose up으로 정상 실행 확인
```

---

#### Step A-3: 인증 엔드포인트 적용 (1일)

**목표**: 구현된 JWT 인증을 데이터 엔드포인트에 적용

**수정 대상 파일**:
- `backend/app/api/screening.py` — `Depends(get_current_user)` 추가
- `backend/app/api/evaluation.py` — 동일
- `backend/app/api/cases.py` — 동일
- `backend/app/api/compare.py` — 동일
- `backend/app/api/draft.py` — 동일
- `backend/app/api/review.py` — 동일
- `backend/app/api/rag.py` — 동일
- `backend/app/api/patterns.py` — 읽기 전용이므로 선택적
- `backend/app/api/data_status.py` — 읽기 전용이므로 선택적
- `frontend/src/lib/api.ts` — Authorization 헤더 추가
- 테스트 파일 — 인증 토큰 픽스처 추가

**수락 기준**:
- 토큰 없는 요청 → 401
- 유효 토큰 → 정상 응답
- pytest 전체 통과 (토큰 픽스처 포함)

**프롬프트**:
```
backend/app/core/auth.py의 JWT 인증이 이미 구현되어 있지만
데이터 엔드포인트에 적용되지 않았어.
screening, evaluation, cases, compare, draft, review, rag 라우터에
Depends(get_current_user)를 추가해줘.
patterns, data_status는 읽기 전용이라 선택적.
frontend api.ts에 Authorization 헤더 추가.
테스트에 인증 토큰 픽스처 추가하여 pytest 전체 통과.
```

---

#### Step A-4: CI/CD 파이프라인 (1일)

**목표**: GitHub Actions로 자동 테스트 + 빌드

**수정 대상 파일**:
- `.github/workflows/ci.yml` (신규) — pytest + pnpm build + Playwright

**수락 기준**:
- Push/PR 시 자동 실행
- pytest 190+ 통과, pnpm build 성공, Playwright 67 통과
- 배지 README에 추가

**프롬프트**:
```
GitHub Actions CI/CD 파이프라인을 만들어줘.
.github/workflows/ci.yml 파일 생성:
- Python 3.12 + Node 20 + pnpm
- pytest (DB 스킵 허용)
- pnpm build
- Playwright E2E (chromium만)
- Push to main + PR 트리거
README.md에 CI 배지 추가.
```

---

### Phase B: 데이터 완결성 (5일)

#### Step B-1: 악취 커넥터 추가 (0.5일)

**목표**: 별표1 "악취" 항목 커버

**수정 대상 파일**:
- `backend/app/connectors/odor.py` (신규) — 악취측정망 API 커넥터
- `backend/app/services/data_fetcher.py` — odor 커넥터 등록
- `backend/app/rules/v1/odor.yaml` (신규) — 악취 규칙 3~4개
- `data/regulations/` — 악취방지법 관련 규제 추가

**수락 기준**:
- 악취측정망 API 호출 성공 또는 캐시 폴백
- 리스크 엔진에서 악취 규칙 평가
- pytest 추가 테스트 통과

**프롬프트**:
```
별표1 "악취" 항목을 커버하는 커넥터를 추가해줘.
1. backend/app/connectors/odor.py — 악취측정망 API (data.go.kr 1480523)
   기존 air_quality.py 패턴 참고, BaseConnector 상속
2. data_fetcher.py에 등록
3. rules/v1/odor.yaml — 악취 규칙 3~4개 (배출시설 근접, 측정값 초과 등)
4. 규제 매핑에 악취방지법 추가
5. pytest 테스트 추가
```

---

#### Step B-2: 일조·전파장해 커넥터 (0.5일)

**목표**: 별표1 "일조장해", "전파장해" 항목 커버

**수정 대상 파일**:
- `backend/app/connectors/weather.py` — 일사량 필드 추가 (ASOS에 이미 존재)
- `backend/app/connectors/radio.py` (신규) — 전파환경측정 API
- `backend/app/rules/v1/` — 해당 규칙 추가

**수락 기준**:
- weather 커넥터에서 일사량 데이터 반환
- 전파장해 커넥터 동작 또는 캐시 폴백
- 리스크 규칙 평가 동작

**프롬프트**:
```
별표1 "일조장해"와 "전파장해" 항목을 커버해줘.
1. weather.py에 ASOS 일사량(sumSsHr) 필드 추가 — 이미 API에 포함되어 있음
2. rules/v1/landscape.yaml 또는 신규 yaml에 일조 관련 규칙 추가
3. connectors/radio.py — 전파환경측정 API (과기정통부 data.go.kr)
4. data_fetcher.py에 등록
5. 리스크 규칙 추가
```

---

#### Step B-3: 산업·위락시설 데이터 (0.5일)

**목표**: 별표1 "산업", "위락시설" 항목 커버

**수정 대상 파일**:
- `backend/app/connectors/industry.py` (신규) — 통계청 사업체조사 API
- `backend/app/connectors/facilities.py` (신규) — 국가공간정보 POI API
- `backend/app/services/data_fetcher.py` — 등록
- `backend/app/rules/v1/social.yaml` — 규칙 추가

**수락 기준**: 산업/위락 데이터 조회 및 리스크 규칙 평가 동작

**프롬프트**:
```
별표1 "산업"과 "위락시설" 항목을 커버해줘.
1. connectors/industry.py — 통계청 사업체조사 API
2. connectors/facilities.py — V-world POI 레이어 (위락시설)
3. data_fetcher.py에 등록
4. rules/v1/social.yaml에 규칙 추가 (산업단지 근접, 위락시설 인접)
```

---

#### Step B-4: 동·식물상 종 데이터 보강 (1일)

**목표**: 생태 데이터를 등급에서 종 목록 수준으로 보강

**수정 대상 파일**:
- `backend/app/connectors/species.py` (신규) — 국가생물종정보 API
- `backend/app/connectors/ecology.py` — species 데이터 통합
- `backend/app/rules/v1/ecology.yaml` — 멸종위기종 규칙 추가

**수락 기준**:
- 좌표 주변 멸종위기종 목록 반환
- 멸종위기 I급 검출 시 Critical 리스크 발생

**프롬프트**:
```
생태 데이터를 종 목록 수준으로 보강해줘.
1. connectors/species.py — 국가생물종정보 API (data.go.kr)
   좌표 주변 반경 5km 내 멸종위기종 조회
2. ecology.py와 통합 (spatial_data에 species 키 추가)
3. ecology.yaml에 멸종위기 I급/II급 규칙 추가
4. pytest 테스트 추가
```

---

#### Step B-5: 수리·수문 + 해양 보강 (1일)

**목표**: 수문 유량/수위 + 해양 수심/조류 데이터 추가

**수정 대상 파일**:
- `backend/app/connectors/hydrology.py` (신규) — 한국수자원공사 수문관측 API
- `backend/app/connectors/ocean.py` (신규) — 국립해양조사원 API
- `backend/app/rules/v1/water.yaml` — 유량 관련 규칙 추가
- `backend/app/rules/v1/marine.yaml` — 조류/수심 규칙 추가

**수락 기준**: 수위/유량, 조류/수심 데이터 조회 가능

**프롬프트**:
```
수리·수문과 해양 데이터를 보강해줘.
1. connectors/hydrology.py — 한국수자원공사 수문관측 API (수위, 유량, 우량)
2. connectors/ocean.py — 국립해양조사원 API (수심, 조류, 조위)
3. data_fetcher.py에 등록
4. water.yaml에 유량 관련 규칙, marine.yaml에 수심/조류 규칙 추가
5. pytest 테스트 추가
```

---

#### Step B-6: 폐기물 실데이터 + 유사사례 매핑 수정 (1일)

**목표**: 폐기물 커넥터 데이터 보강 + 사례 유형 매핑 갭 해결

**수정 대상 파일**:
- `backend/app/connectors/waste_data.py` (신규) — 폐기물발생현황 API
- `backend/app/services/case_search.py` — 유형 매핑 테이블 추가
- `data/cases/cases.json` — 유형 태그 정규화 또는 매핑 추가

**수락 기준**:
- 폐기물 데이터 조회 가능
- urban_dev, mountain, sports, mining, other 유형에서도 유사사례 1건 이상 매칭

**프롬프트**:
```
2가지 수정:
1. 폐기물 실데이터 커넥터 추가 — connectors/waste_data.py
   한국환경공단 폐기물발생현황 API (data.go.kr)
2. 유사사례 유형 매핑 수정 — case_search.py에 API project_type → 사례 유형 매핑 추가
   urban_dev → ["주거단지","도시계획"], mountain → ["채석","토석"],
   sports → ["관광단지","공원"], mining → ["채석","토석"], other → 전체 검색
   89건 사례에서 5개 유형도 매칭되도록 수정
```

---

### Phase C: 법령 최신성 (3일)

#### Step C-1: 법령 개정 감지 시스템 (2일)

**목표**: 국가법령정보 API로 관련 법령 개정 자동 감지

**수정 대상 파일**:
- `backend/app/connectors/legislation.py` (신규) — 국가법령정보센터 API
- `backend/app/services/legislation_monitor.py` (신규) — 주기적 개정 체크
- `backend/app/api/admin.py` (신규) — 관리자 알림 엔드포인트
- `backend/app/rules/v1/` — 버전 관리 메타데이터 추가

**수락 기준**:
- 환경영향평가법 시행령 개정일 자동 감지
- 관리자에게 개정 알림 (이메일/웹)
- 규칙 YAML에 법령 버전 추적

**프롬프트**:
```
법령 개정 자동 감지 시스템을 만들어줘.
1. connectors/legislation.py — 국가법령정보센터 API (law.go.kr)
   환경영향평가법, 자연환경보전법, 대기환경보전법 등 모니터링
2. services/legislation_monitor.py — 주기적 체크 (주 1회)
   마지막 확인 시점 이후 개정 감지 시 알림
3. api/admin.py — 관리자용 개정 현황 조회/확인 엔드포인트
4. 규칙 YAML에 legal_version 필드 추가
```

---

#### Step C-2: 규칙 관리 UI (1일)

**목표**: 관리자가 웹에서 규칙 YAML을 조회/수정

**수정 대상 파일**:
- `backend/app/api/admin.py` — 규칙 CRUD 엔드포인트
- `frontend/src/app/admin/rules/page.tsx` (신규) — 규칙 관리 페이지

**수락 기준**:
- 관리자가 웹에서 64개 규칙 조회
- 개별 규칙 심각도/조건 수정 가능
- 수정 이력 추적

**프롬프트**:
```
관리자 규칙 관리 UI를 만들어줘.
1. backend/app/api/admin.py — 규칙 CRUD
   GET /api/admin/rules — 전체 목록
   GET /api/admin/rules/{rule_id} — 상세
   PUT /api/admin/rules/{rule_id} — 수정
   POST /api/admin/rules — 추가
2. frontend admin/rules/page.tsx — 규칙 테이블 + 편집 모달
   도메인별 필터, 심각도별 정렬, YAML 에디터
3. admin 역할만 접근 가능 (RBAC)
```

---

### Phase D: 보고서 전문성 (3일)

#### Step D-1: 보고서 템플릿 확장 (1일)

**목표**: 현행 6장 18섹션 → 가이드라인 21항목 전체 커버

**수정 대상 파일**:
- `data/templates/eia_report_template.json` — 템플릿 확장
- `backend/app/services/draft_copilot.py` — 추가 섹션 생성 로직

**수락 기준**: 21개 항목 전체 초안 생성

**프롬프트**:
```
Draft Copilot 템플릿을 환경부 가이드라인 21항목 전체로 확장해줘.
data/templates/eia_report_template.json을 수정하여:
1. 총론, 사업의 개요, 지역개황, 환경영향예측, 저감방안, 환경관리계획 등
2. 각 항목별 프롬프트 템플릿 작성
3. draft_copilot.py에서 확장된 섹션 생성 로직 추가
4. 기존 테스트 호환성 유지
```

---

#### Step D-2: 지도 페이지 구현 (1일)

**목표**: placeholder인 map 페이지를 실제 리스크 지도로 구현

**수정 대상 파일**:
- `frontend/src/app/screening/[id]/map/page.tsx` — 지도 페이지
- `frontend/src/components/map/screening-map.tsx` — 레이어 추가

**수락 기준**:
- 사업 위치 마커 표시
- 리스크 카드별 영향 반경 표시
- 규제 구역 오버레이 (용도지역, 보전지역)
- 커넥터 데이터 레이어 토글

**프롬프트**:
```
screening/[id]/map 페이지를 실제 리스크 지도로 구현해줘.
1. MapLibre GL JS로 사업 위치 마커 + 영향 반경 원형
2. 리스크 카드별 색상 코딩 (Critical=빨강, Major=주황 등)
3. V-world 레이어 오버레이 (용도지역, 보전지역)
4. 좌측 패널에 레이어 토글 + 범례
5. 커넥터 데이터 포인트 (대기/수질/소음 측정소)
```

---

#### Step D-3: 보고서 서식 개선 (1일)

**목표**: PDF 보고서 전문 서식 적용

**수정 대상 파일**:
- `backend/app/services/report_generator.py` — 레이아웃/서식 개선

**수락 기준**:
- 표지, 목차, 페이지 번호
- 표/그래프 인라인 삽입
- A4 인쇄 최적화

**프롬프트**:
```
PDF 보고서를 전문 서식으로 개선해줘.
1. report_generator.py에 표지 페이지 추가 (사업명, 일자, 로고)
2. 목차 자동 생성
3. 페이지 번호/헤더/푸터
4. 리스크 요약표, 규제 매칭표를 ReportLab Table로 삽입
5. 차트 이미지 삽입 (matplotlib → PIL → ReportLab)
6. A4 인쇄 여백 최적화
```

---

## 임팩트 × 난이도 매트릭스

| Step | 임팩트 | 난이도 | 우선순위 | 소요 |
|------|--------|--------|---------|------|
| A-1 문서 정합성 | 중 | 쉬움 | **P1** | 0.5일 |
| A-2 Docker 프로덕션 | 중 | 쉬움 | **P1** | 0.5일 |
| A-3 인증 적용 | 높음 | 보통 | **P1** | 1일 |
| A-4 CI/CD | 높음 | 보통 | **P1** | 1일 |
| B-1 악취 커넥터 | 중 | 쉬움 | **P1** | 0.5일 |
| B-2 일조/전파 | 중 | 쉬움 | **P1** | 0.5일 |
| B-3 산업/위락 | 중 | 쉬움 | **P2** | 0.5일 |
| B-4 동·식물종 | 높음 | 보통 | **P2** | 1일 |
| B-5 수문/해양 | 높음 | 보통 | **P2** | 1일 |
| B-6 폐기물+사례매핑 | 높음 | 쉬움 | **P1** | 1일 |
| C-1 법령 감지 | 높음 | 어려움 | **P2** | 2일 |
| C-2 규칙 관리 UI | 중 | 보통 | **P3** | 1일 |
| D-1 템플릿 확장 | 높음 | 보통 | **P2** | 1일 |
| D-2 지도 구현 | 높음 | 보통 | **P2** | 1일 |
| D-3 보고서 서식 | 중 | 보통 | **P3** | 1일 |

**총 소요: 약 12.5일 (2.5주)**

---

## 실행 순서 권장

```
Week 1: Phase A (운영 안정성)
  Day 1: A-1 문서 정합성 + A-2 Docker
  Day 2: A-3 인증 적용
  Day 3: A-4 CI/CD + B-1 악취 + B-2 일조/전파

Week 2: Phase B (데이터 완결성)
  Day 4: B-6 폐기물 + 사례 매핑
  Day 5: B-3 산업/위락 + B-4 동·식물종
  Day 6: B-5 수문/해양
  Day 7: D-2 지도 구현

Week 3: Phase C+D (법령 + 보고서)
  Day 8-9: C-1 법령 감지
  Day 10: D-1 템플릿 확장
  Day 11: C-2 규칙 관리 UI + D-3 보고서 서식

완료 후 목표:
  별표1 커버리지: 55% → 90%+
  운영 준비도: 92% → 98%+
  테스트: 272개 → 350개+
```

---

## 완료 후 예상 수치

| 항목 | 현재 | 목표 |
|------|------|------|
| 별표1 커버리지 | 55% 완전 | 90%+ 완전 |
| 커넥터 | 17개 | 24개 |
| 규칙 | 64개 | 80개+ |
| 규제 매핑 | 174개 | 200개+ |
| 유사사례 매칭율 | 12/17 유형 | 17/17 유형 |
| 테스트 | 272개 | 350개+ |
| 엔드포인트 | 32개 | 40개+ |
| 운영 준비도 | ~92% | ~98% |
