# EIA Pre-Screen — 확장 전략 및 실행 계획 v3

> 작성일: 2026-03-28
> 현재 상태: MVP 완성 (운영 준비도 ~95%), 97 tests, 빌드 클린
> 목표: 데모용 → 실전 참고 → **데이터 기반 예측 시스템**으로 진화

---

## 1. 프로젝트 진화 로드맵

```
[완료] Pre-Screen MVP
  ↓
[완료] 데이터 확보 + 품질 보강
  ↓
[완료] 운영 보완 (Critical 4 + High 5 + Medium 6)
  ↓
[현재] ── 확장 Phase ──
  ↓
Phase E-1: 과거 환평 벌크 수집 + 패턴 분석 DB
  ↓
Phase E-2: 패턴 기반 예측 시스템 (협의결과 예측, 지적항목 예측)
  ↓
Phase E-3: Draft Copilot (평가서 초안 자동 생성)
  ↓
Phase E-4: 검토의견 예측 + 자동 품질 체크
  ↓
[미래] 풀 자동화 (현장 데이터 제외 전 과정)
```

---

## 2. 현재 완성 현황 요약

| 항목 | 수치 |
|------|------|
| API 엔드포인트 | 19개 |
| 테스트 | 97개 전체 통과 |
| 규칙 YAML | 64개 (12개 도메인) |
| 유사사례 | 50건 (DeepSeek 생성) |
| 규제 매핑 | 175개 (81+64+30) |
| API 커넥터 | 14개 (17개 도메인) |
| 공공데이터 API 키 | 22종 승인 |
| LLM | DeepSeek V3 via OpenRouter (무료) |
| 프론트엔드 | 6개 페이지, TypeScript 클린 |
| 보안 | JWT 인증, Rate Limiting, 에러 핸들러 |
| 인프라 | Docker Compose, nginx, Prometheus, CI/CD |

---

## 3. 자동화 가능 범위 분석

### 자동화 가능 (API + LLM)

| 영역 | 방법 | 현재 상태 |
|------|------|----------|
| 과거 환평 데이터 수집 | EIASS API 벌크 호출 | ❌ 미구현 |
| 사업유형별 지적 패턴 분석 | 수집 데이터 + DeepSeek 분석 | ❌ 미구현 |
| 협의결과 확률 예측 | 과거 통계 기반 | ❌ 미구현 |
| 보완 요구 사전 예측 | 패턴 매칭 | ❌ 미구현 |
| 평가서 항목별 초안 생성 | 템플릿 + LLM | ❌ 미구현 (Draft Copilot) |
| 검토의견 예측 | 과거 검토 패턴 학습 | ❌ 미구현 |
| 규칙 자동 보강 제안 | 패턴에서 신규 규칙 도출 | ❌ 미구현 |
| 입지 리스크 스크리닝 | 규칙 엔진 + 공간 질의 | ✅ 완료 |
| 규제 자동 매칭 | PostGIS + 매핑 DB | ✅ 완료 |
| PDF 보고서 생성 | reportlab 템플릿 | ✅ 완료 |
| 유사사례 검색 | 태그 기반 필터 | ✅ 완료 |

### 자동화 불가능 (사람 필수)

| 영역 | 이유 |
|------|------|
| 현장조사 측정 | 물리적 방문 + 장비 측정 필요 |
| 보호종 서식 확인 | 생태 전문가 현장 확인 |
| 수질/토양 시료 분석 | 실험실 분석 필요 |
| AERMOD 모델링 | 현장 기상 + 배출원 데이터 필요 |
| 주민 설명회 | 대면 소통 |
| 최종 전문가 판단 | 법적 책임이 수반되는 판단 |

---

## 4. 확장 Phase 상세

### Phase E-1: 과거 환평 벌크 수집 + 패턴 분석 DB

**목표**: 과거 완료 환평 수백~수천 건을 수집하여 통계적 패턴 추출

