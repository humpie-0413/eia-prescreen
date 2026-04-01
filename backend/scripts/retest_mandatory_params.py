"""필수 파라미터를 추가하여 1, 3, 4번 API 재테스트 + 2번 상세 탐색."""
import sys
import asyncio

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = "9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f"

APIS = [
    # === 2번: 이미 작동 - 상세 데이터 확인 ===
    {
        "name": "2. 협의목록 (numOfRows=5, 전체 목록)",
        "url": "https://apis.data.go.kr/1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService/getBsnsStrtgySmallScaleDscssListInfoInqire",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5},
    },
    {
        "name": "2-json. 협의목록 (type=json 시도)",
        "url": "https://apis.data.go.kr/1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService/getBsnsStrtgySmallScaleDscssListInfoInqire",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "type": "json"},
    },
    {
        "name": "2-totalcount. 협의목록 (numOfRows=1, totalCount 확인)",
        "url": "https://apis.data.go.kr/1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService/getBsnsStrtgySmallScaleDscssListInfoInqire",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 1},
    },

    # === 1번: 수리수문 - 필수 파라미터 탐색 ===
    {
        "name": "1a. 수리수문 + assmtSn (사업번호 추정)",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "assmtSn": "1"},
    },
    {
        "name": "1b. 수리수문 + eiaNo",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "eiaNo": "1"},
    },
    {
        "name": "1c. 수리수문 + ivstgSn",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "ivstgSn": "1"},
    },
    {
        "name": "1d. 수리수문 + bizSn",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "bizSn": "1"},
    },
    {
        "name": "1e. 수리수문 + perCd (사전환경성 고유코드)",
        "url": "https://apis.data.go.kr/1480523/HydraulicsService/getRiver",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "perCd": "WJ20260063"},
    },

    # === 3번: 해양환경 조사속성 - 필수 파라미터 탐색 ===
    {
        "name": "3a. 해양조사 + assmtSn",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "assmtSn": "1"},
    },
    {
        "name": "3b. 해양조사 + eiaNo",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "eiaNo": "1"},
    },
    {
        "name": "3c. 해양조사 + ivstgSn",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "ivstgSn": "1"},
    },
    {
        "name": "3d. 해양조사 + bizSn",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "bizSn": "1"},
    },

    # === 4번: 해양환경 동식물 - 필수 파라미터 탐색 ===
    {
        "name": "4a. 해양동식물 + assmtSn",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getAmplt",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "assmtSn": "1"},
    },
    {
        "name": "4b. 해양동식물 + eiaNo",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getAmplt",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "eiaNo": "1"},
    },
    {
        "name": "4c. 해양동식물 + ivstgSn",
        "url": "https://apis.data.go.kr/1480523/MaritimeService/getAmplt",
        "params": {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10, "type": "json", "ivstgSn": "1"},
    },
]


async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        for api in APIS:
            print(f"\n{'=' * 70}")
            print(f"  {api['name']}")
            print(f"{'=' * 70}")
            try:
                resp = await client.get(api["url"], params=api["params"])
                sc = resp.status_code
                ct = resp.headers.get("content-type", "")
                body = resp.text[:600]

                # Quick tag
                if sc == 200 and "resultCode>00<" in body:
                    tag = "SUCCESS_XML"
                elif sc == 200 and '"resultCode": "00"' in body:
                    tag = "SUCCESS_JSON"
                elif sc == 200 and "resultCode>11<" in body:
                    tag = "MISSING_PARAMS_XML"
                elif sc == 201:
                    if "NO_MANDATORY" in body:
                        tag = "MISSING_PARAMS"
                    else:
                        tag = "201_OTHER"
                elif sc == 500:
                    tag = "SERVER_500"
                else:
                    tag = f"HTTP_{sc}"

                print(f"  [{sc}] {tag}  |  CT: {ct[:50]}")
                print(f"  {body[:500]}")

            except Exception as e:
                print(f"  ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
