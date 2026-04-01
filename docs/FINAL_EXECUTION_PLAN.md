# EIA Pre-Screen 실무 확장 — 최종 실행 문서

> 기반: PROJECT_AUDIT.md (전수조사) + PRODUCTION_PLAN.md (확장 계획)
> 작성일: 2026-03-31
> 이 문서가 다음 페이즈의 유일한 실행 기준입니다. 추가 조사 없음.

---

## 현재 상태 요약

| 항목 | 수치 |
|------|------|
| 서비스 | 14개 |
| 엔드포인트 | 32개 |
| 페이지 | 10개 |
| 커넥터 | 17개 (14개 DataFetcher 등록) |
| 규칙 | 64개 (16 도메인) |
| 규제 매핑 | 174개 |
| 유사사례 | 89건 |
| RAG | 103 보고서, 6,104 청크 |
| 벌크 | 9,973건 |
| 테스트 | 205 pytest + 67 E2E = 272개 |
| 별표1 커버리지 | 11/20 완전 (55%) |
| P0 이슈 | 0건 |
| P1 이슈 | 2건 |
| P2 이슈 | 8건 |
| P3 이슈 | 8건 |

---

## 실행 계획: 15 Steps, 4 Phases

### Phase A: 기반 정비 (Day 1~3)

> 목적: P2 이슈 해소, 프로덕션 인프라, 인증, CI/CD

---

#### Step A-1: 문서 정합성 + 코드 정리

**목표**: P2 이슈 8건 일괄 수정

**수정 파일**: README.md, .env.example, CLAUDE.md, data/demo/, E2E 테스트 9개

**수락 기준**:
- [ ] README.md 수치 = PROJECT_AUDIT.md 7장 수치와 일치
- [ ] .env.example DEMO_MODE 설명 = "커넥터 오류 무시 + 빈 데이터 반환"
- [ ] CLAUDE.md에서 ITERATION_PLAN_V2.md, report.py, regulation.py 참조 제거
- [ ] `find . -path ./node_modules -prune -o -name "*.ts" -print | xargs grep "scenario=yangpyeong"` = 0건
- [ ] `ls data/demo/` = No such file or directory
- [ ] pytest 190+ 통과, pnpm build 성공

**Claude Code 프롬프트**:
```
docs/PROJECT_AUDIT.md 6장의 P2 이슈 8건을 모두 수정해줘.

1. README.md 수치 갱신:
   - 테스트 114→272, 커넥터 18→17, 엔드포인트 29→32
   - 데모 시나리오 섹션 삭제
   - 유사사례 89건, 규제 174개, 규칙 64개, RAG 6,104 청크로 갱신

2. .env.example DEMO_MODE 설명:
   "When true, suppresses connector errors and returns empty data instead of failing"

3. CLAUDE.md 수정:
   - ITERATION_PLAN_V2.md 참조 제거 (ITERATION_PLAN.md만 유지)
   - report.py, regulation.py 라우터 언급 제거
   - 수치 갱신 (89건, 174개, 6,104 청크, 17개 유형)

4. rm -rf data/demo/

5. E2E 테스트 전 파일에서 ?scenario=yangpyeong 제거:
   find frontend -name "*.spec.ts" | xargs에서 scenario 파라미터 삭제

6. dashboard/page.tsx (1,124줄)는 이번에는 그대로 둠 (리팩토링은 별도)

pytest + pnpm build + playwright 확인.
```

---

#### Step A-2: Docker 프로덕션 모드

**목표**: 프로덕션 실행 가능한 Docker 설정

**수정 파일**: docker-compose.yml, docker-compose.dev.yml(신규), backend/Dockerfile, frontend/Dockerfile

**수락 기준**:
- [ ] `docker compose up` → 프로덕션 (no --reload, no pnpm dev)
- [ ] `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` → 개발 모드
- [ ] backend Dockerfile에 `USER appuser` + `HEALTHCHECK`
- [ ] frontend Dockerfile에 `USER appuser` + `HEALTHCHECK`

