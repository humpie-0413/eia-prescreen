"""환경영향평가 정보 서비스 API 전수 테스트.

1. 좌표 기반 검색 (getBsnsPlaceLnMyeonInfoInqire) — gubun 1~15
2. 사전/전략/소규모 상세 API 2종
3. 환평 본안 나머지 3종
"""

import json
import time
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

API_KEY = "9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f"
BASE_SPATIAL = "https://apis.data.go.kr/1480523/EnvrnAffcEvlBsnsInfoInqireService"
BASE_DETAIL = "https://apis.data.go.kr/1480523/EnvrnAffcEvlBsnsInfoInqireService"

# 양평 좌표
CENTER_X = 127.4875
CENTER_Y = 37.4912

# bizSeq 값 (수집된 데이터에서)
BIZ_SEQS = ["103964", "103961", "103958", "103953", "103941"]

GUBUN_LABELS = {
    1: "사업지_선",
    2: "사업지_면",
    3: "멸종위기동물_점",
    4: "멸종위기동물_선",
    5: "멸종위기동물_면",
    6: "멸종위기식물_점",
    7: "멸종위기식물_면",
    8: "대기질_점",
    9: "해양저질",
    10: "해양수질",
    11: "지표수질",
    12: "지하수질",
    13: "토양질",
    14: "멸종위기동물_선(14)",
    15: "진동",
}

results = {
    "spatial_api": {},
    "detail_api": {},
    "bulk_api": {},
}


def test_spatial_api():
    """좌표 기반 검색 API — gubun 1~15 테스트."""
    print("\n" + "=" * 70)
    print("1. 좌표 기반 검색 API (getBsnsPlaceLnMyeonInfoInqire)")
    print("=" * 70)

    url = f"{BASE_SPATIAL}/getBsnsPlaceLnMyeonInfoInqire"

    for gubun in range(1, 16):
        label = GUBUN_LABELS.get(gubun, f"gubun={gubun}")
        params = {
            "serviceKey": API_KEY,
            "gubun": gubun,
            "centerX": CENTER_X,
            "centerY": CENTER_Y,
            "distance": 5000,
            "numOfRows": 100,
            "pageNo": 1,
        }

        try:
            resp = httpx.get(url, params=params, timeout=15)
            status = resp.status_code

            if status == 200:
                try:
                    data = resp.json()
                    # Check response structure
                    body = data.get("getBsnsPlaceLnMyeonInfoInqire", {})
                    header = body.get("header", {})
                    result_code = header.get("resultCode", "?")
                    result_msg = header.get("resultMsg", "?")
                    items = body.get("item", [])
                    if isinstance(items, dict):
                        items = [items]
                    total = body.get("totalCount", len(items))

                    print(f"  gubun={gubun:2d} ({label:20s}): OK  code={result_code}  총 {total}건  items={len(items)}")
                    results["spatial_api"][gubun] = {
                        "label": label,
                        "status": "success",
                        "http_status": status,
                        "result_code": result_code,
                        "total_count": total,
                        "item_count": len(items),
                        "sample": items[0] if items else None,
                    }
                except Exception as e:
                    # Maybe XML response
                    text = resp.text[:300]
                    if "<" in text and ">" in text:
                        # XML - try to parse result code
                        import re
                        code_match = re.search(r"<resultCode>(\w+)</resultCode>", text)
                        msg_match = re.search(r"<resultMsg>([^<]+)</resultMsg>", text)
                        code = code_match.group(1) if code_match else "?"
                        msg = msg_match.group(1) if msg_match else "?"
                        total_match = re.search(r"<totalCount>(\d+)</totalCount>", text)
                        total = int(total_match.group(1)) if total_match else 0
                        print(f"  gubun={gubun:2d} ({label:20s}): XML  code={code}  msg={msg}  총 {total}건")
                        results["spatial_api"][gubun] = {
                            "label": label,
                            "status": "success_xml",
                            "http_status": status,
                            "result_code": code,
                            "total_count": total,
                            "result_msg": msg,
                        }
                    else:
                        print(f"  gubun={gubun:2d} ({label:20s}): PARSE_ERROR — {e}")
                        results["spatial_api"][gubun] = {"label": label, "status": "parse_error", "error": str(e)}
            else:
                print(f"  gubun={gubun:2d} ({label:20s}): HTTP {status}")
                results["spatial_api"][gubun] = {"label": label, "status": "http_error", "http_status": status}

        except Exception as e:
            print(f"  gubun={gubun:2d} ({label:20s}): ERROR — {e}")
            results["spatial_api"][gubun] = {"label": label, "status": "error", "error": str(e)}

        time.sleep(0.5)


