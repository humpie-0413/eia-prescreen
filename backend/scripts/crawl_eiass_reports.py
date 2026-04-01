"""EIASS 환경영향평가서 원문 크롤링 스크립트.

환경영향평가 정보지원시스템(eiass.go.kr)에서 평가서 PDF를 수집한다.

사이트 구조 (2026-03 기준):
- 로그인 필수 (비로그인 시 파일 목록만 표시, 다운로드 불가)
- 로그인: /sys/login/common_pki.do (input: ID, PWD)
- 검색: POST /biz/base/info/eiaList.do (COMPLETE_FL=Y, OPEN_FL=Y)
- 상세: POST /biz/base/info/eiaInfo.do (EIA_CD, EIA_DISC_SEQ)
- 파일 목록: .down_list li a — viewFile('FILE_SEQ', 'filename')
- 다운로드: /common/file/downloadFileByFileSeq.do?FILE_SEQ=xxx
- PDF 뷰어: POST /common/pdf/view.do (FILE_SEQ, SYSTEM_NAME)

사용법:
    # 전체 17개 유형 수집 (유형별 7건)
    python backend/scripts/crawl_eiass_reports.py --all-types --max-per-type 7

    # 특정 유형만
    python backend/scripts/crawl_eiass_reports.py --type 도로건설 --max 10

    # 전체 섹션 다운로드 (기본: 요약문+개요만)
    python backend/scripts/crawl_eiass_reports.py --all-types --max-per-type 7 --all-sections

    # 헤드리스 꺼짐 (디버그)
    python backend/scripts/crawl_eiass_reports.py --type 도시개발 --max 5 --headless false
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("crawl_eiass")

# ── 설정 ──
RAW_DIR = _PROJECT_ROOT / "data" / "reports" / "raw"
COOKIE_PATH = _PROJECT_ROOT / "data" / "reports" / ".eiass_cookies.json"
MANIFEST_PATH = _PROJECT_ROOT / "data" / "reports" / "crawl_manifest.json"

BASE_URL = "https://eiass.go.kr"

# 사업유형 → EIASS 검색 코드 매핑 (환경영향평가법 시행령 별표3 기준 17개 유형)
PROJECT_TYPES = {
    "도시개발": {"biz_gubun_cd": "A", "code": "urban_dev", "keywords": ["도시개발", "택지개발", "대지조성"]},
    "산업입지": {"biz_gubun_cd": "B", "code": "industrial", "keywords": ["산업단지", "산업입지", "농공단지"]},
    "에너지개발": {"biz_gubun_cd": "C", "code": "energy", "keywords": ["발전소", "화력", "원자력", "태양광", "풍력"]},
    "항만건설": {"biz_gubun_cd": "H", "code": "port", "keywords": ["항만", "어항", "마리나"]},
    "도로건설": {"biz_gubun_cd": "E", "code": "road", "keywords": ["도로", "국도", "고속도로"]},
    "수자원개발": {"biz_gubun_cd": "F", "code": "water_resource", "keywords": ["댐", "저수지", "하구둑", "용수"]},
    "철도건설": {"biz_gubun_cd": "G", "code": "railway", "keywords": ["철도", "고속철도", "도시철도", "경전철"]},
    "공항건설": {"biz_gubun_cd": "J", "code": "airport", "keywords": ["공항", "활주로", "비행장"]},
    "하천이용개발": {"biz_gubun_cd": "I", "code": "river", "keywords": ["하천", "하천공사", "하천정비"]},
    "관광단지개발": {"biz_gubun_cd": "M", "code": "tourism", "keywords": ["관광", "리조트", "골프장", "테마파크"]},
    "산지개발": {"biz_gubun_cd": "D", "code": "mountain", "keywords": ["채석", "광업", "산지전용", "석산"]},
    "체육시설": {"biz_gubun_cd": "N", "code": "sports", "keywords": ["체육", "스키장", "경기장", "골프"]},
    "폐기물처리시설": {"biz_gubun_cd": "O", "code": "waste", "keywords": ["폐기물", "소각", "매립", "분뇨"]},
    "국방군사시설": {"biz_gubun_cd": "K", "code": "military", "keywords": ["군사", "국방", "사격장", "훈련장"]},
    "토석광물채취": {"biz_gubun_cd": "Q", "code": "mining", "keywords": ["토석", "골재", "광물", "채굴"]},
    "매립간척": {"biz_gubun_cd": "L", "code": "reclamation", "keywords": ["매립", "간척", "공유수면"]},
    "기타": {"biz_gubun_cd": "Z", "code": "etc", "keywords": ["물류", "유통", "교육", "의료", "상하수도"]},
}

# 다운로드 대상 섹션 패턴 (기본 모드)
KEY_SECTION_PATTERNS = [
    r"0?1000.*요약",     # 요약문
    r"0?100\b.*총론",    # 총론문
    r"0?2000.*개요",     # 사업의 개요
    r"0?4000.*개황",     # 지역개황
    r"0?3000.*설정",     # 대상지역 설정
    r"\b요약문",          # 파일명에 요약문 포함
    r"\b사업.*개요",      # 파일명에 사업의 개요 포함
    r"\b지역개황",        # 파일명에 지역개황 포함
]


def _safe_filename(text: str) -> str:
    """파일명에 사용할 수 없는 문자를 제거한다."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned[:80]


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"downloaded": [], "failed": [], "last_run": None}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest["last_run"] = datetime.now().isoformat()
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def _extract_year(biz_cd: str) -> str:
    match = re.search(r"(20\d{2})", biz_cd)
    return match.group(1) if match else "unknown"


