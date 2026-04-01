"""사전/전략/소규모 협의목록 전수 수집 + 패턴 분석 + cases.json 보강.

API: 1480523/BeffatStrtgySmallScaleDscssSttusInfoInqireService
     /getBsnsStrtgySmallScaleDscssListInfoInqire

Usage:
    python backend/scripts/collect_conslt_list.py
    python backend/scripts/collect_conslt_list.py --skip-collect   # 수집 건너뛰고 분석만
    python backend/scripts/collect_conslt_list.py --skip-analysis  # 수집만
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

import httpx

# ── 프로젝트 루트 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 로깅 ──
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)

# ── .env 로드 ──
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ── 경로 ──
RAW_DIR = PROJECT_ROOT / "data" / "bulk" / "raw"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "bulk" / "analysis"
CASES_PATH = PROJECT_ROOT / "data" / "cases" / "cases.json"
RAW_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# ── API ──
CONSLT_LIST_URL = (
    "https://apis.data.go.kr/1480523/"
    "BeffatStrtgySmallScaleDscssSttusInfoInqireService/"
    "getBsnsStrtgySmallScaleDscssListInfoInqire"
)

PAGE_SIZE = 100
API_DELAY = 2.0
RATE_LIMIT_WAIT = 35


# ================================================================
# 1. 수집
# ================================================================


def collect_all() -> list[dict]:
    """사전/전략/소규모 협의목록 전수 수집."""
    logger.info("=" * 60)
    logger.info("협의목록 전수 수집 시작")
    logger.info("=" * 60)

    all_items: list[dict] = []
    page_no = 1
    total_count = None

    with httpx.Client(follow_redirects=True, timeout=30) as client:
        while True:
            params = {
                "serviceKey": API_KEY,
                "pageNo": page_no,
                "numOfRows": PAGE_SIZE,
            }

            try:
                resp = client.get(CONSLT_LIST_URL, params=params)
            except Exception as e:
                logger.error("Page %d request error: %s", page_no, e)
                time.sleep(RATE_LIMIT_WAIT)
                continue

            # Rate limit handling
            if resp.status_code == 429:
                logger.warning("429 rate limit at page %d, waiting %ds...", page_no, RATE_LIMIT_WAIT)
                time.sleep(RATE_LIMIT_WAIT)
                continue

            if resp.status_code != 200:
                logger.error("Page %d HTTP %d: %s", page_no, resp.status_code, resp.text[:200])
                break

            # Parse XML
            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError as e:
                logger.error("Page %d XML parse error: %s", page_no, e)
                break

            # Check result code
            result_code = root.findtext(".//resultCode", "")
            if result_code != "00":
                msg = root.findtext(".//resultMsg", "")
                logger.error("Page %d API error: %s %s", page_no, result_code, msg)
                if result_code == "99":  # rate limit via API
                    time.sleep(RATE_LIMIT_WAIT)
                    continue
                break

            # Extract totalCount on first page
            if total_count is None:
                total_count = int(root.findtext(".//totalCount", "0"))
                total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
                logger.info("totalCount=%d, pages=%d", total_count, total_pages)

            # Extract items
            items = root.findall(".//item")
            page_items = []
            for item in items:
                record = {}
                for child in item:
                    record[child.tag] = child.text or ""
                page_items.append(record)

            all_items.extend(page_items)

            if page_no % 10 == 0 or page_no == 1:
                logger.info(
                    "Page %d/%d: %d items (total collected: %d)",
                    page_no, total_pages, len(page_items), len(all_items),
                )

            # Check if done
            if total_count and len(all_items) >= total_count:
                break
            if not page_items:
                logger.info("Empty page %d, stopping", page_no)
                break

            page_no += 1
            time.sleep(API_DELAY)

    logger.info("Collection done: %d items", len(all_items))
    return all_items


def save_collected(items: list[dict]) -> Path:
    """수집 데이터를 JSON으로 저장."""
    path = RAW_DIR / "conslt_list_all.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved: %s (%d items)", path, len(items))
    return path


# ================================================================
# 2. 패턴 분석 (로컬)
# ================================================================

# 사업명에서 유형 추출 규칙
_TYPE_PATTERNS = [
    (r"도로|도로건설|국도|고속도로|우회도로", "도로"),
    (r"택지|주거|주택|아파트|주거단지|신도시", "주거단지"),
    (r"산업단지|산단|공단|일반산업|국가산업", "산업단지"),
    (r"발전소|발전|태양광|풍력|LNG|화력|원자력", "발전소"),
    (r"관광|리조트|골프|레저|숙박|테마파크", "관광단지"),
    (r"항만|항|부두|마리나|크루즈|어항", "항만"),
    (r"하천|댐|저수지|수자원|하수|물재생", "하천"),
    (r"철도|KTX|전철|경전철|노면전차|궤도", "철도"),
    (r"군사|국방|군부대|사격장", "군사시설"),
    (r"폐기물|자원회수|소각|매립|폐기물처리", "폐기물"),
    (r"도시관리계획|지구단위계획|용도변경|도시계획", "도시계획"),
    (r"공원|녹지|자연공원|국립공원", "공원"),
    (r"학교|대학|캠퍼스", "교육시설"),
    (r"병원|의료|요양", "의료시설"),
    (r"물류|유통|창고|배송", "물류"),
    (r"매립|간척|공유수면", "매립/간척"),
    (r"하수도|상수도|정수장|급수", "상하수도"),
    (r"해상풍력|해양|연안", "해양"),
]


def classify_biz_type(biz_nm: str) -> str:
    """사업명에서 사업유형을 추출한다."""
    for pattern, label in _TYPE_PATTERNS:
        if re.search(pattern, biz_nm):
            return label
    return "기타"


def extract_year(per_cd: str) -> str:
    """perCd에서 연도를 추출한다 (예: WJ20260063 -> 2026)."""
    m = re.search(r"(\d{4})", per_cd)
    return m.group(1) if m else "미상"


def extract_region(per_cd: str) -> str:
    """perCd 접두사에서 지역을 추론한다."""
    prefix_map = {
        "GG": "국가기관",
        "HG": "수도권(서울/경기/인천)",
        "JJ": "전라권(전북/전남/제주)",
        "ME": "환경부",
        "ND": "경상권(경북/경남/부산/울산/대구)",
        "WJ": "강원/충청권",
        "YS": "충청/전라권",
    }
    prefix = per_cd[:2] if per_cd else ""
    return prefix_map.get(prefix, f"미상({prefix})")


def analyze_patterns(items: list[dict]) -> dict:
    """수집 데이터에서 패턴을 분석한다."""
    logger.info("=" * 60)
    logger.info("패턴 분석 시작 (%d items)", len(items))
    logger.info("=" * 60)

    # 사업유형 분류
    for item in items:
        item["_biz_type"] = classify_biz_type(item.get("bizNm", ""))
        item["_year"] = extract_year(item.get("perCd", ""))
        item["_region"] = extract_region(item.get("perCd", ""))

    # 사업유형별 분포
    type_dist = Counter(item["_biz_type"] for item in items)
    # 진행단계별 분포
    step_dist = Counter(item.get("ccilStepCd", "미상") for item in items)
    # 연도별 추이
    year_dist = Counter(item["_year"] for item in items)
    # 지역별 분포
    region_dist = Counter(item["_region"] for item in items)
    # perCd 접두사 분포
    prefix_dist = Counter(item.get("perCd", "")[:2] for item in items if item.get("perCd"))

    analysis = {
        "summary": {
            "total_count": len(items),
            "analyzed_at": datetime.now().isoformat(),
            "unique_biz_types": len(type_dist),
            "unique_steps": len(step_dist),
            "year_range": f"{min(year_dist.keys())}-{max(year_dist.keys())}",
        },
        "biz_type_distribution": dict(type_dist.most_common()),
        "step_distribution": dict(step_dist.most_common()),
        "year_distribution": dict(sorted(year_dist.items())),
        "region_distribution": dict(region_dist.most_common()),
        "prefix_distribution": dict(prefix_dist.most_common()),
        "top_biz_types_with_examples": {},
    }

    # 유형별 예시 사업 추가
    for biz_type, count in type_dist.most_common(10):
        examples = [
            {"bizNm": item["bizNm"], "perCd": item.get("perCd", ""), "step": item.get("ccilStepCd", "")}
            for item in items
            if item["_biz_type"] == biz_type
        ][:5]
        analysis["top_biz_types_with_examples"][biz_type] = {
            "count": count,
            "examples": examples,
        }

    # 로그 출력
    logger.info("\n사업유형별 분포:")
    for t, c in type_dist.most_common(15):
        logger.info("  %s: %d건 (%.1f%%)", t, c, c / len(items) * 100)

    logger.info("\n진행단계별 분포:")
    for s, c in step_dist.most_common(10):
        logger.info("  %s: %d건", s, c)

    logger.info("\n연도별 추이:")
    for y in sorted(year_dist.keys()):
        logger.info("  %s: %d건", y, year_dist[y])

    return analysis


def save_analysis(analysis: dict) -> Path:
    """분석 결과를 JSON으로 저장."""
    path = ANALYSIS_DIR / "conslt_patterns.json"
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Analysis saved: %s", path)
    return path


# ================================================================
# 3. DeepSeek LLM 보조 태깅
# ================================================================


def llm_tag_cases(cases_to_tag: list[dict]) -> list[dict]:
    """DeepSeek으로 cases에 key_issues, tags 등을 보조 태깅한다."""
    if not OPENROUTER_KEY:
        logger.warning("OPENROUTER_API_KEY not set, skipping LLM tagging")
        return cases_to_tag

    logger.info("DeepSeek LLM 보조 태깅 시작 (%d cases)", len(cases_to_tag))

    # Batch cases into groups of 10
    tagged = []
    batch_size = 10

    with httpx.Client(timeout=60) as client:
        for i in range(0, len(cases_to_tag), batch_size):
            batch = cases_to_tag[i : i + batch_size]
            batch_text = "\n".join(
                f"{j+1}. [{c['case_id']}] {c['project_type']} | {c.get('bizNm', '')} | {c.get('region', '')} | {c.get('step', '')}"
                for j, c in enumerate(batch)
            )

            prompt = f"""다음 환경영향평가 사전검토 사업 목록을 분석하여 각 사업별로 JSON 배열을 반환해주세요.