**Claude Code 프롬프트**:
```
docker-compose.yml을 프로덕션 모드로 전환해줘.

1. docker-compose.yml:
   - backend: command 제거 → Dockerfile CMD 사용 (uvicorn --workers 4)
   - frontend: command 제거 → Dockerfile CMD 사용 (node server.js)

2. docker-compose.dev.yml (신규):
   - backend: command: uvicorn backend.app.main:app --reload --host 0.0.0.0
   - frontend: command: pnpm dev
   - volumes: 소스코드 마운트

3. backend/Dockerfile:
   - RUN adduser --disabled-password --gecos "" appuser
   - USER appuser
   - HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health || exit 1

4. frontend/Dockerfile:
   - 동일하게 non-root + HEALTHCHECK

docker compose config로 문법 검증.
```

---

#### Step A-3: 인증 엔드포인트 적용

**목표**: JWT 인증을 데이터 엔드포인트에 적용

**수정 파일**: evaluation.py, screening.py, cases.py, compare.py, draft.py, review.py, rag.py, api.ts, 테스트 픽스처

**수락 기준**:
- [ ] 토큰 없는 POST /api/screening → 401
- [ ] 유효 토큰 → 200
- [ ] patterns, data_status, health → 토큰 불필요 (공개)
- [ ] pytest 전체 통과 (인증 픽스처 포함)
- [ ] 프론트엔드 로그인 → 토큰 저장 → API 호출 정상

**Claude Code 프롬프트**:
```
JWT 인증을 데이터 엔드포인트에 적용해줘.

backend/app/core/auth.py에 이미 구현된 get_current_user를 사용.

보호 대상 (Depends(get_current_user) 추가):
- screening.py: POST /api/screening, GET /api/screening/{id}
- evaluation.py: GET /api/screening/{id}/evaluate, /regulations, /checklist, /interpret
- cases.py: GET /api/screening/{id}/cases
- compare.py: POST /api/compare
- draft.py: POST /api/screening/{id}/draft, /quality-check
- review.py: POST /api/screening/{id}/predict-review
- rag.py: POST /api/rag/query

공개 유지:
- patterns.py, data_status.py, health (GET)
- auth.py (POST /api/auth/login, /register)

frontend/src/lib/api.ts:
- localStorage에서 토큰 읽기
- fetch 헤더에 Authorization: Bearer {token} 추가
- 401 시 로그인 페이지 리다이렉트

테스트:
- conftest.py에 auth_token 픽스처 추가
- 모든 테스트에서 헤더 포함

pytest + pnpm build 확인.
```

---

#### Step A-4: CI/CD 파이프라인

**목표**: GitHub Actions 자동 테스트 + 빌드

**수정 파일**: .github/workflows/ci.yml(신규), README.md(배지)

**수락 기준**:
- [ ] ci.yml 문법 유효 (act 또는 수동 검증)
- [ ] pytest, pnpm build, Playwright 3단계 포함
- [ ] README.md에 CI 배지

**Claude Code 프롬프트**:
```
GitHub Actions CI 파이프라인을 만들어줘.

.github/workflows/ci.yml:
- trigger: push to main, pull_request
- jobs:
  1. backend-test:
     - Python 3.12, pip install
     - pytest --ignore=backend/scripts -x (DB 스킵 허용)
  2. frontend-build:
     - Node 20, pnpm install, pnpm build, pnpm lint
  3. e2e-test:
     - backend + frontend 동시 실행
     - npx playwright install chromium
     - npx playwright test

README.md 상단에 배지 추가:
![CI](https://github.com/{owner}/{repo}/actions/workflows/ci.yml/badge.svg)
```

---

### Phase B: 데이터 완결성 (Day 4~8)

> 목적: 별표1 커버리지 55% → 90%+
> 모든 커넥터는 기존 패턴(BaseConnector 상속, data_fetcher 등록)을 따름

---

#### Step B-1: 악취 커넥터

**목표**: 별표1 A-3 악취 커버

**신규 파일**: connectors/odor.py, rules/v1/odor.yaml
**수정 파일**: data_fetcher.py, regulation 매핑

**수락 기준**:
- [ ] odor 커넥터 등록 + fetch 성공 또는 캐시 폴백
- [ ] ODR-001 (악취관리지역 중첩) 규칙 동작
- [ ] industrial, waste 유형에서 악취 검토의견 추가
- [ ] pytest 추가 테스트 통과

