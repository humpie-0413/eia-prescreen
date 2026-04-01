"""전체 API 34종 실호출 테스트 스크립트.

기존 22종 + 신규 12종 포함.
양평 좌표 (37.4912, 127.4875) 기준으로 테스트.

Usage:
    python backend/scripts/test_all_apis.py
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

# ── 프로젝트 루트 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Windows stdout 인코딩 ──
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── .env 로드 ──
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

DATA_GO_KR_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
VWORLD_KEY = os.environ.get("VWORLD_API_KEY", "")
ENCODED_KEY = quote(DATA_GO_KR_KEY, safe="")

# ── 양평 좌표 ──
LNG, LAT = 127.4875, 37.4912
TIMEOUT = 15


# ═══════════════════════════════════════════════════════════
# 테스트 결과 저장 구조
# ═══════════════════════════════════════════════════════════

results: list[dict] = []


def test_api(
    idx: int,
    name: str,
    category: str,
    url: str,
    params: dict,
    key_field: str = "serviceKey",
    key_value: str | None = None,
    is_new: bool = False,
    method: str = "GET",
) -> dict:
    """API를 호출하고 결과를 반환한다. Decoding + Encoding 키를 순서대로 시도."""
    actual_key = key_value or DATA_GO_KR_KEY
    result = {
        "idx": idx,
        "name": name,
        "category": category,
        "is_new": is_new,
        "url": url.split("?")[0] if "?" in url else url,
        "status_code": None,
        "data_count": 0,
        "key_type": "decoding",
        "success": False,
        "error": "",
        "response_preview": "",
    }

    if not actual_key and key_field:
        result["error"] = "API 키 없음"
        result["status_code"] = "-"
        return result

    # 1차: Decoding 키
    p = {**params}
    if key_field:
        p[key_field] = actual_key

    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = client.request(method, url, params=p)
            result["status_code"] = resp.status_code

            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                body_text = resp.text[:500]
                result["response_preview"] = body_text[:200]

                if "json" in ct or body_text.strip().startswith(("{", "[")):
                    data = resp.json()
                    count = _count_items(data)
                    result["data_count"] = count
                    result["success"] = True
                    result["key_type"] = "decoding"
                    return result
                elif "xml" in ct or body_text.strip().startswith("<"):
                    # XML 응답 - 에러 확인
                    if "<returnAuthMsg>" in body_text:
                        if "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in body_text:
                            result["error"] = "서비스 키 미등록"
                        elif "INVALID" in body_text.upper():
                            result["error"] = "키 인증 실패"
                        else:
                            result["error"] = "XML 에러 응답"
                    elif "<items" in body_text or "<item>" in body_text:
                        result["success"] = True
                        result["data_count"] = body_text.count("<item>")
                        return result
                    else:
                        # WMS/WFS 성공 응답일 수 있음
                        if "image" in ct or "png" in ct or "tiff" in ct:
                            result["success"] = True
                            result["data_count"] = 1
                            result["response_preview"] = f"Image ({ct}), {len(resp.content)} bytes"
                            return result
                        result["success"] = True
                        result["data_count"] = 0
                        result["response_preview"] = body_text[:200]
                        return result
                elif "image" in ct:
                    result["success"] = True
                    result["data_count"] = 1
                    result["response_preview"] = f"Image ({ct}), {len(resp.content)} bytes"
                    return result
                else:
                    result["success"] = True
                    result["response_preview"] = body_text[:200]
                    return result

            # 500/403 with Decoding key -> try Encoding key
            if resp.status_code in (403, 500) and ENCODED_KEY != actual_key:
                p2 = {**params}
                if key_field:
                    p2[key_field] = ENCODED_KEY
                resp2 = client.request(method, url, params=p2)
                if resp2.status_code == 200:
                    result["status_code"] = 200
                    result["key_type"] = "encoding"
                    ct2 = resp2.headers.get("content-type", "")
                    body2 = resp2.text[:500]
                    result["response_preview"] = body2[:200]
                    if "json" in ct2 or body2.strip().startswith(("{", "[")):
                        data2 = resp2.json()
                        result["data_count"] = _count_items(data2)
                        result["success"] = True
                    elif "image" in ct2:
                        result["success"] = True
                        result["data_count"] = 1
                    else:
                        result["success"] = True
                    return result
                else:
                    result["status_code"] = resp.status_code
                    result["error"] = f"Decoding={resp.status_code}, Encoding={resp2.status_code}"
                    return result

            # Non-200 error
            result["error"] = f"HTTP {resp.status_code}"
            if resp.status_code == 500:
                result["error"] = "서버 장애 (500)"
            elif resp.status_code == 403:
                result["error"] = "키 미승인/미등록 (403)"
            elif resp.status_code == 404:
                result["error"] = "엔드포인트 없음 (404)"
            result["response_preview"] = resp.text[:200]
            return result

    except httpx.TimeoutException:
        result["error"] = "타임아웃"
        result["status_code"] = "T/O"
        return result
    except Exception as e:
        result["error"] = str(e)[:100]
        result["status_code"] = "ERR"
        return result


def _count_items(data: dict | list) -> int:
    """응답에서 데이터 건수를 추출한다."""
    if isinstance(data, list):
        return len(data)
    if not isinstance(data, dict):
        return 0

    # 표준 공공데이터 응답
    if "response" in data:
        body = data["response"].get("body", {})
        tc = body.get("totalCount", 0)
        if tc:
            return int(tc)
        items = body.get("items", {})
        if isinstance(items, dict):
            il = items.get("item", [])
            return len(il) if isinstance(il, list) else (1 if il else 0)
        if isinstance(items, list):
            return len(items)

    # 기타 구조
    if "totalCount" in data:
        return int(data["totalCount"])
    for k in ("items", "item", "data", "results", "features"):
        if k in data and isinstance(data[k], list):
            return len(data[k])

    # getXxx root key
    for k, v in data.items():
        if k.startswith("get") and isinstance(v, dict):
            items = v.get("item", [])
            if isinstance(items, list):
                return len(items)
            if items:
                return 1

    return 0


# ═══════════════════════════════════════════════════════════
# 전체 34종 API 정의
# ═══════════════════════════════════════════════════════════


def run_all_tests():
    """전체 34종 API 테스트를 실행한다."""
    global results
    idx = 0

    print("\n" + "=" * 70)
    print("  전체 API 34종 실호출 테스트")
    print(f"  좌표: ({LAT}, {LNG}) 양평")
    print(f"  시각: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    # ─── 기존 22종 ───────────────────────────────────────

    print(">>> 기존 22종 재테스트\n")

    # 1. 토지이용규제정보
    idx += 1
    r = test_api(idx, "토지이용규제정보", "토지",
        "https://apis.data.go.kr/1611000/nsdi/LandUseService/attr/getLandUseAttr",
        {"format": "json", "numOfRows": 10, "pageNo": 1})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 2. 에어코리아 시도별
    idx += 1
    r = test_api(idx, "에어코리아 시도별", "대기",
        "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
        {"sidoName": "경기", "returnType": "json", "numOfRows": 10, "pageNo": 1, "ver": "1.0"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 3. 에어코리아 근접측정소
    idx += 1
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2097", always_xy=True)
    tm_x, tm_y = tr.transform(LNG, LAT)
    r = test_api(idx, "에어코리아 근접측정소", "대기",
        "https://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getNearbyMsrstnList",
        {"tmX": f"{tm_x:.6f}", "tmY": f"{tm_y:.6f}", "returnType": "json", "ver": "1.1"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 4. 에어코리아 측정소별 실시간
    idx += 1
    r = test_api(idx, "에어코리아 측정소별", "대기",
        "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty",
        {"stationName": "양평읍", "dataTerm": "DAILY", "returnType": "json", "numOfRows": 1, "pageNo": 1, "ver": "1.0"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 5. 수질측정망
    idx += 1
    r = test_api(idx, "수질측정망", "수질",
        "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList",
        {"resultType": "json", "numOfRows": 10, "pageNo": 1})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 6. 소음진동
    idx += 1
    r = test_api(idx, "소음진동정보", "소음",
        "https://apis.data.go.kr/B553748/noisevibrationinformaiton/getListNoisevibrationInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 7. 토양정보
    idx += 1
    r = test_api(idx, "토양정보", "토양",
        "https://apis.data.go.kr/B553748/soilinformation/getListSoilInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 8. 인구주택
    idx += 1
    r = test_api(idx, "인구주택정보", "인구",
        "https://apis.data.go.kr/B553748/populationhousinginformation/getListPopulationHousingInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 9. 사업지역
    idx += 1
    r = test_api(idx, "사업지역정보", "환평",
        "https://apis.data.go.kr/B553748/projectareainformation/getListProjectAreaInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 10. 환평정보
    idx += 1
    r = test_api(idx, "환평정보", "환평",
        "https://apis.data.go.kr/B553748/eiainformation/getListEiaInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 11. 해양환경
    idx += 1
    r = test_api(idx, "해양환경정보", "해양",
        "https://apis.data.go.kr/B553748/marineenvironmentinformation/getListMarineEnvironmentInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 12. 지질정보
    idx += 1
    r = test_api(idx, "지질정보", "지질",
        "https://apis.data.go.kr/B553748/geologyinformation/getListGeologyInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 13. 온실가스
    idx += 1
    r = test_api(idx, "온실가스정보", "GHG",
        "https://apis.data.go.kr/B553748/greenhousegasinformation/getListGreenhouseGasInformation",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 14. 교통량
    idx += 1
    r = test_api(idx, "교통량", "교통",
        "https://apis.data.go.kr/B553755/TrafficVolumeService/getTrafficVolume",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 15. 기상(종관)
    idx += 1
    r = test_api(idx, "기상(ASOS)", "기상",
        "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList",
        {"stnId": "114", "dataCd": "ASOS", "dateCd": "HR",
         "startDt": "20260327", "startHh": "00", "endDt": "20260327", "endHh": "23",
         "numOfRows": 10, "pageNo": 1, "dataType": "JSON"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 16. 문화재
    idx += 1
    r = test_api(idx, "문화재", "문화",
        "https://apis.data.go.kr/1360000/CulturalHeritage/getListCulturalHeritage",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 17. 경관
    idx += 1
    r = test_api(idx, "경관정보", "경관",
        "https://apis.data.go.kr/1613000/LandscapeService/getLandscapeInfo",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "returnType": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 18. 생태자연도 (mcee)
    idx += 1
    r = test_api(idx, "생태자연도(MCEE)", "생태",
        "https://aid.mcee.go.kr/api/eco",
        {"lng": LNG, "lat": LAT, "buffer": 1000, "format": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 19. V-world WFS 연속지적도
    idx += 1
    bbox = f"{LNG-0.01},{LAT-0.01},{LNG+0.01},{LAT+0.01}"
    r = test_api(idx, "V-world WFS 지적도", "토지",
        "https://api.vworld.kr/req/wfs",
        {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
         "typeName": "lt_c_landinfobasemap", "bbox": bbox,
         "srsName": "EPSG:4326", "output": "application/json", "maxFeatures": 5},
        key_field="key", key_value=VWORLD_KEY)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 20. EIASS 사업목록
    idx += 1
    r = test_api(idx, "EIASS 사업목록", "환평",
        "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaInfoList",
        {"bizYr": "2024", "numOfRows": 5, "pageNo": 1, "type": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 21. EIASS 협의현황
    idx += 1
    r = test_api(idx, "EIASS 협의현황", "환평",
        "https://apis.data.go.kr/1480523/EiaConsltSvc/getEiaConsltList",
        {"numOfRows": 5, "pageNo": 1, "type": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 22. EIASS 결정내용
    idx += 1
    r = test_api(idx, "EIASS 결정내용", "환평",
        "https://apis.data.go.kr/1480523/EiaDecsnSvc/getEiaDecsnList",
        {"numOfRows": 5, "pageNo": 1, "type": "json"})
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # ─── 신규 12종 ───────────────────────────────────────

    print("\n>>> 신규 12종 첫 테스트\n")

    # 23. 환평 동식물상정보
    idx += 1
    r = test_api(idx, "환평 동식물상정보", "생태",
        "https://apis.data.go.kr/1480523/FloraFaunaService/getFloraFaunaList",
        {"numOfRows": 10, "pageNo": 1, "type": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 24. 환평 악취정보
    idx += 1
    r = test_api(idx, "환평 악취정보", "대기",
        "https://apis.data.go.kr/1480523/OdorService/getOdorList",
        {"numOfRows": 10, "pageNo": 1, "type": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 25. 환평 수리수문정보
    idx += 1
    r = test_api(idx, "환평 수리수문정보", "수질",
        "https://apis.data.go.kr/1480523/HydroService/getHydroList",
        {"numOfRows": 10, "pageNo": 1, "type": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 26. 환평 위생공중보건정보
    idx += 1
    r = test_api(idx, "환평 위생보건정보", "보건",
        "https://apis.data.go.kr/1480523/HealthService/getHealthList",
        {"numOfRows": 10, "pageNo": 1, "type": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 27. 환평 친환경자원순환정보
    idx += 1
    r = test_api(idx, "환평 자원순환정보", "폐기물",
        "https://apis.data.go.kr/1480523/RecycleService/getRecycleList",
        {"numOfRows": 10, "pageNo": 1, "type": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 28. 국립생태원 습지평가
    idx += 1
    r = test_api(idx, "국립생태원 습지평가", "생태",
        "https://apis.data.go.kr/B553980/WetlandAssessmentService/getWetlandAssessmentList",
        {"numOfRows": 10, "pageNo": 1, "resultType": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 29. 국립생태원 지형평가
    idx += 1
    r = test_api(idx, "국립생태원 지형평가", "생태",
        "https://apis.data.go.kr/B553980/TopographyAssessmentService/getTopographyAssessmentList",
        {"numOfRows": 10, "pageNo": 1, "resultType": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 30. V-world 자연환경보전지역
    idx += 1
    r = test_api(idx, "V-world 자연환경보전", "토지",
        "https://api.vworld.kr/req/data",
        {"data": "LT_C_UQ114", "geomFilter": f"POINT({LNG} {LAT})",
         "buffer": 1000, "domain": "localhost",
         "request": "GetFeature", "size": 10, "page": 1},
        key_field="key", key_value=VWORLD_KEY, is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 31. 한국환경연구원 야생생물보호구역
    idx += 1
    r = test_api(idx, "환경연구원 야생보호구역", "생태",
        "https://apis.data.go.kr/B553798/WildlifeProtectedAreaService/getWildlifeProtectedAreaList",
        {"numOfRows": 10, "pageNo": 1, "resultType": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 32. 해양수산부 해양환경 영향평가정보
    idx += 1
    r = test_api(idx, "해수부 해양환경영향평가", "해양",
        "https://apis.data.go.kr/1192000/MarineEnvironmentService/getMarineEnvironmentList",
        {"numOfRows": 10, "pageNo": 1, "resultType": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 33. 해양수산부 환경영향평가정보 서비스
    idx += 1
    r = test_api(idx, "해수부 환경영향평가정보", "해양",
        "https://apis.data.go.kr/1192000/EiaService/getEiaList",
        {"numOfRows": 10, "pageNo": 1, "resultType": "json"},
        is_new=True)
    results.append(r)
    _print_result(r)
    time.sleep(1)

    # 34. 환경공간정보 토지피복지도 WMS
    idx += 1
    # EPSG:3857 좌표 변환
    from pyproj import Transformer as T3
    tr3857 = T3.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    x, y = tr3857.transform(LNG, LAT)
    bbox_3857 = f"{x-500},{y-500},{x+500},{y+500}"
    r = test_api(idx, "환경공간정보 토지피복WMS", "토지",
        "https://api.mcee.go.kr/geoserver/wms",
        {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
         "LAYERS": "EGIS:lv3_2025y", "SRS": "EPSG:3857",
         "BBOX": bbox_3857, "WIDTH": 256, "HEIGHT": 256,
         "FORMAT": "image/png"},
        key_field="", is_new=True)
    results.append(r)
    _print_result(r)

    # ─── 결과 출력 ───────────────────────────────────────
    print_summary()
    save_results()


def _print_result(r: dict):
    """개별 결과를 한 줄로 출력."""
    tag = "[NEW]" if r["is_new"] else "     "
    status = "OK" if r["success"] else "FAIL"
    emoji = "+" if r["success"] else "-"
    key_info = f"({r['key_type']})" if r["success"] else ""
    count = f"{r['data_count']}건" if r["success"] else r["error"]
    sc = str(r['status_code'])
    print(f"  [{emoji}] {tag} #{r['idx']:02d} {r['name']:<22s} {sc:>5s}  {count}  {key_info}")


def print_summary():
    """결과 테이블 출력."""
    print("\n" + "=" * 90)
    print("  결과 요약")
    print("=" * 90)

    # 분류별 집계
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    new_success = sum(1 for r in results if r["success"] and r["is_new"])
    old_success = sum(1 for r in results if r["success"] and not r["is_new"])

    print(f"\n  전체: {len(results)}종")
    print(f"  성공: {success_count}종 (기존 {old_success} + 신규 {new_success})")
    print(f"  실패: {fail_count}종")

    # 성공 목록
    print(f"\n  {'─' * 86}")
    print(f"  {'#':>3s}  {'상태':^6s}  {'구분':^5s}  {'이름':<24s}  {'코드':>5s}  {'건수':>6s}  {'키':^10s}  {'분류':<8s}")
    print(f"  {'─' * 86}")
    for r in results:
        tag = "신규" if r["is_new"] else "기존"
        status = " OK " if r["success"] else "FAIL"
        key_info = r["key_type"] if r["success"] else "-"
        count_str = str(r["data_count"]) if r["success"] else "-"
        err = r["error"][:20] if not r["success"] else ""
        print(f"  {r['idx']:>3d}  {status:^6s}  {tag:^5s}  {r['name']:<24s}  {str(r['status_code']):>5s}  {count_str:>6s}  {key_info:^10s}  {r['category']:<8s}  {err}")

    # 실패 원인별 분류
    print(f"\n  {'─' * 60}")
    print("  실패 원인별 분류:")
    error_groups: dict[str, list[str]] = {}
    for r in results:
        if not r["success"]:
            cause = _classify_error(r)
            error_groups.setdefault(cause, []).append(r["name"])

    for cause, names in error_groups.items():
        print(f"    [{cause}] ({len(names)}종)")
        for n in names:
            print(f"      - {n}")

    print(f"\n{'=' * 90}")


def _classify_error(r: dict) -> str:
    """에러를 원인별로 분류."""
    err = r["error"].lower()
    code = str(r["status_code"])

    if "500" in code or "서버 장애" in err:
        return "서버 장애"
    if "403" in code or "미승인" in err or "미등록" in err:
        return "키 미승인/미등록"
    if "404" in code or "엔드포인트" in err:
        return "엔드포인트 없음"
    if "타임아웃" in err:
        return "타임아웃"
    if "키 없음" in err:
        return "API 키 미설정"
    if "xml" in err or "인증" in err:
        return "파라미터/인증 문제"
    return "기타"


def save_results():
    """결과를 JSON 파일로 저장."""
    out_path = PROJECT_ROOT / "data" / "bulk" / "api_test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    serializable = []
    for r in results:
        s = {**r}
        s["status_code"] = str(s["status_code"])
        serializable.append(s)

    out_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  결과 저장: {out_path}")


if __name__ == "__main__":
    run_all_tests()
