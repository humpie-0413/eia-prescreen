# EIA Pre-Screen — 데모 실행 가이드

포트폴리오 발표용 오프라인/온라인 데모 절차입니다.

---

## 빠른 시작 (5분)

### 최소 요구사항

| 항목 | 필수 여부 | 설명 |
|------|---------|------|
| Docker Desktop | **필수** | PostgreSQL + PostGIS 실행 |
| Python 3.11+ | **필수** | 백엔드 |
| Node.js 20+ + pnpm | **필수** | 프론트엔드 |
| OPENROUTER_API_KEY | 선택 | AI 해석 기능용 (DeepSeek V3). 없으면 나머지 모든 기능 정상 작동 |

### 1. 환경 변수

```bash
cp .env.example .env
```

`.env` 최소 설정 (AI 해석 없이 데모):
```
DEMO_MODE=true
DATABASE_URL=postgresql+asyncpg://eia_user:change_me_in_production@localhost:5432/eia_prescreen
```

AI 해석 포함:
```
DEMO_MODE=true
OPENROUTER_API_KEY=your-key-here
LLM_MODEL=deepseek/deepseek-chat
DATABASE_URL=postgresql+asyncpg://eia_user:change_me_in_production@localhost:5432/eia_prescreen
```

### 2. 서비스 실행

```bash
# 터미널 1 — DB
docker-compose up -d db

# 터미널 2 — 백엔드 (가상환경 활성화 후)
cd backend
pip install -r requirements.txt        # 최초 1회
alembic upgrade head                   # 최초 1회
uvicorn app.main:app --reload --port 8000

# 터미널 3 — 프론트엔드
cd frontend
pnpm install                           # 최초 1회
pnpm dev
```

브라우저: `http://localhost:3000`

---

## 데모 시나리오 1: 양평 도로 (기본 흐름)

**목적**: 규칙 엔진, 리스크 카드, 체크리스트 기본 흐름 시연

### 단계별 절차

#### Step 1 — 새 검토 생성
1. `http://localhost:3000/screening/new` 접속
2. 사업명: **"양평 국도 우회도로 건설사업"**
3. 사업유형: **도로**
4. 사업규모: `L=4.2km, W=20m`
5. 주소: `경기도 양평군`
6. **검토 시작** 클릭 → 대시보드로 이동

#### Step 2 — 리스크 분석 실행
1. 대시보드 상단 **"리스크 분석 실행"** 버튼 클릭
2. scenario 드롭다운: **yangpyeong** 선택 → 실행
3. 결과: Major 5건 + Review 3건 (ECO-002, LAND-005, NOI-001, WAT-003, WAT-004 등) 총 8건 표시
4. 각 카드의 **"근거 보기"** 클릭 → Evidence Drawer 확인

**시연 포인트**: "모든 리스크에 법적 근거 조항이 명시됩니다"

#### Step 3 — 리스크 맵
1. **리스크 맵** 탭 클릭
2. 지도에서 500m/1km 버퍼 확인
3. 사이드 패널에서 규제 목록 클릭

#### Step 4 — 유사사례 & AI 해석
1. **유사사례** 탭 클릭
2. **AI 해석 탭** → "AI 해석 생성" 클릭 *(OPENROUTER_API_KEY 필요)*
3. 보고서 탭 → "1p 브리프 다운로드" 클릭

---

## 데모 시나리오 2: 보령 발전소 (복합 Critical 리스크)

**목적**: Critical 리스크 4건 동시 발생, 복합 리스크 상황 시연

### 단계별 절차

1. 새 검토 → 사업명: **"보령 LNG 복합화력발전소 건설사업"**, 사업유형: **발전소**
2. 리스크 분석 실행 → scenario: **boryeong**
3. 결과 확인:
   - **Critical 4건**: ECO-001 (생태자연도 1등급), LAND-001 (용도지역 상충), LAND-006 (산지전용제한), WAT-002 (상수원보호구역)
   - 총 30건 리스크 (Major 13, Review 12, Info 1)
4. 대시보드에서 빨간색 Critical 카드 강조 확인
5. 환경현황 요약 보고서 PDF 다운로드

**시연 포인트**: "Critical이 3건이면 사실상 사업 위치 재검토가 필요한 수준입니다"

---

## 데모 시나리오 3: 부지 비교 (양평 vs 세종 vs 보령)

**목적**: 3개 부지 비교를 통한 최적 입지 선정 지원 시연