**Claude Code 프롬프트**:
```
별표1 "악취" 커넥터를 추가해줘.

1. backend/app/connectors/odor.py
   - 국립환경과학원 악취측정망 API (data.go.kr 서비스키: DATA_GO_KR_API_KEY)
   - 좌표 기반 반경 10km 내 악취측정소 조회
   - 캐시 폴백: data/static/odor_management_areas.csv (악취관리지역 목록)
   - 정규화: station_name, value, management_area, distance_m

2. data_fetcher.py에 odor 커넥터 등록

3. rules/v1/odor.yaml:
   - ODR-001 Major: 악취관리지역 직접 중첩
   - ODR-002 Review: 악취배출시설 1km 이내
   - ODR-003 Review: 악취측정값 배출허용기준 초과

4. 규제 매핑: 악취방지법 제6조, 제8조

5. review_predictor.py: industrial, waste 유형에 악취 항목 추가

pytest + pnpm build.
```

---

#### Step B-2: 일조·전파장해

**목표**: 별표1 E-6 전파장해, E-7 일조장해 커버

**수정 파일**: connectors/weather.py (일사량 추가)
**신규 파일**: connectors/radio.py, rules 추가

**수락 기준**:
- [ ] weather 커넥터에서 일사량(sumSsHr) 반환
- [ ] radio 커넥터 등록 + fetch 또는 캐시
- [ ] SUN-001, RAD-001 규칙 동작

**Claude Code 프롬프트**:
```
별표1 "일조장해"와 "전파장해"를 커버해줘.

1. weather.py 수정:
   - ASOS API 응답의 sumSsHr(일조시간), icsr(일사량) 필드 추가 파싱
   - 정규화 데이터에 sunshine_hours, solar_radiation 추가

2. rules/v1/sunshine.yaml (신규):
   - SUN-001 Review: 도시개발(urban_dev) 시 일조권 검토 (고층 건물 계획 시)

3. connectors/radio.py (신규):
   - 과기정통부 전파환경측정 API 또는 CSV 폴백
   - 좌표 기반 전파 간섭 가능 시설 조회

4. rules/v1/radio.yaml (신규):
   - RAD-001 Review: 풍력발전(energy) 시 전파장해 검토

5. data_fetcher.py에 radio 등록

pytest + pnpm build.
```

---

#### Step B-3: 산업·위락시설

**목표**: 별표1 F-3 산업, E-3 위락시설 커버

**신규 파일**: connectors/industry.py, connectors/facilities.py

**수락 기준**:
- [ ] 산업 데이터 조회 또는 CSV 폴백
- [ ] 위락시설 POI 조회 또는 CSV 폴백
- [ ] 관련 규칙 동작

**Claude Code 프롬프트**:
```
별표1 "산업"과 "위락시설"을 커버해줘.

1. connectors/industry.py:
   - 통계청 사업체조사 API 또는 CSV 폴백 (data/static/industry_stats.csv)
   - 좌표 기반 행정구역 → 산업 통계 매핑

2. connectors/facilities.py:
   - V-world WFS POI 레이어에서 위락시설 조회
   - 또는 data/static/recreation_facilities.csv 폴백

3. rules/v1/social.yaml에 규칙 추가:
   - IND-001 Review: 산업단지 500m 이내
   - REC-001 Review: 위락시설 밀집지역 (관광 사업)

4. data_fetcher.py에 등록

pytest + pnpm build.
```

---

#### Step B-4: 동·식물상 종 데이터 보강

**목표**: 생태 데이터를 등급 → 종 목록 수준으로 보강

**신규 파일**: connectors/species.py
**수정 파일**: connectors/ecology.py, rules/v1/ecology.yaml

**수락 기준**:
- [ ] 좌표 반경 5km 내 멸종위기종 목록 반환 (종명, 등급)
- [ ] 멸종위기 I급 검출 시 ECO-007 Critical 발생
- [ ] 리스크 카드에 "멸종위기 I급 반달가슴곰 서식지 인접" 표시

**Claude Code 프롬프트**:
```
생태 데이터를 종 목록 수준으로 보강해줘.

1. connectors/species.py (신규):
   - 국가생물종정보 API (data.go.kr)
   - 좌표 반경 5km 내 멸종위기종 조회
   - 반환: species_name, grade (I급/II급), habitat_type, distance_m

2. ecology.py에서 species 데이터 통합:
   - spatial_data["species"] = species_connector.fetch() 결과

3. rules/v1/ecology.yaml 규칙 추가:
   - ECO-007 Critical: 멸종위기 I급 서식지 직접 중첩
   - ECO-008 Major: 멸종위기 II급 서식지 500m 이내
   - 리스크 설명에 종명 포함: f"멸종위기 {grade} {species_name} 서식지"

4. data_fetcher.py에 species 등록

pytest + pnpm build.
```