**Step 7: 벌크 수집 스크립트**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 7을 실행해줘.
```

상세:
1. backend/scripts/bulk_collect_eia.py 생성
2. 환경영향평가 정보 서비스 API로 2015~2025년 완료 사업 전체 목록 수집
   - 페이지네이션 (numOfRows=100씩)
   - 사업유형, 사업명, 위치, 규모, 연도, 평가구분
   - API 호출 간 1초 딜레이
3. 협의 현황정보 API로 각 사업의 협의 결과 수집
4. 결정내용정보 API로 지적사항/보완요구 수집
5. data/bulk/raw/에 JSON 저장
6. API 500/403이면 건너뛰고 로그 기록
7. 진행률 표시 + 총 수집 건수 출력
8. 실행: python backend/scripts/bulk_collect_eia.py

---

**Step 8: 패턴 분석**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 8을 실행해줘.
```

상세:
1. backend/scripts/analyze_patterns.py 생성
2. 수집 데이터를 DeepSeek으로 분석:
   - 사업유형별 통계 (건수, 협의결과 비율)
   - 자주 지적되는 항목 Top 10 (사업유형별)
   - 사업유형×입지유형별 리스크 매트릭스 (확률)
   - 보완 요구 패턴 (빈도순)
3. data/bulk/analysis/에 저장:
   - patterns_by_type.json
   - risk_matrix.json
   - common_issues.json
   - remediation_patterns.json

---

**Step 9: 패턴 DB 서비스 통합**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 9를 실행해줘.
```

상세:
1. backend/app/services/pattern_advisor.py 생성
   - 분석 결과 로드
   - 사업유형별 과거 패턴 조회
   - "이 유형에서 과거 N건 중 X%가 이 항목을 지적받았습니다" 제공
2. API 엔드포인트:
   - GET /api/patterns/{project_type} — 사업유형별 패턴
   - GET /api/patterns/{project_type}/predict — 예상 지적항목 + 확률
3. 프론트엔드 대시보드에 "과거 데이터 기반 예측" 섹션 추가
   - 예상 협의결과 확률 바 차트
   - 빈출 지적항목 목록
   - "이 사업과 유사한 과거 사례 N건 분석 결과" 카드
4. 규칙 자동 보강 제안:
   - 패턴 중 기존 64개 규칙에 없는 항목 → suggested_rules.json
5. pytest + pnpm build 확인

---

### Phase E-2: Draft Copilot (평가서 초안 자동 생성)

**목표**: 수집된 데이터 + 패턴 분석을 기반으로 평가서 각 항목의 초안을 자동 생성

**Step 10: 평가서 템플릿 구조화**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 10을 실행해줘.
```

상세:
1. data/templates/eia_report_template.json 생성
   - 환경영향평가서 표준 목차 구조:
     1장 사업 개요
     2장 지역 개황
     3장 평가 항목별 현황 (대기, 수질, 소음, 토양, 생태, 경관 등)
     4장 환경영향 예측
     5장 저감 방안
     6장 사후환경영향조사 계획
   - 각 장/절별: 필요 데이터 소스, 자동 생성 가능 여부, 현장조사 필요 여부

2. backend/app/services/draft_copilot.py 생성
   - generate_section(section_id, screening_data, patterns) → 마크다운 초안
   - 각 섹션별 DeepSeek 프롬프트 템플릿
   - "사업 개요"는 입력 데이터에서 자동
   - "지역 개황"은 커넥터 데이터에서 자동
   - "평가 항목별 현황"은 API 데이터 + 패턴에서 자동
   - "환경영향 예측"은 과거 패턴 기반 초안 + "전문가 검토 필요" 표시
   - "저감 방안"은 과거 유사사례의 저감방안 참조

3. API 엔드포인트:
   - POST /api/screening/{id}/draft — 전체 초안 생성
   - POST /api/screening/{id}/draft/{section} — 특정 섹션만

