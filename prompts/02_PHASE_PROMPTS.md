# 🔧 EIA Pre-Screen — Phase 1~5 개발 프롬프트

## 사용법
Phase 0 완료 후, 각 Phase를 순서대로 실행하세요.
brainstorm → plan → execute 흐름으로 진행합니다.

---

## PHASE 1: Data Stabilization

### PROMPT 1-1: 커넥터 검증 & 캐시 구조

```
/brainstorm Phase 1 데이터 안정화를 시작한다.

목표:
1. 구현된 커넥터 5개(토지이용규제, 생태자연도, V-world, 에어코리아, 물환경)에 대해
   - 양평/세종/보령 3개 지역 좌표로 실제 호출 테스트
   - 응답 성공/실패/타임아웃을 기록
   - A/B/C 계층 분류를 실제 결과로 업데이트

2. 캐시 매니저가 정상 동작하는지 검증:
   - 실패 시 자동 fallback이 작동하는지
   - fallback_used 플래그가 정확히 기록되는지
   - snapshot 파일이 data/snapshots/에 올바르게 저장되는지

3. 데모 시나리오 3개에 대한 완전한 mock 데이터셋 생성:
   - 양평(도로): 토지이용 + 생태 + 수계 데이터
   - 세종(주거): 토지이용 + 대기 + 소음 데이터  
   - 보령(발전소): 토지이용 + 대기 + 수질 + 해양 데이터
   각 데이터에 fetched_at, snapshot_at, freshness 메타 포함

4. 규제정보 DB 초기 구축:
   - data/regulations/ 에 규제 매핑 JSON 생성
   - 용도지역 코드 → 관련 법령 조항 매핑
   - 보전지역 유형 → 행위제한 내용 매핑
```

### PROMPT 1-2: 데이터 가용성 API

```
/plan 데이터 가용성 대시보드 백엔드를 구현한다.

backend/app/api/data_status.py에:
- GET /api/data-status/{screening_id}
  - 커넥터별 상태 (STABLE/UNSTABLE/UNAVAILABLE)
  - 각 커넥터의 마지막 성공 시각, 데이터 존재 여부
  - freshness 레벨 (fresh/stale/expired)
  - 전체 데이터 커버리지 퍼센트

- GET /api/data-status/connectors
  - 전체 커넥터 목록과 현재 상태

응답 스키마를 Pydantic으로 명확히 정의하고,
프론트엔드에서 쓸 수 있게 TypeScript 타입도 함께 생성해.
```

---

## PHASE 2: Risk Engine + 규제 매칭

### PROMPT 2-1: 리스크 엔진 통합

```
/plan 리스크 엔진을 완전히 구현한다.

1. backend/app/services/risk_engine.py 완성:
   - load_rules()로 YAML 24개 규칙 로드
   - evaluate() 메서드:
     - 입력: ScreeningInput + 수집된 spatial_data
     - 각 규칙의 trigger_dataset이 spatial_data에 있는지 확인
     - condition 평가 (공간 중첩, 버퍼 거리, 데이터 존재 여부)
     - severity 판정 + rationale 생성 + evidence 연결
     - next_action과 confidence 산출
   - 결과를 severity 순으로 정렬 (Critical > Major > Review > Info)

2. backend/app/services/regulation_matcher.py:
   - 부지 좌표 기반 PostGIS 공간 질의
   - 해당 위치의 용도지역, 보전지역, 규제구역 자동 추출
   - data/regulations/ 매핑 테이블과 조인하여 관련 법령 조항 반환
   - 규제 중첩 여부 판단

3. backend/app/services/checklist_generator.py:
   - 리스크 카드의 next_action 필드를 체크리스트로 포맷팅
   - severity별 그룹핑
   - PDF 출력용 구조 생성

4. API 엔드포인트:
   - POST /api/screening/{id}/evaluate → 리스크 분석 실행
   - GET /api/screening/{id}/regulations → 규제 매칭 결과
   - GET /api/screening/{id}/checklist → 현장조사 체크리스트

5. rule validation matrix:
   - tests/ 폴더에 양평/세종/보령 3개 시나리오 테스트
   - 각 시나리오별 기대 리스크 카드 vs 실제 출력 비교
   - pytest로 자동화
```

### PROMPT 2-2: 리스크 맵 프론트엔드

```
/plan 화면 2 (리스크 맵)와 화면 3 (결과 대시보드)를 구현한다.

## 화면 2: /screening/[id]/map

1. MapLibre GL JS 지도:
   - 사업지 폴리곤 표시 (빨간 외곽선)
   - 주변 규제구역 레이어 (용도지역별 색상)
   - 버퍼 거리 원형 표시 (500m, 1km)
   - 중첩 포인트 하이라이트

2. 오른쪽 패널 (규제 + 리스크):
   - 상단: 적용 규제 목록 (법령 조항 포함)
   - 하단: 리스크 카드 목록 (severity 배지 + 한 줄 설명)
   - 카드 클릭 → 지도에서 해당 geometry 하이라이트
   - 카드 클릭 → Evidence Drawer 열기

3. Evidence Drawer (Sheet 컴포넌트):
   - 데이터 출처, 기준일자
   - 관련 제도/법령
   - 법적 효력 여부
   - 원문 링크
   - 현장확인 필요 여부
   - FreshnessIndicator 표시

## 화면 3: /screening/[id]/dashboard

1. 상단: LLM 종합 해석문 (카드, "AI 생성 참고용" 배지)
2. 핵심 리스크 카드 그리드 (severity별 색상)
3. 우선 검토 항목 3~5개 (번호순)
4. 현장조사 체크리스트 (체크박스 UI)
5. 데이터 신선도 요약 바

각 컴포넌트를 독립적으로 만들어 재사용 가능하게.
```

