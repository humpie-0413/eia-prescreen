# 신규 API 실연동 — Claude Code 실행 프롬프트

> 이 문서의 프롬프트를 Claude Code에 붙여넣어 실행
> 기존 껍데기 커넥터를 실제 API로 교체하는 작업

---

## 확보된 데이터 현황

| # | 데이터 | 형태 | API 키 / 파일 | 상태 |
|---|--------|------|--------------|------|
| 1 | K-water 수문 | Open API | 기존 DATA_GO_KR_API_KEY | ✅ 승인 |
| 2 | 해양조사원 14종 | Open API | `9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f` | ✅ 승인 |
| 3 | 폐기물 통계 | Open API | `EMALO3I5ZSRJHZWJ42LUJS5NZ82GCDSH83IMHIDMHX58L` | ✅ 승인 |
| 4 | 멸종위기종 | CSV | `data/static/endangered_species.csv` (267종, I급60/II급207) | ✅ 다운로드 완료 |

---

## 프롬프트 (한번에 실행)

```
4개 커넥터를 실제 API로 교체해줘. 기존 껍데기 코드를 실제 데이터가 반환되도록 수정.

## 1. hydrology.py — K-water 수문 운영 정보 (실연동)

기존 connectors/hydrology.py를 실제 API로 교체:

- Base URL: http://apis.data.go.kr/B500001/dam/sluicePresentCondition
- 오퍼레이션 3개:
  - /mntlist (10분 주기)
  - /hourlist (시간 주기)  ← 이것 사용
  - /delist (일 주기)
- 인증: serviceKey = 기존 DATA_GO_KR_API_KEY (.env에 이미 있음)
- 요청 파라미터: damcode, stdt, eddt, pageNo, numOfRows, _type=json
- 제공 항목: 댐수위[EL.m], 강우량[mm], 유입량[㎥/sec], 총방류량[㎥/sec], 저수량[백만㎥], 저수율[%]

구현:
1. 좌표 기반으로 가장 가까운 댐/보 코드(damcode) 매칭
   - data/static/kwater_dam_codes.json 생성: 주요 댐 20개의 이름/좌표/damcode 목록
   - 소양강댐, 충주댐, 합천댐, 안동댐, 임하댐, 남강댐, 횡성댐, 용담댐, 섬진강댐, 주암댐,
     보령댐, 대청댐, 영천댐, 밀양댐, 부안댐, 군위댐, 성덕댐, 달방댐, 장흥댐, 수어댐
2. 하버사인 거리로 50km 이내 가장 가까운 댐 선택
3. 최근 7일 hourlist 조회
4. 정규화: dam_name, water_level_m, rainfall_mm, inflow_m3s, discharge_m3s, storage_mcm, storage_rate_pct

## 2. ocean.py — 해양조사원 (실연동)

기존 connectors/ocean.py를 실제 API로 교체:

.env에 추가할 키:
KHOA_API_KEY=9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f

사용할 핵심 API 3개:

(a) 조위관측소 실측·예측 조위
- Endpoint: https://apis.data.go.kr/1192136/surveyTideLevelAPI/GetSurveyTideLevelApiService
- 파라미터: ServiceKey, obs_code(관측소코드), date(YYYYMMDD), resultType=json

(b) 해양관측부이 최신 관측데이터
- 수온, 염분, 파고, 유향, 유속 등 제공

(c) 조류예보(시계열)
- 유향, 유속, 시각 제공

(d) 자연과학용 수심정보
- 좌표 기반 수심 조회

구현:
1. data/static/khoa_stations.json 생성: 주요 조위관측소 30개의 이름/좌표/obs_code
   - 인천, 평택, 군산, 목포, 완도, 여수, 통영, 부산, 울산, 포항, 묵호, 속초 등
2. 좌표 기반 50km 이내 가장 가까운 관측소 선택
3. 조위 + 수온 + 조류 데이터 조회 (가용한 것만)
4. 정규화: station_name, tide_level_cm, water_temp_c, current_dir, current_speed, wave_height_m, depth_m

## 3. waste_data.py — 폐기물 통계 (실연동)

기존 connectors/waste_data.py를 실제 API로 교체:

.env에 추가할 키:
WASTE_API_KEY=EMALO3I5ZSRJHZWJ42LUJS5NZ82GCDSH83IMHIDMHX58L
WASTE_API_USERID=sungjae  (실제 사용자 ID로 교체 필요)

- Endpoint: http://www.recycling-info.or.kr/sds/JsonApi.do
- 파라미터: PID, YEAR, USRID, KEY
- PID 정책 (2020년 이후): NTN001~NTN070
- 응답: result(상태), dataHeader(컬럼매핑), data(실데이터), searchOption(PID목록)
- 에러: E005(분당100회초과), E006(일3000회초과), E099(데이터없음)

구현:
1. 좌표 → 시도/시군구 변환 (기존 V-world 역지오코딩 활용)
2. 해당 시군구의 폐기물 발생량/처리량 조회 (YEAR=2023, PID=NTN001)
3. dataHeader로 영문키→국문 매핑
4. 정규화: region, total_waste_ton, recycled_ton, incinerated_ton, landfill_ton, recycling_rate_pct
5. rate limit 대응: 1초 sleep, E005/E006 시 30초 대기 후 재시도

## 4. species.py — 멸종위기종 CSV (실데이터)

기존 connectors/species.py를 실제 CSV로 교체:

- 파일: /mnt/user-data/uploads/기후에너지환경부_국립생물자원관_한국의_멸종위기종_20241231_.csv
- 인코딩: EUC-KR
- 컬럼: 분류군, 등급(I/II), 국명, 학명, 고유종, 국가적색목록, 세계자연보전연맹
- 총 267종 (I급 60종, II급 207종)

구현:
1. CSV를 data/static/endangered_species.csv로 복사 (UTF-8 변환)
2. 시작 시 CSV 로딩 → 메모리 캐시
3. 좌표 기반 검색은 불가 (위치 정보 없음)
   → 대신 생태자연도 등급과 조합하여 "이 지역에서 발견 가능한 종" 추정
   → 생태자연도 1등급 지역: I급 전체 + II급 주요종 표시
   → 생태자연도 2등급 지역: II급 일부 표시
4. 정규화: species_list[{name, scientific_name, grade, taxon, red_list_kr, red_list_iucn}]
5. ecology.py의 spatial_data에 species 키로 통합

## 공통 작업

1. .env.example에 KHOA_API_KEY, WASTE_API_KEY, WASTE_API_USERID 추가
2. data_fetcher.py에서 4개 커넥터가 실제 API 호출하도록 확인
3. 각 커넥터에 3-tier 캐시 적용 (실시간 → 스냅샷 캐시 → 빈 데이터)
4. 기술문서 /mnt/user-data/uploads/기술문서_한국수자원공사_수문_운영_정보_v1_5_1.docx 참조

pytest + pnpm build 확인.
CLAUDE.md에 실연동 커넥터 수 갱신.
```
