# 🚀 EIA Pre-Screen — 워크스페이스 초기 세팅 프롬프트

## 사용법
VSCode에서 Claude Code를 열고 아래 프롬프트를 **순서대로** 실행하세요.
각 프롬프트는 `---` 구분선으로 나뉘어 있습니다.
한 번에 하나씩 실행하고, 완료 확인 후 다음으로 넘어가세요.

---

## PROMPT 0: 스킬 & 플러그인 설치

```
아래 명령어를 순서대로 실행해줘. 한 줄씩.

/plugin marketplace add obra/superpowers-marketplace
/plugin marketplace add Piebald-AI/claude-code-lsps
/plugin install superpowers@superpowers-marketplace
/plugin install pyright@claude-code-lsps
/plugin install vtsls@claude-code-lsps
/plugin install claude-md-management@claude-plugins-official
```

터미널에서 별도 실행:
```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp@latest
```

---

## PROMPT 1: 프로젝트 초기화

```
현재 디렉토리에 EIA Pre-Screen 프로젝트를 초기화해줘.

1. 프로젝트 루트에 CLAUDE.md가 이미 있으니 읽어서 구조를 파악해
2. 아래 순서로 진행:

### Frontend 초기화
- pnpm create next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --use-pnpm
- cd frontend && pnpm add maplibre-gl @maplibre/maplibre-gl-js react-map-gl
- pnpm add @tanstack/react-query zustand
- npx shadcn@latest init (tailwindcss 스타일, zinc 컬러, CSS variables 사용)
- shadcn 컴포넌트 설치: button, card, badge, dialog, sheet, tabs, separator, tooltip, select, input, label

### Backend 초기화
- mkdir -p backend/app/{api,core,models,schemas,services,rules/v1,connectors,db}
- backend/requirements.txt 생성:
  fastapi[standard]==0.115.*
  uvicorn[standard]==0.34.*
  sqlalchemy[asyncio]==2.0.*
  asyncpg==0.30.*
  geoalchemy2==0.15.*
  alembic==1.14.*
  pydantic==2.10.*
  pydantic-settings==2.7.*
  httpx==0.28.*
  anthropic==0.43.*
  reportlab==4.2.*
  python-dotenv==1.0.*
  shapely==2.0.*
  pyproj==3.7.*

- python -m venv backend/.venv
- backend/.venv/Scripts/pip install -r backend/requirements.txt (Windows)

### Docker
- docker-compose.yml 생성 (postgres:16-postgis, frontend, backend 서비스)

### 기타
- .env.example 생성 (DB, API 키 변수)
- .gitignore 생성 (node_modules, .venv, __pycache__, .env, .next)
- data/ 하위 폴더 생성 (cases, regulations, snapshots, demo/yangpyeong, demo/sejong, demo/boryeong)
- docs/ 폴더에 PRODUCT_SCOPE.md가 이미 있으니 확인

모든 설치가 끝나면 각 서비스 실행 가능 여부를 확인해줘.
```

---

## PROMPT 2: 백엔드 기초 구조

```
CLAUDE.md를 읽고 백엔드 기초 구조를 만들어줘.

1. backend/app/core/config.py
   - pydantic-settings 기반 Settings 클래스
   - DB URL, API 키, 캐시 경로 등 환경변수

2. backend/app/core/database.py
   - async SQLAlchemy engine + session
   - PostGIS 확장 활성화

3. backend/app/models/base.py
   - SQLAlchemy Base + 공통 필드 (id, created_at, updated_at)

4. backend/app/models/screening.py
   - ScreeningRequest: 사업 입력 정보 (위치 geometry, 사업유형, 규모)
   - RiskCard: 리스크 카드 결과 (severity, rationale, evidence, next_action 등)
   - RegulationMatch: 규제 매칭 결과

5. backend/app/schemas/screening.py
   - Pydantic 입력/출력 스키마 (ScreeningInput, RiskCardResponse 등)

6. backend/app/main.py
   - FastAPI 앱 + CORS + 라우터 마운트
   - startup 이벤트에서 DB 연결 확인

7. backend/app/api/screening.py
   - POST /api/screening - 스크리닝 요청
   - GET /api/screening/{id} - 결과 조회

8. Alembic 초기화
   - alembic init backend/app/db/migrations
   - alembic.ini의 sqlalchemy.url을 env.py에서 config로 교체

모든 파일에 타입 힌트를 사용하고, PostGIS geometry 컬럼은 GeoAlchemy2로 정의해.
```

