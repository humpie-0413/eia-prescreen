"""E2E 시나리오 테스트 스크립트 (Step 16).

백엔드 API를 실행한 상태에서 3개 시나리오의 전체 흐름을 자동 검증한다.

사용법:
    # 사전 조건: uvicorn backend.app.main:app --port 8000
    python backend/scripts/e2e_test.py
    python backend/scripts/e2e_test.py --base-url http://localhost:8000
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _PROJECT_ROOT / "data" / "e2e_results"

# Windows cp949 stdout 안전 출력
import io, os
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCENARIOS = {
    "yangpyeong": {
        "project_name": "양평 국도 우회도로 건설사업",
        "project_type": "road",
        "project_scale": "L=4.2km, W=20m (4차로)",
        "address": "경기도 양평군 양평읍",
        "location": {"lng": 127.4875, "lat": 37.4913},
    },
    "boryeong": {
        "project_name": "보령 화력발전소 증설사업",
        "project_type": "energy",
        "project_scale": "500MW급 1기",
        "address": "충청남도 보령시 오천면",
        "location": {"lng": 126.553, "lat": 36.334},
    },
    "sejong": {
        "project_name": "세종 행복도시 생활권 개발사업",
        "project_type": "urban_dev",
        "project_scale": "A=120ha",
        "address": "세종특별자치시 소정면",
        "location": {"lng": 127.0028, "lat": 36.604},
    },
}


def _request(method: str, url: str, data: dict | None = None, timeout: int = 60) -> dict | bytes:
    """HTTP 요청을 수행한다."""
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return json.loads(raw)
            return raw
    except HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"_error": True, "_status": e.code, "_body": body[:500]}
    except URLError as e:
        return {"_error": True, "_status": 0, "_body": str(e)}


def _get(url: str, timeout: int = 60) -> dict | bytes:
    return _request("GET", url, timeout=timeout)


def _post(url: str, data: dict | None = None, timeout: int = 120) -> dict | bytes:
    return _request("POST", url, data=data, timeout=timeout)


class E2EResult:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.steps: list[dict] = []
        self.passed = 0
        self.failed = 0
        self.screening_id: str | None = None

    def check(self, name: str, result: dict | bytes, checks: list[tuple[str, bool]]):
        step = {
            "name": name,
            "passed": [],
            "failed": [],
        }
        is_error = isinstance(result, dict) and result.get("_error")
        if is_error:
            step["failed"].append(f"HTTP 오류: {result.get('_status')} — {result.get('_body', '')[:200]}")
            step["response_preview"] = result.get("_body", "")[:300]
            self.failed += 1
        else:
            for desc, ok in checks:
                if ok:
                    step["passed"].append(desc)
                    self.passed += 1
                else:
                    step["failed"].append(desc)
                    self.failed += 1
            # Save response preview
            if isinstance(result, dict):
                step["response_preview"] = json.dumps(result, ensure_ascii=False, default=str)[:500]
            elif isinstance(result, bytes):
                step["response_preview"] = f"[binary {len(result)} bytes]"

        self.steps.append(step)
        status = "PASS" if not step["failed"] else "FAIL"
        print(f"  [{status}] {name} ({len(step['passed'])} ok, {len(step['failed'])} fail)")
        if step["failed"]:
            for f in step["failed"]:
                print(f"         ✗ {f}")

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "screening_id": self.screening_id,
            "total_checks": self.passed + self.failed,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.passed / max(1, self.passed + self.failed) * 100, 1),
            "steps": self.steps,
        }


def run_scenario(base_url: str, scenario_name: str, project: dict) -> E2EResult:
    """단일 시나리오의 전체 E2E 흐름을 실행한다."""
    result = E2EResult(scenario_name)
    print(f"\n{'='*60}")
    print(f"시나리오: {scenario_name} ({project['project_type']})")
    print(f"{'='*60}")

    # 1. 스크리닝 생성
    resp = _post(f"{base_url}/api/screening", data=project)
    screening_id = resp.get("id", "test-id") if isinstance(resp, dict) else "test-id"
    result.screening_id = screening_id
    result.check("POST /api/screening (스크리닝 생성)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("id 존재", bool(screening_id and screening_id != "test-id")),
        ("project_name 일치", resp.get("project_name") == project["project_name"] if isinstance(resp, dict) else False),
        ("project_type 일치", resp.get("project_type") == project["project_type"] if isinstance(resp, dict) else False),
    ])

    # 2. 리스크 평가
    resp = _post(f"{base_url}/api/screening/{screening_id}/evaluate", data={"scenario": scenario_name})
    risk_cards = resp.get("risk_cards", []) if isinstance(resp, dict) else []
    regulations = resp.get("regulation_matches", []) if isinstance(resp, dict) else []
    summary = resp.get("summary", {}) if isinstance(resp, dict) else {}
    result.check("POST /api/screening/{id}/evaluate (리스크 평가)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("risk_cards 존재", len(risk_cards) > 0),
        ("regulation_matches 존재", len(regulations) > 0),
        ("summary 존재", bool(summary)),
        ("total_risks > 0", summary.get("total_risks", 0) > 0),
    ])

    # 3. 규제 매칭 조회 (데모모드에서는 DB 없으므로 빈 리스트 정상)
    resp = _get(f"{base_url}/api/screening/{screening_id}/regulations")
    result.check("GET /api/screening/{id}/regulations (규제 조회)", resp, [
        ("응답 존재 (리스트 또는 dict)", isinstance(resp, (dict, list)) and not (isinstance(resp, dict) and resp.get("_error"))),
    ])

    # 4. 체크리스트
    resp = _get(f"{base_url}/api/screening/{screening_id}/checklist")
    checklist_items = resp.get("total_items", 0) if isinstance(resp, dict) else 0
    result.check("GET /api/screening/{id}/checklist (체크리스트)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("항목 수 > 0", checklist_items > 0),
    ])

    # 5. 유사사례 (데모모드에서는 DB가 없어 태그 추출 불가, 빈 결과 정상)
    resp = _post(f"{base_url}/api/screening/{screening_id}/similar-cases")
    cases = resp.get("cases", []) if isinstance(resp, dict) else []
    result.check("POST /api/screening/{id}/similar-cases (유사사례)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("사례 구조 정상", "cases" in resp and "total" in resp if isinstance(resp, dict) else False),
    ])

    # 6. LLM 해석
    resp = _post(f"{base_url}/api/screening/{screening_id}/interpret", timeout=180)
    interpretation = resp.get("interpretation", "") if isinstance(resp, dict) else ""
    result.check("POST /api/screening/{id}/interpret (LLM 해석)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("해석문 길이 > 100자", len(interpretation) > 100),
        ("disclaimer 포함", bool(resp.get("disclaimer")) if isinstance(resp, dict) else False),
    ])

    # 7. 초안 생성
    resp = _post(f"{base_url}/api/screening/{screening_id}/draft", data={"scenario": scenario_name}, timeout=180)
    sections = resp.get("sections", []) if isinstance(resp, dict) else []
    result.check("POST /api/screening/{id}/draft (초안 생성)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("섹션 수 > 5", len(sections) > 5),
        ("disclaimer 포함", bool(resp.get("disclaimer")) if isinstance(resp, dict) else False),
    ])

    # 8. 검토의견 예측
    resp = _post(f"{base_url}/api/screening/{screening_id}/predict-review", data={"scenario": scenario_name})
    predicted = resp.get("predicted_comments", []) if isinstance(resp, dict) else []
    result.check("POST /api/screening/{id}/predict-review (검토의견 예측)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("예측 항목 존재", len(predicted) > 0),
    ])

    # 9. 품질 체크
    resp = _post(f"{base_url}/api/screening/{screening_id}/quality-check", data={"scenario": scenario_name}, timeout=180)
    checks = resp.get("checks", []) if isinstance(resp, dict) else []
    result.check("POST /api/screening/{id}/quality-check (품질 체크)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("체크 항목 존재", len(checks) > 0),
        ("점수 존재", resp.get("score") is not None if isinstance(resp, dict) else False),
    ])

    # 10. RAG 질의
    rag_query = {
        "road": "도로 사업의 비산먼지 저감방안은?",
        "energy": "화력발전소의 대기오염물질 배출 저감 기술은?",
        "urban_dev": "택지개발 사업의 교통 영향 저감방안은?",
    }.get(project["project_type"], "환경영향평가 주요 검토항목은?")
    resp = _post(f"{base_url}/api/rag/query", data={
        "question": rag_query,
        "project_type": project["project_type"],
        "n_results": 5,
    }, timeout=180)
    sources = resp.get("sources", []) if isinstance(resp, dict) else []
    result.check("POST /api/rag/query (RAG 질의)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("출처 존재", len(sources) > 0),
        ("답변 존재", len(resp.get("answer", "")) > 50 if isinstance(resp, dict) else False),
    ])

    # 11. 과거 패턴
    resp = _get(f"{base_url}/api/patterns/{project['project_type']}")
    result.check(f"GET /api/patterns/{project['project_type']} (과거 패턴)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("project_type 일치", resp.get("project_type") == project["project_type"] if isinstance(resp, dict) else False),
    ])

    # 12. PDF 생성 (brief)
    resp = _post(f"{base_url}/api/screening/{screening_id}/report", data={
        "report_type": "brief",
        "scenario": scenario_name,
    }, timeout=180)
    result.check("POST /api/screening/{id}/report (PDF 브리프)", resp, [
        ("PDF 생성 성공", isinstance(resp, bytes) and len(resp) > 1000),
    ])
    # Save PDF if successful
    if isinstance(resp, bytes) and len(resp) > 1000:
        pdf_path = OUTPUT_DIR / f"{scenario_name}_brief.pdf"
        pdf_path.write_bytes(resp)

    return result


def run_common_endpoints(base_url: str) -> E2EResult:
    """공통 엔드포인트를 테스트한다."""
    result = E2EResult("common")
    print(f"\n{'='*60}")
    print("공통 엔드포인트 테스트")
    print(f"{'='*60}")

    # Health
    resp = _get(f"{base_url}/health")
    result.check("GET /health", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("status 존재", "status" in resp if isinstance(resp, dict) else False),
        ("demo_mode=true", resp.get("demo_mode") is True if isinstance(resp, dict) else False),
    ])

    # RAG stats
    resp = _get(f"{base_url}/api/rag/stats")
    result.check("GET /api/rag/stats", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("total_chunks > 0", resp.get("total_chunks", 0) > 0 if isinstance(resp, dict) else False),
    ])

    # Overall patterns
    resp = _get(f"{base_url}/api/patterns")
    result.check("GET /api/patterns (전체 요약)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("total_count > 0", resp.get("total_count", 0) > 0 if isinstance(resp, dict) else False),
    ])

    # Draft template
    resp = _get(f"{base_url}/api/draft/template")
    result.check("GET /api/draft/template", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
    ])

    # Connectors
    resp = _get(f"{base_url}/api/data-status/connectors")
    result.check("GET /api/data-status/connectors", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
    ])

    # Cases search
    resp = _get(f"{base_url}/api/cases?limit=5")
    total_cases = resp.get("total", 0) if isinstance(resp, dict) else 0
    result.check("GET /api/cases (사례 검색)", resp, [
        ("응답 존재", isinstance(resp, dict) and not resp.get("_error")),
        ("사례 수 > 0", total_cases > 0),
    ])

    # Suggested rules
    resp = _get(f"{base_url}/api/patterns/rules/suggested")
    result.check("GET /api/patterns/rules/suggested", resp, [
        ("응답 존재", isinstance(resp, (dict, list)) and not (isinstance(resp, dict) and resp.get("_error"))),
    ])

    return result


def main():
    parser = argparse.ArgumentParser(description="E2E 시나리오 테스트")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"E2E 테스트 시작: {base_url}")
    print(f"시간: {datetime.now().isoformat()}")

    # Health check first
    health = _get(f"{base_url}/health")
    if isinstance(health, dict) and health.get("_error"):
        print(f"\n서버 연결 실패: {health}")
        print("서버를 먼저 시작하세요: uvicorn backend.app.main:app --port 8000")
        sys.exit(1)

    all_results = []

    # Common endpoints
    common = run_common_endpoints(base_url)
    all_results.append(common)

    # 3 scenarios
    for scenario_name, project in SCENARIOS.items():
        result = run_scenario(base_url, scenario_name, project)
        all_results.append(result)

        # Save individual result
        out_path = OUTPUT_DIR / f"{scenario_name}_result.json"
        out_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # Summary
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total = total_passed + total_failed

    summary = {
        "test_date": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "total_checks": total,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": round(total_passed / max(1, total) * 100, 1),
        "scenarios": [r.to_dict() for r in all_results],
    }

    # Save summary
    summary_path = OUTPUT_DIR / "e2e_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"\n{'='*60}")
    print("E2E 테스트 결과 요약")
    print(f"{'='*60}")
    for r in all_results:
        status = "PASS" if r.failed == 0 else "FAIL"
        print(f"  [{status}] {r.scenario}: {r.passed}/{r.passed+r.failed} 통과")
    print(f"\n  전체: {total_passed}/{total} 통과 ({summary['pass_rate']}%)")
    print(f"  결과 저장: {OUTPUT_DIR}")

    if total_failed > 0:
        print(f"\n  실패 항목 {total_failed}건:")
        for r in all_results:
            for step in r.steps:
                for f in step["failed"]:
                    print(f"    [{r.scenario}] {step['name']}: {f}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
