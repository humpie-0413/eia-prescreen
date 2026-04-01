# EIA Pre-Screen API Reference

> 기준일: 2026-03-29 | 총 35개 엔드포인트 (29 기능 + 4 인증 + 2 시스템)
>
> Swagger UI: `http://localhost:8000/docs`

---

## 인증 (Auth)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 1 | POST | `/api/auth/register` | 회원가입 |
| 2 | POST | `/api/auth/login` | 로그인 (JWT 발급) |
| 3 | POST | `/api/auth/refresh` | 토큰 갱신 |
| 4 | GET | `/api/auth/me` | 현재 사용자 정보 |

### POST `/api/auth/register`

```jsonc
// Request
{ "email": "user@example.com", "password": "...", "name": "홍길동" }
// Response 201
{ "id": "uuid", "email": "user@example.com", "name": "홍길동", "role": "analyst" }
```

### POST `/api/auth/login`

```jsonc
// Request
{ "email": "user@example.com", "password": "..." }
// Response 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

---

## 스크리닝 (Screening)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 5 | POST | `/api/screening` | 새 스크리닝 생성 |
| 6 | GET | `/api/screening/{id}` | 스크리닝 상세 조회 |
| 7 | GET | `/api/screening` | 스크리닝 목록 |

### POST `/api/screening`

```jsonc
// Request
{
  "project_name": "양평 도로건설",
  "project_type": "road",           // 17개 사업유형 중 택 1
  "project_scale": "연장 4.2km, 폭 20m",
  "address": "경기도 양평군 양평읍",
  "location": { "lat": 37.4917, "lng": 127.4876 }
}
// Response 201 — ScreeningResponse
{
  "id": "uuid",
  "project_name": "양평 도로건설",
  "project_type": "road",
  "status": "created",
  "created_at": "2026-03-29T10:00:00Z",
  "location": { "lat": 37.4917, "lng": 127.4876 },
  "risk_cards": [],
  "regulation_matches": []
}
```

**17개 사업유형** (`project_type`):

| 코드 | 한국어 | 코드 | 한국어 |
|------|--------|------|--------|
| urban_dev | 도시개발 | road | 도로건설 |
| industrial | 산업단지 | railway | 철도건설 |
| energy | 에너지개발 | airport | 공항건설 |
| port | 항만건설 | river | 하천이용·개발 |
| water_resource | 수자원개발 | tourism | 관광단지 |
| mountain | 산지개발 | sports | 체육시설 |
| waste | 폐기물처리 | military | 국방·군사 |
| mining | 광업 | reclamation | 매립·간척 |
| special_area | 특정지역 | | |

---

## 리스크 평가 (Evaluation)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 8 | POST | `/api/screening/{id}/evaluate` | 64개 규칙 기반 리스크 분석 |
| 9 | GET | `/api/screening/{id}/regulations` | 규제 매칭 결과 |
| 10 | GET | `/api/screening/{id}/checklist` | 현장조사 체크리스트 |

### POST `/api/screening/{id}/evaluate`

```jsonc
// Request
{ "scenario": "yangpyeong" }   // 데모 시나리오 (선택)
// Response 200 — EvaluationResponse
{
  "screening_id": "uuid",
  "risk_cards": [
    {
      "rule_id": "ECO-001",
      "title": "생태자연도 1등급 인접",
      "severity": "critical",       // critical | major | review | info
      "domain": "ecology",
      "rationale": "사업지 500m 내 생태자연도 1등급 ...",
      "evidence": { "distance_m": 320, "grade": 1 },
      "legal_basis": "자연환경보전법 제34조",
      "next_action": "생태전문가 현장조사 필수",
      "confidence": 0.92
    }
  ],
  "regulation_matches": [...],
  "summary": {
    "critical": 2, "major": 5, "review": 8, "info": 3,
    "top_domains": ["ecology", "water", "land_use"]
  },
  "data_freshness": { "land_use": "2026-03-29", "ecology": "2026-03-15" }
}
```

### GET `/api/screening/{id}/checklist?scenario=yangpyeong`

```jsonc
// Response 200
{
  "screening_id": "uuid",
  "sections": [
    {
      "domain": "ecology",
      "title": "자연생태환경",
      "items": [
        { "check": "생태자연도 등급 현장 확인", "priority": "high", "related_rules": ["ECO-001"] },
        { "check": "멸종위기종 서식 여부 조사", "priority": "high", "related_rules": ["ECO-002"] }
      ]
    }
  ]
}
```

---

## 유사사례 & AI 해석

| # | Method | Path | 설명 |
|---|--------|------|------|
| 11 | GET | `/api/cases` | 사례 검색 (태그/키워드) |
| 12 | GET | `/api/cases/{id}` | 단일 사례 조회 |
| 13 | POST | `/api/screening/{id}/similar-cases` | 유사사례 추천 |
| 14 | POST | `/api/screening/{id}/interpret` | AI 종합 해석 (DeepSeek V3) |

### GET `/api/cases?project_type=road&tags=ecology,water&limit=10`

```jsonc
// Response 200
{
  "cases": [
    {
      "id": "case-001",
      "project_name": "○○ 국도건설",
      "project_type": "road",
      "location_type": "산지",
      "year": 2023,
      "summary": "...",
      "tags": ["ecology", "water", "endangered_species"],
      "key_issues": ["수달 서식지 보전", "하천 횡단구간 어도 설치"],
      "outcome": "조건부 동의"
    }
  ],
  "total": 84
}
```

### POST `/api/screening/{id}/interpret`

```jsonc
// Response 200
{
  "interpretation": "본 사업지는 생태자연도 1등급 ...(2~3문단)...",
  "model": "deepseek/deepseek-chat",
  "generated_at": "2026-03-29T10:05:00Z",
  "disclaimer": "이 해석은 AI가 생성한 참고 자료이며 법적 효력이 없습니다."
}
```

---

## 부지 비교 (Compare)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 15 | POST | `/api/screening/compare` | 최대 3개 부지 비교 |
| 16 | POST | `/api/screening/compare/report` | 비교 보고서 PDF |

### POST `/api/screening/compare`

```jsonc
// Request
{ "screening_ids": ["uuid-1", "uuid-2", "uuid-3"] }  // 최대 3개
// Response 200
{
  "sites": [
    { "screening_id": "uuid-1", "name": "양평", "critical": 2, "major": 5 },
    { "screening_id": "uuid-2", "name": "세종", "critical": 0, "major": 3 }
  ],
  "risk_matrix": [
    { "domain": "ecology", "site_1": "critical", "site_2": "review" },
    { "domain": "water", "site_1": "major", "site_2": "major" }
  ],
  "recommendation": "부지 2(세종)가 환경 리스크 측면에서 유리"
}
```

---

## 패턴 분석 (Patterns)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 17 | GET | `/api/patterns` | 전체 패턴 요약 (9,973건 통계) |
| 18 | GET | `/api/patterns/{type}` | 사업유형별 패턴 |
| 19 | GET | `/api/patterns/{type}/predict` | 예상 지적항목 예측 |
| 20 | GET | `/api/patterns/rules/suggested` | 규칙 보강 제안 |

### GET `/api/patterns/road`

```jsonc
// Response 200
{
  "project_type": "road",
  "total_cases": 1247,
  "consultation_results": {
    "agreed": 0.72, "conditional": 0.23, "disagreed": 0.05
  },
  "top_issues": [
    { "issue": "소음·진동", "frequency": 0.68 },
    { "issue": "동물 이동통로", "frequency": 0.54 },
    { "issue": "비점오염원", "frequency": 0.41 }
  ],
  "avg_duration_months": 14.2
}
```

---

## Draft Copilot

| # | Method | Path | 설명 |
|---|--------|------|------|
| 21 | POST | `/api/screening/{id}/draft` | 전체 초안 (6장 18섹션) |
| 22 | POST | `/api/screening/{id}/draft/{section}` | 특정 섹션 초안 |
| 23 | GET | `/api/draft/template` | 템플릿 구조 조회 |

### POST `/api/screening/{id}/draft`

```jsonc
// Request
{
  "scenario": "yangpyeong",
  "project_name": "양평 도로건설",
  "project_type": "road",
  "project_scale": "연장 4.2km",
  "address": "경기도 양평군"
}
// Response 200 — 6장 18섹션 초안
{
  "sections": [
    {
      "section_id": "1.1",
      "chapter": "제1장 사업의 개요",
      "title": "사업의 목적",
      "content": "...",
      "rag_references": [
        { "source": "○○도로건설 환경영향평가서", "page": 12, "relevance": 0.87 }
      ]
    }
  ],
  "total_sections": 18
}
```

---

## 검토의견 예측 (Review Prediction)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 24 | POST | `/api/screening/{id}/predict-review` | 예상 검토의견 |
| 25 | POST | `/api/screening/{id}/quality-check` | 품질 체크 |

### POST `/api/screening/{id}/predict-review`

```jsonc
// Request
{ "scenario": "yangpyeong" }
// Response 200
{
  "predictions": [
    {
      "category": "소음·진동",
      "probability": 0.78,
      "typical_comment": "소음 저감대책의 구체적 기준 미비",
      "recommendation": "환경기준 초과 구간별 방음벽 높이 산정 필요"
    }
  ],
  "overall_risk": "medium",
  "data_basis": "9,973건 과거 협의 데이터"
}
```

---

## RAG (평가서 원문 검색)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 26 | POST | `/api/rag/query` | 원문 기반 질의응답 |
| 27 | POST | `/api/rag/draft-assist` | Draft Copilot RAG 보조 |
| 28 | GET | `/api/rag/stats` | 색인 통계 |
| 29 | POST | `/api/rag/index` | 색인 실행 |

### POST `/api/rag/query`

```jsonc
// Request
{
  "question": "도로건설 시 소음저감 대책은?",
  "n_results": 5,
  "project_type": "road"          // 선택: 특정 사업유형 필터
}
// Response 200
{
  "answer": "도로건설 사업에서 소음저감을 위해 ...(LLM 생성 답변)...",
  "sources": [
    {
      "report_name": "○○국도 환경영향평가서",
      "project_type": "road",
      "chunk_text": "방음벽 설치 시 소음 감쇠량은 ...",
      "relevance_score": 0.89,
      "page_info": "제4장 p.45"
    }
  ],
  "model": "deepseek/deepseek-chat",
  "disclaimer": "AI 생성 답변이며 원문 확인을 권장합니다."
}
```

### GET `/api/rag/stats`

```jsonc
// Response 200
{
  "total_reports": 99,
  "total_chunks": 6103,
  "project_types": {
    "road": { "reports": 12, "chunks": 745 },
    "urban_dev": { "reports": 8, "chunks": 521 },
    "energy": { "reports": 9, "chunks": 612 }
  },
  "embedding_model": "jhgan/ko-sroberta-multitask",
  "indexed_at": "2026-03-28T15:00:00Z"
}
```

---

## 데이터 현황 (Data Status)

| # | Method | Path | 설명 |
|---|--------|------|------|
| 30 | GET | `/api/data-status/connectors` | 전체 커넥터 현황 |
| 31 | GET | `/api/data-status/{id}` | 스크리닝별 데이터 상태 |
| 32 | GET | `/api/data-status` | 좌표 기반 데이터 상태 |

### GET `/api/data-status/connectors`

```jsonc
// Response 200
{
  "connectors": [
    {
      "name": "land_use",
      "display_name": "토지이용규제",
      "tier": "A",
      "status": "ok",
      "last_success": "2026-03-29T09:00:00Z",
      "freshness": "fresh",
      "error": null
    },
    {
      "name": "air_quality",
      "display_name": "대기질",
      "tier": "B",
      "status": "cached",
      "last_success": "2026-03-28T15:00:00Z",
      "freshness": "stale",
      "error": "API timeout"
    }
  ],
  "summary": { "ok": 10, "cached": 3, "error": 1 }
}
```

---

## PDF 보고서

| # | Method | Path | 설명 |
|---|--------|------|------|
| 33 | POST | `/api/screening/{id}/report` | PDF 보고서 생성 |
| 34 | POST | `/api/screening/compare/report` | 비교 보고서 PDF |

### POST `/api/screening/{id}/report`

```jsonc
// Request
{ "report_type": "brief" }   // brief (1p) | full (5-10p) | checklist
// Response: StreamingResponse (application/pdf)
```

---

## 시스템

| # | Method | Path | 설명 |
|---|--------|------|------|
| 35 | GET | `/health` | 헬스 체크 |

### GET `/health`

```jsonc
// Response 200
{
  "status": "healthy",
  "database": "connected",    // "connected" | "demo_mode"
  "demo_mode": true
}
```

---

## Rate Limiting

| 엔드포인트 그룹 | 제한 |
|-----------------|------|
| 일반 API | 60 req/min per IP |
| LLM 엔드포인트 (`/interpret`, `/draft`, `/rag/query`) | 10 req/min per user |
| PDF 생성 (`/report`) | 20 req/min per user |

---

## 에러 응답 형식

```jsonc
// 4xx/5xx
{
  "error": "not_found",           // 에러 코드
  "message": "스크리닝을 찾을 수 없습니다.",
  "detail": null                  // 추가 정보 (선택)
}
```

| HTTP 코드 | 의미 |
|-----------|------|
| 400 | 잘못된 요청 (파라미터 오류) |
| 404 | 리소스 없음 |
| 422 | 요청 검증 실패 (Pydantic) |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |
