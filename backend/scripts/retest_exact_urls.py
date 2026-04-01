"""공공데이터포털 상세페이지 정확한 URL로 재테스트."""
import sys
import asyncio

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f"

APIS = [
    # 1~4: 새로 확인한 정확한 URL
    {
        "name": "1. 수리수문정보 (HydraulicsService/getRiver)",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "2. 사전/전략/소규모 협의목록 (XML only)",
        "url": "https://apis.data.go.kr/1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService/getBsnsStrtgySmallScaleDscssListInfoInqire",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10},
    },
    {
        "name": "3. 해양환경 조사속성 (MaritimeService/getIvstg)",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "4. 해양환경 동식물 (MaritimeService/getAmplt)",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getAmplt",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    # 5~7: 이전에 500이었던 기존 API - 정확한 URL 재확인
    {
        "name": "5. 환평 정보서비스 (EiaInfoSvc - 기존 getEiaInfoList)",
        "url": "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaInfoList",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "5b. 환평 정보서비스 (EiaInfoSvc - getEiaList)",
        "url": "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaList",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "5c. 환평 정보서비스 (serviceKey lowercase)",
        "url": "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaInfoList",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json"},
    },
    {
        "name": "6. 환평 협의현황 (EiaConsltSvc - getEiaConsltList)",
        "url": "https://apis.data.go.kr/1480523/EiaConsltSvc/getEiaConsltList",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "6b. 환평 협의현황 (serviceKey lowercase)",
        "url": "https://apis.data.go.kr/1480523/EiaConsltSvc/getEiaConsltList",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json"},
    },
    {
        "name": "7. 환평 소음진동 (NoiseVibraService - getNoiseVibra)",
        "url": "https://apis.data.go.kr/1480523/NoiseVibraService/getNoiseVibra",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    {
        "name": "7b. 환평 소음진동 (NoiseVibraService - getNoiseVibraList)",
        "url": "https://apis.data.go.kr/1480523/NoiseVibraService/getNoiseVibraList",
        "params": {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 10, "resultType": "json"},
    },
    # Bonus: serviceKey casing + type param variants for new APIs
    {
        "name": "1b. 수리수문 (serviceKey lowercase + type=json)",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json"},
    },
    {
        "name": "3b. 해양조사속성 (serviceKey lowercase + type=json)",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json"},
    },
    {
        "name": "4b. 해양동식물 (serviceKey lowercase + type=json)",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getAmplt",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json"},
    },
]


async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        for api in APIS:
            print(f"\n{'=' * 70}")
            print(f"  {api['name']}")
            print(f"  URL: {api['url']}")
            print(f"{'=' * 70}")
            try:
                resp = await client.get(api["url"], params=api["params"])
                sc = resp.status_code
                ct = resp.headers.get("content-type", "")
                body = resp.text[:500]

                # Classify
                if sc == 200:
                    if "SERVICE_KEY_IS_NOT_REGISTERED" in body:
                        tag = "KEY_NOT_REGISTERED"
                    elif "LIMITED_NUMBER_OF_SERVICE" in body:
                        tag = "RATE_LIMITED"
                    elif "NO_OPENAPI_SERVICE_ERROR" in body:
                        tag = "NO_SERVICE"
                    elif "totalCount" in body or "item" in body.lower() or "<body>" in body.lower():
                        tag = "DATA_RETURNED"
                    else:
                        tag = "200_OTHER"
                elif sc == 500:
                    tag = "SERVER_ERROR_500"
                elif sc == 404:
                    tag = "NOT_FOUND_404"
                else:
                    tag = f"HTTP_{sc}"

                print(f"  Status: {sc}  |  Tag: {tag}")
                print(f"  Content-Type: {ct}")
                print(f"  Body[0:500]:")
                print(f"  {body}")

            except Exception as e:
                print(f"  ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
