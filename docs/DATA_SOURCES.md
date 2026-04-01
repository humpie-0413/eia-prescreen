# EIA Pre-Screen 데이터 소스 현황

> 기준일: 2026-03-29
> 공공 API 34종 승인 · 12종 실연동 · 18개 커넥터 구현

---

## 1. 3계층 데이터 전략

```
┌─────────────────────────────────────────────────────────┐
│ A계층: 안정형 실시간                                       │
│   - 실제 검증에서 안정적으로 확인된 API                      │
│   - 장애 시에도 캐시 폴백 (24시간 TTL)                     │
├─────────────────────────────────────────────────────────┤
│ B계층: 불안정형 + 캐시 폴백                                │
│   - 실시간 호출 시도 → 실패 시 마지막 성공 스냅샷으로 전환     │
│   - 필수 메타: fetched_at, snapshot_at, fallback_used     │
├─────────────────────────────────────────────────────────┤
│ C계층: 수동 스냅샷 / 큐레이션                               │
│   - 자동 수집보다 정확한 태깅이 중요                         │
│   - 주기적 수동 업데이트 또는 정적 데이터                     │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 커넥터 상세 (18개)

### A계층 — 안정형 실시간 (2개)

| # | 커넥터 | 파일 | API 출처 | 데이터 |
|---|--------|------|---------|--------|
| 1 | **LandUseConnector** | `land_use.py` | 토지이용규제정보서비스 (토지이음) + V-world Data API | 용도지역/지구, 행위제한, 경계 geometry |
| 2 | **WeatherConnector** | `weather.py` | 기상청 ASOS 종관기상관측 | 기온, 강수, 풍속, 일조, 서리/안개일수 |

### B계층 — 불안정형 + 캐시 폴백 (11개)

| # | 커넥터 | 파일 | API 출처 | 데이터 |
|---|--------|------|---------|--------|
| 3 | **VworldConnector** | `vworld.py` | V-world WFS GetFeature (연속지적도) | 필지 경계, 지목, 면적 |
| 4 | **AirQualityConnector** | `air_quality.py` | 에어코리아 (한국환경공단) | PM2.5, PM10, NO2, SO2, CO, O3 |
| 5 | **WaterQualityConnector** | `water_quality.py` | 물환경정보시스템 (WEIS) | BOD, TP, 수질등급, 하천 근접도 |
| 6 | **SoilConnector** | `soil.py` | 토양측정망 (토양환경정보시스템) | 오염도, 지하수위, 토양유형, pH |
| 7 | **NoiseConnector** | `noise.py` | 국가소음정보시스템 | 소음도 (Leq dB), 주거지 이격, 진동 민감도 |
| 8 | **PopulationConnector** | `population.py` | EIASS 인구주거정보 | 인구밀도, 주거수, 취약계층, 학교/병원 근접 |
| 9 | **ProjectAreaConnector** | `project_area.py` | EIASS 사업구역정보 | 사업면적, 피복유형, 불투수율, 식생율, 경사 |
| 10 | **EcologyConnector** | `ecology.py` | EGIS 환경공간정보 + WMS | 생태등급 (1~3), 멸종위기종, 자연공원, 산림유형 |
| 11 | **EiaInfoConnector** | `eia_info.py` | 환경영향평가 정보 (EIASS) | 인근 EIA 사업, 멸종위기종, 환경측정지점 |
| 12 | **MarineConnector** | `marine.py` | 해양환경정보 + 해양수산부 | 해안 이격, 해양보호구역, 어장, 해양생물 |
| 13 | **GeologyConnector** | `geology.py` | EIASS 지형지질정보 | 지형유형, 암석, 경사등급, 침하위험, 단층 |

### C계층 — 수동 스냅샷 (5개)

| # | 커넥터 | 파일 | API 출처 | 데이터 |
|---|--------|------|---------|--------|
| 14 | **GreenhouseConnector** | `greenhouse.py` | EIASS 온실가스정보 | 연간 CO2 배출량, 탄소중립지역, 배출권거래 |
| 15 | **TrafficConnector** | `traffic.py` | 교통량 통계 (건설기술연구원) | 일교통량, 도로유형, 통학로, 혼잡도 |
| 16 | **LandscapeConnector** | `landscape.py` | 국가경관포탈 | 경관자원 이격, 조망점 영향, 광공해 |
| 17 | **CulturalConnector** | `cultural.py` | 문화재청 GIS | 문화재보호구역, 매장문화재, 천연기념물 |
| 18 | **BaseConnector** | `base.py` | — | 추상 기반 클래스 (재시도, 캐시, 데모 지원) |

---

## 3. 공공 API 승인 현황 (34종)

### 실연동 완료 (12종)

| # | API 서비스명 | 제공기관 | 서비스키 구분 | 커넥터 |
|---|-------------|---------|-------------|--------|
| 1 | 토지이용규제정보서비스 | 국토교통부 | DATA_GO_KR_API_KEY | LandUse |
| 2 | V-world 공간정보 | 국토정보플랫폼 | VWORLD_API_KEY | Vworld |
| 3 | 에어코리아 대기오염정보 | 한국환경공단 | AIRKOREA_API_KEY | AirQuality |
| 4 | 물환경정보시스템 수질측정 | 국립환경과학원 | DATA_GO_KR_API_KEY | WaterQuality |
| 5 | 토양측정망 정보 | 국립환경과학원 | DATA_GO_KR_API_KEY | Soil |
| 6 | 기상청 ASOS 종관기상 | 기상청 | DATA_GO_KR_API_KEY | Weather |
| 7 | 환경공간정보 EGIS | 환경부 | EIASS_API_KEY | Ecology |
| 8 | EIASS 인구주거정보 | 국립환경과학원 | EIASS_API_KEY | Population |
| 9 | EIASS 사업구역정보 | 국립환경과학원 | EIASS_API_KEY | ProjectArea |
| 10 | EIASS 지형지질정보 | 국립환경과학원 | EIASS_API_KEY | Geology |
| 11 | EIASS 환경영향평가정보 | 국립환경과학원 | EIASS_API_KEY | EiaInfo |
| 12 | 해양환경정보 | 해양수산부 | DATA_GO_KR_API_KEY | Marine |

### 승인 완료 · 연동 예정 (22종)

| # | API 서비스명 | 제공기관 | 용도 | 상태 |
|---|-------------|---------|------|------|
| 13 | 국가소음정보 | 국립환경과학원 | 소음 실측 | 서비스 복구 대기 |
| 14 | 교통량 통계 | 건설기술연구원 | 교통량 | 캐시 스냅샷 사용 |
| 15 | 국가경관포탈 | 국토교통부 | 경관자원 | 캐시 스냅샷 사용 |
| 16 | 문화재 GIS | 문화재청 | 문화재 | 캐시 스냅샷 사용 |
| 17 | 온실가스 정보 | 환경부 | 온실가스 | 캐시 스냅샷 사용 |
| 18-34 | 기타 EIASS 계열 17종 | 국립환경과학원 | 각 도메인 | 순차 연동 예정 |

---

## 4. EIASS 환경영향평가서 원문 (RAG)

### 크롤링 현황

| 항목 | 수치 |
|------|------|
| 크롤링 대상 | 103건 (환경영향평가 정보지원시스템) |
| PDF 파일 | 526개 (6.3 GB) |
| 사업유형 | 16개 유형 전체 커버 |
| 크롤링 방식 | Selenium + 로그인 인증 (EIASS_ID, EIASS_PW) |

### 텍스트 추출 & RAG 색인

| 항목 | 수치 |
|------|------|
| 추출 스크립트 | `backend/scripts/extract_report_text.py` |
| 추출 완료 | 395개 JSON (PDF → 텍스트) |
| RAG 색인 | 6,103 청크 (99개 보고서) |
| 임베딩 모델 | `jhgan/ko-sroberta-multitask` |
| 벡터 DB | ChromaDB (persistent, `data/reports/chromadb/`) |
| 청크 크기 | 500자, 100자 오버랩 |

### 사업유형별 분포

| 사업유형 | 프로젝트 수 | 청크 수 |
|---------|-----------|---------|
| road (도로건설) | 12 | 745 |
| energy (에너지개발) | 9 | 612 |
| urban_dev (도시개발) | 8 | 521 |
| industrial (산업단지) | 7 | 489 |
| water_resource (수자원개발) | 7 | 456 |
| port (항만건설) | 6 | 398 |
| railway (철도건설) | 6 | 387 |
| river (하천이용) | 5 | 342 |
| tourism (관광단지) | 5 | 334 |
| waste (폐기물처리) | 5 | 312 |
| mountain (산지개발) | 5 | 298 |
| airport (공항건설) | 4 | 276 |
| reclamation (매립·간척) | 4 | 267 |
| mining (광업) | 4 | 254 |
| sports (체육시설) | 3 | 218 |
| military (국방·군사) | 3 | 194 |

### RAG 품질

| 지표 | 결과 |
|------|------|
| 검색 품질 평균 | 90.3/100 |
| LLM 답변 품질 평균 | 92.7/100 |
| Draft Copilot RAG 통과율 | 100% (5/5) |
| 전체 품질 점수 | 94.0/100 |

---

## 5. 정적 데이터

| 데이터셋 | 파일 위치 | 건수 | 설명 |
|---------|----------|------|------|
| 규칙 YAML | `backend/app/rules/v1/` | 64개 (16 도메인) | 리스크 판정 규칙 |
| 규제 매핑 | `data/regulations/` | 175개 | 용도지역·보호구역·EIA 임계값 |
| 유사사례 | `data/cases/` | 84건 | 큐레이션 사례 (태그·요약) |
| 벌크 협의 데이터 | `data/patterns/` | 9,973건 | 과거 환경영향평가 협의 결과 |
| 데모 시나리오 | `data/demo/` | 3건 | 양평·세종·보령 목 데이터 |

---

## 6. 캐시 전략

```
요청 → 실시간 API 호출 시도
         │
         ├─ 성공 → 결과 반환 + 스냅샷 저장
         │         (fetched_at 기록)
         │
         └─ 실패 → 캐시 스냅샷 조회
                    │
                    ├─ 캐시 있음 → 결과 반환
                    │   (fallback_used=true, snapshot_at 표시)
                    │
                    └─ 캐시 없음 → 데모 데이터 반환
                        (demo_mode=true 시)
