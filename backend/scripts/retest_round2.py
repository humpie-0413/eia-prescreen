"""2차 재테스트 — 파라미터 수정 + operation name 탐색."""
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
SAMPLE_PER_CD = "WJ20260063"
SAMPLE_BIZ_SEQ = "103964"

results = []


def show(tag, name, sc, detail):
    icon = "OK" if "OK" in tag else ("??" if "??" in tag else "XX")
    print(f"  [{icon:2s}] {name[:45]:45s} | {sc:>3} | {detail[:70]}")


async def try_get(client, name, url, params):
    """GET 요청 후 결과 출력."""
    try:
        r = await client.get(url, params=params)
        sc = r.status_code
        body = r.text[:500]
        ct = r.headers.get("content-type", "")

        # Quick analysis
        if sc == 404:
            show("XX", name, sc, "404 NOT FOUND")
            return sc, "404"
        elif sc == 500:
            show("XX", name, sc, "500 SERVER ERROR")
            return sc, "500"
        elif sc == 201:
            if "NO_MANDATORY" in body:
                show("??", name, sc, "201 - 서비스 존재, 필수파라미터 누락")
                return sc, "MISSING_PARAM"
            show("??", name, sc, body[:80])
            return sc, body[:80]
        elif sc == 200:
            # Check for success indicators
            if "json" in ct:
                try:
                    j = r.json()
                    resp = j.get("response", {})
                    header = resp.get("header", {})
                    rc = header.get("resultCode", "")
                    rm = header.get("resultMsg", "")
                    tc = resp.get("body", {}).get("totalCount", -1)
                    if rc == "00":
                        show("OK", name, sc, f"JSON OK totalCount={tc}")
                        return sc, f"SUCCESS tc={tc}"
                    elif rc == "11":
                        show("??", name, sc, f"rc=11: {rm}")
                        return sc, f"MISSING_PARAM: {rm}"
                    elif rc == "20":
                        show("XX", name, sc, f"rc=20: ACCESS_DENIED {rm}")
                        return sc, f"ACCESS_DENIED"
                    else:
                        show("??", name, sc, f"rc={rc}: {rm}")
                        return sc, f"rc={rc}: {rm[:50]}"
                except Exception:
                    # Non-standard JSON
                    show("??", name, sc, f"JSON parse issue: {body[:80]}")
                    return sc, body[:80]
            else:
                # XML
                if "resultCode>00<" in body:
                    m = re.search(r"<totalCount>(\d+)</totalCount>", body)
                    tc = int(m.group(1)) if m else "?"
                    show("OK", name, sc, f"XML OK totalCount={tc}")
                    return sc, f"SUCCESS_XML tc={tc}"
                elif "resultCode>11<" in body:
                    show("??", name, sc, "XML rc=11: MISSING_PARAM")
                    return sc, "MISSING_PARAM"
                elif "resultCode>20<" in body or "SERVICE_ACCESS_DENIED" in body:
                    show("XX", name, sc, "ACCESS_DENIED")
                    return sc, "ACCESS_DENIED"
                elif "resultCode>12<" in body:
                    show("??", name, sc, "XML rc=12: NO_DATA")
                    return sc, "NO_DATA"
                else:
                    snippet = body[:100].replace("\n", " ").replace("\r", "")
                    show("??", name, sc, snippet)
                    return sc, snippet
        else:
            show("XX", name, sc, body[:80])
            return sc, body[:80]
    except Exception as e:
        show("XX", name, "ERR", str(e)[:80])
        return 0, str(e)[:80]