async def _login(page, eiass_id: str, eiass_pw: str) -> bool:
    """EIASS 로그인."""
    logger.info("로그인 시도: %s", eiass_id)
    try:
        await page.goto(
            f"{BASE_URL}/sys/login/common_pki.do?menu=sys",
            wait_until="networkidle", timeout=30000,
        )
        await page.wait_for_timeout(2000)

        # ID/PW 입력
        id_input = await page.query_selector('input[name="ID"]')
        pw_input = await page.query_selector('input[name="PWD"]')
        if not id_input or not pw_input:
            logger.error("로그인 폼을 찾을 수 없음")
            return False

        await id_input.fill(eiass_id)
        await pw_input.fill(eiass_pw)

        # 로그인 submit (두 번째 submit 버튼 - 첫 번째는 검색)
        submit_btns = await page.query_selector_all('input[type="submit"]')
        if len(submit_btns) >= 2:
            await submit_btns[1].click()
        elif submit_btns:
            await submit_btns[0].click()
        else:
            logger.error("로그인 버튼 없음")
            return False

        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # 로그인 성공: main.do로 리다이렉트
        if "main.do" in page.url or "login" not in page.url.lower():
            logger.info("로그인 성공")
            return True

        logger.warning("로그인 실패. URL: %s", page.url[:80])
        return False

    except Exception as exc:
        logger.error("로그인 오류: %s", exc)
        return False


async def _save_cookies(context) -> None:
    cookies = await context.cookies()
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_PATH.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8",
    )


async def _load_cookies(context) -> bool:
    if not COOKIE_PATH.exists():
        return False
    try:
        cookies = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        return True
    except Exception:
        return False


