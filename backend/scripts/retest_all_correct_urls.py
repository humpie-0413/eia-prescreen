"""32개 API 전체 재테스트 — 공공데이터포털 상세페이지 기준 정확한 URL."""
import sys
import asyncio
import json
import os
import re
from pathlib import Path

import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

KEY = os.environ.get("DATA_GO_KR_API_KEY", "")

# 협의목록에서 가져온 실제 사업코드
SAMPLE_PER_CD = "WJ20260063"
SAMPLE_BIZ_SEQ = "103964"

results = []


def record(num, name, old_url, new_url, old_status, new_status, code, count, detail=""):
    results.append({
        "num": num, "name": name,
        "old_url": old_url, "new_url": new_url,
        "old_status": old_status, "new_status": new_status,
        "code": code, "count": count, "detail": detail,
    })
    icon = "OK" if "SUCCESS" in new_status else ("NODATA" if "NODATA" in new_status else "FAIL")
    print(f"  [{icon:6s}] {num:>2s}. {name[:35]:35s} | {code:>3s} | cnt={str(count):>5s} | {detail[:60]}")


async def test_api(client, num, name, url, params, old_url="", old_status="FAIL 500"):
    """단일 API 테스트."""
    try:
        r = await client.get(url, params=params)
        sc = r.status_code
        ct = r.headers.get("content-type", "")
        body = r.text[:1000]

        # 결과 파싱
        count = 0
        status = f"HTTP {sc}"
        detail = ""

        if sc == 200:
            if "json" in ct:
                try:
                    j = r.json()
                    # data.go.kr JSON 구조
                    resp = j.get("response", {})
                    header = resp.get("header", {})
                    rc = header.get("resultCode", "")
                    rm = header.get("resultMsg", "")
                    b = resp.get("body", {})
                    tc = b.get("totalCount", 0)
                    items = b.get("items", {})
                    if isinstance(items, dict):
                        item_list = items.get("item", [])
                    elif isinstance(items, list):
                        item_list = items
                    else:
                        item_list = []
                    if isinstance(item_list, dict):
                        item_list = [item_list]

                    if rc == "00":
                        count = tc if tc else len(item_list)
                        status = "SUCCESS" if count > 0 else "NODATA"
                        detail = f"resultCode=00, totalCount={tc}, items={len(item_list)}"
                    else:
                        status = f"ERROR rc={rc}"
                        detail = f"{rc}: {rm}"
                except Exception:
                    # plain JSON but not standard format
                    if '"totalCount"' in body:
                        m = re.search(r'"totalCount"\s*:\s*(\d+)', body)
                        tc = int(m.group(1)) if m else 0
                        count = tc
                        status = "SUCCESS" if tc > 0 else "NODATA"
                        detail = f"totalCount={tc}"
                    else:
                        status = "JSON_PARSE"
                        detail = body[:80]
            else:
                # XML response
                if "resultCode>00<" in body or "<resultCode>00</resultCode>" in body:
                    m = re.search(r"<totalCount>(\d+)</totalCount>", body)
                    tc = int(m.group(1)) if m else 0
                    count = tc
                    status = "SUCCESS_XML" if tc > 0 else "NODATA_XML"
                    detail = f"XML resultCode=00, totalCount={tc}"
                elif "resultCode>11<" in body or "NO_MANDATORY" in body:
                    status = "MISSING_PARAM"
                    m = re.search(r"<resultMsg>([^<]+)</resultMsg>", body)
                    detail = m.group(1) if m else "NO_MANDATORY_PARAM"
                elif "resultCode>12<" in body:
                    status = "NO_DATA"
                    detail = "resultCode=12 (해당 데이터 없음)"
                elif "resultCode>20<" in body or "SERVICE_ACCESS_DENIED" in body:
                    status = "ACCESS_DENIED"
                    detail = "SERVICE_ACCESS_DENIED (미신청 또는 미승인)"
                elif "resultCode>22<" in body:
                    status = "LIMIT_EXCEEDED"
                    detail = "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"
                elif "resultCode>30<" in body:
                    status = "EXPIRED"
                    detail = "SERVICE_KEY_EXPIRED"
                elif "<items>" in body or "<item>" in body:
                    m = re.search(r"<totalCount>(\d+)</totalCount>", body)
                    tc = int(m.group(1)) if m else 0
                    count = tc
                    status = "SUCCESS_XML" if tc > 0 else "NODATA_XML"
                    detail = f"XML items found, totalCount={tc}"
                else:
                    status = f"XML_OTHER"
                    detail = body[:100].replace("\n", " ")
        elif sc == 201:
            if "NO_MANDATORY" in body:
                status = "MISSING_PARAM_201"
                detail = "201 NO_MANDATORY (필수 파라미터 누락)"
            else:
                status = f"HTTP_201"
                detail = body[:100]
        elif sc == 403:
            status = "FORBIDDEN"
            detail = "403 접근 거부 (키 미신청)"
        elif sc == 404:
            status = "NOT_FOUND"
            detail = "404 엔드포인트 없음"
        elif sc == 500:
            status = "SERVER_500"
            detail = body[:100].replace("\n", " ")
        else:
            detail = body[:100].replace("\n", " ")

        record(num, name, old_url, url, old_status, status, str(sc), count, detail)

    except Exception as e:
        record(num, name, old_url, url, old_status, "EXCEPTION", "ERR", 0, str(e)[:80])