4. 프론트엔드:
   - /screening/[id]/draft 페이지 신규 생성
   - 섹션별 초안 표시 (마크다운 렌더링)
   - 각 섹션에 "자동 생성" / "현장조사 필요" / "전문가 검토 필요" 배지
   - 초안 전체 PDF 다운로드

5. 반드시 표시: "이 초안은 AI가 생성한 참고 자료이며 전문가 검토가 필요합니다"

6. pytest + pnpm build 확인

---

**Step 11: 검토의견 예측**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 11을 실행해줘.
```

상세:
1. backend/app/services/review_predictor.py 생성
   - 과거 협의 데이터에서 검토관이 자주 지적하는 패턴 학습
   - predict_review_comments(screening_data, draft) → 예상 검토의견 목록
   - 각 의견에 확률(%) + 과거 근거 사례 수 표시

2. backend/app/services/quality_checker.py 생성
   - 생성된 초안을 자동 품질 체크
   - 누락 항목 확인 (필수 평가항목이 빠졌는지)
   - 데이터 일관성 확인 (숫자 모순, 단위 오류)
   - 법적 요구사항 충족 여부 확인

3. API 엔드포인트:
   - POST /api/screening/{id}/predict-review — 예상 검토의견
   - POST /api/screening/{id}/quality-check — 품질 체크

4. 프론트엔드 대시보드에 통합:
   - "예상 검토의견" 카드 (확률순 정렬)
   - "품질 체크 결과" 카드 (통과/주의/실패)

5. pytest + pnpm build 확인

---

### Phase E-3: 고도화

**Step 12: GitHub 업로드 + 배포**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 12를 실행해줘.
```

상세:
1. git init + .gitignore 확인
2. 첫 커밋 구조:
   - feat: initial project setup
   - feat: risk engine + regulation matcher
   - feat: case library + LLM integration
   - feat: site comparison
   - feat: auth + security
   - feat: data acquisition + pattern analysis
   - feat: draft copilot (있는 경우)
3. GitHub 리포지토리 생성 안내
4. README.md 최종 점검 (스크린샷 추가 안내)
5. GitHub Actions CI 워크플로우 동작 확인
6. 릴리즈 태그: v1.0.0

---

