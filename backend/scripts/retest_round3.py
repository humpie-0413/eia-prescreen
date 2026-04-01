"""3차 재테스트 — 토지이용규제 PNU, 수질 상세, 생활쓰레기 상세."""
import sys
import asyncio
import os
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


async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:

        # ================================================================
        # 1. 토지이용규제 — PNU 상세 테스트
        # ================================================================
        print("=" * 90)
        print("  1. 토지이용규제 PNU 형식 테스트")
        print("=" * 90)

        # 양평군 양평읍 양근리 = 법정동코드 4183025300
        # PNU = 법정동코드(10) + 대지/산(1) + 본번(4) + 부번(4) = 19자리
        pnus = [
            ("4183025300", "법정동10자리"),
            ("4183025300101200000", "양근리 1-12"),
            ("4183025300100010000", "양근리 1번지"),
            ("4183025300100100000", "양근리 10번지"),
            ("4183025330", "양평읍 코드"),
            ("4183025330101000000", "양평읍 100번지"),
        ]
        for pnu, desc in pnus:
            r = await c.get(
                "https://apis.data.go.kr/1613000/arLandUseInfoService/DTarLandUseInfo",
                params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json", "pnu": pnu})
            print(f"\n  [{r.status_code}] pnu={pnu} ({desc})")
            print(f"  {r.text[:300]}")
            await asyncio.sleep(0.3)

        # ================================================================
        # 2. 수질 XML 상세 응답
        # ================================================================
        print("\n" + "=" * 90)
        print("  2. 수질DB XML 상세 응답")
        print("=" * 90)

        r = await c.get(
            "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList",
            params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5})
        print(f"  [{r.status_code}] len={len(r.text)}")
        print(f"  {r.text[:800]}")
        await asyncio.sleep(0.3)

        # ================================================================
        # 3. 생활쓰레기 상세 응답
        # ================================================================
        print("\n" + "=" * 90)
        print("  3. 생활쓰레기 상세 응답")
        print("=" * 90)

        r = await c.get(
            "https://apis.data.go.kr/1741000/household_waste_info/info",
            params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
        print(f"  [{r.status_code}] CT={r.headers.get('content-type','')}")
        print(f"  {r.text[:500]}")
        await asyncio.sleep(0.3)

        # with sidoCd
        r = await c.get(
            "https://apis.data.go.kr/1741000/household_waste_info/info",
            params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
                    "sidoCd": "41", "year": "2022"})
        print(f"\n  [{r.status_code}] + sidoCd=41, year=2022")
        print(f"  {r.text[:500]}")
        await asyncio.sleep(0.3)

        # ================================================================
        # 4. 교통량 — 서비스 URL 변형
        # ================================================================
        print("\n" + "=" * 90)
        print("  4. 교통량 URL 변형 테스트")
        print("=" * 90)

        traffic_urls = [
            "https://apis.data.go.kr/1613000/KictTmsStat/getTmsStatList",
            "https://apis.data.go.kr/1613000/TrafficAmountInfoService/getTrafficAmountList",
            "https://apis.data.go.kr/B553755/TrafficVolumeService/getTrafficVolume",
            "https://apis.data.go.kr/B553755/TrafficVolumeService/getTrafficVolumeList",
        ]
        for url in traffic_urls:
            r = await c.get(url, params={
                "serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json",
                "statsYear": "2023"})
            print(f"  [{r.status_code}] {url.split('.kr/')[-1][:60]}")
            if r.status_code != 404:
                print(f"  {r.text[:200]}")
            await asyncio.sleep(0.3)

        # ================================================================
        # 5. 해양수산부 #31 — 비표준 JSON 파싱 확인
        # ================================================================
        print("\n" + "=" * 90)
        print("  5. 해양수산부 #31 상세")
        print("=" * 90)

        r = await c.get(
            "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo",
            params={"ServiceKey": KEY, "pageNo": 1, "numOfRows": 3, "resultType": "json",
                    "ACP_YEAR": "2014"})
        print(f"  [{r.status_code}] CT={r.headers.get('content-type','')}")
        import json
        data = r.json()
        info = data.get("getEnvImpactInfo", {})
        header = info.get("header", {})
        items = info.get("item", [])
        total = info.get("totalCount", info.get("numOfRows", "?"))
        print(f"  header: {header}")
        print(f"  totalCount: {total}")
        print(f"  items: {len(items)}")
        if items:
            print(f"  sample item keys: {list(items[0].keys())}")
            print(f"  sample: {json.dumps(items[0], ensure_ascii=False)[:200]}")

        # ================================================================
        # 6. 토양측정망 1480523/SgisSoAPI — 상세 확인
        # ================================================================
        print("\n" + "=" * 90)
        print("  6. 토양측정망 상세 (operation name 탐색)")
        print("=" * 90)

        soil_ops = ["getSgisSoList", "getSgisSo", "getSoilList", "getList"]
        for op in soil_ops:
            r = await c.get(
                f"https://apis.data.go.kr/1480523/SgisSoAPI/{op}",
                params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
            print(f"  [{r.status_code}] SgisSoAPI/{op}: {r.text[:100]}")
            await asyncio.sleep(0.3)

        # ================================================================
        # 7. 국립생태원 — 서비스코드 변형 (B553084 without ecoapi)
        # ================================================================
        print("\n" + "=" * 90)
        print("  7. 국립생태원 B553084 — 서비스코드 변형")
        print("=" * 90)

        nie_variants = [
            "B553084/EcologyzmpService/getEcologyzmpInfo",
            "B553084/EcologyzmpService/getEcologyzmpList",
            "B553084/SmldevalService/getSmldevalInfo",
            "B553084/TpgrphevalService/getTpgrphevalInfo",
        ]
        for path in nie_variants:
            r = await c.get(f"https://apis.data.go.kr/{path}",
                params={"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"})
            print(f"  [{r.status_code}] {path}: {r.text[:120]}")
            await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(main())
