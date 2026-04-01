"""환경영향평가서 PDF → 텍스트 추출 + 챕터/섹션 분할 스크립트.

PyMuPDF(fitz)로 PDF에서 텍스트를 추출하고, 목차 패턴을 인식하여
챕터/섹션 단위로 분할한 뒤 JSON으로 저장한다.

사용법:
    # 전체 추출
    python backend/scripts/extract_report_text.py

    # 특정 파일만
    python backend/scripts/extract_report_text.py --file data/reports/raw/road_양평_2023.pdf

    # 재추출 (기존 결과 덮어쓰기)
    python backend/scripts/extract_report_text.py --overwrite
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("extract_report")

RAW_DIR = _PROJECT_ROOT / "data" / "reports" / "raw"
EXTRACTED_DIR = _PROJECT_ROOT / "data" / "reports" / "extracted"

# ── 챕터/섹션 패턴 ──
# 환경영향평가서 표준 목차 패턴
CHAPTER_PATTERNS = [
    # "제1장", "제 1 장", "제1장."
    re.compile(r"^[ \t]*제\s*(\d+)\s*장[.\s]*(.+)", re.MULTILINE),
    # "I.", "II.", "III." (로마자)
    re.compile(r"^[ \t]*(I{1,3}|IV|V|VI{0,3})[.\s]+(.+)", re.MULTILINE),
    # "Chapter 1" (영문)
    re.compile(r"^[ \t]*Chapter\s+(\d+)[.\s]*(.+)", re.MULTILINE | re.IGNORECASE),
]

SECTION_PATTERNS = [
    # "1.1", "1.2.3"
    re.compile(r"^[ \t]*(\d+\.\d+(?:\.\d+)?)[.\s]+(.+)", re.MULTILINE),
    # "제1절", "제 1 절"
    re.compile(r"^[ \t]*제\s*(\d+)\s*절[.\s]*(.+)", re.MULTILINE),
]

# 환경영향평가서 표준 챕터명 (매칭 보조)
STANDARD_CHAPTERS = {
    "1": "사업의 개요",
    "2": "지역 개황",
    "3": "평가항목별 현황",
    "4": "환경영향 예측 및 저감방안",
    "5": "종합 평가",
    "6": "사후환경영향조사 계획",
}


def _extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """PDF에서 페이지별 텍스트를 추출한다."""
    import fitz

    pages = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages.append({
                    "page": page_num + 1,
                    "text": text,
                })
        doc.close()
        logger.info("  %d페이지에서 텍스트 추출 완료", len(pages))
    except Exception as exc:
        logger.error("  PDF 텍스트 추출 실패 (%s): %s", pdf_path.name, exc)
    return pages


def _detect_chapters(pages: list[dict]) -> list[dict]:
    """페이지 텍스트에서 챕터/섹션 경계를 감지한다."""
    chapters = []
    current_chapter = None
    current_section = None
    current_text_lines = []
    current_pages = []

    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]
        lines = text.split("\n")

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 챕터 경계 감지
            chapter_match = None
            for pattern in CHAPTER_PATTERNS:
                m = pattern.match(line_stripped)
                if m:
                    chapter_match = m
                    break

            if chapter_match:
                # 이전 섹션 저장
                if current_chapter and current_text_lines:
                    chapters.append(_build_section_record(
                        current_chapter, current_section,
                        current_text_lines, current_pages,
                    ))
                    current_text_lines = []
                    current_pages = []

                chapter_num = chapter_match.group(1)
                chapter_title = chapter_match.group(2).strip()
                current_chapter = f"제{chapter_num}장"
                current_section = chapter_title
                current_pages = [page_num]
                continue

            # 섹션 경계 감지
            section_match = None
            for pattern in SECTION_PATTERNS:
                m = pattern.match(line_stripped)
                if m:
                    section_match = m
                    break

            if section_match and current_chapter:
                # 이전 섹션 저장
                if current_text_lines:
                    chapters.append(_build_section_record(
                        current_chapter, current_section,
                        current_text_lines, current_pages,
                    ))
                    current_text_lines = []

                section_id = section_match.group(1)
                section_title = section_match.group(2).strip()
                current_section = f"{section_id} {section_title}"
                current_pages = [page_num]
                continue

            # 일반 텍스트 축적
            current_text_lines.append(line_stripped)
            if page_num not in current_pages:
                current_pages.append(page_num)

    # 마지막 섹션 저장
    if current_chapter and current_text_lines:
        chapters.append(_build_section_record(
            current_chapter, current_section,
            current_text_lines, current_pages,
        ))

    # 챕터를 감지하지 못한 경우 전체를 하나의 덩어리로
    if not chapters and pages:
        all_text = "\n".join(p["text"] for p in pages)
        all_pages = [p["page"] for p in pages]
        chapters.append({
            "chapter": "전체",
            "section": "전문",
            "content": all_text,
            "page_range": f"{min(all_pages)}-{max(all_pages)}",
        })

    return chapters


def _build_section_record(
    chapter: str, section: str | None,
    text_lines: list[str], pages: list[int],
) -> dict:
    """섹션 레코드를 구성한다."""
    content = "\n".join(text_lines)
    page_range = f"{min(pages)}-{max(pages)}" if pages else "unknown"
    return {
        "chapter": chapter,
        "section": section or chapter,
        "content": content,
        "page_range": page_range,
    }


def _infer_metadata_from_filename(filename: str) -> dict:
    """파일명에서 메타데이터를 추출한다.

    기대 형식: {사업유형코드}_{사업명}_{연도}.pdf
    예: road_양평국도건설_2023.pdf, power_plant_보령화력_2022.pdf
    """
    stem = Path(filename).stem

    type_code_to_kr = {
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
        # 이전 호환
        "power_plant": "에너지개발",
        "factory": "산업입지",
        "housing": "도시개발",
    }

    # 긴 타입 코드부터 매칭 (power_plant 등 밑줄 포함 코드 우선)
    type_code = "unknown"
    remainder = stem
    for code in sorted(type_code_to_kr.keys(), key=len, reverse=True):
        prefix = f"{code}_"
        if stem.startswith(prefix):
            type_code = code
            remainder = stem[len(prefix):]
            break

    if type_code == "unknown":
        # 알려진 코드가 아니면 첫 번째 밑줄로 분리
        parts = stem.split("_", maxsplit=1)
        type_code = parts[0]
        remainder = parts[1] if len(parts) > 1 else ""

    # 나머지에서 이름과 연도 분리
    if remainder:
        parts = remainder.rsplit("_", maxsplit=1)
        if len(parts) == 2 and re.match(r"^\d{4}$", parts[1]):
            name = parts[0]
            year = parts[1]
        else:
            name = remainder
            year = "unknown"
    else:
        name = stem
        year = "unknown"

    return {
        "project_type_code": type_code,
        "project_type": type_code_to_kr.get(type_code, type_code),
        "project_name": name,
        "year": year,
    }


def extract_single(pdf_path: Path, overwrite: bool = False) -> list[dict]:
    """단일 PDF를 처리하여 섹션별 JSON을 저장한다."""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    # 하위 디렉토리 구조(type_title_year/)에서 메타데이터 추출 시도
    parent_meta = _infer_metadata_from_filename(pdf_path.parent.name + ".pdf")
    file_meta = _infer_metadata_from_filename(pdf_path.name)

    # 부모 디렉토리에서 알려진 type code가 나오면 우선 사용
    if parent_meta["project_type"] != parent_meta["project_type_code"]:
        meta = parent_meta
    else:
        meta = file_meta

    report_id = f"{meta['project_type_code']}_{meta['project_name']}_{meta['year']}"

    output_path = EXTRACTED_DIR / f"{report_id}.json"
    if output_path.exists() and not overwrite:
        logger.info("  이미 추출됨 (건너뜀): %s", output_path.name)
        return json.loads(output_path.read_text(encoding="utf-8"))

    logger.info("추출 중: %s", pdf_path.name)

    # 텍스트 추출
    pages = _extract_text_from_pdf(pdf_path)
    if not pages:
        logger.warning("  텍스트를 추출할 수 없음: %s", pdf_path.name)
        return []

    # 챕터/섹션 분할
    sections = _detect_chapters(pages)
    logger.info("  %d개 섹션 감지", len(sections))

    # 메타데이터 추가
    results = []
    for section in sections:
        results.append({
            "report_id": report_id,
            "project_type": meta["project_type"],
            "project_type_code": meta["project_type_code"],
            "project_name": meta["project_name"],
            "year": meta["year"],
            "chapter": section["chapter"],
            "section": section["section"],
            "content": section["content"],
            "page_range": section["page_range"],
        })

    # JSON 저장
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    logger.info("  저장 완료: %s (%d개 섹션)", output_path.name, len(results))

    return results


def extract_all(overwrite: bool = False) -> dict:
    """data/reports/raw/ 내 모든 PDF를 추출한다."""
    if not RAW_DIR.exists():
        logger.warning("원문 디렉토리가 없습니다: %s", RAW_DIR)
        return {"total": 0, "success": 0, "failed": 0, "reports": []}

    pdf_files = sorted(RAW_DIR.rglob("*.pdf"))
    logger.info("총 %d개 PDF 발견", len(pdf_files))

    stats = {"total": len(pdf_files), "success": 0, "failed": 0, "reports": []}

    for pdf_path in pdf_files:
        try:
            sections = extract_single(pdf_path, overwrite=overwrite)
            if sections:
                stats["success"] += 1
                stats["reports"].append({
                    "file": pdf_path.name,
                    "sections": len(sections),
                })
            else:
                stats["failed"] += 1
        except Exception as exc:
            logger.error("처리 실패 (%s): %s", pdf_path.name, exc)
            stats["failed"] += 1

    logger.info(
        "추출 완료: 성공 %d / 실패 %d / 전체 %d",
        stats["success"], stats["failed"], stats["total"],
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="환경영향평가서 PDF 텍스트 추출")
    parser.add_argument("--file", help="특정 PDF 파일 경로")
    parser.add_argument("--overwrite", action="store_true", help="기존 결과 덮어쓰기")
    args = parser.parse_args()

    if args.file:
        extract_single(Path(args.file), overwrite=args.overwrite)
    else:
        extract_all(overwrite=args.overwrite)


if __name__ == "__main__":
    main()