---

## PROMPT 3: 룰 엔진 기초

```
CLAUDE.md의 룰 엔진 섹션을 읽고 구현해줘.

1. backend/app/rules/schema.py
   - RuleDefinition Pydantic 모델 (rule_id, rule_version, title, trigger_dataset, condition, severity, rationale, evidence, next_action, legal_basis, source_snapshot_date, confidence, human_review_required)
   - RuleSet 모델 (version, rules 목록, description)

2. backend/app/rules/v1/ 폴더에 규칙 YAML 파일 생성
   영역별로 나눠서 총 24개 규칙 초안 작성:
   - land_regulation.yaml (5개): 용도지역 충돌, 보전지역 중첩, 개발제한구역, 군사시설보호, 농업진흥지역
   - ecology.yaml (4개): 생태민감구역 직접 중첩, 보호종 서식지 인접, 산림/습지 인접, 자연공원 경계
   - air_quality.yaml (3개): 대기오염물질 배경농도 초과, 비산먼지 발생원 인접, 대기환경규제지역
   - water.yaml (3개): 수계 인접, 상수원보호구역, 수질 민감지역
   - noise.yaml (2개): 주거지 인접 거리, 학교/병원 버퍼
   - soil.yaml (2개): 토양오염 우려지역, 지하수 수위
   - landscape.yaml (2개): 경관자원 인접, 조망권 영향
   - cultural.yaml (2개): 문화재 보호구역 중첩, 매장문화재 인접
   - social.yaml (2개): 주민 반복 민원 이력, 유사사업 보완 패턴

3. backend/app/services/risk_engine.py
   - RiskEngine 클래스
   - load_rules(): YAML에서 규칙 로드
   - evaluate(screening_input, spatial_data) → List[RiskCardResult]
   - 각 규칙의 condition을 spatial_data와 매칭하여 severity 판정
   - 결과에 반드시 rationale, evidence, next_action 포함

각 YAML 규칙은 한국 환경영향평가 실무를 기반으로 현실적이고 구체적으로 작성해.
trigger_dataset은 실제 EIASS API나 공공데이터 소스명으로 지정해.
```

---

## PROMPT 4: 데이터 커넥터 & 캐시

```
CLAUDE.md의 데이터 전략 3계층을 읽고 구현해줘.

1. backend/app/connectors/base.py
   - BaseConnector 추상 클래스
   - fetch(), get_cached(), save_snapshot() 인터페이스
   - ConnectorStatus enum (STABLE, UNSTABLE, UNAVAILABLE)
   - DataFreshness 모델 (fetched_at, snapshot_at, fallback_used, freshness)

2. backend/app/connectors/ 에 커넥터 구현:
   - land_use.py: 토지이용규제정보 API (A계층 - 안정형)
   - ecology.py: 생태자연도/보호지역 (B계층 - 불안정형+캐시)
   - vworld.py: V-world WFS 연속지적도 (B계층)
   - air_quality.py: 에어코리아 (B계층)
   - water_quality.py: 물환경정보 (B계층)

3. backend/app/services/cache_manager.py
   - CacheManager 클래스
   - save_snapshot(connector_name, data, metadata)
   - load_snapshot(connector_name) → (data, DataFreshness)
   - 스냅샷은 data/snapshots/ 에 JSON으로 저장
   - 파일명: {connector}_{region}_{timestamp}.json

4. backend/app/services/data_fetcher.py
   - DataFetcher 클래스
   - fetch_all(geometry, buffer_distance) → Dict[str, Any]
   - 각 커넥터를 비동기 병렬 호출
   - 실패 시 자동 캐시 전환 + fallback_used 플래그

5. backend/app/api/data_status.py
   - GET /api/data-status - 커넥터별 상태 대시보드 데이터 반환

MVP에서는 실제 API 호출이 안 되는 커넥터도 있을 수 있으니,
데모 시나리오(양평/세종/보령)용 mock 데이터를 data/demo/ 에 생성해줘.
각 mock 데이터에는 fetched_at, snapshot_at 등 메타데이터를 포함해.
```

