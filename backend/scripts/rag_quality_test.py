"""RAG 품질 테스트 스크립트 (Step 15).

사업유형별 대표 질의 16개를 테스트하고 품질 점수를 산출한다.
Draft Copilot RAG 연동도 검증한다.

사용법:
    python backend/scripts/rag_quality_test.py
    python backend/scripts/rag_quality_test.py --with-llm  # LLM 답변 생성 포함
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rag_quality_test")

# ── 사업유형별 대표 질의 ──
TYPE_QUERIES = {
    "road": "도로 사업의 비산먼지 저감방안은?",
    "energy": "화력발전소의 대기오염물질 배출 저감 기술은?",
    "industrial": "산업단지 조성 시 수질 오염 방지 대책은?",
    "urban_dev": "택지개발 사업의 교통 영향 저감방안은?",
    "railway": "철도 건설 시 소음진동 대책은?",
    "port": "항만 준설 시 해양생태계 보호 방안은?",
    "airport": "공항 건설의 조류 충돌 방지 대책은?",
    "river": "하천 정비 사업의 수생태계 보전 방안은?",
    "water_resource": "댐 건설 시 수몰 지역 주민 대책은?",
    "tourism": "골프장 건설의 산림 훼손 대응 방안은?",
    "mountain": "채석 사업의 지형경관 영향 최소화 방안은?",
    "sports": "스키장 건설의 생태계 영향은?",
    "waste": "소각시설 주변 다이옥신 저감 대책은?",
    "military": "군사시설 건설의 자연환경 보전 방안은?",
    "mining": "골재 채취의 하천 생태계 영향은?",
    "reclamation": "매립 사업의 해양환경 영향 저감방안은?",
}

# Draft Copilot 연동 테스트 섹션
DRAFT_TEST_SECTIONS = [
    ("대기질", "road"),
    ("수질", "road"),
    ("소음·진동", "road"),
    ("대기질", "energy"),
    ("해양환경", "energy"),
]


def evaluate_search_result(
    query_type: str,
    query: str,
    results: list[dict],
) -> dict:
    """검색 결과 품질을 평가한다."""
    evaluation = {
        "query_type": query_type,
        "query": query,
        "hit_count": len(results),
        "has_results": len(results) > 0,
        "scores": {},
        "issues": [],
    }

    if not results:
        evaluation["issues"].append("검색 결과 없음")
        evaluation["scores"] = {
            "relevance": 0,
            "source_quality": 0,
            "content_richness": 0,
            "type_match": 0,
            "total": 0,
        }
        return evaluation

    # 1. 유사도 점수 (similarity)
    similarities = [r.get("similarity", 0) for r in results]
    avg_sim = sum(similarities) / len(similarities) if similarities else 0
    top_sim = max(similarities) if similarities else 0

    # 2. 유형 일치도 (검색된 결과의 project_type_code가 쿼리 유형과 일치하는 비율)
    type_matches = sum(
        1 for r in results
        if r.get("metadata", {}).get("project_type_code") == query_type
    )
    type_match_ratio = type_matches / len(results) if results else 0

    # 3. 컨텐츠 풍부도 (평균 콘텐츠 길이)
    content_lengths = [len(r.get("content", "")) for r in results]
    avg_content_len = sum(content_lengths) / len(content_lengths) if content_lengths else 0

    # 4. 출처 다양성 (고유 report_id 수)
    unique_reports = set(r.get("metadata", {}).get("report_id", "") for r in results)
    source_diversity = len(unique_reports) / len(results) if results else 0

    # 5. 출처 정보 완성도 (page_range, chapter, section 등)
    source_completeness = 0
    for r in results:
        meta = r.get("metadata", {})
        if meta.get("page_range") and meta["page_range"] != "unknown":
            source_completeness += 0.33
        if meta.get("chapter"):
            source_completeness += 0.33
        if meta.get("section"):
            source_completeness += 0.34
    source_completeness /= len(results) if results else 1

    # 점수 산출 (0~100 스케일)
    relevance_score = min(100, top_sim * 150)  # sim 0.67 = 100점
    source_score = min(100, (source_diversity * 50 + source_completeness * 50))
    content_score = min(100, avg_content_len / 3)  # 300자 = 100점
    type_score = type_match_ratio * 100
    total_score = (relevance_score * 0.35 + source_score * 0.2 +
                   content_score * 0.2 + type_score * 0.25)

    evaluation["scores"] = {
        "relevance": round(relevance_score, 1),
        "source_quality": round(source_score, 1),
        "content_richness": round(content_score, 1),
        "type_match": round(type_score, 1),
        "total": round(total_score, 1),
    }

    evaluation["details"] = {
        "top_similarity": round(top_sim, 4),
        "avg_similarity": round(avg_sim, 4),
        "avg_content_length": round(avg_content_len),
        "unique_reports": len(unique_reports),
        "type_match_count": type_matches,
        "source_completeness": round(source_completeness, 2),
    }

    evaluation["top_sources"] = [
        {
            "report_id": r.get("metadata", {}).get("report_id", ""),
            "project_name": r.get("metadata", {}).get("project_name", ""),
            "year": r.get("metadata", {}).get("year", ""),
            "chapter": r.get("metadata", {}).get("chapter", ""),
            "section": r.get("metadata", {}).get("section", ""),
            "page_range": r.get("metadata", {}).get("page_range", ""),
            "similarity": round(r.get("similarity", 0), 4),
            "excerpt": r.get("content", "")[:150],
        }
        for r in results[:3]
    ]

    # 이슈 탐지
    if top_sim < 0.4:
        evaluation["issues"].append(f"최상위 유사도 낮음 ({top_sim:.3f})")
    if type_match_ratio < 0.5:
        evaluation["issues"].append(
            f"유형 불일치 높음 ({type_matches}/{len(results)})"
        )
    if avg_content_len < 100:
        evaluation["issues"].append(f"콘텐츠 빈약 (평균 {avg_content_len:.0f}자)")

    return evaluation


async def evaluate_llm_query(
    rag, query_type: str, query: str,
) -> dict:
    """LLM 답변 생성 품질을 평가한다."""
    try:
        result = await rag.query(query, n_results=5, project_type=query_type)
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        evaluation = {
            "query_type": query_type,
            "query": query,
            "answer_length": len(answer),
            "source_count": len(sources),
            "has_answer": len(answer) > 50,
            "answer_preview": answer[:500] if answer else "",
        }

        # 품질 지표
        scores = {}

        # 1. 답변 길이 (200자 이상 = 만점)
        scores["length"] = min(100, len(answer) / 2)

        # 2. 출처 표시 여부
        has_citation = "[출처" in answer or "출처:" in answer or "[출처 " in answer
        scores["citation"] = 100 if has_citation else 0

        # 3. 구체성 (수치, 법령, 기술명 등)
        specificity_markers = [
            "㎡", "km", "dB", "mg/L", "ppm", "%", "건", "개소",
            "법", "령", "조", "규정", "기준",
            "방지시설", "저감", "대책", "방안", "조치",
        ]
        specificity_count = sum(1 for m in specificity_markers if m in answer)
        scores["specificity"] = min(100, specificity_count * 15)

        # 4. 도메인 관련성 (간이 키워드 체크)
        domain_keywords = {
            "road": ["도로", "교통", "소음", "비산먼지", "노선"],
            "energy": ["발전", "대기", "배출", "연소", "SO2", "NOx"],
            "industrial": ["산업", "수질", "폐수", "오염", "배출"],
            "urban_dev": ["택지", "교통", "개발", "도시", "인구"],
            "railway": ["철도", "소음", "진동", "노선", "열차"],
            "port": ["항만", "해양", "준설", "어류", "퇴적"],
            "airport": ["공항", "소음", "항공", "조류", "활주"],
            "river": ["하천", "수생태", "어류", "유량", "수질"],
            "water_resource": ["댐", "저수지", "수몰", "이주", "용수"],
            "tourism": ["관광", "산림", "경관", "골프", "숙박"],
            "mountain": ["채석", "지형", "경관", "복원", "산림"],
            "sports": ["체육", "스키", "생태", "산림", "경관"],
            "waste": ["폐기물", "소각", "다이옥신", "매립", "오염"],
            "military": ["군사", "자연", "생태", "보전", "환경"],
            "mining": ["골재", "채취", "하천", "생태", "복원"],
            "reclamation": ["매립", "해양", "간척", "갯벌", "생태"],
        }
        keywords = domain_keywords.get(query_type, [])
        keyword_matches = sum(1 for kw in keywords if kw in answer)
        scores["domain_relevance"] = min(100, keyword_matches * 25)

        scores["total"] = round(
            scores["length"] * 0.2 +
            scores["citation"] * 0.25 +
            scores["specificity"] * 0.25 +
            scores["domain_relevance"] * 0.3,
            1,
        )

        evaluation["scores"] = {k: round(v, 1) for k, v in scores.items()}

        return evaluation

    except Exception as exc:
        return {
            "query_type": query_type,
            "query": query,
            "error": str(exc),
            "scores": {"total": 0},
        }


async def test_draft_copilot_rag(rag) -> list[dict]:
    """Draft Copilot RAG 연동을 테스트한다."""
    results = []

    for section_topic, project_type in DRAFT_TEST_SECTIONS:
        try:
            result = await rag.draft_assist(
                section_topic=section_topic,
                project_type=project_type,
            )
            has_references = result.get("available", False)
            ref_text = result.get("reference_text", "")
            sources = result.get("sources", [])

            results.append({
                "section_topic": section_topic,
                "project_type": project_type,
                "available": has_references,
                "reference_length": len(ref_text),
                "source_count": len(sources),
                "sources": [
                    {
                        "report_id": s.get("report_id", ""),
                        "project_name": s.get("project_name", ""),
                        "year": s.get("year", ""),
                        "similarity": s.get("similarity", 0),
                    }
                    for s in sources
                ],
                "reference_preview": ref_text[:300] if ref_text else "",
                "pass": has_references and len(ref_text) > 50,
            })
        except Exception as exc:
            results.append({
                "section_topic": section_topic,
                "project_type": project_type,
                "error": str(exc),
                "pass": False,
            })

    return results


async def main(with_llm: bool = False) -> None:
    from backend.app.services.report_rag import ReportRAG

    rag = ReportRAG()
    rag.load()

    output_dir = _PROJECT_ROOT / "data" / "rag"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "test_date": datetime.now(timezone.utc).isoformat(),
        "total_types_tested": len(TYPE_QUERIES),
        "with_llm": with_llm,
    }

    # ── 1. 벡터 검색 품질 테스트 ──
    logger.info("=== 1. 벡터 검색 품질 테스트 (%d개 유형) ===", len(TYPE_QUERIES))
    search_results = []

    for ptype, query in TYPE_QUERIES.items():
        logger.info("  [%s] %s", ptype, query)
        hits = rag.search(query, n_results=5, project_type=ptype)
        eval_result = evaluate_search_result(ptype, query, hits)
        search_results.append(eval_result)
        score = eval_result["scores"]["total"]
        logger.info("    → %d건, 총점: %.1f", len(hits), score)

    report["search_quality"] = {
        "results": search_results,
        "summary": _compute_search_summary(search_results),
    }

    # ── 2. LLM 답변 생성 테스트 (선택) ──
    if with_llm:
        logger.info("=== 2. LLM 답변 생성 품질 테스트 ===")
        llm_results = []

        for ptype, query in TYPE_QUERIES.items():
            logger.info("  [%s] %s", ptype, query)
            eval_result = await evaluate_llm_query(rag, ptype, query)
            llm_results.append(eval_result)
            score = eval_result.get("scores", {}).get("total", 0)
            length = eval_result.get("answer_length", 0)
            logger.info("    → %d자, 총점: %.1f", length, score)
            # API 레이트 리밋 방지
            await asyncio.sleep(1)

        report["llm_quality"] = {
            "results": llm_results,
            "summary": _compute_llm_summary(llm_results),
        }

    # ── 3. Draft Copilot RAG 연동 테스트 ──
    logger.info("=== 3. Draft Copilot RAG 연동 테스트 ===")
    draft_results = await test_draft_copilot_rag(rag)

    draft_pass_count = sum(1 for r in draft_results if r.get("pass"))
    for r in draft_results:
        status = "PASS" if r.get("pass") else "FAIL"
        logger.info(
            "  [%s/%s] %s (ref=%d자, sources=%d)",
            r["project_type"], r["section_topic"], status,
            r.get("reference_length", 0), r.get("source_count", 0),
        )

    report["draft_copilot_rag"] = {
        "results": draft_results,
        "summary": {
            "total_tests": len(draft_results),
            "passed": draft_pass_count,
            "pass_rate": round(draft_pass_count / len(draft_results) * 100, 1),
        },
    }

    # ── 4. 종합 품질 점수 ──
    search_summary = report["search_quality"]["summary"]
    draft_summary = report["draft_copilot_rag"]["summary"]

    overall = {
        "search_avg_score": search_summary["avg_total_score"],
        "search_pass_rate": search_summary["pass_rate"],
        "draft_pass_rate": draft_summary["pass_rate"],
    }

    if with_llm and "llm_quality" in report:
        llm_summary = report["llm_quality"]["summary"]
        overall["llm_avg_score"] = llm_summary["avg_total_score"]
        overall["llm_pass_rate"] = llm_summary["pass_rate"]
        overall["overall_score"] = round(
            search_summary["avg_total_score"] * 0.35 +
            llm_summary["avg_total_score"] * 0.35 +
            draft_summary["pass_rate"] * 0.3,
            1,
        )
    else:
        overall["overall_score"] = round(
            search_summary["avg_total_score"] * 0.6 +
            draft_summary["pass_rate"] * 0.4,
            1,
        )

    report["overall"] = overall

    # ── 5. 저장 ──
    output_path = output_dir / "quality_report.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("=== 결과 저장: %s ===", output_path)

    # ── 요약 출력 ──
    logger.info("="*60)
    logger.info("RAG 품질 테스트 요약")
    logger.info("="*60)
    logger.info("  벡터 검색 평균 점수: %.1f/100", search_summary["avg_total_score"])
    logger.info("  벡터 검색 통과율: %.1f%% (%d/%d)",
                search_summary["pass_rate"],
                search_summary["passed"], search_summary["total"])
    if with_llm and "llm_quality" in report:
        llm_s = report["llm_quality"]["summary"]
        logger.info("  LLM 답변 평균 점수: %.1f/100", llm_s["avg_total_score"])
        logger.info("  LLM 답변 통과율: %.1f%%", llm_s["pass_rate"])
    logger.info("  Draft Copilot RAG 통과율: %.1f%% (%d/%d)",
                draft_summary["pass_rate"],
                draft_summary["passed"], draft_summary["total_tests"])
    logger.info("  종합 점수: %.1f/100", overall["overall_score"])

    # 저품질 유형 분석
    low_types = [r for r in search_results if r["scores"]["total"] < 50]
    if low_types:
        logger.info("")
        logger.info("⚠ 저품질 유형 분석:")
        for lt in low_types:
            issues = ", ".join(lt["issues"]) if lt["issues"] else "특이사항 없음"
            logger.info("  [%s] 총점=%.1f — %s",
                        lt["query_type"], lt["scores"]["total"], issues)


def _compute_search_summary(results: list[dict]) -> dict:
    """검색 결과 요약 통계를 산출한다."""
    scores = [r["scores"]["total"] for r in results]
    passed = sum(1 for s in scores if s >= 50)

    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results) * 100, 1) if results else 0,
        "avg_total_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "min_score": round(min(scores), 1) if scores else 0,
        "max_score": round(max(scores), 1) if scores else 0,
        "by_metric": {
            "avg_relevance": round(
                sum(r["scores"]["relevance"] for r in results) / len(results), 1
            ),
            "avg_source_quality": round(
                sum(r["scores"]["source_quality"] for r in results) / len(results), 1
            ),
            "avg_content_richness": round(
                sum(r["scores"]["content_richness"] for r in results) / len(results), 1
            ),
            "avg_type_match": round(
                sum(r["scores"]["type_match"] for r in results) / len(results), 1
            ),
        },
    }


def _compute_llm_summary(results: list[dict]) -> dict:
    """LLM 답변 품질 요약 통계를 산출한다."""
    scores = [r.get("scores", {}).get("total", 0) for r in results]
    passed = sum(1 for s in scores if s >= 50)

    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results) * 100, 1) if results else 0,
        "avg_total_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "avg_answer_length": round(
            sum(r.get("answer_length", 0) for r in results) / len(results)
        ) if results else 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG 품질 테스트")
    parser.add_argument("--with-llm", action="store_true", help="LLM 답변 생성 포함")
    args = parser.parse_args()

    asyncio.run(main(with_llm=args.with_llm))