async def _search_completed_projects(
    context, biz_gubun_cd: str, year_start: str = "", year_end: str = "",
) -> list[dict]:
    """완료+공개 프로젝트를 검색한다."""
    page = await context.new_page()
    results = []

    try:
        form_html = f"""
        <html><body>
        <form id="f" method="post" action="{BASE_URL}/biz/base/info/eiaList.do">
            <input type="hidden" name="menu" value="biz">
            <input type="hidden" name="biz_gubn" value="E">
            <input type="hidden" name="COMPLETE_FL" value="Y">
            <input type="hidden" name="OPEN_FL" value="Y">
            <input type="hidden" name="BIZ_GUBUN_CD" value="{biz_gubun_cd}">
            <input type="hidden" name="A_S_YEAR" value="{year_start}">
            <input type="hidden" name="A_E_YEAR" value="{year_end}">
            <input type="hidden" name="pn" value="1">
            <input type="hidden" name="ps" value="10">
            <input type="hidden" name="searchType" value="1">
        </form>
        <script>document.getElementById('f').submit();</script>
        </body></html>
        """
        await page.set_content(form_html)
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # view() 링크 파싱
        projects = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const onclick = a.getAttribute('onclick') || '';
                const href = a.getAttribute('href') || '';
                const call = onclick || href;
                const match = call.match(/view\\s*\\(\\s*'(\\w+)'\\s*,\\s*'([^']+)'\\s*,\\s*'(\\d+)'\\s*\\)/);
                if (match) {
                    results.push({
                        gubn: match[1],
                        biz_cd: match[2],
                        disc_seq: match[3],
                        title: a.textContent.trim().substring(0, 100)
                    });
                }
            });
            const seen = new Set();
            return results.filter(p => {
                if (seen.has(p.biz_cd)) return false;
                seen.add(p.biz_cd);
                return true;
            });
        }""")

        for proj in projects:
            proj["year"] = _extract_year(proj["biz_cd"])
            results.append(proj)

        logger.info(
            "  검색 결과: %d건 (BIZ_GUBUN_CD=%s, COMPLETE=Y, OPEN=Y)",
            len(results), biz_gubun_cd,
        )

    except Exception as exc:
        logger.error("검색 오류: %s", exc)
    finally:
        await page.close()

    return results


async def _extract_file_links(page) -> list[dict]:
    """상세 페이지에서 viewFile('FILE_SEQ', 'filename') 링크를 추출."""
    return await page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('.down_list li a').forEach(a => {
            const href = a.getAttribute('href') || '';
            const match = href.match(/viewFile\\s*\\(\\s*'(\\d+)'\\s*,\\s*'([^']+)'\\s*\\)/);
            if (match) {
                links.push({seq: match[1], name: match[2]});
            }
        });
        return links;
    }""")


def _is_key_section(filename: str) -> bool:
    """RAG에 유용한 핵심 섹션인지 판별."""
    for pattern in KEY_SECTION_PATTERNS:
        if re.search(pattern, filename):
            return True
    return False


async def _download_file(
    page, file_seq: str, save_path: Path, timeout: int = 120000,
) -> bool:
    """FILE_SEQ로 PDF를 다운로드한다."""
    try:
        async with page.expect_download(timeout=timeout) as download_info:
            await page.evaluate(
                f'document.location.href = "/common/file/downloadFileByFileSeq.do?FILE_SEQ={file_seq}";'
            )
        download = await download_info.value
        await download.save_as(str(save_path))

        # PDF 유효성 확인
        if save_path.exists() and save_path.stat().st_size > 100:
            with open(save_path, "rb") as f:
                if f.read(5) == b"%PDF-":
                    return True
            # PDF가 아니면 삭제
            save_path.unlink(missing_ok=True)
            logger.warning("  다운로드된 파일이 PDF가 아님: %s", save_path.name)
            return False

        save_path.unlink(missing_ok=True)
        return False

    except Exception as exc:
        logger.error("  다운로드 오류 (FILE_SEQ=%s): %s", file_seq, exc)
        save_path.unlink(missing_ok=True)
        return False