---

## PHASE 3: Case Library + LLM 통합

### PROMPT 3-1: 유사사례 & LLM

```
/plan 유사사례 라이브러리와 LLM 통합을 구현한다.

1. 유사사례 50건 데이터 구조:
   - data/cases/ 폴더에 JSON 파일로 관리
   - 각 사례 스키마:
     {
       "case_id": "CASE-001",
       "project_type": "도로",
       "location_type": "산지 인접",
       "region": "경기도",
       "key_issues": ["생태민감구역 중첩", "비산먼지"],
       "remediation_required": ["동식물상 보완조사", "비산먼지 저감계획"],
       "public_concerns": ["소음", "교통량 증가"],
       "consultation_result": "조건부 동의",
       "source_document": "평가서 원문 링크",
       "summary": "1문장 해설",
       "tags": ["산지", "도로", "생태"]
     }

   - 먼저 5개 사례를 수동으로 작성 (양평도로, 세종주거 등 데모용)
   - 나머지 45건은 Claude API로 초벌 생성 후 검수할 수 있게 스크립트 준비

2. backend/app/services/case_search.py:
   - 사업유형, 입지유형, 키워드로 필터링
   - 현재 스크리닝 결과와 유사도 매칭 (이슈 태그 기반)

3. backend/app/services/llm_interpreter.py:
   - Claude API 호출
   - 입력: 리스크 카드 목록 + 규제 매칭 결과 + 데이터 현황
   - 출력: 2~3문단 자연어 해석문
   - 프롬프트에 "참고용이며 법적 효력 없음" 반드시 포함
   - 응답에 "AI 생성" 명시

4. backend/app/services/report_generator.py:
   - 1p 브리프 PDF 생성 (reportlab)
   - 5~10p 환경현황 요약 보고서 PDF 생성
   - 현장조사 체크리스트 PDF 생성
   - 보고서 구조: 표지 → 요약 → 리스크 → 규제 → 사례 → 체크리스트

5. 프론트엔드 화면 5 (/screening/[id]/cases):
   - 유사사례 카드 목록 (필터링 가능)
   - 사례 상세 모달
   - "보고서 다운로드" 버튼 (1p, 5~10p, 체크리스트 선택)
```

---

## PHASE 4: 부지 비교 + 데이터 현황

### PROMPT 4-1: 부지 비교 구현

```
/plan 다중 부지 비교 기능과 데이터 현황 대시보드를 구현한다.

## 화면 4: /screening/compare

1. 비교 대상 선택:
   - 기존 스크리닝 결과에서 최대 3개 선택
   - 또는 새 검토 시작 화면에서 여러 부지 입력

2. Side-by-side 그리드:
   - 3개 컬럼 레이아웃
   - 각 컬럼: 부지명 + 지도 미니맵 + 리스크 카드 요약 + 규제 현황
   - 리스크 severity 비교 표 (행: 리스크 항목, 열: 부지)
   - 종합 추천 영역 (어떤 부지가 상대적으로 유리한지)

3. 비교 보고서 PDF 출력:
   - 부지별 비교 테이블
   - 장단점 요약
   - 추천 사항

4. API:
   - POST /api/screening/compare (screening_ids 배열)
   - 각 screening의 결과를 병렬 조회 + 비교 데이터 생성

## 화면 6: /screening/[id]/data-status

1. 커넥터별 상태 카드:
   - 아이콘 + 이름 + 상태 배지 (안정/불안정/미응답)
   - 마지막 성공 시각
   - 데이터 존재 여부 (O/X)

2. 신선도 매트릭스:
   - 행: 데이터 항목 (토지이용, 생태, 대기, 수질 등)
   - 열: 신선도 상태 (실시간/캐시/없음)
   - 색상으로 한눈에 파악

3. "추가 조사 필요" 영역 하이라이트:
   - 데이터가 없거나 오래된 항목을 빨간색으로 표시
   - 해당 항목에 대한 추천 조사 내용
```

---

## PHASE 5: Portfolio Polish

### PROMPT 5-1: UI 마무리 & 데모 완성

```
/plan 최종 마무리를 진행한다.

1. UI 디자인 통일:
   - 전체 색상 체계 확인 (green/teal accent)
   - 지도 스타일 커스터마이징 (MapLibre style JSON)
   - 로딩 상태, 에러 상태 처리
   - 반응형 점검 (데스크탑 + 태블릿)
   - 다크/라이트 모드 점검

2. 데모 시나리오 최종 점검:
   - 양평(도로): 전체 플로우 스크린샷 캡처
   - 세종(주거): 캐시 fallback 시나리오 동작 확인
   - 보령(발전소): 복합 리스크 시나리오 확인
   - 부지 비교 데모: 양평 vs 세종

3. README.md 작성:
   - 프로젝트 소개 (한 줄 + 상세)
   - 주요 기능 스크린샷
   - 기술 스택 + 선택 근거
   - 설치 방법
   - 데모 실행 방법
   - 시스템 한계 명시
   - 향후 확장 계획

4. 시스템 한계 명시 (README + UI 푸터):
   - "이 도구는 법적 판정 시스템이 아닙니다"
   - "데이터 기준일자를 반드시 확인하세요"
   - "현장조사와 전문가 판단이 필요합니다"
   - 데이터 출처 및 갱신 주기

5. .env.example 최종 정리
6. docker-compose.yml 최종 점검
7. 불필요한 코드/파일 정리
```