{batch_text}

각 사업에 대해 다음 필드를 생성해주세요:
- key_issues: 사업 유형과 위치를 고려한 예상 핵심 환경 이슈 3-4개 (배열)
- tags: 검색용 태그 5-6개 (배열)
- summary: 1-2문장 요약 (문자열)
- lessons_learned: 유사 사업에서의 교훈 1문장 (문자열)

JSON 배열만 반환하세요. 설명 없이 순수 JSON만."""

            try:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek/deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "환경영향평가 전문가. JSON만 반환."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4000,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]

                # Extract JSON from response
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    llm_results = json.loads(json_match.group())
                    for j, c in enumerate(batch):
                        if j < len(llm_results):
                            c.update(llm_results[j])
                    logger.info("  Batch %d-%d tagged", i + 1, i + len(batch))
                else:
                    logger.warning("  Batch %d: no JSON in LLM response", i + 1)

            except Exception as e:
                logger.warning("  LLM tagging error batch %d: %s", i + 1, e)

            tagged.extend(batch)
            time.sleep(1)

    return tagged


# ================================================================
# 4. cases.json 보강
# ================================================================


def enrich_cases(items: list[dict], analysis: dict) -> int:
    """실제 데이터로 cases.json을 보강한다."""
    logger.info("=" * 60)
    logger.info("cases.json 실데이터 보강")
    logger.info("=" * 60)

    with open(CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    existing_ids = {c["case_id"] for c in cases}
    next_id = max(int(c["case_id"].split("-")[1]) for c in cases) + 1

    # 유형별로 대표 사업 선별 (각 유형에서 다양한 단계의 사업을 선택)
    type_groups: dict[str, list[dict]] = {}
    for item in items:
        btype = item.get("_biz_type", "기타")
        if btype == "기타" or btype == "도시계획":
            continue
        type_groups.setdefault(btype, []).append(item)

    # 기존에 적은 유형 우선 + 새로운 유형 추가
    existing_type_counts = Counter(c.get("project_type", "") for c in cases)
    new_cases = []

    # 유형별 목표: 기존 2건 미만인 유형은 3건까지, 나머지는 1건 추가
    for btype, group in sorted(type_groups.items(), key=lambda x: existing_type_counts.get(x[0], 0)):
        existing_count = existing_type_counts.get(btype, 0)
        if btype in ("기타", "도시계획"):
            continue

        # 목표 추가 건수
        if existing_count == 0:
            target = 3
        elif existing_count < 5:
            target = 2
        else:
            target = 0

        if target == 0:
            continue

        # 다양한 진행단계에서 선택
        selected = []
        steps_seen = set()
        for item in group:
            step = item.get("ccilStepCd", "")
            if step not in steps_seen and len(selected) < target:
                steps_seen.add(step)
                selected.append(item)
        # 부족하면 아무거나 추가
        for item in group:
            if len(selected) >= target:
                break
            if item not in selected:
                selected.append(item)

        for item in selected:
            case_id = f"CASE-{next_id:03d}"
            next_id += 1

            region = extract_region(item.get("perCd", ""))
            year = extract_year(item.get("perCd", ""))

            case = {
                "case_id": case_id,
                "project_type": btype,
                "location_type": "미분류",
                "region": region,
                "bizNm": item.get("bizNm", ""),
                "bizSeq": item.get("bizSeq", ""),
                "perCd": item.get("perCd", ""),
                "step": item.get("ccilStepCd", ""),
                "year": year,
                "key_issues": [],
                "remediation_required": [],
                "public_concerns": [],
                "consultation_result": item.get("ccilStepCd", "진행중"),
                "source_document": f"사전환경성검토 협의 ({year})",
                "summary": f"{item.get('bizNm', '')} - {item.get('ccilStepCd', '')}",
                "tags": [btype, region, year],
                "lessons_learned": "",
            }
            new_cases.append(case)

    if not new_cases:
        logger.info("No new cases to add")
        return 0

    # LLM 태깅
    new_cases = llm_tag_cases(new_cases)

    # 기존 cases에 추가
    cases.extend(new_cases)

    with open(CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    logger.info("Added %d new cases (total: %d)", len(new_cases), len(cases))

    # 유형별 현황
    final_types = Counter(c.get("project_type", "") for c in cases)
    for t, cnt in final_types.most_common():
        logger.info("  %s: %d", t, cnt)

    return len(new_cases)


# ================================================================
# main
# ================================================================


def main():
    parser = argparse.ArgumentParser(description="사전/전략/소규모 협의목록 전수 수집")
    parser.add_argument("--skip-collect", action="store_true", help="수집 건너뛰기 (기존 파일 사용)")
    parser.add_argument("--skip-analysis", action="store_true", help="분석 건너뛰기")
    parser.add_argument("--skip-enrich", action="store_true", help="cases.json 보강 건너뛰기")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("사전/전략/소규모 협의목록 수집 + 분석")
    logger.info("시각: %s", datetime.now().isoformat())
    logger.info("=" * 60)

    if not API_KEY:
        logger.error("DATA_GO_KR_API_KEY not set")
        sys.exit(1)

    raw_path = RAW_DIR / "conslt_list_all.json"

    # 1. 수집
    if not args.skip_collect:
        items = collect_all()
        if not items:
            logger.error("Collection returned 0 items")
            sys.exit(1)
        save_collected(items)
    else:
        if not raw_path.exists():
            logger.error("No existing data at %s", raw_path)
            sys.exit(1)
        items = json.loads(raw_path.read_text(encoding="utf-8"))
        logger.info("Loaded existing data: %d items", len(items))

    # 2. 분석
    if not args.skip_analysis:
        analysis = analyze_patterns(items)
        save_analysis(analysis)
    else:
        analysis = {}

    # 3. cases.json 보강
    if not args.skip_enrich:
        enrich_cases(items, analysis)

    logger.info("\nDone!")


if __name__ == "__main__":
    main()