---

## PROMPT 5: 프론트엔드 기초 레이아웃

```
CLAUDE.md의 화면 흐름 설계를 읽고 프론트엔드 기초를 만들어줘.

1. 전체 레이아웃 (frontend/src/app/layout.tsx)
   - 좌측 사이드바 (네비게이션) + 메인 콘텐츠 영역
   - 반응형 (모바일에서는 하단 탭)
   - shadcn/ui 기반 다크/라이트 토글

2. 6개 화면을 App Router 페이지로 생성:
   - /screening/new → 화면 1: 새 검토 시작
   - /screening/[id]/map → 화면 2: 리스크 맵 + 규제 패널
   - /screening/[id]/dashboard → 화면 3: 결과 대시보드
   - /screening/compare → 화면 4: 부지 비교
   - /screening/[id]/cases → 화면 5: 유사사례 & 보고서
   - /screening/[id]/data-status → 화면 6: 데이터 현황

3. 화면 1 구현 (새 검토 시작):
   - 주소 검색 입력 (텍스트)
   - 또는 지도에서 직접 위치 지정 (MapLibre GL JS)
   - 사업유형 선택 (select: 도로, 주거, 발전소, 공장, 기타)
   - 사업규모 입력
   - "부지 추가" 버튼 (비교용, 최대 3개)
   - "검토 시작" 버튼

4. 공통 컴포넌트:
   - RiskBadge: severity별 색상 배지 (Critical=red, Major=orange, Review=yellow, Info=blue)
   - EvidenceDrawer: 근거 정보 사이드 패널 (Sheet 컴포넌트 활용)
   - FreshnessIndicator: 데이터 신선도 표시 (배지 + 툴팁)
   - FallbackBanner: "캐시 데이터로 전환" 알림 배너

5. API 클라이언트 (frontend/src/lib/api.ts):
   - axios 또는 fetch 기반
   - React Query와 연동
   - 에러 핸들링

MapLibre GL JS 지도 초기화 시 기본 타일은 OSM 또는 무료 타일 사용.
디자인은 환경/자연을 연상시키는 톤(green/teal 계열 accent)으로 하되,
shadcn/ui의 깔끔한 구조를 유지해.
```

---

## PROMPT 6: Phase 0 완료 체크

```
지금까지 만든 구조를 점검해줘.

1. CLAUDE.md 읽고 모든 폴더 구조가 맞는지 확인
2. PRODUCT_SCOPE.md 읽고 non-goal이 명확히 정의되었는지 확인
3. 룰 엔진 YAML 파일들이 모두 존재하고 스키마에 맞는지 검증
4. 백엔드 서버 실행 가능 여부 확인 (uvicorn backend.app.main:app --reload)
5. 프론트엔드 개발 서버 실행 가능 여부 확인 (cd frontend && pnpm dev)
6. Docker Compose로 PostgreSQL + PostGIS 실행 가능 여부 확인

문제가 있으면 수정하고, 없으면 Phase 0 완료 보고를 해줘.
Phase 0 완료 기준:
- [ ] 이름 통일 (EIA Pre-Screen)
- [ ] non-goal 확정 (PRODUCT_SCOPE.md)
- [ ] rule v2 범위 확정 (24개 규칙 YAML)
- [ ] 프로젝트 구조 완성
- [ ] 개발 서버 실행 가능
```
