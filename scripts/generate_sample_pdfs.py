"""샘플 PDF 생성 스크립트.

3개 데모 시나리오(양평·세종·보령)의 실제 리스크 평가 결과를
PDF 파일로 출력한다. DB 불필요 — 서비스 레이어 직접 실행.

출력: data/demo/pdf_samples/
  yangpyeong_brief.pdf
  yangpyeong_full_report.pdf
  yangpyeong_checklist.pdf
  sejong_brief.pdf
  ...
  comparison_yangpyeong_vs_sejong_vs_boryeong.pdf
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.services.data_fetcher import DataFetcher
from backend.app.services.risk_engine import RiskEngine
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.checklist_generator import ChecklistGenerator
from backend.app.services.case_search import CaseSearchService
from backend.app.services.report_generator import ReportGenerator

# ── 설정 ──────────────────────────────────────────────────────

SCENARIOS = {
    "yangpyeong": {
        "coords": (127.4875, 37.4913),
        "project": {
            "project_name": "양평 국도 우회도로 건설사업",
            "project_type": "road",
            "project_scale": "L=4.2km, W=20m (4차로)",
            "address": "경기도 양평군 양평읍 일원",
        },
    },
    "sejong": {
        "coords": (127.0028, 36.6040),
        "project": {
            "project_name": "세종 행정복합타운 주거단지 조성사업",
            "project_type": "housing",
            "project_scale": "A=52만㎡, 2,500세대",
            "address": "세종특별자치시 도담동 일원",
        },
    },
    "boryeong": {
        "coords": (126.5530, 36.3340),
        "project": {
            "project_name": "보령 석탄화력발전소 증설사업",
            "project_type": "power_plant",
            "project_scale": "500MW × 2기",
            "address": "충청남도 보령시 오천면 일원",
        },
    },
}

DEMO_DATA_DIR = ROOT / "data" / "demo"
OUTPUT_DIR = ROOT / "data" / "demo" / "pdf_samples"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_demo_project_info(scenario: str) -> dict:
    path = DEMO_DATA_DIR / scenario / "mock_data.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw.get("project", {})
    return {}


async def evaluate_scenario(
    scenario: str,
    fetcher: DataFetcher,
    engine: RiskEngine,
    matcher: RegulationMatcher,
) -> dict:
    """시나리오 평가 실행."""
    cfg = SCENARIOS[scenario]
    lng, lat = cfg["coords"]

    print(f"  [{scenario}] 공간 데이터 수집 중...")
    spatial = await fetcher.fetch_all_as_spatial_data(lng, lat, scenario=scenario)

    # 프로젝트 정보 (mock 데이터로 보강)
    project_info = dict(cfg["project"])
    demo_info = _load_demo_project_info(scenario)
    project_info.update({k: v for k, v in demo_info.items() if v is not None})

    print(f"  [{scenario}] 리스크 엔진 평가 중...")
    risks = engine.evaluate(project_info, spatial)

    print(f"  [{scenario}] 규제 매칭 중...")
    regs = matcher.match(project_info, spatial)

    return {
        "scenario": scenario,
        "project": cfg["project"],
        "risks": risks,
        "regs": regs,
    }


def risks_to_dicts(risks) -> list[dict]:
    return [
        {
            "rule_id": r.rule_id,
            "title": r.title,
            "severity": r.severity,
            "rationale": r.rationale,
            "next_action": r.next_action,
            "legal_basis": r.legal_basis,
            "evidence": r.evidence,
        }
        for r in risks
    ]


def regs_to_dicts(regs) -> list[dict]:
    return [
        {
            "regulation_name": r.regulation_name,
            "regulation_code": r.regulation_code,
            "legal_basis": r.legal_basis,
            "description": r.description,
            "restriction_level": r.restriction_level,
            "permit_required": r.permit_required,
            "related_authority": r.related_authority,
        }
        for r in regs
    ]


def severity_label(severity: str) -> str:
    return {"critical": "Critical", "major": "Major", "review": "Review", "info": "Info"}.get(severity, severity)


async def main():
    print("=" * 60)
    print("EIA Pre-Screen 샘플 PDF 생성")
    print("=" * 60)

    # 서비스 초기화
    engine = RiskEngine()
    engine.load_rules()
    fetcher = DataFetcher()
    matcher = RegulationMatcher()
    checklist_gen = ChecklistGenerator()
    case_svc = CaseSearchService()
    report_gen = ReportGenerator()

    # 3개 시나리오 평가
    results = {}
    for scenario in SCENARIOS:
        print(f"\n[{scenario.upper()}] 평가 시작")
        results[scenario] = await evaluate_scenario(scenario, fetcher, engine, matcher)

    # ── 개별 시나리오 PDF 생성 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("PDF 생성 중...")
    print("=" * 60)

    site_summaries = []  # 비교 보고서용

    for scenario, res in results.items():
        print(f"\n[{scenario}] PDF 생성")

        risk_dicts = risks_to_dicts(res["risks"])
        reg_dicts = regs_to_dicts(res["regs"])
        project_info = res["project"]

        critical = sum(1 for r in risk_dicts if r["severity"] == "critical")
        major    = sum(1 for r in risk_dicts if r["severity"] == "major")
        review   = sum(1 for r in risk_dicts if r["severity"] == "review")
        info_cnt = sum(1 for r in risk_dicts if r["severity"] == "info")

        print(f"  리스크: Critical={critical}, Major={major}, Review={review}, Info={info_cnt} (총 {len(risk_dicts)}건)")
        print(f"  규제: {len(reg_dicts)}건")

        # 체크리스트 생성
        checklist_result = checklist_gen.generate(risk_dicts, reg_dicts, screening_id=f"demo-{scenario}")
        checklist_data = checklist_gen.to_pdf_structure(checklist_result)

        # 유사사례 검색
        tags = [r["title"] for r in risk_dicts[:5]]
        similar = case_svc.find_similar(
            risk_card_tags=tags,
            project_type=project_info.get("project_type"),
            limit=3,
        )
        cases_data = [c.model_dump() for c in similar.results]

        # AI 해석 텍스트 (하드코딩 — API 키 불필요)
        interpretation = _build_interpretation(scenario, risk_dicts, reg_dicts)

        # 1p 브리프
        print(f"  → {scenario}_brief.pdf")
        brief_pdf = report_gen.generate_brief(
            project_info=project_info,
            risk_cards=risk_dicts,
            regulations=reg_dicts,
            interpretation=interpretation,
        )
        (OUTPUT_DIR / f"{scenario}_brief.pdf").write_bytes(brief_pdf)

        # 환경현황 요약 보고서
        print(f"  → {scenario}_full_report.pdf")
        full_pdf = report_gen.generate_full_report(
            project_info=project_info,
            risk_cards=risk_dicts,
            regulations=reg_dicts,
            cases=cases_data,
            interpretation=interpretation,
            checklist=checklist_data,
        )
        (OUTPUT_DIR / f"{scenario}_full_report.pdf").write_bytes(full_pdf)

        # 체크리스트
        print(f"  → {scenario}_checklist.pdf")
        cl_pdf = report_gen.generate_checklist_pdf(checklist=checklist_data)
        (OUTPUT_DIR / f"{scenario}_checklist.pdf").write_bytes(cl_pdf)

        # 비교 보고서용 사이트 요약 누적
        site_summaries.append({
            "screening_id": f"demo-{scenario}",
            "project_name": project_info["project_name"],
            "project_type": project_info.get("project_type", ""),
            "address": project_info.get("address", ""),
            "total_risks": len(risk_dicts),
            "critical_count": critical,
            "major_count": major,
            "review_count": review,
            "info_count": info_cnt,
            "total_regulations": len(reg_dicts),
            "permit_required_count": sum(1 for r in reg_dicts if r.get("permit_required")),
        })

    # ── 비교 보고서 ────────────────────────────────────────────
    print("\n[비교] PDF 생성")

    # 리스크 매트릭스 구성
    all_rules: dict[str, str] = {}
    for res in results.values():
        for r in res["risks"]:
            all_rules[r.rule_id] = r.title

    risk_matrix = []
    for rule_id, title in sorted(all_rules.items()):
        row = {"rule_id": rule_id, "title": title, "severity_by_site": {}}
        for scenario, res in results.items():
            site_id = f"demo-{scenario}"
            matched = next((r.severity for r in res["risks"] if r.rule_id == rule_id), None)
            row["severity_by_site"][site_id] = matched
        risk_matrix.append(row)

    recommendation = (
        "비교 분석 결과, 3개 부지 중 '양평 국도 우회도로 건설사업'이 상대적으로 환경 리스크가 낮습니다. "
        "'보령 석탄화력발전소 증설사업'은 Critical 3건(ECO-001, LAND-001, WAT-002)이 있어 "
        "사업 추진 전 반드시 입지 타당성 재검토가 필요합니다. "
        "'세종 행정복합타운'은 대기관리권역·소음 리스크가 있으나 Critical은 없습니다. "
        "본 비교는 AI 기반 사전검토 결과이며, 최종 판단은 전문가 검토를 통해 이루어져야 합니다."
    )

    print(f"  → comparison_all_scenarios.pdf")
    comp_pdf = report_gen.generate_comparison_report(
        sites=site_summaries,
        risk_matrix=risk_matrix,
        recommendation=recommendation,
    )
    (OUTPUT_DIR / "comparison_all_scenarios.pdf").write_bytes(comp_pdf)

    # ── 완료 요약 ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("생성 완료:")
    for f in sorted(OUTPUT_DIR.iterdir()):
        size_kb = f.stat().st_size // 1024
        print(f"  {f.name:<50} {size_kb:>5} KB")
    print(f"\n출력 경로: {OUTPUT_DIR}")
    print("=" * 60)


def _build_interpretation(scenario: str, risks: list[dict], regs: list[dict]) -> str:
    """시나리오별 사전 작성된 AI 해석문."""
    criticals = [r for r in risks if r["severity"] == "critical"]
    majors    = [r for r in risks if r["severity"] == "major"]

    if scenario == "yangpyeong":
        return (
            "본 사업지(양평 국도 우회도로)는 관리지역(계획관리)에 위치하며, 농업진흥지역과 중첩됩니다. "
            "팔당상수원 수변구역에 해당하여 수질 관련 규제가 적용되며, 800m 이내 멸종위기종(수달·삵) "
            "서식이 확인되어 생태 조사가 필수적입니다.\n\n"
            "주요 리스크는 농지전용 협의(농지법 제34조), 수변구역 행위제한(한강수계법 제4조), "
            "멸종위기종 서식지 보호(야생생물법 제14조) 순으로, 사전 협의를 통해 사업 지연을 최소화할 수 있습니다. "
            "소음·진동 영향과 경관 영향도 주거지역 인접으로 인해 검토가 필요합니다.\n\n"
            "권고 사항: 생태 정밀조사 및 대안 노선 검토를 사업 계획 초기 단계에 착수하고, "
            "농지전용 허가와 수변구역 협의를 병행 추진하여 인허가 기간을 단축하는 것이 효율적입니다."
        )
    elif scenario == "sejong":
        return (
            "세종 행정복합타운은 도시지역(주거지역) 내 위치하며, 대기관리권역에 포함되어 있어 "
            "대기오염물질 총량 관리 의무가 부과됩니다. 인근 80m 이내에 학교·병원 등 소음 민감 시설이 있어 "
            "공사 및 운영 단계 소음 관리가 핵심 이슈입니다.\n\n"
            "대기관리권역 내 사업으로 수도권대기환경청 협의가 의무이며, NOI-001(주거 인접)과 "
            "NOI-002(소음 민감 시설 인접) 두 가지 소음 규정이 동시에 적용됩니다. "
            "반복 민원(4건) 이력이 있어 주민설명회 및 의견 수렴 절차를 조기 추진해야 합니다.\n\n"
            "Critical 리스크는 없으나, 대기·소음·민원 3개 영역의 복합적 관리 체계 수립이 필요합니다. "
            "사업 계획 단계에서 소음저감시설 설계와 대기오염 저감 기술 적용을 사전 반영하십시오."
        )
    else:  # boryeong
        return (
            "보령 석탄화력발전소 부지는 생태자연도 1등급 지역(ECO-001)이 사업지와 직접 중첩되며, "
            "용도지역 상충(LAND-001)과 상수원보호구역 인접(WAT-002) 등 Critical 리스크 3건이 확인됩니다. "
            "이는 현재 입지에서 사업 추진이 사실상 불가능하거나 대규모 설계 변경이 불가피한 수준입니다.\n\n"
            "자연환경보전법 제28조에 따라 생태자연도 1등급 지역은 개발 행위가 원칙적으로 금지됩니다. "
            "군사시설보호구역(LAND-004) 중첩으로 국방부 협의도 필요하며, PM2.5 연평균 농도가 "
            "기준치(35㎍/㎥)를 초과(38.2㎍/㎥)하여 대기환경 부하가 이미 높은 지역입니다.\n\n"
            "강력 권고: 현재 입지는 환경적·법적 타당성 확보가 매우 어렵습니다. "
            "생태자연도 2등급 이하, 상수원보호구역 500m 외부, 용도지역 적합 지역으로 "
            "대안 입지 선정을 우선 검토하십시오."
        )


if __name__ == "__main__":
    asyncio.run(main())
