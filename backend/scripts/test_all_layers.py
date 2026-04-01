"""V-world + WMS + 기타 API 전체 레이어 테스트."""
import sys
import asyncio
import json
import os
from pathlib import Path

import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# .env 로드
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

VWORLD_KEY = os.environ.get("VWORLD_API_KEY", "")
DATA_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")

LNG, LAT = 127.4875, 37.4912
BUFFER = 1000

results = []


def record(category, name, status, code, detail=""):
    results.append({"category": category, "name": name, "status": status, "code": code, "detail": detail})
    icon = "OK" if status == "SUCCESS" else ("NODATA" if status == "NODATA" else "FAIL")
    print(f"  [{icon:6s}] {code:>3s} | {name} | {detail[:80]}")


async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:

        # ============================================================
        # 1. V-world Data API layers
        # ============================================================
        print("\n" + "=" * 70)
        print("  1. V-world Data API layers")
        print("=" * 70)

        vworld_layers = [
            ("LT_C_UQ111", "도시지역"),
            ("LT_C_UQ112", "관리지역"),
            ("LT_C_UQ113", "농림지역"),
            ("LT_C_UQ114", "자연환경보전지역"),
            ("LT_C_UQ141", "개발제한구역(그린벨트)"),
            ("LT_C_UD001", "경관지구"),
            ("LT_C_UD002", "고도지구"),
            ("LT_C_UD003", "방화지구"),
            ("LT_C_UD004", "방재지구"),
            ("LT_C_UD005", "보호지구"),
        ]

        for layer_code, layer_name in vworld_layers:
            try:
                r = await c.get("https://api.vworld.kr/req/data", params={
                    "key": VWORLD_KEY,
                    "service": "data",
                    "request": "GetFeature",
                    "data": layer_code,
                    "geomFilter": f"POINT({LNG} {LAT})",
                    "buffer": BUFFER,
                    "domain": "localhost",
                    "size": 10,
                    "page": 1,
                })
                if r.status_code != 200:
                    record("V-world", f"{layer_code} {layer_name}", "FAIL", str(r.status_code), r.text[:100])
                    continue

                data = r.json()
                resp = data.get("response", {})
                status = resp.get("status", "")
                if status == "NOT_FOUND":
                    record("V-world", f"{layer_code} {layer_name}", "NODATA", "200", "NOT_FOUND (buffer 내 없음)")
                elif status == "OK":
                    features = resp.get("result", {}).get("featureCollection", {}).get("features", [])
                    fc = len(features)
                    props = features[0].get("properties", {}) if features else {}
                    field_names = list(props.keys())[:6]
                    record("V-world", f"{layer_code} {layer_name}", "SUCCESS", "200",
                           f"{fc} features, fields: {field_names}")
                elif status == "ERROR":
                    err = resp.get("error", {})
                    record("V-world", f"{layer_code} {layer_name}", "FAIL", "200",
                           f"ERROR: {err.get('text', '')[:80]}")
                else:
                    record("V-world", f"{layer_code} {layer_name}", "FAIL", "200", f"status={status}")

            except Exception as e:
                record("V-world", f"{layer_code} {layer_name}", "FAIL", "ERR", str(e)[:80])

            await asyncio.sleep(0.5)

        # ============================================================
        # 2. 환경공간정보 WMS GetCapabilities
        # ============================================================
        print("\n" + "=" * 70)
        print("  2. 환경공간정보 WMS layers (mcee.go.kr)")
        print("=" * 70)

        try:
            r = await c.get("https://api.mcee.go.kr/geoserver/wms", params={
                "SERVICE": "WMS",
                "VERSION": "1.1.1",
                "REQUEST": "GetCapabilities",
            }, timeout=30)
            if r.status_code == 200 and "Layer" in r.text:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(r.text)
                ns = {"wms": "http://www.opengis.net/wms"}
                layers_el = root.findall(".//Layer/Layer")
                if not layers_el:
                    layers_el = root.findall(".//{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer")

                # Fallback: regex for layer names
                import re
                layer_names = re.findall(r"<Name>([^<]+)</Name>", r.text)
                layer_titles = re.findall(r"<Title>([^<]+)</Title>", r.text)

                print(f"  Total layers found: {len(layer_names)}")

                # Filter for EIA-relevant layers
                eia_keywords = ["eco", "lv", "gree", "natur", "protect", "wetland",
                                "forest", "land", "water", "soil", "noise",
                                "EGIS", "생태", "보호", "습지", "산림", "토지", "수질", "토양"]
                relevant = []
                for i, name in enumerate(layer_names):
                    title = layer_titles[i] if i < len(layer_titles) else ""
                    combined = f"{name} {title}".lower()
                    if any(kw.lower() in combined for kw in eia_keywords):
                        relevant.append((name, title))

                print(f"  EIA-relevant layers: {len(relevant)}")
                for name, title in relevant[:20]:
                    print(f"    {name}: {title}")

                # Test a few relevant layers with GetFeatureInfo
                test_layers = [l[0] for l in relevant[:8]]
                from pyproj import Transformer
                t = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                x, y = t.transform(LNG, LAT)
                bbox = f"{x-1000},{y-1000},{x+1000},{y+1000}"

                for lyr in test_layers:
                    await asyncio.sleep(0.3)
                    try:
                        r2 = await c.get("https://api.mcee.go.kr/geoserver/wms", params={
                            "SERVICE": "WMS",
                            "VERSION": "1.1.1",
                            "REQUEST": "GetFeatureInfo",
                            "LAYERS": lyr,
                            "QUERY_LAYERS": lyr,
                            "SRS": "EPSG:3857",
                            "BBOX": bbox,
                            "WIDTH": 256, "HEIGHT": 256,
                            "X": 128, "Y": 128,
                            "INFO_FORMAT": "application/json",
                        })
                        ct = r2.headers.get("content-type", "")
                        if r2.status_code == 200 and "json" in ct:
                            info = r2.json()
                            feats = info.get("features", [])
                            if feats:
                                props = feats[0].get("properties", {})
                                record("WMS", lyr, "SUCCESS", "200",
                                       f"{len(feats)} feats, props: {list(props.keys())[:5]}")
                            else:
                                record("WMS", lyr, "NODATA", "200", "0 features (GFI)")
                        elif r2.status_code == 200:
                            record("WMS", lyr, "NODATA", "200", f"non-json ct: {ct[:40]}")
                        else:
                            record("WMS", lyr, "FAIL", str(r2.status_code), r2.text[:80])
                    except Exception as e:
                        record("WMS", lyr, "FAIL", "ERR", str(e)[:80])
            else:
                record("WMS", "GetCapabilities", "FAIL", str(r.status_code), r.text[:100])
        except Exception as e:
            record("WMS", "GetCapabilities", "FAIL", "ERR", str(e)[:80])

        # ============================================================
        # 3. 국립생태원 습지/지형 API
        # ============================================================
        print("\n" + "=" * 70)
        print("  3. 국립생태원 API")
        print("=" * 70)

        nie_apis = [
            ("습지평가 (nie wetland)", "https://apis.data.go.kr/B553982/wetland/getWetlandList",
             {"serviceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}),
            ("지형평가 (nie terrain)", "https://apis.data.go.kr/B553982/terrain/getTerrainList",
             {"serviceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}),
            ("생태등급 (nie eco grade)", "https://apis.data.go.kr/B553982/ecoGrade/getEcoGradeList",
             {"serviceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}),
            ("보호지역 (nie protected)", "https://apis.data.go.kr/B553982/protArea/getProtAreaList",
             {"serviceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}),
            # Alternative service codes
            ("국립생태원 1480523 eco", "https://apis.data.go.kr/1480523/NieEcoService/getEcoGrade",
             {"serviceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "type": "json"}),
        ]

        for name, url, params in nie_apis:
            try:
                r = await c.get(url, params=params)
                body = r.text[:300]
                if r.status_code == 200 and ("item" in body.lower() or "totalCount" in body):
                    record("NIE", name, "SUCCESS", "200", body[:80])
                elif r.status_code == 200:
                    record("NIE", name, "NODATA", "200", body[:80])
                elif r.status_code == 404:
                    record("NIE", name, "FAIL", "404", "endpoint not found")
                else:
                    record("NIE", name, "FAIL", str(r.status_code), body[:80])
            except Exception as e:
                record("NIE", name, "FAIL", "ERR", str(e)[:80])
            await asyncio.sleep(1)

        # ============================================================
        # 4. 해양수산부 1192000 재테스트 (연도 일괄)
        # ============================================================
        print("\n" + "=" * 70)
        print("  4. 해양수산부 1192000 EnvImpactService (연도별)")
        print("=" * 70)

        mof_url = "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo"
        any_data = False
        for year in range(2010, 2026):
            r = await c.get(mof_url, params={
                "ServiceKey": DATA_KEY, "pageNo": 1, "numOfRows": 5, "resultType": "json", "ACP_YEAR": str(year),
            })
            if r.status_code == 200:
                body = r.text
                import re
                m = re.search(r'"totalCount"\s*:\s*(\d+)', body)
                tc = int(m.group(1)) if m else 0
                if tc > 0:
                    record("MOF", f"EnvImpact {year}", "SUCCESS", "200", f"totalCount={tc}")
                    any_data = True
            await asyncio.sleep(0.3)

        if not any_data:
            record("MOF", "EnvImpact 2010-2025", "NODATA", "200", "all years totalCount=0")

        # ============================================================
        # 5. V-world GetCapabilities (추가 레이어 탐색)
        # ============================================================
        print("\n" + "=" * 70)
        print("  5. V-world additional layers")
        print("=" * 70)

        extra_vworld = [
            ("LT_C_ADSIDO", "행정구역(시도)"),
            ("LT_C_ADSIGG", "행정구역(시군구)"),
            ("LT_C_ADEMD", "행정구역(읍면동)"),
            ("LT_C_SPBD", "건물"),
            ("LT_C_LHBLPN", "토지이용계획"),
            ("LT_C_WKMBBSN", "유역권역"),
            ("LT_C_WKMSTRM", "하천"),
            ("LT_C_FRSTCLIMR", "산림이용구분"),
            ("LT_C_AISRESC", "문화재보호구역"),
            ("LT_C_AISPC", "문화재(점)"),
            ("LT_C_MOCTLINK", "도로망"),
            ("LT_C_RIRCRE", "하천구역"),
            ("LT_C_LDSLADMS", "연속지적(행정동)"),
            ("LT_C_TDWAREA", "상수원보호구역"),
            ("LT_C_DAMDAN", "댐"),
        ]

        for layer_code, layer_name in extra_vworld:
            try:
                r = await c.get("https://api.vworld.kr/req/data", params={
                    "key": VWORLD_KEY,
                    "service": "data",
                    "request": "GetFeature",
                    "data": layer_code,
                    "geomFilter": f"POINT({LNG} {LAT})",
                    "buffer": BUFFER,
                    "domain": "localhost",
                    "size": 10,
                    "page": 1,
                })
                if r.status_code == 200:
                    data = r.json()
                    resp = data.get("response", {})
                    status = resp.get("status", "")
                    if status == "OK":
                        feats = resp.get("result", {}).get("featureCollection", {}).get("features", [])
                        fc = len(feats)
                        props = feats[0].get("properties", {}) if feats else {}
                        record("V-world+", f"{layer_code} {layer_name}", "SUCCESS", "200",
                               f"{fc} feats, fields: {list(props.keys())[:5]}")
                    elif status == "NOT_FOUND":
                        record("V-world+", f"{layer_code} {layer_name}", "NODATA", "200", "NOT_FOUND")
                    else:
                        err = resp.get("error", {})
                        record("V-world+", f"{layer_code} {layer_name}", "FAIL", "200",
                               f"{status}: {err.get('text', '')[:60]}")
                else:
                    record("V-world+", f"{layer_code} {layer_name}", "FAIL", str(r.status_code), r.text[:80])
            except Exception as e:
                record("V-world+", f"{layer_code} {layer_name}", "FAIL", "ERR", str(e)[:80])
            await asyncio.sleep(0.5)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    success = [r for r in results if r["status"] == "SUCCESS"]
    nodata = [r for r in results if r["status"] == "NODATA"]
    fail = [r for r in results if r["status"] == "FAIL"]

    print(f"\n  SUCCESS: {len(success)}  |  NODATA: {len(nodata)}  |  FAIL: {len(fail)}")
    print(f"\n  === SUCCESS ({len(success)}) ===")
    for r in success:
        print(f"    [{r['category']:8s}] {r['name']}")
    print(f"\n  === NODATA ({len(nodata)}) ===")
    for r in nodata:
        print(f"    [{r['category']:8s}] {r['name']}: {r['detail'][:60]}")
    print(f"\n  === FAIL ({len(fail)}) ===")
    for r in fail:
        print(f"    [{r['category']:8s}] {r['name']}: {r['code']} {r['detail'][:60]}")

    # Save results
    out_path = PROJECT_ROOT / "data" / "bulk" / "layer_test_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Results saved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