async def _process_project(
    context, report: dict, project_type_code: str, all_sections: bool,
) -> list[dict]:
    """하나의 프로젝트에서 PDF를 다운로드한다."""
    title = report["title"]
    year = report["year"]
    biz_cd = report["biz_cd"]
    disc_seq = report["disc_seq"]
    gubn = report.get("gubn", "eia")

    # gubn별 URL/필드
    gubn_config = {
        "eia": ("/biz/base/info/eiaInfo.do", "EIA_CD", "EIA_DISC_SEQ"),
        "per": ("/biz/base/info/perInfo.do", "PER_CD", "PER_DISC_SEQ"),
    }
    url, cd_field, seq_field = gubn_config.get(
        gubn, (f"/biz/base/info/{gubn}Info.do", f"{gubn.upper()}_CD", f"{gubn.upper()}_DISC_SEQ")
    )

    logger.info("프로젝트 처리: %s (%s)", title[:50], biz_cd)

    page = await context.new_page()
    downloaded_files = []

    try:
        form_html = f"""
        <html><body>
        <form id="f" method="post" action="{BASE_URL}{url}">
            <input type="hidden" name="{cd_field}" value="{biz_cd}">
            <input type="hidden" name="{seq_field}" value="{disc_seq}">
            <input type="hidden" name="menu" value="biz">
        </form>
        <script>document.getElementById('f').submit();</script>
        </body></html>
        """
        await page.set_content(form_html)
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # 파일 링크 추출 (로그인 필수)
        file_links = await _extract_file_links(page)
        if not file_links:
            logger.warning("  파일 링크 없음 (로그인 필요하거나 비공개)")
            return []

        logger.info("  파일 %d개 발견", len(file_links))

        # 다운로드 대상 선택
        if all_sections:
            targets = file_links
        else:
            # 핵심 섹션만 + 첫 번째 파일 (표지/목차)
            targets = [f for f in file_links if _is_key_section(f["name"])]
            if not targets and file_links:
                targets = file_links[:1]

        safe_title = _safe_filename(title)
        project_dir = RAW_DIR / f"{project_type_code}_{safe_title}_{year}"
        project_dir.mkdir(parents=True, exist_ok=True)

        for fl in targets:
            safe_name = _safe_filename(fl["name"])
            if not safe_name.endswith(".pdf"):
                safe_name += ".pdf"
            save_path = project_dir / safe_name

            if save_path.exists() and save_path.stat().st_size > 100:
                logger.info("  이미 존재 (건너뜀): %s", save_path.name)
                downloaded_files.append({
                    "seq": fl["seq"], "name": fl["name"],
                    "path": str(save_path), "size": save_path.stat().st_size,
                })
                continue

            logger.info("  다운로드: %s (seq=%s)", fl["name"][:40], fl["seq"])
            success = await _download_file(page, fl["seq"], save_path)

            if success:
                size = save_path.stat().st_size
                logger.info("  완료: %s (%s bytes)", save_path.name, f"{size:,}")
                downloaded_files.append({
                    "seq": fl["seq"], "name": fl["name"],
                    "path": str(save_path), "size": size,
                })
            else:
                logger.warning("  실패: %s", fl["name"][:40])

            # 다운로드 간 대기
            await page.wait_for_timeout(2000)

    except Exception as exc:
        logger.error("  프로젝트 처리 오류 (%s): %s", biz_cd, exc)
    finally:
        await page.close()

    return downloaded_files


