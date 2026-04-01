"""51건 전체 웹 표시 데이터 수집 및 문서화.

각 사례의 대시보드/유사사례/검토의견/패턴 데이터를 수집하여
data/test_results/web_data_51cases.json + docs/WEB_DATA_51CASES.md 로 출력.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "http://localhost:8000/api"
ROOT = Path(__file__).resolve().parent.parent.parent

TEST_CASES = [
    {"name": "위례신도시 2단계", "type": "urban_dev", "lat": 37.4780, "lng": 127.1430, "addr": "서울 송파구/성남시", "scale": "면적 680만㎡"},
    {"name": "김포한강 신도시", "type": "urban_dev", "lat": 37.6320, "lng": 126.7150, "addr": "경기도 김포시", "scale": "면적 1,170만㎡"},
    {"name": "나주 혁신도시", "type": "urban_dev", "lat": 34.9540, "lng": 126.7210, "addr": "전라남도 나주시", "scale": "면적 736만㎡"},
    {"name": "구미 4공단 확장", "type": "industrial", "lat": 36.1190, "lng": 128.3440, "addr": "경상북도 구미시", "scale": "면적 330만㎡"},
    {"name": "당진 석문산단", "type": "industrial", "lat": 36.9280, "lng": 126.6870, "addr": "충청남도 당진시", "scale": "면적 910만㎡"},
    {"name": "광양만권 율촌산단", "type": "industrial", "lat": 34.9150, "lng": 127.6200, "addr": "전라남도 광양시", "scale": "면적 580만㎡"},
    {"name": "삼척 화력발전소", "type": "energy", "lat": 37.4200, "lng": 129.1950, "addr": "강원 삼척시", "scale": "2,100MW"},
    {"name": "영광 태양광단지", "type": "energy", "lat": 35.2780, "lng": 126.5120, "addr": "전라남도 영광군", "scale": "100MW"},
    {"name": "태백 풍력발전단지", "type": "energy", "lat": 37.1640, "lng": 128.9860, "addr": "강원 태백시", "scale": "50MW"},
    {"name": "부산 신항 3단계", "type": "port", "lat": 35.0750, "lng": 128.8120, "addr": "부산 강서구", "scale": "부두 3선석"},
    {"name": "새만금 신항만", "type": "port", "lat": 35.7900, "lng": 126.6800, "addr": "전북 군산시", "scale": "부두 5선석"},
    {"name": "포항 영일만항 확장", "type": "port", "lat": 36.0480, "lng": 129.3790, "addr": "경상북도 포항시", "scale": "부두 2선석"},
    {"name": "세종~포천 고속도로", "type": "road", "lat": 36.8540, "lng": 127.1520, "addr": "충북 음성군", "scale": "연장 128km"},
    {"name": "광주 제2순환도로", "type": "road", "lat": 35.1260, "lng": 126.8540, "addr": "광주광역시 북구", "scale": "연장 42km"},
    {"name": "동해안 관광도로", "type": "road", "lat": 37.7930, "lng": 128.9120, "addr": "강원 강릉시", "scale": "연장 18km"},
    {"name": "영주댐", "type": "water_resource", "lat": 36.8720, "lng": 128.7240, "addr": "경상북도 영주시", "scale": "저수량 1.8억톤"},
    {"name": "보현산댐", "type": "water_resource", "lat": 36.1680, "lng": 128.9870, "addr": "경상북도 영천시", "scale": "저수량 0.5억톤"},
    {"name": "낙동강 하구둑 개선", "type": "water_resource", "lat": 35.0820, "lng": 128.9640, "addr": "부산 사하구", "scale": "하구둑 개보수"},
    {"name": "수도권 GTX-D", "type": "railway", "lat": 37.3940, "lng": 126.9630, "addr": "경기도 안양시", "scale": "연장 45km"},
    {"name": "남부내륙고속철도", "type": "railway", "lat": 35.2280, "lng": 128.6820, "addr": "경상남도 함안군", "scale": "연장 180km"},
    {"name": "동해선 강릉~제진", "type": "railway", "lat": 37.7650, "lng": 128.8970, "addr": "강원 강릉시", "scale": "연장 111km"},
    {"name": "가덕도 신공항", "type": "airport", "lat": 35.0720, "lng": 128.9310, "addr": "부산 강서구", "scale": "활주로 3,500m"},
    {"name": "울릉공항", "type": "airport", "lat": 37.4840, "lng": 130.9060, "addr": "경상북도 울릉군", "scale": "활주로 1,200m"},
    {"name": "흑산공항", "type": "airport", "lat": 34.6840, "lng": 125.4260, "addr": "전라남도 신안군", "scale": "활주로 1,500m"},
    {"name": "금강 살리기 2단계", "type": "river", "lat": 36.4720, "lng": 126.9310, "addr": "충남 부여군", "scale": "연장 35km"},
    {"name": "영산강 자연성 회복", "type": "river", "lat": 34.9680, "lng": 126.4870, "addr": "전남 무안군", "scale": "연장 25km"},
    {"name": "한탄강 지질공원 정비", "type": "river", "lat": 38.0940, "lng": 127.0780, "addr": "경기도 연천군", "scale": "연장 15km"},
    {"name": "설악 케이블카", "type": "tourism", "lat": 38.1190, "lng": 128.4650, "addr": "강원 속초시", "scale": "연장 3.5km"},
    {"name": "해남 땅끝마을 리조트", "type": "tourism", "lat": 34.2940, "lng": 126.5280, "addr": "전라남도 해남군", "scale": "면적 50만㎡"},
    {"name": "가평 복합리조트", "type": "tourism", "lat": 37.8120, "lng": 127.5340, "addr": "경기도 가평군", "scale": "면적 80만㎡"},
    {"name": "포천 채석장 확장", "type": "mountain", "lat": 37.8940, "lng": 127.2010, "addr": "경기도 포천시", "scale": "면적 15만㎡"},
    {"name": "문경 석회석 광산", "type": "mountain", "lat": 36.7280, "lng": 128.1540, "addr": "경상북도 문경시", "scale": "면적 40만㎡"},
    {"name": "제주 오름 채석", "type": "mountain", "lat": 33.4120, "lng": 126.5680, "addr": "제주 서귀포시", "scale": "면적 8만㎡"},
    {"name": "평창 스키리조트 확장", "type": "sports", "lat": 37.6430, "lng": 128.6790, "addr": "강원 평창군", "scale": "면적 200만㎡"},
    {"name": "세종 종합운동장", "type": "sports", "lat": 36.5120, "lng": 127.0020, "addr": "세종특별자치시", "scale": "면적 30만㎡"},
    {"name": "해운대 해양스포츠센터", "type": "sports", "lat": 35.1580, "lng": 129.1640, "addr": "부산 해운대구", "scale": "면적 5만㎡"},
    {"name": "수도권 광역소각장", "type": "waste", "lat": 37.5680, "lng": 126.7340, "addr": "인천 서구", "scale": "처리 2,000톤/일"},
    {"name": "제주 자원순환센터", "type": "waste", "lat": 33.4580, "lng": 126.5740, "addr": "제주 서귀포시", "scale": "처리 500톤/일"},
    {"name": "영남권 매립장 확장", "type": "waste", "lat": 35.4720, "lng": 129.0580, "addr": "경상남도 양산시", "scale": "면적 100만㎡"},
    {"name": "평택 미군기지 확장", "type": "military", "lat": 36.9640, "lng": 127.0320, "addr": "경기도 평택시", "scale": "면적 1,470만㎡"},
    {"name": "제주 해군기지", "type": "military", "lat": 33.2270, "lng": 126.2560, "addr": "제주 서귀포시", "scale": "면적 55만㎡"},
    {"name": "원주 종합훈련장", "type": "military", "lat": 37.3420, "lng": 127.9510, "addr": "강원 원주시", "scale": "면적 300만㎡"},
    {"name": "보령 석탄광 재개발", "type": "mining", "lat": 36.3340, "lng": 126.6120, "addr": "충남 보령시", "scale": "면적 25만㎡"},
    {"name": "강릉 규사 채취", "type": "mining", "lat": 37.7520, "lng": 128.8960, "addr": "강원 강릉시", "scale": "면적 10만㎡"},
    {"name": "거제 골재 채취", "type": "mining", "lat": 34.8810, "lng": 128.6210, "addr": "경상남도 거제시", "scale": "면적 12만㎡"},
    {"name": "인천 영종 2지구 매립", "type": "reclamation", "lat": 37.4630, "lng": 126.5720, "addr": "인천 중구", "scale": "면적 400만㎡"},
    {"name": "군산 비응도 매립", "type": "reclamation", "lat": 35.9540, "lng": 126.5870, "addr": "전북 군산시", "scale": "면적 250만㎡"},
    {"name": "목포 남항 매립", "type": "reclamation", "lat": 34.7870, "lng": 126.3920, "addr": "전남 목포시", "scale": "면적 80만㎡"},
    {"name": "이천 물류센터", "type": "etc", "lat": 37.2720, "lng": 127.4350, "addr": "경기도 이천시", "scale": "면적 30만㎡"},
    {"name": "대전 과학기술원 확장", "type": "etc", "lat": 36.3740, "lng": 127.3610, "addr": "대전 유성구", "scale": "면적 15만㎡"},
    {"name": "세종 상수도 정수장", "type": "etc", "lat": 36.5240, "lng": 127.0180, "addr": "세종특별자치시", "scale": "처리 10만톤/일"},
]

TYPE_KR = {
    "urban_dev": "도시개발", "industrial": "산업입지", "energy": "에너지개발",
    "port": "항만건설", "road": "도로건설", "water_resource": "수자원개발",
    "railway": "철도건설", "airport": "공항건설", "river": "하천이용개발",
    "tourism": "관광단지개발", "mountain": "산지개발", "sports": "체육시설",
    "waste": "폐기물처리시설", "military": "국방군사시설", "mining": "토석광물채취",
    "reclamation": "매립간척", "etc": "기타",
}


def collect(tc: dict) -> dict:
    """한 사례의 웹 데이터를 수집."""
    r = requests.post(f"{BASE}/screening", json={
        "project_name": tc["name"], "project_type": tc["type"],
        "project_scale": tc["scale"], "address": tc["addr"],
        "location": {"lng": tc["lng"], "lat": tc["lat"]},
    }, timeout=30)
    r.raise_for_status()
    sid = r.json()["id"]

    # evaluate
    r = requests.post(f"{BASE}/screening/{sid}/evaluate", json={"force": False}, timeout=60)
    r.raise_for_status()
    ev = r.json()

    # regulations
    r = requests.get(f"{BASE}/screening/{sid}/regulations", timeout=30)
    regs = r.json() if r.ok else []

    # similar-cases
    r = requests.post(f"{BASE}/screening/{sid}/similar-cases", json={}, timeout=30)
    cases = r.json() if r.ok else {"cases": [], "total": 0}

    # checklist
    r = requests.get(f"{BASE}/screening/{sid}/checklist", timeout=30)
    checklist = r.json() if r.ok else {}

    # predict-review
    r = requests.post(f"{BASE}/screening/{sid}/predict-review", json={}, timeout=30)
    review = r.json() if r.ok else {}

    # patterns (by type, cached outside)
    return {
        "screening_id": sid,
        "name": tc["name"],
        "type": tc["type"],
        "type_kr": TYPE_KR.get(tc["type"], tc["type"]),
        "lat": tc["lat"], "lng": tc["lng"],
        "address": tc["addr"], "scale": tc["scale"],
        "risk_cards": ev.get("risk_cards", []),
        "regulations": regs if isinstance(regs, list) else regs.get("regulations", []),
        "similar_cases": cases.get("cases", []),
        "checklist": checklist,
        "review": review,
    }


def fmt_severity(s: str) -> str:
    return {"critical": "Critical", "major": "Major", "review": "Review", "info": "Info"}.get(s, s)


def write_md(all_data: list[dict], patterns: dict[str, dict], path: Path) -> None:
    """마크다운 문서 생성."""
    lines: list[str] = []
    w = lines.append

    w("# EIA Pre-Screen 51건 전체 웹 데이터 리포트")
    w("")
    w(f"> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"> 사례 수: {len(all_data)}건 (17개 사업유형 x 3사례)")
    w("> 데이터 범위: 대시보드(리스크+규제+체크리스트+검토의견), 유사사례, 패턴 통계")
    w("")

    # ── 전체 요약 테이블
    w("## 전체 요약")
    w("")
    w("| # | 사업명 | 유형 | 위치 | 리스크 | 규제 | 유사사례 | 검토의견 Top | 확률 |")
    w("|---|--------|------|------|--------|------|---------|-------------|------|")

    for i, d in enumerate(all_data, 1):
        n_risk = len(d["risk_cards"])
        sev_counts = {}
        for rc in d["risk_cards"]:
            s = fmt_severity(rc.get("severity", "?"))
            sev_counts[s] = sev_counts.get(s, 0) + 1
        sev_str = " ".join(f"{s}{c}" for s, c in sorted(sev_counts.items())) if sev_counts else "-"
        n_reg = len(d["regulations"])
        n_cases = len(d["similar_cases"])
        rv = d.get("review", {})
        comments = rv.get("predicted_comments", [])
        top_cat = comments[0]["category"] if comments else "-"
        top_pct = f'{comments[0]["probability_pct"]:.1f}%' if comments else "-"
        w(f"| {i} | {d['name']} | {d['type_kr']} | {d['address']} | {sev_str} ({n_risk}건) | {n_reg} | {n_cases} | {top_cat} | {top_pct} |")

    # ── 사업유형별 패턴 요약
    w("")
    w("## 사업유형별 패턴 통계")
    w("")
    w("| 유형 | 코드 | 패턴건수 | 평균검토(월) | 보완확률 | Top 지적항목 | 확률 |")
    w("|------|------|---------|-------------|---------|-------------|------|")

    type_order = list(dict.fromkeys(tc["type"] for tc in TEST_CASES))
    for pt in type_order:
        kr = TYPE_KR.get(pt, pt)
        pat = patterns.get(pt, {})
        total = pat.get("total_analyzed", 0)
        td_list = pat.get("type_data", [])
        if td_list:
            td = td_list[0]
            months = td.get("avg_review_months") or "-"
            suppl = f'{td.get("supplement_required_pct", 0):.1f}%' if td.get("supplement_required_pct") else "-"
            issues = td.get("common_issues", [])
            top_issue = issues[0]["issue"] if issues else "-"
            top_pct = f'{issues[0]["pct"]:.1f}%' if issues else "-"
        else:
            months = "-"
            suppl = "-"
            top_issue = "(데이터 없음)"
            top_pct = "-"
        w(f"| {kr} | {pt} | {total} | {months} | {suppl} | {top_issue} | {top_pct} |")

    # ── 사례별 상세 데이터
    w("")
    w("---")
    w("")
    prev_type = None
    for i, d in enumerate(all_data, 1):
        if d["type"] != prev_type:
            prev_type = d["type"]
            type_num = type_order.index(d["type"]) + 1
            w(f"## {type_num}. {d['type_kr']} ({d['type']})")
            w("")

        w(f"### [{i}] {d['name']}")
        w("")
        w(f"- **위치**: {d['address']} ({d['lat']}, {d['lng']})")
        w(f"- **규모**: {d['scale']}")
        w("")

        # 리스크 카드
        risk_cards = d["risk_cards"]
        w(f"**리스크 카드** ({len(risk_cards)}건)")
        w("")
        if risk_cards:
            w("| 심각도 | 제목 | 근거 |")
            w("|--------|------|------|")
            for rc in risk_cards:
                sev = fmt_severity(rc.get("severity", "?"))
                title = rc.get("title", "?")
                rationale = rc.get("rationale", "")
                if len(rationale) > 80:
                    rationale = rationale[:77] + "..."
                w(f"| {sev} | {title} | {rationale} |")
        else:
            w("(없음)")
        w("")

        # 규제 매칭
        regs = d["regulations"]
        w(f"**규제 매칭** ({len(regs)}건)")
        w("")
        if regs:
            for rg in regs[:5]:
                w(f"- {rg.get('regulation_name', rg.get('name', '?'))}")
        else:
            w("(V-world API 연결 필요 - 데모 모드에서 빈 결과)")
        w("")

        # 유사사례
        sim = d["similar_cases"]
        w(f"**유사사례** ({len(sim)}건)")
        w("")
        if sim:
            for sc in sim[:5]:
                name = sc.get("case_name") or sc.get("project_name", "?")
                score = sc.get("similarity_score", sc.get("score", 0))
                w(f"- {name} (유사도 {score:.0%})" if isinstance(score, float) and score <= 1
                  else f"- {name} (유사도 {score})")
        else:
            w("(매칭 사례 없음)")
        w("")

        # 검토의견 예측
        rv = d.get("review", {})
        comments = rv.get("predicted_comments", [])
        rv_total = rv.get("total_past_cases", 0)
        rv_months = rv.get("avg_review_months")
        rv_suppl = rv.get("supplement_required_pct")
        rv_kr = rv.get("korean_type", "?")

        w(f"**검토의견 예측** (유형: {rv_kr}, 과거 {rv_total}건)")
        if rv_months:
            w(f"- 평균 검토기간: {rv_months}개월 | 보완요구 확률: {rv_suppl}%")
        w("")
        if comments:
            w("| 카테고리 | 확률 | 과거건수 | 심각도 | 리스크매칭 |")
            w("|---------|------|---------|--------|-----------|")
            for c in comments:
                cat = c.get("category", "?")
                pct = f'{c.get("probability_pct", 0):.1f}%'
                past = f'{c.get("past_count", 0)}/{c.get("total_past_cases", 0)}'
                sev = c.get("severity", "?")
                matched = "O" if c.get("risk_matched") else "-"
                w(f"| {cat} | {pct} | {past} | {sev} | {matched} |")
        w("")

        # 체크리스트 요약
        cl = d.get("checklist", {})
        items = cl.get("items", cl.get("checklist", []))
        if items:
            w(f"**현장조사 체크리스트** ({len(items)}항목)")
            w("")
            for item in items[:8]:
                if isinstance(item, dict):
                    w(f"- {item.get('item', item.get('title', item.get('description', str(item))))}")
                else:
                    w(f"- {item}")
            if len(items) > 8:
                w(f"- ... 외 {len(items) - 8}항목")
            w("")

        w("---")
        w("")

    return "\n".join(lines)


def main():
    # health check
    try:
        requests.get(f"{BASE.replace('/api', '')}/health", timeout=5)
    except requests.ConnectionError:
        print("ERROR: backend not running on port 8000")
        sys.exit(1)

    total = len(TEST_CASES)
    print(f"Collecting web data for {total} cases...")

    # patterns cache (1 call per type)
    patterns: dict[str, dict] = {}
    type_order = list(dict.fromkeys(tc["type"] for tc in TEST_CASES))
    for pt in type_order:
        r = requests.get(f"{BASE}/patterns/{pt}", timeout=30)
        if r.ok:
            patterns[pt] = r.json()
        else:
            patterns[pt] = {}

    all_data: list[dict] = []
    t0 = time.time()

    for i, tc in enumerate(TEST_CASES, 1):
        elapsed = time.time() - t0
        eta = (elapsed / max(i - 1, 1)) * (total - i + 1) if i > 1 else 0
        print(f"[{i:2d}/{total}] {tc['name']:24s} ...", end="", flush=True)

        try:
            data = collect(tc)
            n_risk = len(data["risk_cards"])
            n_reg = len(data["regulations"])
            n_cases = len(data["similar_cases"])
            rv = data.get("review", {})
            top = rv.get("predicted_comments", [{}])[0].get("category", "?") if rv.get("predicted_comments") else "?"
            print(f" risks={n_risk} regs={n_reg} cases={n_cases} top={top}  ({eta:.0f}s left)")
            all_data.append(data)
        except Exception as e:
            print(f" ERROR: {e}")
            all_data.append({
                "name": tc["name"], "type": tc["type"],
                "type_kr": TYPE_KR.get(tc["type"], "?"),
                "address": tc["addr"], "scale": tc["scale"],
                "lat": tc["lat"], "lng": tc["lng"],
                "risk_cards": [], "regulations": [],
                "similar_cases": [], "checklist": {},
                "review": {}, "error": str(e),
            })

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s ({elapsed/total:.1f}s/case)")

    # Save JSON
    out_dir = ROOT / "data" / "test_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "web_data_51cases.json"
    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "elapsed_seconds": round(elapsed, 1),
        "patterns": patterns,
        "cases": all_data,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {json_path}")

    # Generate markdown
    md_path = ROOT / "docs" / "WEB_DATA_51CASES.md"
    md_content = write_md(all_data, patterns, md_path)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