def test_detail_apis():
    """사전/전략/소규모 상세 API 2종 테스트."""
    print("\n" + "=" * 70)
    print("2. 상세정보 API (getBsnsStrtgySmallScaleDscssBsnsDetailInfoInqire)")
    print("   협의진행 API (getBsnsStrtgySmallScaleDscssBsnsDetailIngInfoInqire)")
    print("=" * 70)

    apis = [
        ("detail_info", "getBsnsStrtgySmallScaleDscssBsnsDetailInfoInqire", "상세정보"),
        ("detail_ing", "getBsnsStrtgySmallScaleDscssBsnsDetailIngInfoInqire", "협의진행"),
    ]

    for api_key_name, endpoint, label in apis:
        url = f"{BASE_DETAIL}/{endpoint}"
        print(f"\n  [{label}] {endpoint}")

        for seq in BIZ_SEQS[:5]:
            params = {
                "serviceKey": API_KEY,
                "bizSeq": seq,
            }

            try:
                resp = httpx.get(url, params=params, timeout=15)
                status = resp.status_code
                text = resp.text[:500]

                if status == 200:
                    import re
                    code_match = re.search(r"<resultCode>(\w+)</resultCode>", text)
                    msg_match = re.search(r"<resultMsg>([^<]+)</resultMsg>", text)
                    code = code_match.group(1) if code_match else "?"
                    msg = msg_match.group(1) if msg_match else "?"

                    # Try JSON first
                    has_data = False
                    try:
                        data = resp.json()
                        has_data = True
                        print(f"    bizSeq={seq}: JSON  code={code}  msg={msg}")
                    except Exception:
                        total_match = re.search(r"<totalCount>(\d+)</totalCount>", text)
                        total = int(total_match.group(1)) if total_match else 0
                        print(f"    bizSeq={seq}: XML  code={code}  msg={msg}  총 {total}건")

                    key = f"{api_key_name}_{seq}"
                    results["detail_api"][key] = {
                        "endpoint": endpoint,
                        "label": label,
                        "bizSeq": seq,
                        "status": "success",
                        "http_status": status,
                        "result_code": code,
                        "result_msg": msg,
                        "sample_text": text[:200],
                    }
                else:
                    print(f"    bizSeq={seq}: HTTP {status}")
                    results["detail_api"][f"{api_key_name}_{seq}"] = {
                        "status": "http_error",
                        "http_status": status,
                    }

            except Exception as e:
                print(f"    bizSeq={seq}: ERROR — {e}")
                results["detail_api"][f"{api_key_name}_{seq}"] = {"status": "error", "error": str(e)}

            time.sleep(0.5)


def test_bulk_apis():
    """환평 본안 나머지 3종 테스트."""
    print("\n" + "=" * 70)
    print("3. 환평 본안 API 3종")
    print("=" * 70)

    apis = [
        ("conslt_list", "getDscssBsnsListInfoInqire", "협의현황"),
        ("decsn_list", "getDecsnCnListInfoInqire", "결정내용"),
        ("draft_list", "getDraftPblancDsplayListInfoInqire", "초안공람"),
    ]

    for api_key_name, endpoint, label in apis:
        url = f"{BASE_DETAIL}/{endpoint}"
        params = {
            "serviceKey": API_KEY,
            "pageNo": 1,
            "numOfRows": 5,
        }

        print(f"\n  [{label}] {endpoint}")

        try:
            resp = httpx.get(url, params=params, timeout=15)
            status = resp.status_code
            text = resp.text[:1000]

            if status == 200:
                import re
                code_match = re.search(r"<resultCode>(\w+)</resultCode>", text)
                msg_match = re.search(r"<resultMsg>([^<]+)</resultMsg>", text)
                code = code_match.group(1) if code_match else "?"
                msg = msg_match.group(1) if msg_match else "?"
                total_match = re.search(r"<totalCount>(\d+)</totalCount>", text)
                total = int(total_match.group(1)) if total_match else 0

                # Try JSON
                try:
                    data = resp.json()
                    # Extract items
                    root_key = list(data.keys())[0] if data else "?"
                    body = data.get(root_key, {})
                    items = body.get("item", [])
                    if isinstance(items, dict):
                        items = [items]
                    total_from_json = body.get("totalCount", len(items))
                    print(f"    JSON  code={code}  msg={msg}  총 {total_from_json}건  items={len(items)}")
                    results["bulk_api"][api_key_name] = {
                        "endpoint": endpoint,
                        "label": label,
                        "status": "success",
                        "format": "json",
                        "http_status": status,
                        "result_code": code,
                        "total_count": total_from_json,
                        "item_count": len(items),
                        "sample": items[0] if items else None,
                    }
                except Exception:
                    print(f"    XML  code={code}  msg={msg}  총 {total}건")
                    results["bulk_api"][api_key_name] = {
                        "endpoint": endpoint,
                        "label": label,
                        "status": "success_xml",
                        "format": "xml",
                        "http_status": status,
                        "result_code": code,
                        "total_count": total,
                        "result_msg": msg,
                        "sample_text": text[:300],
                    }
            else:
                print(f"    HTTP {status}")
                results["bulk_api"][api_key_name] = {
                    "endpoint": endpoint,
                    "status": "http_error",
                    "http_status": status,
                    "response_text": text[:300],
                }

        except Exception as e:
            print(f"    ERROR — {e}")
            results["bulk_api"][api_key_name] = {"status": "error", "error": str(e)}

        time.sleep(0.5)


def main():
    print("환경영향평가 정보 서비스 API 전수 테스트")
    print(f"API Key: {API_KEY[:20]}...")
    print(f"좌표: ({CENTER_X}, {CENTER_Y}) — 양평")
    print(f"bizSeq: {BIZ_SEQS}")

    test_spatial_api()
    test_detail_apis()
    test_bulk_apis()

    # 결과 저장
    out_path = Path(__file__).parent.parent.parent / "data" / "bulk" / "eia_spatial_api_test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n결과 저장: {out_path}")

    # 요약
    print("\n" + "=" * 70)
    print("테스트 요약")
    print("=" * 70)

    spatial_ok = sum(1 for v in results["spatial_api"].values() if "success" in v.get("status", ""))
    spatial_total = len(results["spatial_api"])
    print(f"  좌표 기반 검색: {spatial_ok}/{spatial_total} 성공")

    detail_ok = sum(1 for v in results["detail_api"].values() if "success" in v.get("status", ""))
    detail_total = len(results["detail_api"])
    print(f"  상세 API: {detail_ok}/{detail_total} 성공")

    bulk_ok = sum(1 for v in results["bulk_api"].values() if "success" in v.get("status", ""))
    bulk_total = len(results["bulk_api"])
    print(f"  본안 API: {bulk_ok}/{bulk_total} 성공")


if __name__ == "__main__":
    main()
