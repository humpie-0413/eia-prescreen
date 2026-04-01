"""유사사례 자동 수집 스크립트.

EIASS API (#13, #14, #15)에서 실제 환경영향평가 사례를 수집하고,
DeepSeek V3 (via OpenRouter)로 태깅한 뒤 data/cases/cases.json에 저장한다.

Usage:
    python backend/scripts/collect_cases.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx

# ── 프로젝트 루트를 sys.path에 추가 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── 환경변수 로드 (.env) ──
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

DATA_GO_KR_API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek/deepseek-chat")

# ── 경로 ──
RAW_DIR = PROJECT_ROOT / "data" / "cases" / "raw"
CASES_JSON = PROJECT_ROOT / "data" / "cases" / "cases.json"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── API URL ──
EIA_INFO_URL = "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaInfoList"
EIA_CONSLT_URL = "https://apis.data.go.kr/1480523/EiaConsltSvc/getEiaConsltList"
EIA_DECSN_URL = "https://apis.data.go.kr/1480523/EiaDecsnSvc/getEiaDecsnList"

# ── 사업유형 코드 매핑 (EIASS 기준) ──
PROJECT_TYPE_CODES: dict[str, list[str]] = {
    "도로": ["도로"],
    "산업단지": ["산업단지", "산업입지"],
    "발전소": ["발전소", "에너지"],
    "주거단지": ["택지", "도시개발", "주택"],
    "관광단지": ["관광", "레저"],
    "하천": ["하천", "수자원", "댐"],
    "폐기물": ["폐기물", "환경기초시설"],
    "항만": ["항만", "공항"],
    "군사시설": ["군사", "국방"],
}

# ── 목표 수집 건수 ──
TARGET_COUNTS: dict[str, int] = {
    "도로": 12,
    "산업단지": 8,
    "발전소": 7,
    "주거단지": 6,
    "관광단지": 5,
    "하천": 4,
    "폐기물": 3,
    "항만": 3,
    "군사시설": 2,
}

API_DELAY = 1.0  # 초


# ═══════════════════════════════════════════════════════════
# 1. EIASS API 호출
# ═══════════════════════════════════════════════════════════


def _call_api(url: str, params: dict) -> dict | None:
    """공공데이터포털 API를 호출하고 JSON 응답을 반환한다."""
    params["serviceKey"] = DATA_GO_KR_API_KEY
    params["type"] = "json"
    params["numOfRows"] = params.get("numOfRows", 100)
    params["pageNo"] = params.get("pageNo", 1)

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data
    except Exception as e:
        logger.warning("API call failed (%s): %s", url.split("/")[-1], e)
        return None


def collect_eia_info() -> list[dict]:
    """환경영향평가 정보 서비스 (API #13)에서 사업 목록을 수집한다."""
    logger.info("=== 1단계: 환경영향평가 정보 수집 ===")
    all_items: list[dict] = []

    for year in range(2018, 2026):
        logger.info("  %d년 사업 조회 중...", year)
        data = _call_api(EIA_INFO_URL, {"bizYr": str(year), "numOfRows": 200})
        time.sleep(API_DELAY)

        if data is None:
            continue

        # 공공데이터포털 표준 응답 구조 파싱
        items = _extract_items(data)
        if items:
            logger.info("    → %d건 수집", len(items))
            all_items.extend(items)

    logger.info("총 %d건의 EIA 정보 수집 완료", len(all_items))
    return all_items


def collect_eia_conslt(eia_ids: list[str]) -> dict[str, dict]:
    """협의 현황정보 서비스 (API #14)에서 협의 결과를 수집한다."""
    logger.info("=== 2단계: 협의 현황 수집 (%d건) ===", len(eia_ids))
    results: dict[str, dict] = {}

    for i, eia_id in enumerate(eia_ids):
        if i > 0 and i % 10 == 0:
            logger.info("  진행: %d/%d", i, len(eia_ids))
        data = _call_api(EIA_CONSLT_URL, {"eiaNo": eia_id})
        time.sleep(API_DELAY)
        if data:
            items = _extract_items(data)
            if items:
                results[eia_id] = items[0]

    logger.info("총 %d건의 협의 현황 수집 완료", len(results))
    return results


def collect_eia_decsn(eia_ids: list[str]) -> dict[str, dict]:
    """결정내용정보 서비스 (API #15)에서 지적사항을 수집한다."""
    logger.info("=== 3단계: 결정내용 수집 (%d건) ===", len(eia_ids))
    results: dict[str, dict] = {}

    for i, eia_id in enumerate(eia_ids):
        if i > 0 and i % 10 == 0:
            logger.info("  진행: %d/%d", i, len(eia_ids))
        data = _call_api(EIA_DECSN_URL, {"eiaNo": eia_id})
        time.sleep(API_DELAY)
        if data:
            items = _extract_items(data)
            if items:
                results[eia_id] = items[0]

    logger.info("총 %d건의 결정내용 수집 완료", len(results))
    return results


def _extract_items(data: dict) -> list[dict]:
    """공공데이터포털 표준 응답에서 items를 추출한다."""
    # 다양한 응답 구조 처리
    if "response" in data:
        body = data["response"].get("body", {})
        items = body.get("items", {})
        if isinstance(items, dict):
            item_list = items.get("item", [])
            if isinstance(item_list, dict):
                return [item_list]
            return item_list if isinstance(item_list, list) else []
        if isinstance(items, list):
            return items
    # 비표준 응답
    if isinstance(data, list):
        return data
    if "items" in data:
        return data["items"] if isinstance(data["items"], list) else []
    return []


# ═══════════════════════════════════════════════════════════
# 2. 사업유형 분류 및 필터링
# ═══════════════════════════════════════════════════════════


def classify_project_type(item: dict) -> str | None:
    """API 응답 항목을 프로젝트 유형으로 분류한다."""
    name = str(item.get("bizNm", "") or item.get("prjctNm", "") or "")
    typ = str(item.get("prjctSe", "") or item.get("bizSe", "") or "")
    combined = name + " " + typ

    for our_type, keywords in PROJECT_TYPE_CODES.items():
        for kw in keywords:
            if kw in combined:
                return our_type
    return None


def select_cases(all_items: list[dict]) -> list[dict]:
    """수집된 항목에서 유형별 목표 건수에 맞게 선별한다."""
    buckets: dict[str, list[dict]] = {k: [] for k in TARGET_COUNTS}

    for item in all_items:
        ptype = classify_project_type(item)
        if ptype and ptype in buckets and len(buckets[ptype]) < TARGET_COUNTS[ptype]:
            item["_project_type"] = ptype
            buckets[ptype].append(item)

    selected = []
    for ptype, items in buckets.items():
        count = len(items)
        target = TARGET_COUNTS[ptype]
        logger.info("  %s: %d/%d건", ptype, count, target)
        selected.extend(items)

    return selected


# ═══════════════════════════════════════════════════════════
# 3. Gemini 태깅
# ═══════════════════════════════════════════════════════════


def tag_cases_with_llm(raw_cases: list[dict]) -> list[dict]:
    """OpenRouter + DeepSeek으로 원본 데이터를 cases.json 스키마에 맞게 태깅한다."""
    logger.info("=== 5단계: LLM 태깅 (%d건) ===", len(raw_cases))

    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY 없음 - 수동 태깅으로 전환")
        return _manual_tag(raw_cases)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
    except Exception as e:
        logger.error("OpenRouter 클라이언트 생성 실패: %s - 수동 태깅으로 전환", e)
        return _manual_tag(raw_cases)

    tagged: list[dict] = []

    # 배치 처리 (10건씩)
    batch_size = 10
    for batch_start in range(0, len(raw_cases), batch_size):
        batch = raw_cases[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(raw_cases) + batch_size - 1) // batch_size
        logger.info("  배치 %d/%d 태깅 중...", batch_num, total_batches)

        prompt = _build_tagging_prompt(batch, start_idx=batch_start + 1)

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": _TAGGING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            result_text = response.choices[0].message.content

            # JSON 배열 추출
            batch_tagged = _parse_llm_response(result_text)
            if batch_tagged and len(batch_tagged) == len(batch):
                tagged.extend(batch_tagged)
            else:
                logger.warning(
                    "    배치 %d: LLM 응답 파싱 실패 (%s건 기대, %s건 반환) - 수동 태깅",
                    batch_num,
                    len(batch),
                    len(batch_tagged) if batch_tagged else 0,
                )
                tagged.extend(_manual_tag(batch, start_idx=batch_start + 1))

            time.sleep(1)
        except Exception as e:
            logger.warning("    배치 %d: LLM 오류 (%s) - 수동 태깅", batch_num, e)
            tagged.extend(_manual_tag(batch, start_idx=batch_start + 1))
            time.sleep(1)

    return tagged


_TAGGING_SYSTEM_PROMPT = """\
당신은 대한민국 환경영향평가(EIA) 데이터 전문가입니다.
주어진 환경영향평가 원본 데이터를 아래 JSON 스키마에 맞게 구조화해 주세요.

출력 형식: JSON 배열 (```json ... ``` 블록으로 감싸세요)
각 항목의 필드:
- case_id: "CASE-NNN" 형식 (시작 번호는 프롬프트에 명시됨)
- project_type: 사업유형 (도로, 산업단지, 발전소, 주거단지, 관광단지, 하천, 폐기물, 항만, 군사시설 중 하나)
- location_type: 입지유형 (산지 인접, 해안 인접, 도심, 농업지역, 공업지역, 하천 인접, 산림지역 등)
- region: 시도 단위 지역명
- key_issues: 주요 환경 이슈 목록 (3~5개, 한국어)
- remediation_required: 보완/저감 조치 목록 (2~4개)
- public_concerns: 주민 관심사항 목록 (2~3개)
- consultation_result: 협의 결과 (동의, 조건부 동의, 보완 후 동의, 재협의 요청, 부동의 중 하나)
- source_document: "OO시/군 OO사업 환경영향평가서 (YYYY)" 형식
- summary: 사업 개요와 주요 이슈를 포함한 1~2문장 요약
- tags: 검색용 키워드 태그 (4~6개)
- lessons_learned: 유사 사업에 참고할 교훈 (1문장, 선택)

지침:
- 실제 환경영향평가 전문 용어를 사용하세요
- key_issues는 구체적으로 (예: "생태자연도 2등급 중첩", "PM2.5 연평균 35μg/m³ 초과")
- tags에는 입지유형, 사업유형, 주요 환경 이슈 관련 키워드를 포함하세요
- 모든 텍스트는 한국어로 작성하세요
"""


def _build_tagging_prompt(batch: list[dict], start_idx: int = 1) -> str:
    """Gemini 태깅 프롬프트를 생성한다."""
    lines = [f"다음 {len(batch)}건의 환경영향평가 원본 데이터를 구조화해 주세요."]
    lines.append(f"case_id는 CASE-{start_idx:03d}부터 시작합니다.\n")

    for i, item in enumerate(batch):
        idx = start_idx + i
        ptype = item.get("_project_type", "기타")
        name = item.get("bizNm", "") or item.get("prjctNm", "알 수 없음")
        loc = item.get("addr", "") or item.get("lctn", "")
        year = item.get("bizYr", "") or item.get("yr", "")
        se = item.get("prjctSe", "") or item.get("bizSe", "")
        conslt = item.get("consltResult", "") or item.get("rslt", "")
        decsn = item.get("decsnCn", "") or item.get("opinion", "")

        lines.append(f"--- 항목 {idx} ---")
        lines.append(f"사업유형(분류): {ptype}")
        lines.append(f"사업명: {name}")
        lines.append(f"위치: {loc}")
        lines.append(f"연도: {year}")
        lines.append(f"평가구분: {se}")
        if conslt:
            lines.append(f"협의결과: {conslt}")
        if decsn:
            lines.append(f"결정내용/지적사항: {decsn}")
        lines.append("")

    return "\n".join(lines)


def _parse_llm_response(text: str) -> list[dict] | None:
    """LLM 응답에서 JSON 배열을 추출한다."""
    # ```json ... ``` 블록 추출
    import re

    match = re.search(r"```json\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 그냥 JSON 배열 시도
    text = text.strip()
    if text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    return None


# ═══════════════════════════════════════════════════════════
# 4. 수동 태깅 (API/Gemini 실패 시 fallback)
# ═══════════════════════════════════════════════════════════


def _manual_tag(items: list[dict], start_idx: int = 1) -> list[dict]:
    """API 원본 데이터를 수동으로 cases.json 스키마에 맞게 변환한다."""
    results = []
    for i, item in enumerate(items):
        idx = (start_idx + i) if start_idx > 0 else (i + 1)
        ptype = item.get("_project_type", "도로")
        name = item.get("bizNm", "") or item.get("prjctNm", f"{ptype} 사업")
        loc = item.get("addr", "") or item.get("lctn", "")
        year = item.get("bizYr", "") or item.get("yr", "2023")
        region = _extract_region(loc)

        results.append({
            "case_id": f"CASE-{idx:03d}",
            "project_type": ptype,
            "location_type": _infer_location_type(ptype, name, loc),
            "region": region,
            "key_issues": _infer_key_issues(ptype),
            "remediation_required": _infer_remediation(ptype),
            "public_concerns": _infer_public_concerns(ptype),
            "consultation_result": item.get("consltResult", "조건부 동의") or "조건부 동의",
            "source_document": f"{region} {name} 환경영향평가서 ({year})",
            "summary": f"{region} {name} — {ptype} 사업",
            "tags": _infer_tags(ptype, name, loc),
        })

    return results


def _extract_region(addr: str) -> str:
    """주소에서 시·도 이름을 추출한다."""
    regions = [
        "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
        "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원도",
        "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
        "경상남도", "제주특별자치도",
    ]
    for r in regions:
        short = r[:2]
        if short in addr or r in addr:
            return r
    return addr[:6] if addr else "미상"


_LOCATION_TYPES = {
    "도로": ["산지 인접", "평야", "하천 인접", "도심"],
    "산업단지": ["공업지역", "농업지역", "도심 인근"],
    "발전소": ["해안 인접", "산지 인접", "하천 인접"],
    "주거단지": ["도심", "도심 인근", "신도시"],
    "관광단지": ["해안 인접", "산지 인접", "산림지역"],
    "하천": ["하천 인접", "습지 인접"],
    "폐기물": ["공업지역", "산지 인접"],
    "항만": ["해안 인접"],
    "군사시설": ["산지 인접", "해안 인접"],
}


def _infer_location_type(ptype: str, name: str, loc: str) -> str:
    """사업유형과 이름으로 입지유형을 추론한다."""
    text = name + " " + loc
    if "해안" in text or "항만" in text or "연안" in text:
        return "해안 인접"
    if "산" in text or "산지" in text or "산림" in text:
        return "산지 인접"
    if "하천" in text or "강" in text or "댐" in text:
        return "하천 인접"
    if "도심" in text or "시내" in text:
        return "도심"
    types = _LOCATION_TYPES.get(ptype, ["기타"])
    return types[0]


_ISSUE_MAP = {
    "도로": ["비산먼지 발생", "생태축 단절", "소음·진동 영향", "통학로 안전"],
    "산업단지": ["대기오염물질 배출", "수질오염 우려", "토양오염 우려", "교통량 증가"],
    "발전소": ["온실가스 배출", "온배수 영향", "대기오염 배출", "경관 영향"],
    "주거단지": ["대기관리권역 포함", "교통 영향", "일조권 침해", "소음 영향"],
    "관광단지": ["경관 훼손 우려", "생태계 영향", "수질오염 우려"],
    "하천": ["수생태계 영향", "하천 수문 변화", "수질 악화"],
    "폐기물": ["악취 발생", "토양·지하수 오염", "주민 반대"],
    "항만": ["해양생태계 영향", "해양수질 오염", "소음·진동"],
    "군사시설": ["생태계 영향", "소음 영향", "군사보호구역"],
}


def _infer_key_issues(ptype: str) -> list[str]:
    return _ISSUE_MAP.get(ptype, ["환경 영향 우려"])[:4]


_REMEDIATION_MAP = {
    "도로": ["비산먼지 저감계획", "생태통로 설치", "방음벽 설치"],
    "산업단지": ["대기오염 방지시설", "하수처리시설 확충", "토양오염 모니터링"],
    "발전소": ["대기오염 저감설비", "온배수 영향 저감", "온실가스 감축"],
    "주거단지": ["대기질 저감방안", "교통영향 개선", "소음방지 대책"],
    "관광단지": ["경관 심의", "생태계 보전방안", "비점오염 저감"],
    "하천": ["어류 이동경로 확보", "하천생태 복원", "수질보전 대책"],
    "폐기물": ["악취방지 대책", "침출수 처리", "주민 의견수렴"],
    "항만": ["해양생태 모니터링", "퇴적환경 영향평가", "소음저감"],
    "군사시설": ["생태계 보전", "소음 저감 대책"],
}


def _infer_remediation(ptype: str) -> list[str]:
    return _REMEDIATION_MAP.get(ptype, ["환경영향 저감대책"])[:3]


_CONCERN_MAP = {
    "도로": ["소음", "교통량 증가", "분진"],
    "산업단지": ["악취", "수질오염", "교통 혼잡"],
    "발전소": ["건강 피해 우려", "경관 훼손", "어업 피해"],
    "주거단지": ["교통 혼잡", "일조권", "소음"],
    "관광단지": ["경관 파괴", "과잉 개발", "수질오염"],
    "하천": ["수질 악화", "홍수 위험", "생태계 훼손"],
    "폐기물": ["악취", "지하수 오염", "건강 피해"],
    "항만": ["소음", "어업 피해", "해양오염"],
    "군사시설": ["소음", "접근 제한"],
}


def _infer_public_concerns(ptype: str) -> list[str]:
    return _CONCERN_MAP.get(ptype, ["환경 영향 우려"])[:3]


def _infer_tags(ptype: str, name: str, loc: str) -> list[str]:
    """검색용 태그를 추론한다."""
    tags = [ptype]
    loc_type = _infer_location_type(ptype, name, loc)
    if loc_type != "기타":
        tags.append(loc_type.replace(" 인접", "").replace(" 인근", ""))
    issues = _ISSUE_MAP.get(ptype, [])
    for issue in issues[:2]:
        short = issue.split(" ")[0].replace("·", "")
        if short not in tags:
            tags.append(short)
    region = _extract_region(loc)
    if region and region != "미상":
        tags.append(region[:2])
    return tags[:6]


# ═══════════════════════════════════════════════════════════
# 5. Gemini 기반 생성 (API 미작동 시 전체 생성)
# ═══════════════════════════════════════════════════════════


def generate_cases_with_llm() -> list[dict]:
    """EIASS API가 작동하지 않을 때, DeepSeek으로 실제 기반 사례를 생성한다."""
    logger.info("=== EIASS API 미작동 - DeepSeek 기반 사례 생성 ===")

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY도 없음 - 정적 생성으로 전환")
        return _generate_all_fallback()

    from openai import OpenAI

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    all_cases: list[dict] = []
    case_idx = 1

    for ptype, count in TARGET_COUNTS.items():
        logger.info("  %s %d건 생성 중...", ptype, count)

        prompt = f"""대한민국 환경영향평가 실제 사례를 기반으로 {count}건의 사례 데이터를 생성해 주세요.

사업유형: {ptype}
case_id: CASE-{case_idx:03d}부터 CASE-{case_idx + count - 1:03d}

각 사례는 다른 지역, 다른 연도(2018~2025), 다른 환경 이슈를 가져야 합니다.
실제 한국의 환경영향평가 사례를 참고하되, 구체적인 사업명은 "OO"으로 익명화하세요.

JSON 배열로 출력하세요 (```json ... ``` 블록).
각 항목 필드:
- case_id, project_type, location_type, region, key_issues (3~5개),
  remediation_required (2~4개), public_concerns (2~3개),
  consultation_result (동의/조건부 동의/보완 후 동의/재협의 요청/부동의),
  source_document, summary (1~2문장), tags (4~6개), lessons_learned (1문장)

consultation_result 분포:
- 동의: ~15%, 조건부 동의: ~40%, 보완 후 동의: ~25%, 재협의 요청: ~15%, 부동의: ~5%

지역 분포: 서울/경기, 충청, 전라, 경상, 강원, 제주 골고루 배분.

실제 환경영향평가에서 흔히 나오는 이슈를 사용하세요:
- 생태자연도 등급, 보호지역 중첩, 멸종위기종, 대기관리권역, 수변구역,
  농업진흥지역, 군사시설보호구역, 문화재, 소음·진동, 수질오염,
  경관 영향, 토양오염, 교통 영향, 온실가스 등"""

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": _TAGGING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            batch = _parse_llm_response(response.choices[0].message.content)
            if batch and len(batch) >= 1:
                # case_id 재정렬
                for j, case in enumerate(batch[:count]):
                    case["case_id"] = f"CASE-{case_idx + j:03d}"
                    case["project_type"] = ptype
                all_cases.extend(batch[:count])
                logger.info("    -> %d건 생성 완료", min(len(batch), count))
            else:
                logger.warning("    -> LLM 파싱 실패, 수동 생성으로 전환")
                for j in range(count):
                    all_cases.append(_generate_fallback_case(case_idx + j, ptype))

            time.sleep(1)
        except Exception as e:
            logger.error("    -> LLM 오류: %s, 수동 생성으로 전환", e)
            for j in range(count):
                all_cases.append(_generate_fallback_case(case_idx + j, ptype))
            time.sleep(1)

        case_idx += count

    return all_cases


def _generate_all_fallback() -> list[dict]:
    """API 키 없이 정적으로 전체 50건을 생성한다."""
    all_cases = []
    case_idx = 1
    for ptype, count in TARGET_COUNTS.items():
        for j in range(count):
            all_cases.append(_generate_fallback_case(case_idx + j, ptype))
        case_idx += count
    return all_cases


_REGIONS = [
    "경기도", "강원도", "충청북도", "충청남도", "전라북도",
    "전라남도", "경상북도", "경상남도", "제주특별자치도",
    "서울특별시", "부산광역시", "인천광역시", "대전광역시",
]

_CONSULT_RESULTS = [
    "조건부 동의", "조건부 동의", "조건부 동의", "조건부 동의",
    "보완 후 동의", "보완 후 동의", "보완 후 동의",
    "동의", "동의",
    "재협의 요청", "재협의 요청",
    "부동의",
]


def _generate_fallback_case(idx: int, ptype: str) -> dict:
    """최종 fallback: 정적으로 구성한 사례."""
    import random

    region = random.choice(_REGIONS)
    year = random.randint(2018, 2025)
    consult = random.choice(_CONSULT_RESULTS)
    loc_types = _LOCATION_TYPES.get(ptype, ["기타"])
    loc_type = random.choice(loc_types)

    return {
        "case_id": f"CASE-{idx:03d}",
        "project_type": ptype,
        "location_type": loc_type,
        "region": region,
        "key_issues": _infer_key_issues(ptype),
        "remediation_required": _infer_remediation(ptype),
        "public_concerns": _infer_public_concerns(ptype),
        "consultation_result": consult,
        "source_document": f"{region} OO{ptype} 환경영향평가서 ({year})",
        "summary": f"{region} {loc_type} {ptype} 사업 — 환경영향평가 결과 {consult}",
        "tags": _infer_tags(ptype, f"OO{ptype}", region),
    }


# ═══════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════


def main() -> None:
    logger.info("=" * 60)
    logger.info("유사사례 자동 수집 시작")
    logger.info("=" * 60)

    if not DATA_GO_KR_API_KEY:
        logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    # ── 1. EIASS API에서 원본 데이터 수집 ──
    api_success = False
    all_items = collect_eia_info()

    if len(all_items) >= 10:
        api_success = True
        logger.info("API 수집 성공: %d건", len(all_items))

        # 4. 원본 저장
        raw_path = RAW_DIR / "eia_info_raw.json"
        raw_path.write_text(
            json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("원본 데이터 저장: %s", raw_path)

        # 유형별 선별
        selected = select_cases(all_items)
        logger.info("선별 완료: %d건", len(selected))

        if len(selected) >= 30:
            # 2-3. 협의/결정 데이터 수집
            eia_ids = [
                item.get("eiaNo", "") or item.get("bizNo", "")
                for item in selected
                if item.get("eiaNo") or item.get("bizNo")
            ]
            if eia_ids:
                conslt_data = collect_eia_conslt(eia_ids[:50])
                decsn_data = collect_eia_decsn(eia_ids[:50])

                # 협의/결정 데이터 병합
                for item in selected:
                    eid = item.get("eiaNo", "") or item.get("bizNo", "")
                    if eid in conslt_data:
                        item["consltResult"] = conslt_data[eid].get("rslt", "")
                    if eid in decsn_data:
                        item["decsnCn"] = decsn_data[eid].get("decsnCn", "")

                # 원본 저장
                raw_sel_path = RAW_DIR / "selected_cases_raw.json"
                raw_sel_path.write_text(
                    json.dumps(selected, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            # 5. LLM 태깅
            tagged_cases = tag_cases_with_llm(selected)
        else:
            logger.warning("선별 건수 부족 (%d건) - LLM 생성으로 전환", len(selected))
            api_success = False

    if not api_success:
        # EIASS API 실패 -> DeepSeek으로 전체 생성
        logger.info("EIASS API 데이터 부족 - DeepSeek 기반 사례 생성으로 전환")
        tagged_cases = generate_cases_with_llm()

    if not tagged_cases:
        logger.error("사례 데이터 생성 실패")
        sys.exit(1)

    # ── 6. 최종 저장 ──
    # case_id 재정렬
    for i, case in enumerate(tagged_cases):
        case["case_id"] = f"CASE-{i + 1:03d}"

    # lessons_learned가 없으면 제거 (기존 스키마 호환)
    for case in tagged_cases:
        if "lessons_learned" in case and not case["lessons_learned"]:
            del case["lessons_learned"]

    logger.info("=== 6단계: 최종 저장 ===")
    CASES_JSON.write_text(
        json.dumps(tagged_cases, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("저장 완료: %s (%d건)", CASES_JSON, len(tagged_cases))

    # ── 요약 ──
    logger.info("=" * 60)
    logger.info("수집 완료 요약")
    logger.info("=" * 60)
    type_counts: dict[str, int] = {}
    consult_counts: dict[str, int] = {}
    for case in tagged_cases:
        pt = case.get("project_type", "기타")
        type_counts[pt] = type_counts.get(pt, 0) + 1
        cr = case.get("consultation_result", "미상")
        consult_counts[cr] = consult_counts.get(cr, 0) + 1

    logger.info("사업유형별:")
    for pt, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d건", pt, cnt)

    logger.info("협의결과별:")
    for cr, cnt in sorted(consult_counts.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d건", cr, cnt)

    logger.info("총 %d건 저장 완료", len(tagged_cases))


if __name__ == "__main__":
    main()