### 전제 조건
- 시나리오 1, 2에서 생성된 스크리닝 + 세종 스크리닝 1개 필요
- 세종 추가: 사업명 "세종시 행복도시 공동주택 건설사업", 사업유형 "주거", scenario: sejong

### 절차
1. `/screening/compare` 접속
2. 3개 스크리닝 선택 (체크박스)
3. **비교 실행** 클릭
4. 결과 확인:
   - 부지별 요약 카드 (Critical/Major/Review/Info 카운트)
   - ★ 상대적으로 낮은 리스크 표시 (양평)
   - 리스크 비교 매트릭스 테이블
   - 종합 추천 텍스트
5. **비교 보고서 PDF** 다운로드

**시연 포인트**: "3개 부지의 리스크를 한눈에 비교해 의사결정을 지원합니다"

---

## 데모 시나리오 4: 데이터 가용성 현황

**목적**: 데이터 신뢰도와 캐시 폴백 시스템 시연

1. 임의 스크리닝 → **데이터 현황** 탭
2. scenario: **sejong** → 생태 데이터 "cached (폴백)", 수질 "stale" 표시 확인
3. 커버리지 % 게이지, 신선도 분포 막대 확인
4. "추가 조사 필요" 섹션의 빨간 항목 확인

**시연 포인트**: "데이터 기준일자와 신선도를 명시해 분석 신뢰도를 투명하게 공개합니다"

---

## OPENROUTER_API_KEY 없이 발표하는 경우

다음 기능들은 **API 키 없이도 정상 작동**합니다:

| 기능 | API 키 불필요 이유 |
|------|-----------------|
| 리스크 분석 | 규칙 엔진 (YAML 기반, 로컬 실행) |
| 규제 매칭 | JSON 파일 기반, 로컬 실행 |
| 유사사례 검색 | cases.json 파일 기반 |
| 체크리스트 생성 | 로컬 로직 |
| PDF 보고서 (모든 종류) | reportlab, 로컬 생성 |
| 리스크 맵 | MapLibre + 로컬 GeoJSON |
| 부지 비교 | 로컬 점수 계산 |
| 데이터 현황 | 데모 스냅샷 (mock_data.json) |

**AI 해석 버튼만** 에러 메시지를 표시합니다.

대안 → "AI 해석 탭에는 사전 생성된 해석을 DB에 저장해두고 표시"하는 방식으로 발표 가능:
```sql
UPDATE screening_requests
SET llm_interpretation = '본 사업지는 팔당상수원 수변구역에 해당하며...'
WHERE project_name = '양평 국도 우회도로 건설사업';
```

---

## 발표 중 자주 받는 질문과 답변

**Q: 실제 공공 API와 연동됩니까?**
A: 14개 커넥터(토지이음, 에어코리아, 환경부, 기상청, 통계청 등)가 구현되어 있습니다. 데모에서는 안정성을 위해 검증된 스냅샷 데이터를 사용합니다 (DEMO_MODE=true).

**Q: 규칙 64개는 어디서 왔나요?**
A: 환경부 환경영향평가 작성 안내서 기반 + 국토계획법·농지법·자연환경보전법 등 핵심 법령. 16개 도메인(토지, 생태, 대기, 수질, 소음, 토양, 경관, 문화재, 사회, 지질, 온실가스, 위험물, 해양, 인구, 교통, 폐기물)을 커버합니다. YAML 파일로 관리되어 법령 개정 시 코드 변경 없이 업데이트 가능합니다.

**Q: AI 해석의 정확도는?**
A: DeepSeek V3 (via OpenRouter)는 규칙 엔진 출력을 요약하는 역할입니다. "법적 효력 없음" 명시 + 근거 카드와 함께 표시해 AI 단독 판단을 방지합니다.

**Q: 상용화하려면?**
A: 공공 API 정식 키 발급, HWP 출력, 사용자 인증이 필요합니다. 규칙은 현재 64개(16도메인)까지 확장 완료.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| DB 연결 실패 | Docker 미실행 | `docker-compose up -d db` |
| 지도 안 나옴 | MapLibre CDN 차단 | 인터넷 연결 확인 |
| PDF 한국어 깨짐 | CID 폰트 미지원 | reportlab ≥4.2 확인 |
| AI 해석 실패 | API 키 미설정 | `.env`에 `OPENROUTER_API_KEY` + `LLM_MODEL` 추가 |
| alembic 에러 | 마이그레이션 미실행 | `alembic upgrade head` |
| pnpm: command not found | pnpm 미설치 | `npm install -g pnpm` |