async def crawl(
    max_total: int = 50,
    max_per_type: int | None = None,
    target_type: str | None = None,
    headless: bool = True,
    reuse_cookies: bool = False,
    all_sections: bool = False,
) -> dict:
    """EIASS에서 환경영향평가서 PDF를 크롤링한다."""
    from playwright.async_api import async_playwright

    manifest = _load_manifest()
    already_downloaded = {d["biz_cd"] for d in manifest["downloaded"]}
    total_downloaded = 0
    type_stats: dict[str, int] = {}

    eiass_id = os.getenv("EIASS_ID", "")
    eiass_pw = os.getenv("EIASS_PW", "")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 수집 대상 유형
    if target_type:
        if target_type not in PROJECT_TYPES:
            logger.error(
                "알 수 없는 유형: %s (가능: %s)",
                target_type, ", ".join(PROJECT_TYPES.keys()),
            )
            return manifest
        types_to_crawl = {target_type: PROJECT_TYPES[target_type]}
    else:
        types_to_crawl = PROJECT_TYPES

    per_type_max = max_per_type or max(1, max_total // len(types_to_crawl))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--ignore-certificate-errors"],
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            accept_downloads=True,
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # 쿠키 복원
        if reuse_cookies:
            await _load_cookies(context)

        # 로그인 (필수)
        page = await context.new_page()
        logged_in = False
        if eiass_id and eiass_pw:
            logged_in = await _login(page, eiass_id, eiass_pw)
            if logged_in:
                await _save_cookies(context)
        await page.close()

        if not logged_in:
            logger.error("로그인 실패. 로그인이 필요합니다.")
            await browser.close()
            return manifest

        # 유형별 크롤링
        for type_name, type_info in types_to_crawl.items():
            if total_downloaded >= max_total:
                break

            logger.info("=== [%d/%d] %s 유형 크롤링 (BIZ_GUBUN_CD=%s) ===",
                         list(types_to_crawl.keys()).index(type_name) + 1,
                         len(types_to_crawl), type_name, type_info["biz_gubun_cd"])
            type_count = 0

            # 완료+공개 프로젝트 검색
            reports = await _search_completed_projects(
                context, type_info["biz_gubun_cd"],
            )

            for report in reports:
                if total_downloaded >= max_total or type_count >= per_type_max:
                    break
                if report["biz_cd"] in already_downloaded:
                    logger.info("  건너뜀 (이미 수집): %s", report["biz_cd"])
                    continue

                files = await _process_project(
                    context, report, type_info["code"], all_sections,
                )

                if files:
                    manifest["downloaded"].append({
                        "title": report["title"],
                        "year": report["year"],
                        "biz_cd": report["biz_cd"],
                        "project_type": type_name,
                        "project_type_code": type_info["code"],
                        "files": [
                            {"name": f["name"], "path": f["path"], "size": f["size"]}
                            for f in files
                        ],
                        "downloaded_at": datetime.now().isoformat(),
                    })
                    total_downloaded += 1
                    type_count += 1
                    already_downloaded.add(report["biz_cd"])
                else:
                    manifest["failed"].append({
                        "title": report["title"],
                        "year": report["year"],
                        "biz_cd": report["biz_cd"],
                        "project_type": type_name,
                        "reason": "파일 다운로드 실패",
                        "attempted_at": datetime.now().isoformat(),
                    })

                # 프로젝트 간 대기
                await asyncio.sleep(3)

            type_stats[type_name] = type_count
            logger.info("  %s: %d건 완료", type_name, type_count)

        await _save_cookies(context)
        await browser.close()

    _save_manifest(manifest)

    # 유형별 수집 현황 로그
    logger.info("=" * 60)
    logger.info("크롤링 완료 요약")
    logger.info("=" * 60)
    for tn, tc in type_stats.items():
        logger.info("  %-12s: %d건", tn, tc)
    logger.info("-" * 60)
    logger.info(
        "  총계: %d건 다운로드, %d건 실패",
        len(manifest["downloaded"]), len(manifest["failed"]),
    )
    logger.info("=" * 60)

    return manifest


def main() -> None:
    type_names = ", ".join(PROJECT_TYPES.keys())
    parser = argparse.ArgumentParser(description="EIASS 환경영향평가서 PDF 크롤러")
    parser.add_argument("--max", type=int, default=150, help="최대 프로젝트 수 (기본: 150)")
    parser.add_argument("--max-per-type", type=int, help="유형별 최대 프로젝트 수")
    parser.add_argument("--type", dest="project_type", help=f"유형 ({type_names})")
    parser.add_argument("--all-types", action="store_true", help="전체 17개 유형 순차 수집")
    parser.add_argument("--headless", default="true", help="헤드리스 모드 (true/false)")
    parser.add_argument("--reuse-cookies", action="store_true", help="쿠키 재사용")
    parser.add_argument("--all-sections", action="store_true", help="전체 섹션 다운로드 (기본: 핵심만)")
    args = parser.parse_args()

    # --all-types: 전체 유형 (target_type=None), --type: 특정 유형
    target_type = None if args.all_types else args.project_type

    asyncio.run(
        crawl(
            max_total=args.max,
            max_per_type=args.max_per_type,
            target_type=target_type,
            headless=args.headless.lower() != "false",
            reuse_cookies=args.reuse_cookies,
            all_sections=args.all_sections,
        )
    )


if __name__ == "__main__":
    main()
