# EIA Pre-Screen

**환경영향평가 사전검토 지원 도구** — 사업 위치와 유형을 입력하면 공공 데이터·사례 라이브러리·실제 평가서 원문(RAG)을 바탕으로 입지 리스크와 우선 검토 항목을 근거와 함께 제시합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **입지 리스크 카드** | Critical / Major / Review / Info 4단계 심각도 + 법적 근거 |
| **규제 자동 매칭** | 용도지역·보호구역·EIA 임계값 기반 174개 법령 자동 매칭 |
| **AI 리스크 해석** | Gemini 2.5 Flash가 결과를 2~3문단으로 종합 서술 |
| **RAG 원문 검색** | 103건 실제 환경영향평가서 원문 기반 질의응답 (6,103 청크) |
| **Draft Copilot** | 7장 22섹션 초안 자동 생성 (템플릿 + RAG 참조 + LLM 보완) |
| **검토의견 예측** | 9,996건 과거 데이터 기반 예상 지적항목·확률 예측 |
| **유사사례 라이브러리** | 89건 큐레이션 사례 태그 기반 필터·유사도 검색 |
| **부지 비교** | 최대 3개 부지 Side-by-side 리스크 매트릭스 비교 |
| **리스크 맵** | MapLibre GL 기반 500m/1km 버퍼 + 규제 레이어 시각화 |
| **PDF 보고서** | 1p 브리프 / 5~10p 환경현황 요약 / 현장조사 체크리스트 / 비교 |
| **데이터 가용성 대시보드** | 22개 커넥터별 신선도·오류 현황 실시간 확인 |
| **법령 모니터링** | 6개 환경법률 개정 자동 감지 + 관리자 규칙 관리 UI |

---

## 기술 아키텍처

```
                       ┌──────────────────────────────────┐
                       │        Frontend (Next.js 16)      │
                       │  TypeScript + Tailwind + shadcn   │
                       │      MapLibre GL JS (지도)         │
                       └───────────────┬──────────────────┘
                                       │ REST API (JWT 인증)
                       ┌───────────────┴──────────────────┐
                       │        Backend (FastAPI)           │
                       │     41개 엔드포인트 · 15 서비스      │
                       ├───────────────────────────────────┤
                       │ 리스크 엔진   │ 규제 매처  │ LLM   │
                       │ (77규칙/19도메인)│ (174개)  │해석문  │
                       ├──────────┬────┴───────┬───────────┤
                       │ RAG 서비스│ Draft Copilot│ 패턴분석 │
                       │ ChromaDB │ 7장 22섹션   │ 9,996건  │
                       │ 6,103청크 │ 초안 생성    │ 통계     │
                       ├──────────┴────────────┴───────────┤
                       │     26개 커넥터 (22개 DataFetcher)   │
                       │  A계층(실시간) B계층(캐시) C계층(수동) │
                       └───────────────┬──────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────┴────────┐    ┌─────────┴─────────┐    ┌────────┴────────┐
     │ PostgreSQL+PostGIS│   │ 공공 API 34종      │    │ EIASS 원문      │
     │  (공간 질의)       │   │ (16종 실연동)       │    │ (103건 PDF)     │
     └───────────────────┘   └────────────────────┘    └─────────────────┘
```

---

## 기술 스택

### 프론트엔드
| 기술 | 버전 | 선택 근거 |
|------|------|----------|
| Next.js (App Router) | 16.2 | 서버 컴포넌트 + 파일 기반 라우팅 |
| TypeScript | 5.x | 타입 안전성으로 API 응답 오류 사전 차단 |
| Tailwind CSS v4 | 4.x | JIT 기반 유틸리티 클래스 |
| shadcn/ui (Base UI) | v4 | headless 컴포넌트 |
| MapLibre GL JS | 5.x | 오픈소스 벡터 지도, GeoJSON 직접 연동 |

### 백엔드
| 기술 | 버전 | 선택 근거 |
|------|------|----------|
| FastAPI | 0.115 | async-first, 자동 OpenAPI 문서 |
| SQLAlchemy (asyncio) | 2.0 | ORM + async 세션 |
| PostgreSQL + PostGIS | 16 + 3.4 | 공간 질의 네이티브 지원 |
| ReportLab | 4.2 | 한국어 CID 폰트 PDF 생성 |

### AI / 데이터
| 기술 | 선택 근거 |
|------|----------|
| Gemini 2.5 Flash (Google) | 빠른 응답, 한국어 우수, 무료 |
| ChromaDB + ko-sroberta | 한국어 임베딩 RAG (103건 평가서 원문) |
| 규칙 엔진 (YAML) | 77개 규칙 파일 관리, 버전 제어 |
| 3-tier 데이터 전략 | A(실시간) / B(캐시 폴백) / C(수동 스냅샷) |

### 인프라
| 기술 | 선택 근거 |
|------|----------|
| Docker Compose | 5 서비스 (backend, frontend, postgres, nginx, certbot) |
| GitHub Actions | CI 5 jobs (lint, pytest, build, e2e, docker) |
| JWT + bcrypt + RBAC | 3역할 (admin/analyst/viewer) 인증·인가 |
| Prometheus | 9개 메트릭 (/metrics 엔드포인트) |