---

#### Step B-5: 수리·수문 + 해양 보강

**목표**: 별표1 B-2 수리·수문, B-3 해양환경 완전 커버

**신규 파일**: connectors/hydrology.py, connectors/ocean.py
**수정 파일**: rules/v1/water.yaml, rules/v1/marine.yaml

**수락 기준**:
- [ ] 하천 수위/유량 데이터 반환
- [ ] 해양 수심/조류 데이터 반환
- [ ] HYD-001, OCN-001 규칙 동작

**Claude Code 프롬프트**:
```
수리·수문과 해양 데이터를 보강해줘.

1. connectors/hydrology.py (신규):
   - WAMIS 수문관측 API (wamis.go.kr) 또는 K-water API
   - 좌표 기반 인근 수위관측소 조회
   - 반환: station_name, water_level, flow_rate, flood_level, river_name

2. connectors/ocean.py (신규):
   - 국립해양조사원 API (khoa.go.kr)
   - 좌표 기반 수심, 조류, 조위 조회
   - 반환: depth, tidal_current, tide_level, station_name

3. rules/v1/water.yaml 추가:
   - HYD-001 Major: 홍수위 이하 저지대
   - HYD-002 Review: 하천 유지유량 부족 구간

4. rules/v1/marine.yaml 추가:
   - OCN-001 Review: 항만/매립 시 조류 영향 검토
   - OCN-002 Review: 수심 변화 예상 구역

5. data_fetcher.py에 hydrology, ocean 등록

pytest + pnpm build.
```

---

#### Step B-6: 폐기물 실데이터 + 유사사례 매핑 수정 + 초안 연동

**목표**: 폐기물 데이터 확보 + 유사사례 5개 유형 매핑 해결 + marine/greenhouse 초안 반영

**수정 파일**: case_search.py, draft_copilot.py
**신규 파일**: connectors/waste_data.py

**수락 기준**:
- [ ] 폐기물 데이터 조회 가능
- [ ] urban_dev, mountain, sports, mining, other에서 유사사례 1건+ 매칭
- [ ] 항만 초안에 해양환경 섹션 포함
- [ ] 에너지 초안에 온실가스 섹션 포함

**Claude Code 프롬프트**:
```
3가지 수정:

## 1. 폐기물 커넥터
connectors/waste_data.py — 한국환경공단 폐기물발생현황 API (data.go.kr)
좌표 기반 시군구 → 폐기물 발생량/처리량 조회

## 2. 유사사례 유형 매핑
case_search.py에 _TYPE_ALIASES 딕셔너리 추가:
{
  "urban_dev": ["주거단지", "도시계획", "택지"],
  "mountain": ["채석", "토석", "산지"],
  "sports": ["관광단지", "공원", "체육"],
  "mining": ["채석", "토석", "광산"],
  "other": None  # None이면 전체 검색
}
검색 시 project_type을 aliases로 확장하여 매칭

## 3. 초안 해양/온실가스 연동
draft_copilot.py 수정:
- port, reclamation 유형: marine 커넥터 데이터 → "3.7 해양환경" 섹션 자동 추가
- energy 유형: greenhouse 커넥터 데이터 → "3.7 온실가스" 섹션 자동 추가
- 기존 18섹션 → 유형에 따라 19~20섹션

pytest + pnpm build.
```

---

### Phase C: 법령 최신성 (Day 9~11)

> 목적: 규칙의 법적 근거가 최신 법령과 일치하는지 자동 검증

---

#### Step C-1: 법령 개정 감지 시스템

**목표**: 관련 법령 개정 자동 감지 + 관리자 알림

**신규 파일**: connectors/legislation.py, services/legislation_monitor.py, api/admin.py
**수정 파일**: 규칙 YAML (법령 버전 메타 추가)

**수락 기준**:
- [ ] GET /api/admin/law-status → 6개 법령의 최종 개정일 + 시스템 기준일 반환
- [ ] 개정 감지 시 is_outdated: true 표시
- [ ] 규칙 YAML에 legal_version 필드 존재
- [ ] 프론트엔드에 "법령 업데이트 필요" 배너 (is_outdated 시)

