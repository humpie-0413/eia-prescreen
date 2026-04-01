"""EIA API 추가 테스트.

1. 좌표 기반 API: 반경 확대(10km, 20km) + 서울/세종 좌표
2. 상세/본안 API: 다른 서비스 경로 탐색
"""

import json
import re
import time
from pathlib import Path
import httpx

API_KEY = "9b65d7635b6bdd909b1abebd6eabaea6f026cdf4a860ba3db335971ab8af585f"

results = {}


def parse_xml(text):
    """XML 응답에서 주요 정보 추출."""
    code = re.search(r"<resultCode>(\w+)</resultCode>", text)
    msg = re.search(r"<resultMsg>([^<]+)</resultMsg>", text)
    total = re.search(r"<totalCount>(\d+)</totalCount>", text)
    return {
        "code": code.group(1) if code else "?",
        "msg": msg.group(1) if msg else "?",
        "total": int(total.group(1)) if total else 0,
    }


def try_api(label, url, params, key=None):
    """API 호출 + 결과 요약."""
    try:
        resp = httpx.get(url, params=params, timeout=15)
        text = resp.text[:2000]

        if resp.status_code != 200:
            print(f"  {label}: HTTP {resp.status_code}")
            return {"status": "http_error", "code": resp.status_code, "text": text[:200]}

        # Try JSON
        try:
            data = resp.json()
            root = list(data.keys())[0] if data else "?"
            body = data.get(root, {})
            if isinstance(body, dict):
                items = body.get("item", [])
                if isinstance(items, dict):
                    items = [items]
                total = body.get("totalCount", len(items))
                print(f"  {label}: JSON  총 {total}건  items={len(items)}")
                result = {
                    "status": "success",
                    "format": "json",
                    "total": total,
                    "items": len(items),
                }
                if items:
                    result["sample_keys"] = list(items[0].keys()) if isinstance(items[0], dict) else str(type(items[0]))
                    result["sample"] = items[0]
                return result
            else:
                print(f"  {label}: JSON (unexpected body type)")
                return {"status": "success", "format": "json", "body_type": str(type(body))}
        except Exception:
            pass

        # XML
        info = parse_xml(text)
        print(f"  {label}: XML  code={info['code']}  총 {info['total']}건")
        result = {"status": "success_xml", **info}

        # Extract items from XML
        item_matches = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
        if item_matches:
            result["items_found"] = len(item_matches)
            # Parse first item fields
            fields = re.findall(r"<(\w+)>([^<]*)</\w+>", item_matches[0])
            result["sample_fields"] = {k: v for k, v in fields}
        return result

    except Exception as e:
        print(f"  {label}: ERROR - {e}")
        return {"status": "error", "error": str(e)}


def test_spatial_wider():
    """좌표 기반 API - 반경 확대 + 다른 좌표."""
    print("\n=== 1. 좌표 기반 API 반경/좌표 변경 테스트 ===")
    url = "https://apis.data.go.kr/1480523/EnvrnAffcEvlBsnsInfoInqireService/getBsnsPlaceLnMyeonInfoInqire"

    tests = [
        # (label, centerX, centerY, distance, gubun)
        ("양평 20km gubun=2", 127.4875, 37.4912, 20000, 2),
        ("서울 강남 5km gubun=2", 127.0276, 37.4979, 5000, 2),
        ("서울 강남 10km gubun=2", 127.0276, 37.4979, 10000, 2),
        ("��종 5km gubun=2", 127.0028, 36.6040, 5000, 2),
        ("세종 10km gubun=2", 127.0028, 36.6040, 10000, 2),
        ("서울 강남 5km gubun=1", 127.0276, 37.4979, 5000, 1),
        ("서울 강남 10km gubun=3(멸종위기동물)", 127.0276, 37.4979, 10000, 3),
        ("서울 강남 10km gubun=8(대기질)", 127.0276, 37.4979, 10000, 8),
        ("서울 강남 10km gubun=11(지표수질)", 127.0276, 37.4979, 10000, 11),
        ("서울 강남 10km gubun=13(토양질)", 127.0276, 37.4979, 10000, 13),
        ("보령 10km gubun=2", 126.5530, 36.3340, 10000, 2),
        ("보령 10km gubun=9(해양저질)", 126.5530, 36.3340, 10000, 9),
        ("보령 10km gubun=10(해양수질)", 126.5530, 36.3340, 10000, 10),
    ]

    spatial_results = {}
    for label, cx, cy, dist, gubun in tests:
        params = {
            "serviceKey": API_KEY,
            "gubun": gubun,
            "centerX": cx,
            "centerY": cy,
            "distance": dist,
            "numOfRows": 100,
            "pageNo": 1,
        }
        r = try_api(label, url, params)
        spatial_results[label] = r
        time.sleep(0.5)

    results["spatial_wider"] = spatial_results


