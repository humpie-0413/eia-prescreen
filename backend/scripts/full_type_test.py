"""17개 사업유형 × 3사례 = 51건 전체 자동 테스트.

사용법:
    python backend/scripts/full_type_test.py [--base-url http://localhost:8000]

필요: 백엔드가 실행 중이어야 함 (uvicorn --port 8000).
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ─── 51건 테스트 데이터 ──────────────────────────────────────────

TEST_CASES: list[dict] = [
    # 1. 도시개발 (urban_dev)
    {"name": "위례신도시 2단계", "type": "urban_dev", "lat": 37.4780, "lng": 127.1430, "address": "서울 송파구/성남시", "scale": "면적 680만㎡"},
    {"name": "김포한강 신도시", "type": "urban_dev", "lat": 37.6320, "lng": 126.7150, "address": "경기도 김포시", "scale": "면적 1,170만㎡"},
    {"name": "나주 혁신도시", "type": "urban_dev", "lat": 34.9540, "lng": 126.7210, "address": "전라남도 나주시", "scale": "면적 736만㎡"},
    # 2. 산업입지 (industrial)
    {"name": "구미 4공단 확장", "type": "industrial", "lat": 36.1190, "lng": 128.3440, "address": "경상북도 구미시", "scale": "면적 330만㎡"},
    {"name": "당진 석문산단", "type": "industrial", "lat": 36.9280, "lng": 126.6870, "address": "충청남도 당진시", "scale": "면적 910만㎡"},
    {"name": "광양만권 율촌산단", "type": "industrial", "lat": 34.9150, "lng": 127.6200, "address": "전라남도 광양시", "scale": "면적 580만㎡"},
    # 3. 에너지개발 (energy)
    {"name": "삼척 화력발전소", "type": "energy", "lat": 37.4200, "lng": 129.1950, "address": "강원 삼척시", "scale": "2,100MW"},
    {"name": "영광 태양광단지", "type": "energy", "lat": 35.2780, "lng": 126.5120, "address": "전라남도 영광군", "scale": "100MW"},
    {"name": "태백 풍력발전단지", "type": "energy", "lat": 37.1640, "lng": 128.9860, "address": "강원 태백시", "scale": "50MW"},
    # 4. 항만건설 (port)
    {"name": "부산 신항 3단계", "type": "port", "lat": 35.0750, "lng": 128.8120, "address": "부산 강서구", "scale": "부두 3선석"},
    {"name": "새만금 신항만", "type": "port", "lat": 35.7900, "lng": 126.6800, "address": "전북 군산시", "scale": "부두 5선석"},
    {"name": "포항 영일만항 확장", "type": "port", "lat": 36.0480, "lng": 129.3790, "address": "경상북도 포항시", "scale": "부두 2선석"},
    # 5. 도로건설 (road)
    {"name": "세종~포천 고속도로", "type": "road", "lat": 36.8540, "lng": 127.1520, "address": "충북 음성군", "scale": "연장 128km"},
    {"name": "광주 제2순환도로", "type": "road", "lat": 35.1260, "lng": 126.8540, "address": "광주광역시 북구", "scale": "연장 42km"},
    {"name": "동해안 관광도로", "type": "road", "lat": 37.7930, "lng": 128.9120, "address": "강원 강릉시", "scale": "연장 18km"},
    # 6. 수자원개발 (water_resource)
    {"name": "영주댐", "type": "water_resource", "lat": 36.8720, "lng": 128.7240, "address": "경상북도 영주시", "scale": "저수량 1.8억톤"},
    {"name": "보현산댐", "type": "water_resource", "lat": 36.1680, "lng": 128.9870, "address": "경상북도 영천시", "scale": "저수량 0.5억톤"},
    {"name": "낙동강 하구둑 개선", "type": "water_resource", "lat": 35.0820, "lng": 128.9640, "address": "부산 사하구", "scale": "하구둑 개보수"},
    # 7. 철도건설 (railway)
    {"name": "수도권 GTX-D", "type": "railway", "lat": 37.3940, "lng": 126.9630, "address": "경기도 안양시", "scale": "연장 45km"},
    {"name": "남부내륙고속철도", "type": "railway", "lat": 35.2280, "lng": 128.6820, "address": "경상남도 함안군", "scale": "연장 180km"},
    {"name": "동해선 강릉~제진", "type": "railway", "lat": 37.7650, "lng": 128.8970, "address": "강원 강릉시", "scale": "연장 111km"},
    # 8. 공항건설 (airport)
    {"name": "가덕도 신공항", "type": "airport", "lat": 35.0720, "lng": 128.9310, "address": "부산 강서구", "scale": "활주로 3,500m"},
    {"name": "울릉공항", "type": "airport", "lat": 37.4840, "lng": 130.9060, "address": "경상북도 울릉군", "scale": "활주로 1,200m"},
    {"name": "흑산공항", "type": "airport", "lat": 34.6840, "lng": 125.4260, "address": "전라남도 신안군", "scale": "활주로 1,500m"},
    # 9. 하천이용개발 (river)
    {"name": "금강 살리기 2단계", "type": "river", "lat": 36.4720, "lng": 126.9310, "address": "충남 부여군", "scale": "연장 35km"},
    {"name": "영산강 자연성 회복", "type": "river", "lat": 34.9680, "lng": 126.4870, "address": "전남 무안군", "scale": "연장 25km"},
    {"name": "한탄강 지질공원 정비", "type": "river", "lat": 38.0940, "lng": 127.0780, "address": "경기도 연천군", "scale": "연장 15km"},
    # 10. 관광단지개발 (tourism)
    {"name": "설악 케이블카", "type": "tourism", "lat": 38.1190, "lng": 128.4650, "address": "강원 속초시", "scale": "연장 3.5km"},
    {"name": "해남 땅끝마을 리조트", "type": "tourism", "lat": 34.2940, "lng": 126.5280, "address": "전라남도 해남군", "scale": "면적 50만㎡"},
    {"name": "가평 복합리조트", "type": "tourism", "lat": 37.8120, "lng": 127.5340, "address": "경기도 가평군", "scale": "면적 80만㎡"},
    # 11. 산지개발 (mountain)
    {"name": "포천 채석장 확장", "type": "mountain", "lat": 37.8940, "lng": 127.2010, "address": "경기도 포천시", "scale": "면적 15만㎡"},
    {"name": "문경 석회석 광산", "type": "mountain", "lat": 36.7280, "lng": 128.1540, "address": "경상북도 문경시", "scale": "면적 40만㎡"},
    {"name": "제주 오름 채석", "type": "mountain", "lat": 33.4120, "lng": 126.5680, "address": "제주 서귀포시", "scale": "면적 8만㎡"},
    # 12. 체육시설 (sports)
    {"name": "평창 스키리조트 확장", "type": "sports", "lat": 37.6430, "lng": 128.6790, "address": "강원 평창군", "scale": "면적 200만㎡"},
    {"name": "세종 종합운동장", "type": "sports", "lat": 36.5120, "lng": 127.0020, "address": "세종특별자치시", "scale": "면적 30만㎡"},
    {"name": "해운대 해양스포츠센터", "type": "sports", "lat": 35.1580, "lng": 129.1640, "address": "부산 해운대구", "scale": "면적 5만㎡"},
    # 13. 폐기물처리시설 (waste)
    {"name": "수도권 광역소각장", "type": "waste", "lat": 37.5680, "lng": 126.7340, "address": "인천 서구", "scale": "처리 2,000톤/일"},
    {"name": "제주 자원순환센터", "type": "waste", "lat": 33.4580, "lng": 126.5740, "address": "제주 서귀포시", "scale": "처리 500톤/일"},
    {"name": "영남권 매립장 확장", "type": "waste", "lat": 35.4720, "lng": 129.0580, "address": "경상남도 양산시", "scale": "면적 100만㎡"},
    # 14. 국방군사시설 (military)
    {"name": "평택 미군기지 확장", "type": "military", "lat": 36.9640, "lng": 127.0320, "address": "경기도 평택시", "scale": "면적 1,470만㎡"},
    {"name": "제주 해군기지", "type": "military", "lat": 33.2270, "lng": 126.2560, "address": "제주 서귀포시", "scale": "면적 55만㎡"},
    {"name": "원주 종합훈련장", "type": "military", "lat": 37.3420, "lng": 127.9510, "address": "강원 원주시", "scale": "면적 300만㎡"},
    # 15. 토석광물채취 (mining)
    {"name": "보령 석탄광 재개발", "type": "mining", "lat": 36.3340, "lng": 126.6120, "address": "충남 보령시", "scale": "면적 25만㎡"},
    {"name": "강릉 규사 채취", "type": "mining", "lat": 37.7520, "lng": 128.8960, "address": "강원 강릉시", "scale": "면적 10만㎡"},
    {"name": "거제 골재 채취", "type": "mining", "lat": 34.8810, "lng": 128.6210, "address": "경상남도 거제시", "scale": "면적 12만㎡"},
    # 16. 매립간척 (reclamation)
    {"name": "인천 영종 2지구 매립", "type": "reclamation", "lat": 37.4630, "lng": 126.5720, "address": "인천 중구", "scale": "면적 400만㎡"},
    {"name": "군산 비응도 매립", "type": "reclamation", "lat": 35.9540, "lng": 126.5870, "address": "전북 군산시", "scale": "면적 250만㎡"},
    {"name": "목포 남항 매립", "type": "reclamation", "lat": 34.7870, "lng": 126.3920, "address": "전남 목포시", "scale": "면적 80만㎡"},
    # 17. 기타 (etc)
    {"name": "이천 물류센터", "type": "etc", "lat": 37.2720, "lng": 127.4350, "address": "경기도 이천시", "scale": "면적 30만㎡"},
    {"name": "대전 과학기술원 확장", "type": "etc", "lat": 36.3740, "lng": 127.3610, "address": "대전 유성구", "scale": "면적 15만㎡"},
    {"name": "세종 상수도 정수장", "type": "etc", "lat": 36.5240, "lng": 127.0180, "address": "세종특별자치시", "scale": "처리 10만톤/일"},
]

# 사업유형 한글명
TYPE_LABELS: dict[str, str] = {
    "urban_dev": "도시개발",
    "industrial": "산업입지",
    "energy": "에너지개발",
    "port": "항만건설",
    "road": "도로건설",
    "water_resource": "수자원개발",
    "railway": "철도건설",
    "airport": "공항건설",
    "river": "하천이용개발",
    "tourism": "관광단지개발",
    "mountain": "산지개발",
    "sports": "체육시설",
    "waste": "폐기물처리시설",
    "military": "국방군사시설",
    "mining": "토석광물채취",
    "reclamation": "매립간척",
    "etc": "기타",
}


# ─── 테스트 실행 ─────────────────────────────────────────────────

def run_test(base_url: str) -> dict:
    """51건 전체 테스트를 실행하고 결과를 반환한다."""
    api = base_url.rstrip("/") + "/api"
    results: list[dict] = []
    passed = 0
    failed = 0
    errors: list[dict] = []

    # 패턴 캐시 (유형별 1회만 호출)
    pattern_cache: dict[str, dict] = {}

    total = len(TEST_CASES)
    start_time = time.time()

    for idx, tc in enumerate(TEST_CASES, 1):
        name = tc["name"]
        ptype = tc["type"]
        label = TYPE_LABELS.get(ptype, ptype)
        print(f"[{idx:2d}/{total}] {label:8s} {name:24s} ", end="", flush=True)

        result: dict = {
            "index": idx,
            "name": name,
            "project_type": ptype,
            "korean_type": label,
            "screening_id": None,
            "checks": {},
            "passed": False,
            "failures": [],
        }

        try:
            # 1) 스크리닝 생성
            r = requests.post(f"{api}/screening", json={
                "project_name": name,
                "project_type": ptype,
                "project_scale": tc["scale"],
                "address": tc["address"],
                "location": {"lng": tc["lng"], "lat": tc["lat"]},
            }, timeout=30)
            r.raise_for_status()
            sid = r.json()["id"]
            result["screening_id"] = sid

            # 2) 평가 실행
            r = requests.post(f"{api}/screening/{sid}/evaluate",
                              json={"force": False}, timeout=60)
            r.raise_for_status()
            eval_data = r.json()

            # ── 검증 1: 리스크 카드 ──
            risk_cards = eval_data.get("risk_cards", [])
            n_risks = len(risk_cards)
            result["checks"]["risk_cards"] = n_risks
            if n_risks < 1:
                result["failures"].append(f"리스크 카드 0건")

            # ── 검증 2: 규제 매칭 ──
            r = requests.get(f"{api}/screening/{sid}/regulations", timeout=30)
            r.raise_for_status()
            reg_data = r.json()
            # 응답이 리스트(규제 목록) 또는 dict({"regulations": [...]})
            n_regs = len(reg_data) if isinstance(reg_data, list) else len(reg_data.get("regulations", []))
            result["checks"]["regulations"] = n_regs
            if n_regs < 1:
                result["failures"].append(f"규제 매칭 0건")

            # ── 검증 3: 유사사례 ──
            r = requests.post(f"{api}/screening/{sid}/similar-cases",
                              json={}, timeout=30)
            r.raise_for_status()
            cases_data = r.json()
            n_cases = len(cases_data.get("cases", []))
            result["checks"]["similar_cases"] = n_cases

            # ── 검증 4: 검토의견 예측 ──
            r = requests.post(f"{api}/screening/{sid}/predict-review",
                              json={}, timeout=30)
            r.raise_for_status()
            review_data = r.json()
            n_comments = len(review_data.get("predicted_comments", []))
            review_kr_type = review_data.get("korean_type", "?")
            review_total = review_data.get("total_past_cases", 0)
            review_months = review_data.get("avg_review_months")
            result["checks"]["predicted_comments"] = n_comments
            result["checks"]["review_korean_type"] = review_kr_type
            result["checks"]["review_total_past_cases"] = review_total
            result["checks"]["review_avg_months"] = review_months
            if n_comments < 1:
                result["failures"].append(f"검토의견 예측 0건")

            # ── 검증 5: 패턴 데이터 ──
            if ptype not in pattern_cache:
                r = requests.get(f"{api}/patterns/{ptype}", timeout=30)
                r.raise_for_status()
                pattern_cache[ptype] = r.json()
            pat = pattern_cache[ptype]
            n_pattern = pat.get("total_analyzed", 0)
            result["checks"]["pattern_total"] = n_pattern
            if n_pattern < 1:
                result["failures"].append(f"패턴 데이터 0건")

            # Top 예측 카테고리 기록
            if review_data.get("predicted_comments"):
                top = review_data["predicted_comments"][0]
                result["checks"]["top_comment_category"] = top.get("category", "?")
                result["checks"]["top_comment_pct"] = top.get("probability_pct", 0)

        except requests.RequestException as e:
            result["failures"].append(f"API 오류: {e}")
        except (KeyError, IndexError, TypeError) as e:
            result["failures"].append(f"데이터 파싱 오류: {e}")

        # 판정
        result["passed"] = len(result["failures"]) == 0
        if result["passed"]:
            passed += 1
            print("PASS")
        else:
            failed += 1
            print(f"FAIL --{'; '.join(result['failures'])}")
            errors.append(result)

        results.append(result)

    elapsed = time.time() - start_time

    # ── 사업유형별 요약 테이블 ──────────────────────────────
    print("\n" + "=" * 100)
    print("사업유형별 요약")
    print("=" * 100)
    print(f"{'유형':10s} {'코드':16s} {'사례':4s} {'Pass':4s} {'Fail':4s} "
          f"{'리스크':6s} {'규제':6s} {'의견':6s} {'패턴':8s} {'Top 카테고리':14s} {'Top%':6s}")
    print("-" * 100)

    # 유형별 집계
    type_groups: dict[str, list[dict]] = {}
    for r in results:
        pt = r["project_type"]
        type_groups.setdefault(pt, []).append(r)

    type_order = list(dict.fromkeys(tc["type"] for tc in TEST_CASES))
    for pt in type_order:
        group = type_groups.get(pt, [])
        label = TYPE_LABELS.get(pt, pt)
        n_pass = sum(1 for r in group if r["passed"])
        n_fail = len(group) - n_pass
        avg_risks = sum(r["checks"].get("risk_cards", 0) for r in group) / max(len(group), 1)
        avg_regs = sum(r["checks"].get("regulations", 0) for r in group) / max(len(group), 1)
        avg_comments = sum(r["checks"].get("predicted_comments", 0) for r in group) / max(len(group), 1)
        pattern_total = group[0]["checks"].get("pattern_total", 0) if group else 0
        # 가장 빈번한 top 카테고리
        top_cats = [r["checks"].get("top_comment_category", "?") for r in group if r["checks"].get("top_comment_category")]
        top_cat = max(set(top_cats), key=top_cats.count) if top_cats else "?"
        top_pcts = [r["checks"].get("top_comment_pct", 0) for r in group if r["checks"].get("top_comment_pct")]
        avg_top_pct = sum(top_pcts) / max(len(top_pcts), 1) if top_pcts else 0

        print(f"{label:10s} {pt:16s} {len(group):4d} {n_pass:4d} {n_fail:4d} "
              f"{avg_risks:6.1f} {avg_regs:6.1f} {avg_comments:6.1f} {pattern_total:8d} "
              f"{top_cat:14s} {avg_top_pct:5.1f}%")

    print("-" * 100)
    print(f"{'합계':10s} {'':16s} {total:4d} {passed:4d} {failed:4d}")
    print(f"\n소요시간: {elapsed:.1f}초  ({elapsed/total:.1f}초/건)")

    # ── 실패 사례 상세 리포트 ────────────────────────────
    if errors:
        print(f"\n{'=' * 80}")
        print(f"실패 사례 상세 ({len(errors)}건)")
        print("=" * 80)
        for err in errors:
            print(f"\n[{err['index']}] {err['name']} ({err['project_type']})")
            print(f"  screening_id: {err['screening_id']}")
            print(f"  checks: {json.dumps(err['checks'], ensure_ascii=False)}")
            for f in err["failures"]:
                print(f"  X {f}")

    # ── 최종 요약 ────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"최종 결과: {passed}/{total} PASSED, {failed}/{total} FAILED")
    print("=" * 80)

    return {
        "test_date": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
        "type_summary": {
            pt: {
                "korean_type": TYPE_LABELS.get(pt, pt),
                "count": len(group),
                "passed": sum(1 for r in group if r["passed"]),
                "failed": sum(1 for r in group if not r["passed"]),
                "avg_risk_cards": round(sum(r["checks"].get("risk_cards", 0) for r in group) / max(len(group), 1), 1),
                "avg_regulations": round(sum(r["checks"].get("regulations", 0) for r in group) / max(len(group), 1), 1),
                "avg_comments": round(sum(r["checks"].get("predicted_comments", 0) for r in group) / max(len(group), 1), 1),
                "pattern_total": group[0]["checks"].get("pattern_total", 0) if group else 0,
            }
            for pt, group in type_groups.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="17유형 × 3사례 = 51건 전체 테스트")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="백엔드 URL (기본: http://localhost:8000)")
    args = parser.parse_args()

    # 서버 상태 확인
    try:
        r = requests.get(f"{args.base_url}/health", timeout=5)
    except requests.ConnectionError:
        print(f"ERROR: 백엔드가 실행되지 않음 ({args.base_url})")
        print("  uvicorn backend.app.main:app --port 8000 으로 시작 후 재실행하세요.")
        sys.exit(1)

    print(f"백엔드: {args.base_url} (정상)")
    print(f"테스트 시작: 17유형 × 3사례 = {len(TEST_CASES)}건\n")

    report = run_test(args.base_url)

    # 결과 저장
    out_dir = Path(__file__).resolve().parent.parent.parent / "data" / "test_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "full_type_test.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out_path}")

    sys.exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