```

**캐시 설정**:
- 저장 경로: `data/snapshots/`
- 기본 TTL: 24시간 (`CACHE_TTL_HOURS`)
- 형식: JSON (connector_name + 좌표 해시 키)
- 신선도 표시: fresh (24h 이내) / stale (24h 초과) / expired (7일 초과)

---

## 7. 환경 변수

| 변수 | 용도 | 필수 |
|------|------|------|
| `DATA_GO_KR_API_KEY` | 공공데이터포털 통합키 | 실연동 시 |
| `VWORLD_API_KEY` | V-world 공간정보 | 실연동 시 |
| `AIRKOREA_API_KEY` | 에어코리아 대기질 | 실연동 시 |
| `EIASS_API_KEY` | EIASS 환경영향평가 | 실연동 시 |
| `EIASS_ID` / `EIASS_PW` | EIASS 크롤링 로그인 | RAG 색인 시 |
| `OPENROUTER_API_KEY` | LLM (DeepSeek V3) | AI 해석 시 |
| `RAG_EMBED_MODEL` | 임베딩 모델 | 기본값 사용 가능 |
| `CACHE_DIR` | 캐시 저장 경로 | 기본값: `./data/snapshots` |
| `CACHE_TTL_HOURS` | 캐시 만료 시간 | 기본값: 24 |
| `DEMO_MODE` | 데모 모드 (DB 불필요) | 기본값: true |
