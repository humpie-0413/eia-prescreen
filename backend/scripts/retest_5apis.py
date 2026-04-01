"""5개 API 재테스트 - 새 키로."""
import sys
import asyncio
import urllib.parse

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY_RAW = "9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f"
KEY_ENC = urllib.parse.quote_plus(KEY_RAW)

APIS = [
    {
        "name": "1. 토지이용규제정보 (1611000)",
        "url": "https://apis.data.go.kr/1611000/nsdi/LandUseService/attr/getLandUseAttr",
        "params_fn": lambda k: {"serviceKey": k, "format": "json", "numOfRows": 5, "pageNo": 1},
    },
    {
        "name": "2. EIASS 환평정보 EiaInfoSvc (1480523)",
        "url": "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaList",
        "params_fn": lambda k: {"serviceKey": k, "type": "json", "numOfRows": 5, "pageNo": 1},
    },
    {
        "name": "3. EIASS 토양정보 (B553748)",
        "url": "https://apis.data.go.kr/B553748/ewtrInfrImpctAssmtInfoSvc/getSoilInfoList",
        "params_fn": lambda k: {"serviceKey": k, "type": "json", "numOfRows": 5, "pageNo": 1},
    },
    {
        "name": "4. EIASS 소음진동정보 (B553748)",
        "url": "https://apis.data.go.kr/B553748/ewtrInfrImpctAssmtInfoSvc/getNoiseVibInfoList",
        "params_fn": lambda k: {"serviceKey": k, "type": "json", "numOfRows": 5, "pageNo": 1},
    },
    {
        "name": "5. 수질DB WaterQualityService (1480523)",
        "url": "https://apis.data.go.kr/1480523/WaterQualityService/getWaterQualityList",
        "params_fn": lambda k: {"serviceKey": k, "type": "json", "numOfRows": 5, "pageNo": 1},
    },
]


async def test_one(client, api, key):
    try:
        resp = await client.get(api["url"], params=api["params_fn"](key), timeout=15)
        sc = resp.status_code
        ct = resp.headers.get("content-type", "")
        body = resp.text[:500]
        return {"status": sc, "ct": ct, "body": body}
    except Exception as e:
        return {"status": "ERR", "ct": "", "body": str(e)[:300]}


async def main():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for api in APIS:
            print(f"\n{'='*60}")
            print(f"  {api['name']}")
            print(f"{'='*60}")
            for label, key in [("Decoding(raw)", KEY_RAW), ("Encoding(enc)", KEY_ENC)]:
                r = await test_one(client, api, key)
                sc = r["status"]
                has_data = False
                error_msg = ""
                if sc == 200:
                    b = r["body"]
                    if "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in b:
                        error_msg = "KEY_NOT_REGISTERED"
                    elif "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR" in b:
                        error_msg = "RATE_LIMITED"
                    elif "NO_OPENAPI_SERVICE_ERROR" in b:
                        error_msg = "NO_SERVICE"
                    elif "item" in b.lower() or "result" in b.lower() or '"response"' in b.lower():
                        has_data = True
                    else:
                        error_msg = "UNKNOWN_RESPONSE"

                if has_data:
                    icon = "SUCCESS"
                elif sc == 200 and error_msg:
                    icon = f"200-but-{error_msg}"
                else:
                    icon = f"FAIL({sc})"

                print(f"  [{label:15s}] {icon}")
                print(f"    Content-Type: {r['ct'][:60]}")
                print(f"    Body preview: {r['body'][:300]}")


if __name__ == "__main__":
    asyncio.run(main())