**Claude Code 프롬프트**:
```
법령 개정 자동 감지 시스템을 만들어줘.

1. connectors/legislation.py:
   - 국가법령정보센터 Open API (open.law.go.kr)
   - 법령명으로 검색 → 최종 개정일(시행일) 반환
   - 모니터링 대상 6개:
     환경영향평가법, 환경영향평가법 시행령,
     자연환경보전법, 국토의 계획 및 이용에 관한 법률,
     농지법, 습지보전법

2. services/legislation_monitor.py:
   - check_all() → 6개 법령 최종 개정일 조회
   - data/law_versions.json에 마지막 확인 결과 저장:
     { "환경영향평가법": {"last_amendment": "2025-02-18", "checked_at": "2026-03-31", "system_version": "2025-02-18"} }
   - is_outdated = last_amendment > system_version

3. api/admin.py:
   - GET /api/admin/law-status → 6개 법령 상태
   - POST /api/admin/law-check → 수동 체크 트리거
   - POST /api/admin/law-acknowledge/{law_name} → 관리자가 확인 처리

4. 규칙 YAML 전체에 메타데이터 추가:
   metadata:
     legal_basis_version: "2025-02-18"
     last_verified: "2026-03-31"

5. 프론트엔드:
   - 대시보드 상단에 법령 상태 배너
   - is_outdated 있으면 노란 경고: "관련 법령이 개정되었습니다. 관리자 확인이 필요합니다."

pytest + pnpm build.
```

---

#### Step C-2: 규칙 관리 UI

**목표**: 관리자가 웹에서 규칙 조회/수정

**신규 파일**: frontend/src/app/admin/rules/page.tsx
**수정 파일**: api/admin.py (CRUD 추가)

**수락 기준**:
- [ ] GET /api/admin/rules → 64개+ 규칙 목록
- [ ] PUT /api/admin/rules/{id} → 규칙 수정 (심각도, 조건값)
- [ ] 관리자 페이지에서 도메인별 필터, 규칙 편집 동작
- [ ] admin 역할만 접근 (RBAC)

**Claude Code 프롬프트**:
```
관리자 규칙 관리 UI를 만들어줘.

1. api/admin.py 확장:
   - GET /api/admin/rules — 전체 규칙 목록 (도메인별 그룹)
   - GET /api/admin/rules/{rule_id} — 규칙 상세 (YAML 원문 포함)
   - PUT /api/admin/rules/{rule_id} — 수정 (severity, threshold, enabled)
   - 수정 시 이력 기록 (data/rule_changes.jsonl에 append)
   - admin 역할 체크 (get_current_user의 role == "admin")

2. frontend/src/app/admin/rules/page.tsx:
   - 규칙 테이블: ID, 도메인, 심각도, 제목, 활성화 상태
   - 도메인별 필터 드롭다운
   - 행 클릭 → 편집 모달 (심각도 선택, 임계값 입력, 활성/비활성)
   - 저장 → PUT 호출 → 토스트 "규칙 수정 완료"

3. 사이드바에 관리자 메뉴 추가 (admin 역할 시만 표시)

pytest + pnpm build.
```

---

### Phase D: 보고서·UI 전문화 (Day 12~14)

> 목적: 초안 품질 향상 + 지도 구현 + PDF 서식

---

#### Step D-1: 초안 템플릿 확장

**목표**: 6장 18섹션 → 가이드라인 21항목 커버

**수정 파일**: draft_copilot.py, eia_report_template.json

**수락 기준**:
- [ ] 초안 생성 시 21개 항목 전체 포함
- [ ] 사업유형별 중점 항목 차별화
- [ ] 기존 테스트 호환

**Claude Code 프롬프트**:
```
Draft Copilot을 가이드라인 21항목으로 확장해줘.

현재 18섹션에 추가:
- 3.7 악취 (industrial, waste 유형)
- 3.8 온실가스 (energy 유형) — B-6에서 이미 추가했으면 확인만
- 3.9 해양환경 (port, reclamation 유형) — B-6에서 이미 추가했으면 확인만
- 7.1 대안 검토 (전체 — 부지비교 결과 연동 가능 시)

사업유형별 섹션 선택:
- energy: 대기+온실가스 중심
- port/reclamation: 해양환경 중심
- industrial/waste: 악취+대기 중심
- tourism: 경관+생태 중심
- road/railway: 소음+생태단절 중심

기존 테스트 호환성 유지. pytest + pnpm build.
```

