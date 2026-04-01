# 커넥터 오류 현황 및 해결 방안

> 작성일: 2026-03-30 | 최종 수정: 2026-03-30
> 총 14개 커넥터 중 **13개 정상, 1개 미전환** (project_area)

## 현황 요약 (수정 후)

| 커넥터 | 데이터 소스 | 상태 | 비고 |
|--------|-----------|------|------|
| geology | 로컬 CSV (지형지질 개요/경사/표고) | **정상** | API → CSV 전환 (2026-03-30) |
| greenhouse | 로컬 CSV (국가 온실가스 인벤토리) | **정상** | API → CSV 전환 (2026-03-30) |
| noise | 로컬 CSV (소음진동측정망 144,927건) | **정상** | API → CSV 전환 (2026-03-30) |
| population | 로컬 CSV (인구주거 조사/예측) | **정상** | API → CSV 전환 (2026-03-30) |
| soil | 로컬 CSV (토양오염실태조사 2,949건) | **정상** | API → CSV 전환 (2026-03-30) |
| traffic | 한국도로공사 OpenAPI (실시간 교통량) | **정상** | API URL 변경 (data.ex.co.kr) |
| project_area | ~~B553748 API~~ | **미전환** | SHP 파일 (geopandas 필요) |

## 수정 이전 상태 (참고)

| 커넥터 | 이전 URL 경로 | 이전 오류 | 원인 |
|--------|--------------|-----------|------|
| geology | `B553748/geologyinformation/...` | 500 | 서비스 경로 미등록/폐기 |
| greenhouse | `B553748/greenhousegasinformation/...` | 500 | 서비스 경로 미등록/폐기 |
| noise | `B553748/noisevibrationinformaiton/...` | 500 | 서비스 경로 미등록, 1480523도 404 |
| population | `B553748/populationhousinginformation/...` | 500 | 서비스 경로 미등록/폐기 |
| project_area | `B553748/projectareainformation/...` | 500 | 서비스 경로 미등록/폐기 |
| soil | `1480523/SgisSoAPI/getSgisSoList` | 500 | 좌표 파라미터 미전송 |
| traffic | `B553755/TrafficVolumeService/...` | 404 | 엔드포인트 폐기 |

## 정상 작동 커넥터 (7개, 참고용)

| 커넥터 | URL 경로 | 특징 |
|--------|---------|------|
| air_quality | `B552584/ArpltnInforInqireSvc` | TM 좌표 변환, 2단계 폴백 |
| ecology | `B553084/ecoapi/EcologyzmpService` | WMS 좌표 질의 |
| water_quality | `1480523/WaterQualityService` | XML 파싱, 측정소 목록 |
| weather | `1360000/AsosDalyInfoService` | 지역번호 기반 조회 |
| marine | `1192000/service/EnvImpactService` | JSON/XML 복합 |
| land_use | `1611000/nsdi/EIAService` | V-world WFS 연계 |
| eia_info | `1480523/EnvrnAffcEvlBsnsInfoInqireService` | XML 파싱, 6종 공간 검색 |

---

## 상세 분석

### 1. geology (지형지질)

**코드 위치**: `backend/app/connectors/geology.py:45`

**현재 URL**:
```
https://apis.data.go.kr/B553748/geologyinformation/getListGeologyInformation
```

**코드 내 TODO**:
```python
# TODO: 1480523/GeologicalService 확인 대기
```