def test_detail_alternative_paths():
    """상세/본안 API - 다른 서비스 경로 시도."""
    print("\n=== 2. 상세/본안 API 대체 경로 탐색 ===")

    biz_seqs = ["103964", "103961", "103953"]

    # 후보 서비스 경로들
    service_bases = [
        "https://apis.data.go.kr/1480523/EnvrnAffcEvlBsnsInfoInqireService",
        "https://apis.data.go.kr/B553748/eiainformation",
        "https://apis.data.go.kr/1480523/EvlBsnsInfoInqireService",
    ]

    detail_endpoints = [
        "getBsnsStrtgySmallScaleDscssBsnsDetailInfoInqire",
        "getBsnsStrtgySmallScaleDscssBsnsDetailIngInfoInqire",
        "getDscssBsnsListInfoInqire",
        "getDecsnCnListInfoInqire",
        "getDraftPblancDsplayListInfoInqire",
    ]

    detail_results = {}

    # Test each base + endpoint combo
    for base in service_bases:
        base_label = base.split("/")[-1]
        for ep in detail_endpoints:
            url = f"{base}/{ep}"
            label = f"{base_label}/{ep[:40]}"

            # For list endpoints, use pageNo
            if "List" in ep or "Dsplay" in ep:
                params = {"serviceKey": API_KEY, "pageNo": 1, "numOfRows": 5}
                r = try_api(label, url, params)
                detail_results[f"{base_label}_{ep}"] = r
            else:
                # For detail endpoints, use bizSeq
                params = {"serviceKey": API_KEY, "bizSeq": biz_seqs[0]}
                r = try_api(f"{label} (seq={biz_seqs[0]})", url, params)
                detail_results[f"{base_label}_{ep}"] = r

            time.sleep(0.5)

    results["detail_paths"] = detail_results


def test_existing_api():
    """기존 프로젝트에서 사용 중인 B553748 API 테스트."""
    print("\n=== 3. 기존 B553748 API 테스트 ===")
    url = "https://apis.data.go.kr/B553748/eiainformation/getListEiaInformation"
    params = {
        "serviceKey": API_KEY,
        "lng": 127.4875,
        "lat": 37.4912,
        "buffer": 5000,
        "returnType": "json",
    }
    r = try_api("B553748 기존 API", url, params)
    results["existing_api"] = r
    time.sleep(0.5)

    # pageNo variant
    params2 = {
        "serviceKey": API_KEY,
        "pageNo": 1,
        "numOfRows": 10,
        "returnType": "json",
    }
    r2 = try_api("B553748 목록 (pageNo)", url, params2)
    results["existing_api_list"] = r2


def main():
    test_spatial_wider()
    test_detail_alternative_paths()
    test_existing_api()

    out_path = Path(__file__).parent.parent.parent / "data" / "bulk" / "eia_spatial_api_test_v2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n결과 저장: {out_path}")

    # Summary
    print("\n=== 최종 요약 ===")
    for section, data in results.items():
        if isinstance(data, dict) and "status" in data:
            total_val = data.get("total", 0)
            print(f"  {section}: {data['status']}  (총 {total_val}건)")
        elif isinstance(data, dict):
            ok = sum(1 for v in data.values() if isinstance(v, dict) and "success" in v.get("status", ""))
            has_data = sum(1 for v in data.values() if isinstance(v, dict) and v.get("total", 0) > 0)
            print(f"  {section}: {ok}/{len(data)} 연결 성공, {has_data}개 데이터 있음")


if __name__ == "__main__":
    main()