---

#### Step D-2: 지도 페이지 구현

**목표**: placeholder → 실제 리스크 지도

**수정 파일**: map/page.tsx, screening-map.tsx

**수락 기준**:
- [ ] 사업 위치 마커 + 영향 반경 원형 표시
- [ ] 리스크 카드별 색상 코딩
- [ ] 레이어 토글 (용도지역, 보전지역, 측정소)
- [ ] 모바일 반응형

**Claude Code 프롬프트**:
```
screening/[id]/map 페이지를 실제 리스크 지도로 구현해줘.

1. MapLibre GL JS (이미 설치됨) 사용
2. 기본 레이어: CARTO Positron 타일
3. 사업 위치: 빨간 마커 + 1km/3km/5km 반경 원형 (반투명)
4. 리스크 포인트:
   - Critical: 빨강 원, Major: 주황, Review: 파랑
   - 클릭 → 팝업 (리스크 제목 + 근거 요약)
5. 좌측 패널:
   - 레이어 토글 체크박스 (V-world 용도지역 WMS, 생태자연도 WMS)
   - 범례
6. 우측 하단: 축척 표시
7. 반응형: 모바일에서 패널 접기

pnpm build 확인.
```

---

#### Step D-3: PDF 보고서 서식 개선

**목표**: 전문 보고서 서식

**수정 파일**: report_generator.py

**수락 기준**:
- [ ] 표지 (사업명, 일자, 생성 도구명)
- [ ] 목차
- [ ] 페이지 번호 + 헤더/푸터
- [ ] 표 삽입 (리스크 요약, 규제 매칭)
- [ ] A4 인쇄 여백

**Claude Code 프롬프트**:
```
PDF 보고서를 전문 서식으로 개선해줘.

report_generator.py 수정:
1. 표지 페이지: 사업명, 생성일, "EIA Pre-Screen 사전검토 보고서", 면책 문구
2. 목차 자동 생성 (장/절 기반)
3. 페이지 번호 (하단 중앙)
4. 헤더: "EIA Pre-Screen — {사업명}" (좌), 페이지 번호 (우)
5. 리스크 요약표: ReportLab Table (심각도 색상 코딩)
6. 규제 매칭표: Table (법적 근거, 인허가 필요 여부)
7. A4 여백: 상하 2.5cm, 좌우 2cm
8. 폰트: fonts-japanese-gothic.ttf (기존 NotoKR 등록 유지)

테스트: 하동 양수발전소 데이터로 PDF 생성하여 /mnt/user-data/outputs/에 저장.
```

---

## 실행 일정 요약

```
Day 1:  A-1 문서 정합성 + A-2 Docker
Day 2:  A-3 인증 적용
Day 3:  A-4 CI/CD
Day 4:  B-1 악취 + B-2 일조/전파
Day 5:  B-3 산업/위락
Day 6:  B-4 동·식물종
Day 7:  B-5 수리·수문/해양
Day 8:  B-6 폐기물+사례매핑+초안연동
Day 9:  C-1 법령 감지 (1/2)
Day 10: C-1 법령 감지 (2/2)
Day 11: C-2 규칙 관리 UI
Day 12: D-1 초안 확장
Day 13: D-2 지도 구현
Day 14: D-3 PDF 서식
```

## 완료 후 목표 수치

| 항목 | 현재 | 목표 |
|------|------|------|
| 별표1 커버리지 | 55% (11/20) | 90%+ (18/20) |
| 커넥터 | 17개 | 24개 |
| 규칙 | 64개 | 85개+ |
| 규제 매핑 | 174개 | 200개+ |
| 유사사례 매칭 | 12/17 유형 | 17/17 유형 |
| 테스트 | 272개 | 350개+ |
| 엔드포인트 | 32개 | 42개+ |
| 초안 섹션 | 18개 | 21개+ |
| 법령 모니터링 | 없음 | 6개 법령 자동 감지 |

---

## 실행 방법

각 Step을 순서대로 Claude Code에서 실행:

```
docs/FINAL_EXECUTION_PLAN.md를 읽고 Step {X}를 실행해줘.
```

수락 기준의 체크박스를 전부 통과해야 다음 Step으로 진행.