**테스트 이력** (`data/bulk/api_retest_results.json` #18):
- 기존 `B553748/...` → 500 Internal Server Error
- 대안 `1480523/GeologicalService/getGeological` → 404 Not Found

**파라미터**: `serviceKey, lng, lat, buffer, returnType=json`

**문제점**:
1. `B553748` 서비스 경로가 존재하지 않거나 폐기됨
2. `1480523/GeologicalService`도 공공데이터포털에 등록되지 않은 경로
3. 좌표 파라미터명 `lng/lat` — 실제 API가 다른 파라미터명을 요구할 가능성

---

### 2. greenhouse (온실가스)

**코드 위치**: `backend/app/connectors/greenhouse.py:45`

**현재 URL**:
```
https://apis.data.go.kr/B553748/greenhousegasinformation/getListGreenhouseGasInformation
```

**코드 내 TODO**:
```python
# TODO: 1480523/GreenhouseGasService 확인 대기
```

**테스트 이력** (`api_retest_results.json` #17):
- 기존 `B553748/...` → 500
- 대안 `1480523/GreenhouseGasService/getGreenhouseGas` → 404

**문제점**:
1. 두 경로 모두 유효하지 않음
2. C계층(수동 큐레이션)으로 분류되어 있으나 실시간 API 호출을 시도하는 구조

---

### 3. noise (소음진동)

**코드 위치**: `backend/app/connectors/noise.py:4`

**현재 URL**:
```
https://apis.data.go.kr/B553748/noisevibrationinformaiton/getListNoisevibrationInformation
```

**코드 내 NOTE** (가장 상세한 기록):
```python
NOTE: 서비스명 미확인 — B553748 500, 1480523 후보도 404. 서버 복구 대기.
```

**테스트 이력** (`api_retest_results.json` #14):
- 기존 `B553748/...` → 500
- 대안 `1480523/NoiseVibrationService/getNoiseVibration` → 404

**문제점**:
1. 두 경로 모두 확인 실패 — 이 서비스가 공공데이터포털에 존재하는지 자체가 불확실
2. URL의 `noisevibrationinformaiton`에 오타 가능성 (`information` → `informaiton`)

---

### 4. population (인구주거)

**코드 위치**: `backend/app/connectors/population.py:45`

**현재 URL**:
```
https://apis.data.go.kr/B553748/populationhousinginformation/getListPopulationHousingInformation
```

**코드 내 TODO**:
```python
# TODO: 1480523/PopulationService 확인 대기
```

**테스트 이력** (`api_retest_results.json` #16):
- 기존 `B553748/...` → 500
- 대안 `1480523/PopulationService/getPopulation` → 404

---

### 5. project_area (사업구역)

**코드 위치**: `backend/app/connectors/project_area.py:45`

**현재 URL**:
```
https://apis.data.go.kr/B553748/projectareainformation/getListProjectAreaInformation
```

**코드 내 TODO**:
```python
# TODO: 1480523/BsnsAreaService 확인 대기
```

**테스트 이력** (`api_retest_results.json` #15):
- 기존 `B553748/...` → 500
- 대안 `1480523/BsnsAreaService/getBsnsArea` → 404

---

### 6. soil (토양측정망)

**코드 위치**: `backend/app/connectors/soil.py`

**현재 URL**:
```
https://apis.data.go.kr/1480523/SgisSoAPI/getSgisSoList
```

**테스트 이력** (`api_retest_results.json` #5):
- `1480523/SgisSoAPI/getSgisSoList` → 500 "Unexpected errors"

**파라미터**: `serviceKey, pageNo=1, numOfRows=10, type=json`

**문제점 (다른 커넥터와 다름)**:
1. **좌표 파라미터를 전혀 전송하지 않음** — `lng`, `lat`, `buffer` 없이 페이지네이션만 전송
2. 공간 필터링 없이 전체 목록을 조회하는 구조
3. URL 경로(`1480523`)는 다른 커넥터와 달리 유효한 기관 코드이나, 서비스 자체가 500 응답

---

### 7. traffic (교통량)

**코드 위치**: `backend/app/connectors/traffic.py:45`

**현재 URL**:
```
https://apis.data.go.kr/B553755/TrafficVolumeService/getTrafficVolume
```

**코드 내 TODO**:
```python
# TODO: 1613000/TrafficAmountInfoService 확인 대기
```

**테스트 이력** (`api_retest_results.json` #7):
- 기존 `B553755/...` → 500
- 대안 `1613000/KictTmsStat/getTmsStatInfo` → 404

**문제점**:
1. `B553755`는 한국건설기술연구원 코드이나 해당 엔드포인트 없음
2. `1613000`(국토교통부) 경로도 실패
3. C계층으로 분류 — 수동 데이터가 적합할 수 있음

---

## 공통 원인 분석

### 1. `B553748` 서비스 경로 문제 (5개 커넥터)

geology, greenhouse, noise, population, project_area가 모두 `B553748` 기관 코드를 사용합니다. 이 코드는 **환경영향평가정보지원시스템(EIASS) 관련 API**로 추정되나, 해당 서비스가 공공데이터포털에 **등록되지 않았거나 폐기**된 상태입니다.

### 2. 대안 경로(`1480523`) 실패

모든 대안 경로(`1480523/GeologicalService` 등)도 404를 반환합니다. `1480523`은 국립환경과학원 코드로, 일부 서비스(WaterQualityService, EnvrnAffcEvlBsnsInfoInqireService)는 정상 작동하지만 위 7개 서비스는 존재하지 않습니다.

### 3. 정상 커넥터와의 구조적 차이

| 항목 | 정상 커넥터 | 오류 커넥터 |
|------|-----------|-----------|
| API URL | 공공데이터포털에서 직접 확인한 URL | 추정/미확인 URL |
| 좌표 변환 | TM 좌표, 지역번호, 측정소코드 등 API별 맞춤 | `lng/lat/buffer` 일률 전송 |
| 폴백 전략 | 2단계 폴백 (air_quality) | 단일 시도, 캐시 폴백만 |
| 캐시 이력 | `data/snapshots/`에 다수 스냅샷 존재 | 스냅샷 0건 (한번도 성공 못함) |

---

## 해결 방안

### 방안 A: 공공데이터포털에서 정확한 API 확인 (권장)

**작업 내용**:
1. [data.go.kr](https://www.data.go.kr) 포털에서 각 데이터 항목 검색
2. 실제 서비스 URL, 파라미터 명세 확인
3. 필요 시 API 활용 신청 (승인 필요)
4. 커넥터 코드의 URL + 파라미터 수정

**확인 필요 항목**:

| 데이터 | 검색 키워드 | 예상 제공기관 |
|--------|-----------|-------------|
| 지형지질 | "지질도", "지형정보" | 한국지질자원연구원, 국토지리정보원 |
| 온실가스 | "온실가스 배출", "탄소 배출" | 환경부, 온실가스종합정보센터 |
| 소음진동 | "소음측정", "진동측정" | 국립환경과학원 |
| 인구주거 | "인구통계", "주택현황" | 통계청, 행정안전부 |
| 사업구역 | "환경영향평가 사업구역" | 환경부 EIASS |
| 토양측정 | "토양오염", "토양측정망" | 국립환경과학원 |
| 교통량 | "교통량 통계", "도로교통량" | 한국도로공사, 국토교통부 |

**예상 공수**: 커넥터당 0.5~1일 (API 탐색 + 신청 + 테스트)

### 방안 B: 대체 데이터 소스 활용

일부 커넥터는 다른 API로 대체 가능합니다:

| 커넥터 | 대체 가능 소스 | 비고 |
|--------|-------------|------|
| soil | 토양환경정보시스템 (토양오염도조사) | 별도 API 확인 필요 |
| traffic | 도로교통량 통계연보 (공공데이터포털) | `1613000` 계열 재탐색 |
| population | 행정안전부 주민등록 인구통계 | SGIS 통계지리정보 API |
| geology | 한국지질자원연구원 지질도 WMS | 래스터 데이터, 좌표 쿼리 가능 |
| noise | 에어코리아 소음측정소 데이터 | 대기질과 유사 구조 |
| greenhouse | 환경부 온실가스 종합정보센터 | 지역별 통계 |
| project_area | EIASS 환경영향평가서 원문 (RAG) | 이미 구축된 RAG 활용 |

### 방안 C: 수동 캐시 스냅샷 구축 (즉시 적용 가능)

API가 작동하지 않는 동안 **대표 데이터를 수동으로 캐시**에 넣어 빈 결과 대신 참고 데이터를 제공:

1. 각 커넥터의 기대 응답 구조에 맞는 JSON 파일 생성
2. `data/snapshots/{connector}_{region}_{timestamp}.json` 형식으로 저장
3. CacheManager가 자동으로 fallback 사용

**예시** (`data/snapshots/geology_default_2026-03-30.json`):
```json
{
  "terrain_type": "구릉지",
  "slope_grade": "15도 이상 급경사지 포함",
  "geological_feature": "화강암/편마암 기반",
  "disaster_risk": "산사태 위험등급 2등급",
  "note": "수동 입력 대표값 — 실제 조사 필요"
}
```

**장점**: 즉시 적용, 대시보드에서 0% 대신 참고 데이터 표시
**단점**: 위치별 정확도 없음, "수동 데이터" 표시 필요

### 방안 D: 현상 유지 (리스크 낮음)

현재 7개 커넥터는 `_make_empty_result()`로 빈 결과를 반환하며, **앱 동작에 영향 없음**:
- 에러 전파 없음 (graceful 처리)
- 정상 작동 7개 커넥터가 핵심 데이터(토지이용, 생태, 대기, 수질, 기상, 해양, 환경영향평가) 커버
- 데이터현황 대시보드에서 해당 커넥터는 "unavailable" 상태로 표시

---

## 권장 우선순위

| 순서 | 방안 | 대상 커넥터 | 기대 효과 |
|------|------|-----------|----------|
| 1 | **C (수동 캐시)** | 전체 7개 | 즉시 빈 데이터 해소, 참고값 제공 |
| 2 | **A (API 확인)** | soil, traffic, population | 가장 데이터 확보 가능성 높은 3개 우선 |
| 3 | **B (대체 소스)** | geology, noise | 지질자원연구원 WMS, 소음측정소 |
| 4 | **D (유지)** | greenhouse, project_area | 대체 소스 부재 시 현상 유지 |

---

## 참고 파일

| 파일 | 내용 |
|------|------|
| `data/bulk/api_test_results.json` | 최초 API 테스트 결과 |
| `data/bulk/api_retest_results.json` | 대안 URL 포함 재테스트 결과 (32개 API) |
| `backend/app/connectors/base.py` | BaseConnector, `_make_empty_result()` 정의 |
| `backend/app/services/cache_manager.py` | CacheManager 스냅샷 관리 |
| `backend/app/core/config.py:52` | `DATA_GO_KR_API_KEY` 설정 |