---

## 화면 구성

```
/                               랜딩 페이지
/screening/new                  새 사전검토 (위치·사업유형 입력 + 지도 선택)
/screening/[id]/dashboard       리스크 카드 대시보드 + AI 해석 + 체크리스트
/screening/[id]/map             리스크 지도 (MapLibre, 버퍼 레이어)
/screening/[id]/data-status     데이터 가용성 현황 (커넥터별 신선도)
/screening/[id]/cases           유사사례 + PDF 보고서 다운로드
/screening/[id]/draft           Draft Copilot (7장 22섹션 초안)
/screening/[id]/rag             RAG 평가서 원문 검색
/screening/compare              최대 3개 부지 Side-by-side 비교
/admin/rules                    관리자 규칙 관리 + 법령 모니터링
```

---

## 설치 및 실행

### 사전 요구사항

- Node.js 20+, pnpm 9+
- Python 3.11+
- Docker Desktop (PostgreSQL + PostGIS용, 선택)

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env에서 최소 다음 값 입력:
# OPENROUTER_API_KEY=your-api-key   ← OpenRouter 발급 (무료)
# DEMO_MODE=true                    ← DB 없이 데모 실행
```

### 2. 백엔드 실행

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 서버 실행 (데모 모드)
cd ..
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 3. 프론트엔드 실행

```bash
cd frontend
pnpm install
pnpm dev
```

브라우저에서 `http://localhost:3000` 접속.

### 4. Docker Compose (전체 스택)

```bash
docker compose up -d
# http://localhost (Nginx reverse proxy)
```

### 5. RAG 색인 (선택)

```bash
# 추출된 평가서 텍스트를 ChromaDB에 색인
python backend/scripts/extract_report_text.py
python -c "
import sys; sys.path.insert(0, '.')
from backend.app.services.report_rag import ReportRAG
rag = ReportRAG()
rag.index_reports(overwrite=True)
"
```

---

## 주요 수치

| 항목 | 수치 |
|------|------|
| 테스트 | 272개 (pytest 205 + E2E 67) |
| 환경영향평가서 원문 | 103건 (526 PDF, 6.3GB, 16개 사업유형) |
| RAG 청크 | 6,103개 |
| 벌크 협의 데이터 | 9,996건 |
| 실연동 공공 API | 16종 (34종 승인) |
| 규칙 YAML | 77개 (19개 도메인) |
| 유사사례 | 89건 (18개 유형) |
| 규제 매핑 | 174개 |
| 커넥터 파일 | 26개 (22개 DataFetcher 등록) |
| 서비스 레이어 | 15개 |
| 백엔드 엔드포인트 | 41개 (11 라우터) |
| 프론트엔드 페이지 | 10개 (11 빌드 라우트) |
| 프론트엔드 컴포넌트 | 27개 |
| 초안 템플릿 | 7장 22섹션 |
| 사업유형 | 17개 (환경영향평가법 시행령 별표3 전체) |

---

## API 문서

백엔드 실행 후 `http://localhost:8000/docs` (Swagger UI)

주요 엔드포인트 — 전체 목록은 [docs/API_REFERENCE.md](docs/API_REFERENCE.md) 참조.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/screening` | 새 스크리닝 생성 |
| POST | `/api/screening/{id}/evaluate` | 리스크 분석 실행 |
| POST | `/api/screening/{id}/interpret` | AI 해석 생성 |
| POST | `/api/screening/{id}/draft` | Draft Copilot 초안 |
| POST | `/api/rag/query` | RAG 원문 질의 |
| POST | `/api/screening/{id}/predict-review` | 검토의견 예측 |
| POST | `/api/screening/{id}/report` | PDF 보고서 |
| GET  | `/api/patterns/{type}` | 과거 패턴 분석 |
| GET  | `/api/data-status/connectors` | 커넥터 상태 확인 |

---

## 데이터 전략 (3계층)

| 계층 | 전략 | 예시 |
|------|------|------|
| **A계층** (안정형 실시간) | 직접 호출, 안정적 API | 토지이용규제, V-world WFS |
| **B계층** (불안정형 + 캐시) | 실시간 시도 → 실패 시 스냅샷 폴백 | 대기질, 수질, 기상, 교통량 |
| **C계층** (수동 스냅샷) | 정적 데이터, 수동 큐레이션 | 유사사례 89건, EIASS 원문 103건 |

---

## 시스템 한계

> **이 도구는 법적 판정 시스템이 아닙니다.**

- 77개 규칙은 주요 환경 법령을 커버하지만 모든 특수 규정을 포함하지 않습니다.
- 공공 API 데이터의 기준일자를 반드시 확인하세요 (데이터 현황 탭).
- AI 해석·RAG 답변·초안은 참고 자료이며 법적 효력이 없습니다.
- 최종 판단은 반드시 **전문가 현장조사**와 **법적 검토**를 거쳐야 합니다.

---

## 라이선스

MIT License — 개인 포트폴리오 프로젝트. 상업적 사용 전 공공 API 이용약관을 확인하세요.