async def main():
    print(f"\nAPI Key: {KEY[:8]}...{KEY[-8:]}")
    print(f"Sample perCd: {SAMPLE_PER_CD}, bizSeq: {SAMPLE_BIZ_SEQ}\n")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:

        # ================================================================
        # 1. 토지이용규제
        # ================================================================
        print("=" * 90)
        print("  [A] 독립 API — 토지/기상/교통/생활")
        print("=" * 90)

        await test_api(c, "1", "토지이용규제정보",
            "https://apis.data.go.kr/1613000/arLandUseInfoService/DTarLandUseInfo",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "pnu": "4183025330"},
            old_url="1611000/nsdi/LandUseService/attr/getLandUseAttr",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        # ================================================================
        # 2-3. 에어코리아
        # ================================================================
        await test_api(c, "2a", "에어코리아 시도별 대기",
            "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
            {"serviceKey": KEY, "returnType": "json", "numOfRows": 5, "pageNo": 1,
             "sidoName": "경기"},
            old_url="B552584/ArpltnInforInqireSvc (동일)",
            old_status="SUCCESS")
        await asyncio.sleep(0.3)

        await test_api(c, "2b", "에어코리아 측정소별 대기",
            "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty",
            {"serviceKey": KEY, "returnType": "json", "numOfRows": 5, "pageNo": 1,
             "stationName": "양평읍"},
            old_url="B552584/ArpltnInforInqireSvc (동일)",
            old_status="SUCCESS")
        await asyncio.sleep(0.3)

        await test_api(c, "3", "에어코리아 근접측정소",
            "https://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getNearbyMsrstnList",
            {"serviceKey": KEY, "returnType": "json",
             "tmX": "294029", "tmY": "505864"},
            old_url="B552584/MsrstnInfoInqireSvc (동일)",
            old_status="SUCCESS")
        await asyncio.sleep(0.3)

        # ================================================================
        # 4. 수질DB
        # ================================================================
        await test_api(c, "4", "수질DB (물환경정보)",
            "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="1480523/WaterQualityService (동일)",
            old_status="SUCCESS (고정데이터)")
        await asyncio.sleep(0.3)

        # ================================================================
        # 5. 토양측정망 (NEW URL)
        # ================================================================
        await test_api(c, "5", "토양측정망",
            "https://apis.data.go.kr/1480523/SgisSoAPI/getSgisSoList",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="B553748/soilinformation/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.3)

        # ================================================================
        # 6. 기상청 ASOS
        # ================================================================
        await test_api(c, "6", "기상청 ASOS 일자료",
            "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "dataType": "JSON",
             "dataCd": "ASOS", "dateCd": "DAY",
             "startDt": "20250101", "endDt": "20250107", "stnIds": "108"},
            old_url="1360000/AsosHourlyInfoService/getWthrDataList",
            old_status="FAIL 403")
        await asyncio.sleep(0.3)

        # ================================================================
        # 7. 교통량
        # ================================================================
        print("\n" + "=" * 90)
        print("  [B] 독립 API — 교통/폐기물")
        print("=" * 90)

        await test_api(c, "7", "교통량 통계",
            "https://apis.data.go.kr/1613000/KictTmsStat/getTmsStatInfo",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "statsYear": "2023"},
            old_url="B553755/TrafficVolumeService/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.3)

        # ================================================================
        # 8. 생활쓰레기
        # ================================================================
        await test_api(c, "8", "생활쓰레기 정보",
            "https://apis.data.go.kr/1741000/household_waste_info/info",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="(없음)",
            old_status="(미테스트)")
        await asyncio.sleep(0.3)

        # ================================================================
        # 9-11. 국립생태원 (B553084)
        # ================================================================
        print("\n" + "=" * 90)
        print("  [C] 국립생태원 B553084 — 생태자연도/습지/지형")
        print("=" * 90)

        await test_api(c, "9", "생태자연도",
            "https://apis.data.go.kr/B553084/ecoapi/EcologyzmpService/getEcologyzmpInfo",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="B553982/ecoGrade/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        await test_api(c, "10", "습지평가",
            "https://apis.data.go.kr/B553084/ecoapi/SmldevalService/getSmldevalInfo",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="B553982/wetland/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        await test_api(c, "11", "지형평가",
            "https://apis.data.go.kr/B553084/ecoapi/TpgrphevalService/getTpgrphevalInfo",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
            old_url="B553982/terrain/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        # ================================================================
        # 12-25. 환평 1480523 계열 (환경영향평가 정보)
        # ================================================================
        print("\n" + "=" * 90)
        print("  [D] 환평 1480523 — 주제별 환경정보 (perCd/bizSeq 필요)")
        print("=" * 90)

        eiass_1480523 = [
            ("12", "환평 토지이용", "LandUseService", "getLandUse",
             {"perCd": SAMPLE_PER_CD}),
            ("13", "환평 동식물상", "FlorafaunaService", "getFlorafauna",
             {"perCd": SAMPLE_PER_CD}),
            ("14", "환평 소음진동", "NoiseVibrationService", "getNoiseVibration",
             {"perCd": SAMPLE_PER_CD}),
            ("15", "환평 사업구역", "BsnsAreaService", "getBsnsArea",
             {"perCd": SAMPLE_PER_CD}),
            ("16", "환평 인구주거", "PopulationService", "getPopulation",
             {"perCd": SAMPLE_PER_CD}),
            ("17", "환평 온실가스", "GreenhouseGasService", "getGreenhouseGas",
             {"perCd": SAMPLE_PER_CD}),
            ("18", "환평 지형지질", "GeologicalService", "getGeological",
             {"perCd": SAMPLE_PER_CD}),
            ("19", "환평 해양환경", "MaritimeService", "getIvstg",
             {"perCd": SAMPLE_PER_CD}),
            ("20", "환평 악취", "FoulsmellService", "getFoulsmell",
             {"perCd": SAMPLE_PER_CD}),
            ("21", "환평 위생공중보건", "SntPblhService", "getSntPblh",
             {"perCd": SAMPLE_PER_CD}),
            ("22", "환평 친환경자원순환", "EcocycleService", "getEcocycle",
             {"perCd": SAMPLE_PER_CD}),
            ("23", "환평 수리수문", "HydraulicsService", "getRiver",
             {"perCd": SAMPLE_PER_CD}),
            ("24", "환평 수질", "WaterQualityInfoService", "getWaterQuality",
             {"perCd": SAMPLE_PER_CD}),
            ("25", "환평 대기질", "AtmosphereService", "getAtmosphere",
             {"perCd": SAMPLE_PER_CD}),
        ]

        for num, name, svc, op, extra in eiass_1480523:
            url = f"https://apis.data.go.kr/1480523/{svc}/{op}"
            params = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}
            params.update(extra)
            old = f"B553748/... or 1480523/{svc}"
            await test_api(c, num, name, url, params,
                          old_url=old, old_status="FAIL 500")
            await asyncio.sleep(0.5)

        # ================================================================
        # 26-30. 환평 사업관리 계열
        # ================================================================
        print("\n" + "=" * 90)
        print("  [E] 환평 1480523 — 사업/협의 정보조회")
        print("=" * 90)

        await test_api(c, "26", "환평 정보서비스 (사업목록)",
            "https://apis.data.go.kr/1480523/EnvrnAffcEvlBsnsInfoInqireService/getEnvrnAffcEvlBsnsInfoInqire",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
            old_url="1480523/EiaInfoSvc/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        await test_api(c, "27", "환평 협의현황",
            "https://apis.data.go.kr/1480523/EnvrnAffcEvlDscssSttusInfoInqireService/getEnvrnAffcEvlDscssSttusInfoInqire",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
            old_url="1480523/EiaConsltSvc/...",
            old_status="FAIL 500")
        await asyncio.sleep(0.5)

        await test_api(c, "28", "환평 결정내용",
            "https://apis.data.go.kr/1480523/EnvrnAffcEvlDecsnCnInfoInqireService/getEnvrnAffcEvlDecsnCnInfoInqire",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
            old_url="(미테스트)",
            old_status="(미테스트)")
        await asyncio.sleep(0.5)

        await test_api(c, "29", "환평 초안공람",
            "https://apis.data.go.kr/1480523/EnvrnAffcEvlDraftDsplayInfoInqireService/getEnvrnAffcEvlDraftDsplayInfoInqire",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
            old_url="(미테스트)",
            old_status="(미테스트)")
        await asyncio.sleep(0.5)

        await test_api(c, "30", "사전/전략/소규모 협의목록",
            "https://apis.data.go.kr/1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService/getBsnsStrtgySmallScaleDscssListInfoInqire",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
            old_url="1480523/BeffatStrtgy... (동일)",
            old_status="SUCCESS (9973건)")
        await asyncio.sleep(0.5)

        # ================================================================
        # 31-32. 해양수산부 1192000
        # ================================================================
        print("\n" + "=" * 90)
        print("  [F] 해양수산부 1192000")
        print("=" * 90)

        await test_api(c, "31", "해양수산부 환경영향평가",
            "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo",
            {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 5, "resultType": "json",
             "ACP_YEAR": "2014"},
            old_url="1192000/service/EnvImpactService (동일)",
            old_status="PARTIAL (2011-14,17)")
        await asyncio.sleep(0.5)

        await test_api(c, "32", "해양수산부 해양환경영향평가",
            "https://apis.data.go.kr/1192000/service/OceansEnvImpactService1/getOceansEnvImpactInfo1",
            {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 5, "resultType": "json"},
            old_url="(미테스트)",
            old_status="(미테스트)")
        await asyncio.sleep(0.3)

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 90)
    print("  FINAL SUMMARY")
    print("=" * 90)

    success = [r for r in results if "SUCCESS" in r["new_status"]]
    nodata = [r for r in results if "NODATA" in r["new_status"] or "NO_DATA" in r["new_status"]]
    fail = [r for r in results if r not in success and r not in nodata]

    print(f"\n  SUCCESS: {len(success)}  |  NODATA: {len(nodata)}  |  FAIL: {len(fail)}")

    print(f"\n  === SUCCESS ({len(success)}) ===")
    for r in success:
        print(f"    {r['num']:>3s}. {r['name'][:30]:30s} | cnt={r['count']} | {r['detail'][:50]}")

    print(f"\n  === NODATA ({len(nodata)}) ===")
    for r in nodata:
        print(f"    {r['num']:>3s}. {r['name'][:30]:30s} | {r['detail'][:60]}")

    print(f"\n  === FAIL ({len(fail)}) ===")
    for r in fail:
        print(f"    {r['num']:>3s}. {r['name'][:30]:30s} | {r['new_status']:20s} | {r['detail'][:50]}")

    # 이전 vs 현재 비교 표
    print(f"\n{'=' * 90}")
    print(f"  STATUS CHANGE TABLE")
    print(f"{'=' * 90}")
    print(f"  {'#':>3s} | {'API명':30s} | {'이전':18s} | {'현재':18s} | {'건수':>5s}")
    print(f"  {'-'*3} | {'-'*30} | {'-'*18} | {'-'*18} | {'-'*5}")
    for r in results:
        changed = "***" if r["old_status"][:4] != r["new_status"][:4] else "   "
        print(f"  {r['num']:>3s} | {r['name'][:30]:30s} | {r['old_status'][:18]:18s} | {r['new_status'][:18]:18s} | {str(r['count']):>5s} {changed}")

    # Save
    out = PROJECT_ROOT / "data" / "bulk" / "api_retest_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Results saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
