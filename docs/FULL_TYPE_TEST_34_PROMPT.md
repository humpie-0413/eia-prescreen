# EIA Pre-Screen 전체 사업유형 풀테스트 (34건)

> 17개 사업유형 × 2건 = 34건
> 기존 테스트 사례(부여, 울산, 영주, 새만금, 춘천, 시화호) 미포함 — 전부 신규

---

## 프롬프트 (Claude Code에 붙여넣기)

```
EIA Pre-Screen 전체 사업유형 풀테스트를 실행해줘.
백엔드 localhost:8000에서 실행 중이어야 함.
JWT 토큰을 먼저 생성하고, 34건 사례를 dispatching-parallel-agents로 병렬 테스트.

각 사례별 10개 API 호출:
1. POST /api/screening (생성)
2. GET /api/screening/{id}/evaluate (리스크 평가)
3. GET /api/screening/{id}/regulations (규제 매칭)
4. GET /api/screening/{id}/cases (유사사례)
5. POST /api/screening/{id}/predict-review (검토의견 예측)
6. POST /api/screening/{id}/quality-check (품질 체크)
7. GET /api/patterns/{type} (과거 패턴)
8. POST /api/screening/{id}/draft (초안 생성)
9. POST /api/rag/query (RAG 질의 — 사업유형 관련)
10. GET /api/screening/{id}/data-status (데이터 현황)

모든 API에 Authorization: Bearer {token} 포함.

## 34건 테스트 데이터

### 1. 도로 (road) — 2건

사례 1-1: 세종~대전 고속도로 건설
- project_name: 세종-대전 고속도로
- project_type: road
- latitude: 36.5100
- longitude: 127.0200
- address: 세종특별자치시 장군면

사례 1-2: 양양~속초 국도 확장
- project_name: 양양-속초 국도7호선 확장
- project_type: road
- latitude: 38.0750
- longitude: 128.6180
- address: 강원특별자치도 양양군 현북면

### 2. 철도 (railway) — 2건

사례 2-1: 대구~광주 달빛고속철도
- project_name: 대구-광주 달빛고속철도
- project_type: railway
- latitude: 35.5400
- longitude: 127.3300
- address: 전라북도 남원시 인월면

사례 2-2: 수원~인천 광역급행철도
- project_name: 수원-인천 GTX-C 연장
- project_type: railway
- latitude: 37.2630
- longitude: 126.9990
- address: 경기도 수원시 팔달구

### 3. 공항 (airport) — 2건

사례 3-1: 가덕도 신공항
- project_name: 부산 가덕도 신공항
- project_type: airport
- latitude: 35.0830
- longitude: 128.9350
- address: 부산광역시 강서구 가덕도동

사례 3-2: 울릉도 소형공항
- project_name: 울릉도 소형공항
- project_type: airport
- latitude: 37.4840
- longitude: 130.9060
- address: 경상북도 울릉군 울릉읍

### 4. 항만 (port) — 2건

사례 4-1: 광양항 3단계 확장
- project_name: 광양항 컨테이너부두 3단계
- project_type: port
- latitude: 34.9200
- longitude: 127.6950
- address: 전라남도 광양시 태인동

사례 4-2: 제주 한림항 재개발
- project_name: 제주 한림항 재개발
- project_type: port
- latitude: 33.4120
- longitude: 126.2650
- address: 제주특별자치도 제주시 한림읍

### 5. 댐·저수지 (dam) — 2건

사례 5-1: 영주댐 수질개선 사업
- project_name: 영주댐 수질개선 및 활용
- project_type: dam
- latitude: 36.8700
- longitude: 128.7600
- address: 경상북도 영주시 평은면

사례 5-2: 한탄강댐 수력발전
- project_name: 한탄강댐 수력발전시설
- project_type: dam
- latitude: 38.1500
- longitude: 127.1300
- address: 강원특별자치도 철원군 동송읍

### 6. 산업단지 (industrial) — 2건

사례 6-1: 나주 에너지산업단지
- project_name: 나주 에너지신소재 산업단지
- project_type: industrial
- latitude: 34.9380
- longitude: 126.7100
- address: 전라남도 나주시 산포면

사례 6-2: 평택 고덕산업단지
- project_name: 평택 고덕일반산업단지
- project_type: industrial
- latitude: 36.9920
- longitude: 127.1130
- address: 경기도 평택시 고덕면

### 7. 에너지 (energy) — 2건

사례 7-1: 태안 해상풍력발전단지
- project_name: 태안 해상풍력발전단지
- project_type: energy
- latitude: 36.7450
- longitude: 126.2900
- address: 충청남도 태안군 근흥면

사례 7-2: 당진 LNG복합화력발전소
- project_name: 당진 LNG복합화력발전소
- project_type: energy
- latitude: 36.8800
- longitude: 126.6300
- address: 충청남도 당진시 석문면

### 8. 폐기물 (waste) — 2건

사례 8-1: 인천 자원순환센터
- project_name: 인천 서구 자원순환센터
- project_type: waste
- latitude: 37.5560
- longitude: 126.6770
- address: 인천광역시 서구 오류동

사례 8-2: 김해 폐기물매립시설
- project_name: 김해 생곡 폐기물매립시설
- project_type: waste
- latitude: 35.2280
- longitude: 128.8600
- address: 경상남도 김해시 생림면

### 9. 도시개발 (urban_dev) — 2건

사례 9-1: 세종시 6-3생활권
- project_name: 세종 6-3생활권 도시개발
- project_type: urban_dev
- latitude: 36.5350
- longitude: 127.0050
- address: 세종특별자치시 소정면

사례 9-2: 위례신도시 3단계
- project_name: 위례신도시 3단계
- project_type: urban_dev
- latitude: 37.4780
- longitude: 127.1450
- address: 경기도 성남시 수정구

### 10. 주거단지 (housing) — 2건

사례 10-1: 광명 시흥 신도시
- project_name: 광명시흥 공공주택지구
- project_type: housing
- latitude: 37.4180
- longitude: 126.8650
- address: 경기도 광명시 옥길동

사례 10-2: 진주 문산지구
- project_name: 진주 문산지구 공공주택
- project_type: housing
- latitude: 35.1550
- longitude: 128.0480
- address: 경상남도 진주시 문산읍

### 11. 관광단지 (tourism) — 2건

사례 11-1: 강릉 경포 해양관광단지
- project_name: 강릉 경포 해양관광단지
- project_type: tourism
- latitude: 37.7950
- longitude: 128.8960
- address: 강원특별자치도 강릉시 강문동

사례 11-2: 해남 땅끝마을 관광지
- project_name: 해남 땅끝마을 관광지 조성
- project_type: tourism
- latitude: 34.2940
- longitude: 126.5280
- address: 전라남도 해남군 송지면

### 12. 채석·광업 (mining) — 2건

사례 12-1: 포천 석산 개발
- project_name: 포천 관인 석산 개발
- project_type: mining
- latitude: 38.0650
- longitude: 127.1550
- address: 경기도 포천시 관인면

사례 12-2: 영월 석회석 광산 확장
- project_name: 영월 쌍용 석회석광산 확장
- project_type: mining
- latitude: 37.1830
- longitude: 128.4610
- address: 강원특별자치도 영월군 영월읍

### 13. 군사시설 (military) — 2건

사례 13-1: 대구 군 비행장 이전
- project_name: 대구 군공항 이전 사업
- project_type: military
- latitude: 35.8960
- longitude: 128.6540
- address: 경상북도 군위군 소보면

사례 13-2: 백령도 군항 확장
- project_name: 백령도 군항 시설 확장
- project_type: military
- latitude: 37.9680
- longitude: 124.6300
- address: 인천광역시 옹진군 백령면

### 14. 하천·수로 (waterway) — 2건

사례 14-1: 낙동강 하구 복원
- project_name: 낙동강 하구 생태복원 사업
- project_type: waterway
- latitude: 35.0650
- longitude: 128.9430
- address: 부산광역시 사하구 하단동

사례 14-2: 금강 세종보 철거
- project_name: 금강 세종보 해체 및 하천 복원
- project_type: waterway
- latitude: 36.5050
- longitude: 127.0350
- address: 세종특별자치시 연서면

### 15. 매립·간척 (reclamation) — 2건

사례 15-1: 군산 비응도 매립
- project_name: 군산 비응도 산업단지 매립
- project_type: reclamation
- latitude: 35.9850
- longitude: 126.5600
- address: 전북특별자치도 군산시 비응도동

사례 15-2: 목포 남항 매립
- project_name: 목포 남항 매립 및 개발
- project_type: reclamation
- latitude: 34.7800
- longitude: 126.3830
- address: 전라남도 목포시 용해동

### 16. 산지개발 (forest) — 2건

사례 16-1: 양평 친환경 힐링단지
- project_name: 양평 친환경 산림힐링단지
- project_type: forest
- latitude: 37.4910
- longitude: 127.4870
- address: 경기도 양평군 용문면

사례 16-2: 무주 덕유산 리조트 확장
- project_name: 무주 덕유산 리조트 확장
- project_type: forest
- latitude: 35.8930
- longitude: 127.7380
- address: 전북특별자치도 무주군 설천면

### 17. 기타 (other) — 2건

사례 17-1: 전주 대학병원 증축
- project_name: 전북대학교병원 증축 사업
- project_type: other
- latitude: 35.8420
- longitude: 127.1360
- address: 전북특별자치도 전주시 덕진구

사례 17-2: 부산 북항 복합개발
- project_name: 부산 북항 2단계 복합개발
- project_type: other
- latitude: 35.1100
- longitude: 129.0450
- address: 부산광역시 동구 초량동

---

## 수집 데이터 및 결과 문서화

docs/FULL_TYPE_TEST_34.md에 다음 구조로 작성:

### 1. 전체 요약 테이블

| # | 사업유형 | 사례명 | 리스크(C/M/R/I) | 규제 | 유사사례 | 최고유사도 | 검토의견Top3 | 초안(장/섹션) | 품질 | 커넥터 | 패턴건수 | RAG출처 |
|---|---------|--------|----------------|------|---------|-----------|-------------|-------------|------|--------|---------|---------|

### 2. 사업유형별 상세

각 유형(17개)마다:
- 2건의 리스크 카드 목록 (rule_id, severity, title)
- 규제 매칭 목록
- 유사사례 상위 3건 (이름, 유사도)
- 검토의견 Top-5 (항목, 확률%)
- 과거 패턴 (사례수, 보완율, 조건부협의율)
- 초안 섹션 수 / 장 수
- 품질 점수 / 100
- 커넥터 가용 수 / 22
- RAG 답변 길이 / 출처 수

### 3. 품질 검증 기준

| 기준 | 판정 |
|------|------|
| 34건 전부 리스크 1건+ | PASS/FAIL |
| 34건 전부 규제 1건+ | PASS/FAIL |
| 유사사례 이름 None 없음 | PASS/FAIL |
| 유사도 0% 없음 | PASS/FAIL |
| 초안 22섹션/7장 전부 | PASS/FAIL |
| 품질 80점+ 전부 | PASS/FAIL |
| 커넥터 20개+ 전부 | PASS/FAIL |
| 검토의견 유형별 차별화 | PASS/FAIL |

### 4. 발견된 이슈

유형별로 발견된 문제점 정리.

### 5. 유형별 검토의견 차별화 매트릭스

| 유형 | 1순위 | 2순위 | 3순위 |
|------|-------|-------|-------|
| road | ? | ? | ? |
| railway | ? | ? | ? |
| ... | ... | ... | ... |

34건 전부 완료 후 pytest + pnpm build 확인.
```