async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:

        # ================================================================
        # A. 토지이용규제 — PNU 형식 수정 (19자리)
        # ================================================================
        print("=" * 90)
        print("  A. 토지이용규제 — PNU 형식 수정")
        print("=" * 90)

        # 양평군 양평읍 양근리 PNU (경기도 양평군 = 41830)
        pnu_candidates = [
            "4183025330",            # 10자리 (법정동코드)
            "4183025330100000000",   # 19자리 추정
            "4183025330100010000",   # 19자리 다른 번지
            "4183025330100",         # 13자리
        ]
        for pnu in pnu_candidates:
            await try_get(c, f"토지이용규제 pnu={pnu}",
                "https://apis.data.go.kr/1613000/arLandUseInfoService/DTarLandUseInfo",
                {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json", "pnu": pnu})
            await asyncio.sleep(0.3)

        # ================================================================
        # B. 에어코리아 측정소별 — stationName 수정
        # ================================================================
        print("\n" + "=" * 90)
        print("  B. 에어코리아 측정소별 — stationName 수정")
        print("=" * 90)

        stations = ["양평", "양평읍", "수원", "종로구"]
        for stn in stations:
            await try_get(c, f"에어코리아 측정소별 stn={stn}",
                "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty",
                {"serviceKey": KEY, "returnType": "json", "numOfRows": 5, "pageNo": 1,
                 "stationName": stn, "dataTerm": "DAILY", "ver": "1.0"})
            await asyncio.sleep(0.3)

        # ================================================================
        # C. 수질DB — 파라미터 변형 시도
        # ================================================================
        print("\n" + "=" * 90)
        print("  C. 수질DB — 파라미터 변형")
        print("=" * 90)

        await try_get(c, "수질 기본 (type=json)",
            "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
        await asyncio.sleep(0.3)

        await try_get(c, "수질 XML (type 없음)",
            "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5})
        await asyncio.sleep(0.3)

        # ================================================================
        # D. 생활쓰레기 — 파라미터 탐색
        # ================================================================
        print("\n" + "=" * 90)
        print("  D. 생활쓰레기 — 파라미터 탐색")
        print("=" * 90)

        await try_get(c, "생활쓰레기 기본",
            "https://apis.data.go.kr/1741000/household_waste_info/info",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
        await asyncio.sleep(0.3)

        await try_get(c, "생활쓰레기 + year",
            "https://apis.data.go.kr/1741000/household_waste_info/info",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json", "year": "2023"})
        await asyncio.sleep(0.3)

        # ================================================================
        # E. 교통량 — operation name 탐색
        # ================================================================
        print("\n" + "=" * 90)
        print("  E. 교통량 — operation name 탐색")
        print("=" * 90)

        traffic_ops = [
            "getTmsStatInfo", "getStatInfo", "getStat", "getTmsStat",
            "getTrafficVolume", "getTmsStatList",
        ]
        for op in traffic_ops:
            await try_get(c, f"교통량 /{op}",
                f"https://apis.data.go.kr/1613000/KictTmsStat/{op}",
                {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json", "statsYear": "2023"})
            await asyncio.sleep(0.3)

        # ================================================================
        # F. 국립생태원 B553084 — operation name 탐색
        # ================================================================
        print("\n" + "=" * 90)
        print("  F. 국립생태원 B553084 — operation name 탐색")
        print("=" * 90)

        eco_services = [
            ("EcologyzmpService", ["getEcologyzmpInfo", "getEcologyzmpList", "getEcologyzmp"]),
            ("SmldevalService", ["getSmldevalInfo", "getSmldevalList", "getSmldeval"]),
            ("TpgrphevalService", ["getTpgrphevalInfo", "getTpgrphevalList", "getTpgrpheval"]),
        ]
        for svc, ops in eco_services:
            for op in ops:
                await try_get(c, f"B553084/{svc}/{op}",
                    f"https://apis.data.go.kr/B553084/ecoapi/{svc}/{op}",
                    {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
                await asyncio.sleep(0.3)

        # Also try without /ecoapi/ prefix
        for svc, ops in eco_services:
            for op in ops[:1]:
                await try_get(c, f"B553084/{svc}/{op} (no ecoapi)",
                    f"https://apis.data.go.kr/B553084/{svc}/{op}",
                    {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
                await asyncio.sleep(0.3)

        # ================================================================
        # G. 1480523 환평 — operation name 탐색
        # ================================================================
        print("\n" + "=" * 90)
        print("  G. 1480523 환평 서비스 — operation name 탐색")
        print("=" * 90)

        # 서비스별 가능한 operation 패턴 시도
        svc_ops = [
            ("LandUseService", ["getLandUse", "getLandUseInfo", "getLandUseList", "getList"]),
            ("FlorafaunaService", ["getFlorafauna", "getFlorafaunaInfo", "getFlorafaunaList", "getList"]),
            ("NoiseVibrationService", ["getNoiseVibration", "getNoiseVibrationInfo", "getNoise", "getList"]),
            ("BsnsAreaService", ["getBsnsArea", "getBsnsAreaInfo", "getBsnsAreaList", "getList"]),
            ("PopulationService", ["getPopulation", "getPopulationInfo", "getPopulationList", "getList"]),
            ("GreenhouseGasService", ["getGreenhouseGas", "getGreenhouseGasInfo", "getGhg", "getList"]),
            ("GeologicalService", ["getGeological", "getGeologicalInfo", "getGeology", "getList"]),
            ("FoulsmellService", ["getFoulsmell", "getFoulsmellInfo", "getSmell", "getList"]),
            ("SntPblhService", ["getSntPblh", "getSntPblhInfo", "getHealth", "getList"]),
            ("EcocycleService", ["getEcocycle", "getEcocycleInfo", "getRecycle", "getList"]),
            ("AtmosphereService", ["getAtmosphere", "getAtmosphereInfo", "getAir", "getList"]),
            ("WaterQualityInfoService", ["getWaterQuality", "getWaterQualityInfo", "getWater", "getList"]),
        ]

        for svc, ops in svc_ops:
            found = False
            for op in ops:
                sc, result = await try_get(c, f"1480523/{svc}/{op}",
                    f"https://apis.data.go.kr/1480523/{svc}/{op}",
                    {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
                     "perCd": SAMPLE_PER_CD})
                if sc != 404:
                    found = True
                    break
                await asyncio.sleep(0.2)
            if not found:
                # Try without perCd
                for op in ops[:2]:
                    sc, result = await try_get(c, f"1480523/{svc}/{op} (no perCd)",
                        f"https://apis.data.go.kr/1480523/{svc}/{op}",
                        {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
                    if sc != 404:
                        break
                    await asyncio.sleep(0.2)

        # ================================================================
        # H. 환평 사업관리 — operation name 탐색
        # ================================================================
        print("\n" + "=" * 90)
        print("  H. 1480523 환평 사업관리 — operation name 탐색")
        print("=" * 90)

        mgmt_svcs = [
            ("EnvrnAffcEvlBsnsInfoInqireService",
             ["getEnvrnAffcEvlBsnsInfoInqire", "getEnvrnAffcEvlBsnsInfo", "getBsnsInfo", "getList"]),
            ("EnvrnAffcEvlDscssSttusInfoInqireService",
             ["getEnvrnAffcEvlDscssSttusInfoInqire", "getDscssSttusInfo", "getList"]),
            ("EnvrnAffcEvlDecsnCnInfoInqireService",
             ["getEnvrnAffcEvlDecsnCnInfoInqire", "getDecsnCnInfo", "getList"]),
            ("EnvrnAffcEvlDraftDsplayInfoInqireService",
             ["getEnvrnAffcEvlDraftDsplayInfoInqire", "getDraftDsplayInfo", "getList"]),
        ]

        for svc, ops in mgmt_svcs:
            for op in ops:
                sc, _ = await try_get(c, f"{svc[:30]}/{op[:20]}",
                    f"https://apis.data.go.kr/1480523/{svc}/{op}",
                    {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5})
                if sc != 404:
                    break
                await asyncio.sleep(0.2)

        # ================================================================
        # I. 해양수산부 — response 확인
        # ================================================================
        print("\n" + "=" * 90)
        print("  I. 해양수산부 — 상세 응답 확인")
        print("=" * 90)

        # #31 with ACP_YEAR that we know has data
        r = await c.get(
            "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo",
            params={"ServiceKey": KEY, "pageNo": 1, "numOfRows": 5, "resultType": "json", "ACP_YEAR": "2014"})
        print(f"  #31 ACP_YEAR=2014: status={r.status_code}")
        print(f"  Body: {r.text[:300]}")
        await asyncio.sleep(0.3)

        # #32 variants
        mof_ops = [
            "getOceansEnvImpactInfo1", "getOceansEnvImpactInfo",
            "getOceansEnvImpact", "getList",
        ]
        for op in mof_ops:
            sc, _ = await try_get(c, f"OceansEnvImpactService1/{op}",
                f"https://apis.data.go.kr/1192000/service/OceansEnvImpactService1/{op}",
                {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 5, "resultType": "json"})
            if sc != 404:
                break
            await asyncio.sleep(0.3)

        # Also try the MaritimeService with correct mgtNo from the data
        print("\n" + "=" * 90)
        print("  J. 환평 해양/수리수문 — mgtNo=perCd 시도")
        print("=" * 90)

        await try_get(c, "MaritimeService/getIvstg mgtNo=perCd",
            "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "mgtNo": SAMPLE_PER_CD})
        await asyncio.sleep(0.3)

        await try_get(c, "HydraulicsService/getRiver mgtNo=perCd",
            "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "mgtNo": SAMPLE_PER_CD})
        await asyncio.sleep(0.3)

        # Try with bizSeq as mgtNo
        await try_get(c, "MaritimeService/getIvstg mgtNo=bizSeq",
            "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "mgtNo": SAMPLE_BIZ_SEQ})
        await asyncio.sleep(0.3)

        await try_get(c, "HydraulicsService/getRiver mgtNo=bizSeq",
            "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
            {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
             "mgtNo": SAMPLE_BIZ_SEQ})
        await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(main())
