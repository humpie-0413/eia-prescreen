"""과거 환경영향평가 벌크 수집 스크립트.

2015~2025년 완료 사업을 EIASS API에서 전수 수집하고,
각 사업의 협의 결과 및 결정내용(지적사항/보완요구)을 함께 저장한다.

데이터 저장: data/bulk/raw/
  - eia_projects.json   -전체 사업 목록
  - eia_conslt.json     -협의 현황 (사업별)
  - eia_decsn.json      -결정내용 (사업별)
  - bulk_merged.json    -3종 병합 최종 데이터

Usage:
    python backend/scripts/bulk_collect_eia.py
    python backend/scripts/bulk_collect_eia.py --year-start 2020 --year-end 2025
    python backend/scripts/bulk_collect_eia.py --skip-conslt --skip-decsn  # 목록만
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# ── 프로젝트 루트를 sys.path에 추가 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 로깅 설정 (Windows cp949 인코딩 문제 방지) ──
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
logging.basicConfig(level=logging.INFO, handlers=[_handler])
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

# ── 경로 ──
RAW_DIR = PROJECT_ROOT / "data" / "bulk" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── API URL (공공데이터포털 EIASS 서비스 -1480523) ──
EIA_INFO_URL = "https://apis.data.go.kr/1480523/EiaInfoSvc/getEiaInfoList"
EIA_CONSLT_URL = "https://apis.data.go.kr/1480523/EiaConsltSvc/getEiaConsltList"
EIA_DECSN_URL = "https://apis.data.go.kr/1480523/EiaDecsnSvc/getEiaDecsnList"

# 대체 URL (B553748 서비스 그룹 - 일부 키에서 작동)
EIA_INFO_URL_ALT = "https://apis.data.go.kr/B553748/eiainformation/getListEiaInformation"

# 해양수산부 환경영향평가정보 (1192000 서비스 그룹)
MOF_ENV_IMPACT_URL = "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo"

# ── 설정 ──
PAGE_SIZE = 100
API_DELAY = 1.0  # 초 (일일 10,000건 제한 고려)
REQUEST_TIMEOUT = 20  # 초


# ═══════════════════════════════════════════════════════════
# API 호출 유틸
# ═══════════════════════════════════════════════════════════


def _call_api(url: str, params: dict, retry_encoded: bool = True) -> dict | None:
    """공공데이터포털 API를 호출하고 JSON 응답을 반환한다.

    500/403 에러는 URL-인코딩된 키로 재시도 후 None을 반환한다.
    """
    from urllib.parse import quote

    params_copy = {**params}
    params_copy["serviceKey"] = DATA_GO_KR_API_KEY
    params_copy["type"] = "json"

    endpoint_name = url.split("/")[-1]

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params=params_copy)

            if resp.status_code in (403, 500, 502, 503):
                # URL-인코딩된 키로 재시도 (일부 공공 API에서 필요)
                if retry_encoded:
                    encoded_key = quote(DATA_GO_KR_API_KEY, safe="")
                    if encoded_key != DATA_GO_KR_API_KEY:
                        params_copy["serviceKey"] = encoded_key
                        resp2 = client.get(url, params=params_copy)
                        if resp2.status_code == 200:
                            return resp2.json()

                logger.warning(
                    "  API %d: %s (params: %s)",
                    resp.status_code,
                    endpoint_name,
                    {k: v for k, v in params.items() if k != "serviceKey"},
                )
                return None

            resp.raise_for_status()

            # XML 응답 감지 (type=json인데 XML 반환하는 경우)
            content_type = resp.headers.get("content-type", "")
            if "xml" in content_type:
                logger.warning("  API returned XML instead of JSON: %s", endpoint_name)
                return None

            return resp.json()

    except httpx.TimeoutException:
        logger.warning("  API timeout: %s", endpoint_name)
        return None
    except Exception as e:
        logger.warning("  API error: %s - %s", endpoint_name, e)
        return None


def _extract_items(data: dict) -> list[dict]:
    """공공데이터포털 표준 응답에서 items를 추출한다."""
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
    if isinstance(data, list):
        return data
    if "items" in data:
        return data["items"] if isinstance(data["items"], list) else []
    return []


def _get_total_count(data: dict) -> int:
    """응답에서 totalCount를 추출한다."""
    if "response" in data:
        body = data["response"].get("body", {})
        return int(body.get("totalCount", 0))
    return 0


# ═══════════════════════════════════════════════════════════
# 1단계: 사업 목록 전수 수집
# ═══════════════════════════════════════════════════════════


def _call_mof_api(url: str, params: dict) -> dict | None:
    """해양수산부 1192000 API를 호출한다.

    응답 구조가 표준 공공데이터포털과 다르므로 별도 처리한다.
    """
    from urllib.parse import quote

    params_copy = {**params}
    params_copy["ServiceKey"] = DATA_GO_KR_API_KEY
    params_copy["resultType"] = "json"

    endpoint_name = url.split("/")[-1]

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params=params_copy)

            if resp.status_code in (403, 500, 502, 503):
                encoded_key = quote(DATA_GO_KR_API_KEY, safe="")
                if encoded_key != DATA_GO_KR_API_KEY:
                    params_copy["ServiceKey"] = encoded_key
                    resp2 = client.get(url, params=params_copy)
                    if resp2.status_code == 200:
                        return resp2.json()
                logger.warning(
                    "  MOF API %d: %s", resp.status_code, endpoint_name,
                )
                return None

            resp.raise_for_status()
            return resp.json()

    except Exception as e:
        logger.warning("  MOF API error: %s - %s", endpoint_name, e)
        return None


def _extract_mof_items(data: dict) -> list[dict]:
    """해양수산부 1192000 응답에서 item 목록을 추출한다."""
    info = data.get("getEnvImpactInfo", {})
    items = info.get("item", [])
    if isinstance(items, dict):
        return [items]
    return items if isinstance(items, list) else []


def _get_mof_total_count(data: dict) -> int:
    """해양수산부 1192000 응답에서 totalCount를 추출한다."""
    info = data.get("getEnvImpactInfo", {})
    return int(info.get("totalCount", 0))


def _try_info_api(params: dict) -> dict | None:
    """EIA 정보 API를 주 URL + 대체 URL 순서로 시도한다."""
    result = _call_api(EIA_INFO_URL, {**params})
    if result is not None:
        return result

    # 대체 URL 시도 (B553748 서비스)
    alt_params = {**params}
    # B553748 서비스는 파라미터명이 다를 수 있음
    result = _call_api(EIA_INFO_URL_ALT, alt_params)
    return result


def collect_projects(year_start: int, year_end: int) -> list[dict]:
    """환경영향평가 정보 서비스에서 연도별 사업 목록을 전수 수집한다."""
    logger.info("=" * 60)
    logger.info("1단계: 사업 목록 수집 (%d~%d)", year_start, year_end)
    logger.info("=" * 60)

    all_items: list[dict] = []
    total_api_calls = 0
    skipped_years: list[int] = []

    for year in range(year_start, year_end + 1):
        logger.info("[%d년] 조회 시작...", year)

        # 첫 페이지에서 totalCount 확인
        first_page = _try_info_api(
            {"bizYr": str(year), "numOfRows": PAGE_SIZE, "pageNo": 1},
        )
        total_api_calls += 1
        time.sleep(API_DELAY)

        if first_page is None:
            logger.warning("[%d년] API 호출 실패 - 건너뜀", year)
            skipped_years.append(year)
            continue

        total_count = _get_total_count(first_page)
        items = _extract_items(first_page)

        if total_count == 0 and not items:
            logger.info("[%d년] 데이터 없음", year)
            continue

        all_items.extend(items)
        logger.info(
            "[%d년] totalCount=%d, 1페이지 %d건 수집",
            year, total_count, len(items),
        )

        # 나머지 페이지 수집
        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
        for page_no in range(2, total_pages + 1):
            data = _try_info_api(
                {"bizYr": str(year), "numOfRows": PAGE_SIZE, "pageNo": page_no},
            )
            total_api_calls += 1
            time.sleep(API_DELAY)

            if data is None:
                logger.warning("[%d년] 페이지 %d 실패 -건너뜀", year, page_no)
                continue

            page_items = _extract_items(data)
            all_items.extend(page_items)
            logger.info(
                "[%d년] 페이지 %d/%d: %d건 (누적 %d)",
                year, page_no, total_pages, len(page_items), len(all_items),
            )

    logger.info("-" * 40)
    logger.info(
        "사업 목록 수집 완료: %d건 (API 호출 %d회)", len(all_items), total_api_calls
    )
    if skipped_years:
        logger.warning("건너뛴 연도: %s", skipped_years)

    return all_items


# ═══════════════════════════════════════════════════════════
# 2단계: 협의 현황 수집
# ═══════════════════════════════════════════════════════════


def collect_consultations(eia_ids: list[str]) -> dict[str, list[dict]]:
    """각 사업의 협의 결과를 수집한다."""
    logger.info("=" * 60)
    logger.info("2단계: 협의 현황 수집 (%d건)", len(eia_ids))
    logger.info("=" * 60)

    results: dict[str, list[dict]] = {}
    success = 0
    failed = 0

    for i, eia_id in enumerate(eia_ids):
        if (i + 1) % 50 == 0 or i == 0:
            logger.info(
                "  진행: %d/%d (성공 %d, 실패 %d)",
                i + 1, len(eia_ids), success, failed,
            )

        data = _call_api(EIA_CONSLT_URL, {"eiaNo": eia_id})
        time.sleep(API_DELAY)

        if data is not None:
            items = _extract_items(data)
            if items:
                results[eia_id] = items
                success += 1
            else:
                failed += 1
        else:
            failed += 1

    logger.info(
        "협의 현황 수집 완료: 성공 %d, 실패 %d", success, failed
    )
    return results


# ═══════════════════════════════════════════════════════════
# 3단계: 결정내용(지적사항/보완요구) 수집
# ═══════════════════════════════════════════════════════════


def collect_decisions(eia_ids: list[str]) -> dict[str, list[dict]]:
    """각 사업의 결정내용(지적사항, 보완요구)을 수집한다."""
    logger.info("=" * 60)
    logger.info("3단계: 결정내용 수집 (%d건)", len(eia_ids))
    logger.info("=" * 60)

    results: dict[str, list[dict]] = {}
    success = 0
    failed = 0

    for i, eia_id in enumerate(eia_ids):
        if (i + 1) % 50 == 0 or i == 0:
            logger.info(
                "  진행: %d/%d (성공 %d, 실패 %d)",
                i + 1, len(eia_ids), success, failed,
            )

        data = _call_api(EIA_DECSN_URL, {"eiaNo": eia_id})
        time.sleep(API_DELAY)

        if data is not None:
            items = _extract_items(data)
            if items:
                results[eia_id] = items
                success += 1
            else:
                failed += 1
        else:
            failed += 1

    logger.info(
        "결정내용 수집 완료: 성공 %d, 실패 %d", success, failed
    )
    return results


# ═══════════════════════════════════════════════════════════
# 4단계: 데이터 병합 + 저장
# ═══════════════════════════════════════════════════════════


def extract_eia_id(item: dict) -> str:
    """사업 항목에서 EIA 번호를 추출한다."""
    return str(
        item.get("eiaNo", "")
        or item.get("bizNo", "")
        or item.get("assmtNo", "")
        or ""
    )


def merge_and_save(
    projects: list[dict],
    consultations: dict[str, list[dict]],
    decisions: dict[str, list[dict]],
) -> Path:
    """3종 데이터를 사업 ID 기준으로 병합하여 저장한다."""
    logger.info("=" * 60)
    logger.info("4단계: 데이터 병합 + 저장")
    logger.info("=" * 60)

    merged: list[dict] = []

    for item in projects:
        eia_id = extract_eia_id(item)
        record = {
            "eia_id": eia_id,
            "project_name": item.get("bizNm", "") or item.get("prjctNm", ""),
            "project_type_raw": item.get("prjctSe", "") or item.get("bizSe", ""),
            "address": item.get("addr", "") or item.get("lctn", ""),
            "year": item.get("bizYr", "") or item.get("yr", ""),
            "assessment_type": item.get("assmtSe", "") or item.get("eiaClsNm", ""),
            "scale": item.get("bizScale", "") or item.get("prjctScale", ""),
            "status": item.get("bizSttus", "") or item.get("prgrsStts", ""),
            "raw_project": item,
            "consultations": consultations.get(eia_id, []),
            "decisions": decisions.get(eia_id, []),
        }

        # 협의결과 요약
        conslt_list = consultations.get(eia_id, [])
        if conslt_list:
            record["consultation_result"] = (
                conslt_list[0].get("rslt", "")
                or conslt_list[0].get("consltResult", "")
            )
        else:
            record["consultation_result"] = ""

        # 지적사항 요약
        decsn_list = decisions.get(eia_id, [])
        if decsn_list:
            record["decision_summary"] = (
                decsn_list[0].get("decsnCn", "")
                or decsn_list[0].get("opinion", "")
            )
        else:
            record["decision_summary"] = ""

        merged.append(record)

    # 저장
    merged_path = RAW_DIR / "bulk_merged.json"
    merged_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("병합 데이터 저장: %s (%d건)", merged_path, len(merged))

    return merged_path


def save_raw(filename: str, data: object) -> Path:
    """원본 데이터를 JSON 파일로 저장한다."""
    path = RAW_DIR / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("저장: %s", path)
    return path


# ═══════════════════════════════════════════════════════════
# 통계 출력
# ═══════════════════════════════════════════════════════════


def print_summary(merged_path: Path) -> None:
    """수집 결과 통계를 출력한다."""
    data = json.loads(merged_path.read_text(encoding="utf-8"))

    logger.info("=" * 60)
    logger.info("수집 결과 요약")
    logger.info("=" * 60)
    logger.info("총 수집 건수: %d", len(data))

    # 연도별
    year_counts: dict[str, int] = {}
    for item in data:
        yr = str(item.get("year", "미상"))[:4]
        year_counts[yr] = year_counts.get(yr, 0) + 1

    logger.info("\n연도별 분포:")
    for yr in sorted(year_counts.keys()):
        logger.info("  %s: %d건", yr, year_counts[yr])

    # 사업유형별
    type_counts: dict[str, int] = {}
    for item in data:
        ptype = item.get("project_type_raw", "미상") or "미상"
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

    logger.info("\n사업유형별 분포 (상위 15):")
    for ptype, cnt in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
        logger.info("  %s: %d건", ptype, cnt)

    # 협의결과별
    conslt_counts: dict[str, int] = {}
    for item in data:
        cr = item.get("consultation_result", "") or "미수집"
        conslt_counts[cr] = conslt_counts.get(cr, 0) + 1

    logger.info("\n협의결과별 분포:")
    for cr, cnt in sorted(conslt_counts.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d건", cr if cr else "(빈값)", cnt)

    # 지적사항 보유 건수
    with_decsn = sum(1 for item in data if item.get("decision_summary"))
    logger.info("\n지적사항 보유: %d건 / %d건", with_decsn, len(data))

    logger.info("=" * 60)
    logger.info("데이터 저장 위치: %s", RAW_DIR)


# ---------------------------------------------------------------
# 해양수산부 (1192000) 수집
# ---------------------------------------------------------------


def collect_mof_projects(year_start: int, year_end: int) -> list[dict]:
    """해양수산부 환경영향평가정보(1192000)에서 연도별 수집한다."""
    logger.info("=" * 60)
    logger.info("MOF API (1192000) collection (%d~%d)", year_start, year_end)
    logger.info("=" * 60)

    all_items: list[dict] = []

    for year in range(year_start, year_end + 1):
        data = _call_mof_api(
            MOF_ENV_IMPACT_URL,
            {"pageNo": 1, "numOfRows": PAGE_SIZE, "ACP_YEAR": str(year)},
        )
        time.sleep(API_DELAY)

        if data is None:
            logger.warning("[MOF %d] API call failed", year)
            continue

        total_count = _get_mof_total_count(data)
        items = _extract_mof_items(data)

        if total_count == 0 and not items:
            logger.info("[MOF %d] no data", year)
            continue

        all_items.extend(items)
        logger.info("[MOF %d] totalCount=%d, %d items", year, total_count, len(items))

        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
        for page_no in range(2, total_pages + 1):
            page_data = _call_mof_api(
                MOF_ENV_IMPACT_URL,
                {"pageNo": page_no, "numOfRows": PAGE_SIZE, "ACP_YEAR": str(year)},
            )
            time.sleep(API_DELAY)
            if page_data:
                page_items = _extract_mof_items(page_data)
                all_items.extend(page_items)

    logger.info("MOF collection done: %d items", len(all_items))
    return all_items


def _normalize_mof_items(mof_items: list[dict]) -> list[dict]:
    """해양수산부 응답을 EIASS 형식과 호환되도록 정규화한다."""
    normalized = []
    for item in mof_items:
        normalized.append({
            "eiaNo": item.get("eiaNo", "") or item.get("bizNo", ""),
            "bizNm": item.get("bizNm", "") or item.get("prjctNm", ""),
            "bizYr": item.get("acpYear", "") or item.get("bizYr", ""),
            "prjctSe": item.get("bizTypNm", "") or "해양/항만",
            "addr": " ".join(filter(None, [
                item.get("sidoNm", ""),
                item.get("sggNm", ""),
                item.get("emdNm", ""),
            ])),
            "bizScale": item.get("bizSiz", ""),
            "bizSttus": item.get("stpNm", ""),
            "assmtSe": item.get("rstNm", ""),
            "lat": item.get("lat", ""),
            "lon": item.get("lon", ""),
            "_source": "MOF_1192000",
            "_raw": item,
        })
    return normalized



# ═══════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="과거 환경영향평가 벌크 수집 (2015~2025)",
    )
    parser.add_argument(
        "--year-start", type=int, default=2015, help="수집 시작 연도 (기본: 2015)"
    )
    parser.add_argument(
        "--year-end", type=int, default=2025, help="수집 종료 연도 (기본: 2025)"
    )
    parser.add_argument(
        "--skip-conslt", action="store_true", help="협의현황 수집 건너뜀"
    )
    parser.add_argument(
        "--skip-decsn", action="store_true", help="결정내용 수집 건너뜀"
    )
    parser.add_argument(
        "--max-conslt", type=int, default=0,
        help="협의현황 수집 최대 건수 (0=전체, 기본: 0)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("과거 환경영향평가 벌크 수집 시작")
    logger.info("기간: %d ~ %d", args.year_start, args.year_end)
    logger.info("시각: %s", datetime.now().isoformat())
    logger.info("=" * 60)

    if not DATA_GO_KR_API_KEY:
        logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
        logger.error(".env 파일에 DATA_GO_KR_API_KEY=... 를 추가하세요.")
        sys.exit(1)

    # ── 0. 해양수산부 API (1192000) 시도 ──
    mof_projects = collect_mof_projects(args.year_start, args.year_end)
    if mof_projects:
        save_raw("mof_env_impact.json", mof_projects)

    # ── 1. 사업 목록 수집 ──
    projects = collect_projects(args.year_start, args.year_end)

    # MOF 데이터를 EIASS 결과에 병합
    if mof_projects and not projects:
        logger.info("EIASS 결과 0건이나 해양수산부 데이터 %d건 확보", len(mof_projects))
        projects = _normalize_mof_items(mof_projects)
    elif mof_projects:
        projects.extend(_normalize_mof_items(mof_projects))
        logger.info("해양수산부 데이터 %d건 병합 (총 %d건)", len(mof_projects), len(projects))

    if not projects:
        logger.error("사업 목록 수집 결과 0건 - 종료")
        logger.info("가능한 원인:")
        logger.info("  1. API 키 미승인 (공공데이터포털에서 EIASS 서비스 신청 필요)")
        logger.info("  2. API 서버 일시 장애")
        logger.info("  3. 연도 범위에 데이터 없음")
        sys.exit(1)

    save_raw("eia_projects.json", projects)

    # ── 2. EIA ID 추출 ──
    eia_ids = []
    for item in projects:
        eid = extract_eia_id(item)
        if eid:
            eia_ids.append(eid)

    eia_ids_unique = list(dict.fromkeys(eia_ids))  # 중복 제거 (순서 유지)
    logger.info("고유 사업 ID: %d건", len(eia_ids_unique))

    # ── 3. 협의현황 수집 ──
    consultations: dict[str, list[dict]] = {}
    if not args.skip_conslt and eia_ids_unique:
        target_ids = eia_ids_unique
        if args.max_conslt > 0:
            target_ids = eia_ids_unique[: args.max_conslt]
            logger.info("협의현황 수집 대상: %d건 (max_conslt 제한)", len(target_ids))
        consultations = collect_consultations(target_ids)
        save_raw("eia_conslt.json", consultations)
    else:
        logger.info("협의현황 수집 건너뜀")

    # ── 4. 결정내용 수집 ──
    decisions: dict[str, list[dict]] = {}
    if not args.skip_decsn and eia_ids_unique:
        target_ids = eia_ids_unique
        if args.max_conslt > 0:
            target_ids = eia_ids_unique[: args.max_conslt]
        decisions = collect_decisions(target_ids)
        save_raw("eia_decsn.json", decisions)
    else:
        logger.info("결정내용 수집 건너뜀")

    # ── 5. 병합 + 저장 ──
    merged_path = merge_and_save(projects, consultations, decisions)

    # ── 6. 통계 출력 ──
    print_summary(merged_path)

    logger.info("\n완료! 다음 단계: python backend/scripts/analyze_patterns.py")


if __name__ == "__main__":
    main()