**Step 13: UI/UX 디자인 개선**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 13을 실행해줘.
```

상세:
1. 전체 색상 체계 통일 (환경/자연 톤 — teal/green accent)
2. 대시보드 레이아웃 개선:
   - 리스크 요약을 상단 히어로 영역에
   - 과거 패턴 예측을 사이드 패널에
   - 유사사례를 하단 카드 그리드에
3. 지도 스타일 커스터마이징 (MapLibre style JSON)
4. 로딩 애니메이션 개선 (스켈레톤 → shimmer)
5. 모바일 반응형 최종 점검
6. 다크 모드 색상 점검
7. 랜딩 페이지 (/) 디자인 — 프로젝트 소개 + 데모 시작 버튼
8. pnpm build 확인

---

**Step 14: 포트폴리오 발표 자료**

Claude Code 프롬프트:
```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 14를 실행해줘.
```

상세:
1. docs/PORTFOLIO_PRESENTATION.md 생성:
   - 프로젝트 한 줄 소개
   - 해결하려는 문제
   - 기술 아키텍처 다이어그램
   - 주요 기능 데모 시나리오 (양평 도로 → 보령 발전소 → 부지 비교)
   - 기술적 도전과 해결 (3계층 캐시, 룰 엔진 설계, LLM 통합)
   - 데이터 기반 확장 (벌크 수집 → 패턴 분석 → 예측)
   - 향후 계획
2. 데모 스크린샷 캡처 스크립트 (playwright 기반)
3. 시스템 아키텍처 다이어그램 (mermaid)

---

## 5. 실행 요약 (Step 번호 체계)

### 완료된 Step (이전 문서)

| Step | 작업 | 상태 |
|------|------|------|
| 1 | 유사사례 자동 수집 | ✅ 완료 (DeepSeek 50건) |
| 2 | 규제 매핑 확장 | ✅ 완료 (175개) |
| 3 | 규칙 YAML 확장 | ✅ 완료 (64개) |
| 4 | 커넥터 14개 확장 | ✅ 완료 |
| 5 | 데모 실데이터 교체 | ✅ 완료 |
| 6 | 최종 통합 검증 | ✅ 완료 |

### 남은 Step (이 문서)

| Step | 작업 | Phase | 예상 시간 | 프롬프트 |
|------|------|-------|----------|---------|
| 7 | 과거 환평 벌크 수집 | E-1 | 15~20분 | `Step 7을 실행해줘` |
| 8 | 패턴 분석 | E-1 | 10~15분 | `Step 8을 실행해줘` |
| 9 | 패턴 DB 서비스 통합 | E-1 | 15~20분 | `Step 9를 실행해줘` |
| 10 | Draft Copilot 초안 생성 | E-2 | 20~25분 | `Step 10을 실행해줘` |
| 11 | 검토의견 예측 + 품질 체크 | E-2 | 15~20분 | `Step 11을 실행해줘` |
| 12 | GitHub 업로드 + 배포 | E-3 | 10분 | `Step 12를 실행해줘` |
| 13 | UI/UX 디자인 개선 | E-3 | 15~20분 | `Step 13을 실행해줘` |
| 14 | 포트폴리오 발표 자료 | E-3 | 10~15분 | `Step 14를 실행해줘` |

**총 예상: 2~3시간 (전부 자동)**

---

## 6. 사용 방법

모든 Step은 Claude Code에서 한 문장으로 실행:

```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 7을 실행해줘.
```

Step 완료 후 다음:

```
docs/EXPANSION_PLAN_V3.md를 읽고 Step 8을 실행해줘.
```

컨텍스트 부족 시 새 대화 열고 같은 문장 입력하면 됩니다.
CLAUDE.md가 루트에 있으므로 프로젝트 맥락은 자동 인식됩니다.

---

## 7. 최종 완성 후 예상 시스템

| 기능 | 설명 |
|------|------|
| 입지 리스크 스크리닝 | 64개 규칙 + 14개 커넥터 실시간 분석 |
| 규제 자동 매칭 | 175개 규제 매핑 + 법령 조항 |
| 유사사례 검색 | 50건 큐레이션 + 과거 벌크 데이터 |
| 과거 패턴 예측 | 수백~수천 건 통계 기반 지적항목/협의결과 예측 |
| 평가서 초안 생성 | 섹션별 자동 초안 (Draft Copilot) |
| 검토의견 예측 | 과거 패턴 기반 예상 지적 + 확률 |
| 품질 자동 체크 | 누락/모순/법적 요구 충족 확인 |
| 부지 비교 | 최대 3개 Side-by-side |
| 보고서 출력 | 브리프 1p + 환경현황 5~10p + 체크리스트 + 비교 |
| 데이터 투명성 | 신선도, 캐시 전환, 출처 표시 |

**"지도 웹앱 하나 만들었다"가 아니라
"과거 수천 건의 환경영향평가를 학습하여 초기 검토부터 평가서 초안까지 자동화하는 AI 기반 환평 지원 시스템을 설계했다"로 보입니다.**

---

## 8. 주의사항

- Step 7 (벌크 수집)은 공공데이터 API 일일 10,000건 제한에 주의
- Step 8 (패턴 분석)은 DeepSeek 호출이 많으므로 OpenRouter 할당량 확인
- Step 10 (Draft Copilot)에서 생성되는 초안에 반드시 "AI 생성 참고용" 명시
- Step 11 (검토의견 예측)의 확률은 통계적 참고치이며 법적 근거 아님
- 모든 자동 생성 콘텐츠에 면책 문구 포함 필수

---

*이 문서를 프로젝트의 docs/EXPANSION_PLAN_V3.md에 저장하세요.*
*Claude Code에서 "docs/EXPANSION_PLAN_V3.md를 읽고 Step N을 실행해줘"로 사용합니다.*
