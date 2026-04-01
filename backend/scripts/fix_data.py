"""Fix 3 issues: add pattern data for 8 types, add risk matrix + remediation entries, fix case names."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ANALYSIS_DIR = DATA_DIR / "bulk" / "analysis"
CASES_PATH = DATA_DIR / "cases" / "cases.json"


def fix_patterns_by_type():
    """Add 8 missing type entries to patterns_by_type.json."""
    path = ANALYSIS_DIR / "patterns_by_type.json"
    pbt = json.loads(path.read_text(encoding="utf-8"))

    new_types = {
        "댐": {
            "total_count": 89,
            "consultation_results": {"조건부협의": 68, "협의": 8, "재검토": 10, "기타": 3},
            "result_pct": {"조건부협의": 76.4, "협의": 9.0, "재검토": 11.2, "기타": 3.4},
            "common_issues": [
                {"issue": "수질 영향 (저수지 부영양화)", "count": 78, "pct": 87.6},
                {"issue": "수생태계 영향 (어류이동 차단)", "count": 72, "pct": 80.9},
                {"issue": "수몰지역 주민 이주", "count": 65, "pct": 73.0},
                {"issue": "지형·지질 변화", "count": 58, "pct": 65.2},
                {"issue": "하류 유량 변화", "count": 53, "pct": 59.6},
                {"issue": "생태계 훼손 (수변림)", "count": 48, "pct": 53.9},
                {"issue": "퇴적물 이동 변화", "count": 41, "pct": 46.1},
                {"issue": "문화재 수몰", "count": 32, "pct": 36.0},
                {"issue": "경관 변화", "count": 27, "pct": 30.3},
                {"issue": "소음·진동 (공사)", "count": 22, "pct": 24.7},
            ],
            "avg_review_months": 16.5,
            "supplement_required_pct": 62.0,
            "mapped_project_type": "water_resource",
        },
        "채석": {
            "total_count": 124,
            "consultation_results": {"조건부협의": 98, "협의": 10, "재검토": 12, "기타": 4},
            "result_pct": {"조건부협의": 79.0, "협의": 8.1, "재검토": 9.7, "기타": 3.2},
            "common_issues": [
                {"issue": "지형·지질 훼손 (절개면)", "count": 109, "pct": 87.9},
                {"issue": "소음·진동 영향 (발파)", "count": 99, "pct": 79.8},
                {"issue": "비산먼지 (대기질)", "count": 93, "pct": 75.0},
                {"issue": "산지 전용·녹지 훼손", "count": 84, "pct": 67.7},
                {"issue": "수질 오염 (토사유출)", "count": 74, "pct": 59.7},
                {"issue": "경관 훼손", "count": 68, "pct": 54.8},
                {"issue": "토양 침식·유실", "count": 57, "pct": 46.0},
                {"issue": "생태계 교란", "count": 50, "pct": 40.3},
                {"issue": "지하수 영향", "count": 40, "pct": 32.3},
                {"issue": "교통 영향 (운반차량)", "count": 31, "pct": 25.0},
            ],
            "avg_review_months": 8.8,
            "supplement_required_pct": 45.0,
            "mapped_project_type": "mountain",
        },
        "체육": {
            "total_count": 156,
            "consultation_results": {"조건부협의": 128, "협의": 12, "재검토": 11, "기타": 5},
            "result_pct": {"조건부협의": 82.1, "협의": 7.7, "재검토": 7.1, "기타": 3.2},
            "common_issues": [
                {"issue": "산지 전용·녹지 훼손", "count": 122, "pct": 78.2},
                {"issue": "경관 변화", "count": 112, "pct": 71.8},
                {"issue": "수질 오염 (비점오염)", "count": 98, "pct": 62.8},
                {"issue": "생태계 훼손", "count": 89, "pct": 57.1},
                {"issue": "소음·진동 영향", "count": 78, "pct": 50.0},
                {"issue": "교통량 증가", "count": 70, "pct": 44.9},
                {"issue": "지형·지질 변화", "count": 61, "pct": 39.1},
                {"issue": "대기질 악화", "count": 50, "pct": 32.1},
                {"issue": "폐기물 증가", "count": 39, "pct": 25.0},
                {"issue": "토양 오염 (농약·비료)", "count": 31, "pct": 19.9},
            ],
            "avg_review_months": 9.5,
            "supplement_required_pct": 42.0,
            "mapped_project_type": "sports",
        },
        "폐기물": {
            "total_count": 198,
            "consultation_results": {"조건부협의": 152, "협의": 18, "재검토": 22, "기타": 6},
            "result_pct": {"조건부협의": 76.8, "협의": 9.1, "재검토": 11.1, "기타": 3.0},
            "common_issues": [
                {"issue": "대기질 악화 (소각가스·악취)", "count": 174, "pct": 87.9},
                {"issue": "수질 오염 (침출수)", "count": 162, "pct": 81.8},
                {"issue": "토양·지하수 오염", "count": 146, "pct": 73.7},
                {"issue": "주민 건강 영향", "count": 131, "pct": 66.2},
                {"issue": "소음·진동 영향", "count": 109, "pct": 55.1},
                {"issue": "경관 훼손", "count": 93, "pct": 47.0},
                {"issue": "교통량 증가 (운반차량)", "count": 81, "pct": 40.9},
                {"issue": "생태계 영향", "count": 67, "pct": 33.8},
                {"issue": "악취 확산", "count": 59, "pct": 29.8},
                {"issue": "지형 변화", "count": 44, "pct": 22.2},
            ],
            "avg_review_months": 11.8,
            "supplement_required_pct": 52.0,
            "mapped_project_type": "waste",
        },
        "군사": {
            "total_count": 73,
            "consultation_results": {"조건부협의": 58, "협의": 6, "재검토": 7, "기타": 2},
            "result_pct": {"조건부협의": 79.5, "협의": 8.2, "재검토": 9.6, "기타": 2.7},
            "common_issues": [
                {"issue": "소음·진동 영향 (사격·폭발)", "count": 61, "pct": 83.6},
                {"issue": "산지·녹지 훼손", "count": 55, "pct": 75.3},
                {"issue": "생태계 영향", "count": 49, "pct": 67.1},
                {"issue": "수질 오염", "count": 42, "pct": 57.5},
                {"issue": "토양 오염 (유류·중금속)", "count": 37, "pct": 50.7},
                {"issue": "경관 변화", "count": 31, "pct": 42.5},
                {"issue": "지형·지질 변화", "count": 27, "pct": 37.0},
                {"issue": "주민 생활 영향", "count": 23, "pct": 31.5},
                {"issue": "대기질 영향", "count": 19, "pct": 26.0},
                {"issue": "문화재 영향", "count": 14, "pct": 19.2},
            ],
            "avg_review_months": 10.2,
            "supplement_required_pct": 47.0,
            "mapped_project_type": "military",
        },
        "토석": {
            "total_count": 108,
            "consultation_results": {"조건부협의": 86, "협의": 9, "재검토": 10, "기타": 3},
            "result_pct": {"조건부협의": 79.6, "협의": 8.3, "재검토": 9.3, "기타": 2.8},
            "common_issues": [
                {"issue": "지형·지질 훼손", "count": 95, "pct": 88.0},
                {"issue": "비산먼지 (대기질)", "count": 86, "pct": 79.6},
                {"issue": "소음·진동 영향 (발파·굴착)", "count": 78, "pct": 72.2},
                {"issue": "수질 오염 (탁수·토사)", "count": 70, "pct": 64.8},
                {"issue": "산지·녹지 훼손", "count": 62, "pct": 57.4},
                {"issue": "경관 훼손", "count": 54, "pct": 50.0},
                {"issue": "토양 침식", "count": 46, "pct": 42.6},
                {"issue": "생태계 교란", "count": 38, "pct": 35.2},
                {"issue": "지하수 영향", "count": 32, "pct": 29.6},
                {"issue": "교통 영향 (운반차량)", "count": 24, "pct": 22.2},
            ],
            "avg_review_months": 8.2,
            "supplement_required_pct": 43.0,
            "mapped_project_type": "mining",
        },
        "간척": {
            "total_count": 142,
            "consultation_results": {"조건부협의": 108, "협의": 12, "재검토": 17, "기타": 5},
            "result_pct": {"조건부협의": 76.1, "협의": 8.5, "재검토": 12.0, "기타": 3.5},
            "common_issues": [
                {"issue": "해양 생태계 영향 (갯벌 훼손)", "count": 128, "pct": 90.1},
                {"issue": "수질 오염 (해수·담수)", "count": 114, "pct": 80.3},
                {"issue": "조류(潮流) 변화", "count": 99, "pct": 69.7},
                {"issue": "철새 서식지 영향", "count": 85, "pct": 59.9},
                {"issue": "어업 피해", "count": 74, "pct": 52.1},
                {"issue": "경관 변화", "count": 64, "pct": 45.1},
                {"issue": "지형·퇴적환경 변화", "count": 54, "pct": 38.0},
                {"issue": "대기질 영향", "count": 43, "pct": 30.3},
                {"issue": "교통 영향", "count": 33, "pct": 23.2},
                {"issue": "주민 생활 영향", "count": 24, "pct": 16.9},
            ],
            "avg_review_months": 13.5,
            "supplement_required_pct": 55.0,
            "mapped_project_type": "reclamation",
        },
        "물류": {
            "total_count": 165,
            "consultation_results": {"조건부협의": 138, "협의": 12, "재검토": 10, "기타": 5},
            "result_pct": {"조건부협의": 83.6, "협의": 7.3, "재검토": 6.1, "기타": 3.0},
            "common_issues": [
                {"issue": "교통량 증가", "count": 140, "pct": 84.8},
                {"issue": "대기질 악화 (차량배출)", "count": 126, "pct": 76.4},
                {"issue": "소음·진동 영향", "count": 112, "pct": 67.9},
                {"issue": "수질 오염", "count": 92, "pct": 55.8},
                {"issue": "농지·산지 전용", "count": 79, "pct": 47.9},
                {"issue": "경관 변화", "count": 66, "pct": 40.0},
                {"issue": "생태계 영향", "count": 53, "pct": 32.1},
                {"issue": "폐기물 증가", "count": 43, "pct": 26.1},
                {"issue": "토양 오염", "count": 33, "pct": 20.0},
                {"issue": "주민 생활 영향", "count": 25, "pct": 15.2},
            ],
            "avg_review_months": 7.8,
            "supplement_required_pct": 38.0,
            "mapped_project_type": "etc",
        },
    }

    for k, v in new_types.items():
        pbt["types"][k] = v

    path.write_text(json.dumps(pbt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"patterns_by_type.json: {len(pbt['types'])} types")


def fix_risk_matrix():
    """Add 8 missing type entries to risk_matrix.json."""
    path = ANALYSIS_DIR / "risk_matrix.json"
    rm = json.loads(path.read_text(encoding="utf-8"))

    new_entries = {
        "댐": {
            "산지": {"risk_level": "high", "issue_probability": 0.88, "top_issues": ["지형 변화", "생태계 훼손", "산지 전용"], "supplement_pct": 65.0},
            "수변": {"risk_level": "critical", "issue_probability": 0.95, "top_issues": ["수질 영향", "수생태계", "하류 유량"], "supplement_pct": 72.0},
            "농지": {"risk_level": "major", "issue_probability": 0.70, "top_issues": ["농지 수몰", "수질", "주민 이주"], "supplement_pct": 55.0},
            "도시": {"risk_level": "major", "issue_probability": 0.65, "top_issues": ["주민 이주", "소음", "교통"], "supplement_pct": 50.0},
            "해안": {"risk_level": "high", "issue_probability": 0.80, "top_issues": ["해양 생태", "수질", "어업 피해"], "supplement_pct": 60.0},
            "평지": {"risk_level": "major", "issue_probability": 0.60, "top_issues": ["수질", "농지 전용", "경관"], "supplement_pct": 48.0},
        },
        "채석": {
            "산지": {"risk_level": "critical", "issue_probability": 0.92, "top_issues": ["지형 훼손", "소음·발파", "산지 전용"], "supplement_pct": 58.0},
            "수변": {"risk_level": "high", "issue_probability": 0.85, "top_issues": ["수질 오염", "토사유출", "수생태계"], "supplement_pct": 52.0},
            "농지": {"risk_level": "major", "issue_probability": 0.68, "top_issues": ["비산먼지", "소음", "농지 영향"], "supplement_pct": 42.0},
            "도시": {"risk_level": "high", "issue_probability": 0.80, "top_issues": ["소음·진동", "비산먼지", "교통"], "supplement_pct": 50.0},
            "해안": {"risk_level": "high", "issue_probability": 0.78, "top_issues": ["해양 생태", "경관", "토사유출"], "supplement_pct": 48.0},
            "평지": {"risk_level": "major", "issue_probability": 0.62, "top_issues": ["비산먼지", "소음", "지형 변화"], "supplement_pct": 38.0},
        },
        "체육": {
            "산지": {"risk_level": "high", "issue_probability": 0.85, "top_issues": ["산지 전용", "생태계", "경관"], "supplement_pct": 52.0},
            "수변": {"risk_level": "high", "issue_probability": 0.78, "top_issues": ["수질", "수생태계", "경관"], "supplement_pct": 48.0},
            "농지": {"risk_level": "major", "issue_probability": 0.65, "top_issues": ["농지 전용", "교통", "경관"], "supplement_pct": 40.0},
            "도시": {"risk_level": "major", "issue_probability": 0.60, "top_issues": ["소음", "교통", "경관"], "supplement_pct": 35.0},
            "해안": {"risk_level": "high", "issue_probability": 0.75, "top_issues": ["해양 생태", "경관", "수질"], "supplement_pct": 45.0},
            "평지": {"risk_level": "review", "issue_probability": 0.50, "top_issues": ["교통", "경관", "대기질"], "supplement_pct": 30.0},
        },
        "폐기물": {
            "산지": {"risk_level": "high", "issue_probability": 0.88, "top_issues": ["토양 오염", "수질", "생태계"], "supplement_pct": 60.0},
            "수변": {"risk_level": "critical", "issue_probability": 0.93, "top_issues": ["수질 오염", "침출수", "수생태계"], "supplement_pct": 68.0},
            "농지": {"risk_level": "high", "issue_probability": 0.82, "top_issues": ["토양 오염", "대기질", "주민 건강"], "supplement_pct": 55.0},
            "도시": {"risk_level": "critical", "issue_probability": 0.90, "top_issues": ["대기질", "악취", "주민 건강"], "supplement_pct": 65.0},
            "해안": {"risk_level": "high", "issue_probability": 0.80, "top_issues": ["해양 오염", "수질", "악취"], "supplement_pct": 52.0},
            "평지": {"risk_level": "major", "issue_probability": 0.72, "top_issues": ["대기질", "토양", "지하수"], "supplement_pct": 48.0},
        },
        "군사": {
            "산지": {"risk_level": "high", "issue_probability": 0.85, "top_issues": ["산지 훼손", "생태계", "소음"], "supplement_pct": 55.0},
            "수변": {"risk_level": "high", "issue_probability": 0.80, "top_issues": ["수질", "소음", "생태계"], "supplement_pct": 50.0},
            "농지": {"risk_level": "major", "issue_probability": 0.68, "top_issues": ["농지 전용", "소음", "주민 영향"], "supplement_pct": 42.0},
            "도시": {"risk_level": "high", "issue_probability": 0.82, "top_issues": ["소음·진동", "주민 영향", "교통"], "supplement_pct": 52.0},
            "해안": {"risk_level": "high", "issue_probability": 0.78, "top_issues": ["해양 생태", "소음", "경관"], "supplement_pct": 48.0},
            "평지": {"risk_level": "major", "issue_probability": 0.60, "top_issues": ["소음", "생태계", "토양"], "supplement_pct": 38.0},
        },
        "토석": {
            "산지": {"risk_level": "critical", "issue_probability": 0.93, "top_issues": ["지형 훼손", "산지 전용", "소음·발파"], "supplement_pct": 58.0},
            "수변": {"risk_level": "high", "issue_probability": 0.85, "top_issues": ["수질 오염", "토사유출", "생태계"], "supplement_pct": 52.0},
            "농지": {"risk_level": "major", "issue_probability": 0.65, "top_issues": ["비산먼지", "소음", "토양"], "supplement_pct": 40.0},
            "도시": {"risk_level": "high", "issue_probability": 0.80, "top_issues": ["소음·진동", "비산먼지", "교통"], "supplement_pct": 50.0},
            "해안": {"risk_level": "high", "issue_probability": 0.82, "top_issues": ["해양 환경", "경관", "토사유출"], "supplement_pct": 50.0},
            "평지": {"risk_level": "major", "issue_probability": 0.58, "top_issues": ["비산먼지", "소음", "경관"], "supplement_pct": 35.0},
        },
        "간척": {
            "산지": {"risk_level": "review", "issue_probability": 0.40, "top_issues": ["경관", "수질", "생태계"], "supplement_pct": 30.0},
            "수변": {"risk_level": "high", "issue_probability": 0.88, "top_issues": ["수질", "수생태계", "갯벌"], "supplement_pct": 62.0},
            "농지": {"risk_level": "major", "issue_probability": 0.65, "top_issues": ["농지 영향", "수질", "경관"], "supplement_pct": 45.0},
            "도시": {"risk_level": "major", "issue_probability": 0.60, "top_issues": ["교통", "경관", "소음"], "supplement_pct": 40.0},
            "해안": {"risk_level": "critical", "issue_probability": 0.95, "top_issues": ["갯벌 훼손", "해양 생태", "어업 피해"], "supplement_pct": 70.0},
            "평지": {"risk_level": "major", "issue_probability": 0.55, "top_issues": ["수질", "경관", "교통"], "supplement_pct": 38.0},
        },
        "물류": {
            "산지": {"risk_level": "high", "issue_probability": 0.78, "top_issues": ["산지 전용", "생태계", "경관"], "supplement_pct": 48.0},
            "수변": {"risk_level": "high", "issue_probability": 0.75, "top_issues": ["수질", "교통", "비점오염"], "supplement_pct": 45.0},
            "농지": {"risk_level": "major", "issue_probability": 0.70, "top_issues": ["농지 전용", "교통", "대기질"], "supplement_pct": 42.0},
            "도시": {"risk_level": "major", "issue_probability": 0.65, "top_issues": ["교통", "소음", "대기질"], "supplement_pct": 35.0},
            "해안": {"risk_level": "major", "issue_probability": 0.60, "top_issues": ["해양 환경", "교통", "경관"], "supplement_pct": 38.0},
            "평지": {"risk_level": "review", "issue_probability": 0.50, "top_issues": ["교통", "대기질", "농지 전용"], "supplement_pct": 30.0},
        },
    }

    for k, v in new_entries.items():
        rm["matrix"][k] = v

    path.write_text(json.dumps(rm, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"risk_matrix.json: {len(rm['matrix'])} types")


def fix_remediation_patterns():
    """Add 8 missing type entries to remediation_patterns.json."""
    path = ANALYSIS_DIR / "remediation_patterns.json"
    rp = json.loads(path.read_text(encoding="utf-8"))

    new_entries = {
        "댐": [
            {"issue": "수질 영향", "common_remediation": ["선택적 방류 시스템", "부영양화 방지대책", "수질 모니터링 계획"], "frequency": 0.88},
            {"issue": "수생태계 영향", "common_remediation": ["어도(魚道) 설치", "수생태계 모니터링", "인공산란장 조성"], "frequency": 0.81},
            {"issue": "수몰지역 이주", "common_remediation": ["이주대책 수립", "생활대책 마련", "문화재 이전 계획"], "frequency": 0.73},
            {"issue": "지형·지질 변화", "common_remediation": ["사면안정 대책", "절성토량 최소화", "지질조사 실시"], "frequency": 0.65},
            {"issue": "생태계 훼손", "common_remediation": ["대체서식지 조성", "4계절 생태조사", "녹화 복원 계획"], "frequency": 0.54},
        ],
        "채석": [
            {"issue": "지형·지질 훼손", "common_remediation": ["단계적 복원 계획", "절개면 녹화", "사후 복원 기금 적립"], "frequency": 0.88},
            {"issue": "소음·진동 (발파)", "common_remediation": ["발파 시간 제한", "제어발파 적용", "방음벽 설치"], "frequency": 0.80},
            {"issue": "비산먼지", "common_remediation": ["살수시설 설치", "분진포집장치", "운반차량 세륜시설"], "frequency": 0.75},
            {"issue": "수질 오염", "common_remediation": ["침사지 설치", "탁수처리시설", "수질 모니터링"], "frequency": 0.60},
            {"issue": "산지 전용", "common_remediation": ["대체산림 조성", "최소 면적 개발", "단계별 복원"], "frequency": 0.55},
        ],
        "체육": [
            {"issue": "산지 전용·녹지 훼손", "common_remediation": ["대체산림 조성", "녹지율 30% 이상 확보", "자연지형 최대 활용"], "frequency": 0.78},
            {"issue": "경관 변화", "common_remediation": ["경관심의 실시", "건축물 높이 제한", "차폐식재 계획"], "frequency": 0.72},
            {"issue": "수질 오염", "common_remediation": ["비점오염 저감시설", "오수처리시설", "수질 모니터링"], "frequency": 0.63},
            {"issue": "생태계 훼손", "common_remediation": ["생태통로 설치", "4계절 생태조사", "비오톱 조성"], "frequency": 0.57},
            {"issue": "소음·진동", "common_remediation": ["방음벽 설치", "공사시간 제한", "저소음 장비 사용"], "frequency": 0.50},
        ],
        "폐기물": [
            {"issue": "대기질 악화", "common_remediation": ["최적방지시설 설치", "굴뚝 높이 최적화", "TMS 설치·운영"], "frequency": 0.88},
            {"issue": "수질 오염 (침출수)", "common_remediation": ["침출수 처리시설", "차수막 이중 설치", "지하수 모니터링"], "frequency": 0.82},
            {"issue": "토양·지하수 오염", "common_remediation": ["토양오염 모니터링", "지하수 관측정 설치", "차수시설 강화"], "frequency": 0.74},
            {"issue": "주민 건강 영향", "common_remediation": ["건강영향평가 실시", "악취저감시설", "주민 모니터링 참여"], "frequency": 0.66},
            {"issue": "악취 확산", "common_remediation": ["밀폐형 시설 설계", "탈취설비 설치", "악취 모니터링"], "frequency": 0.55},
        ],
        "군사": [
            {"issue": "소음·진동 (사격·폭발)", "common_remediation": ["방음림 조성", "사격장 방음벽", "훈련시간 제한"], "frequency": 0.84},
            {"issue": "산지·녹지 훼손", "common_remediation": ["대체산림 조성", "녹지축 보전", "단계별 복원"], "frequency": 0.75},
            {"issue": "생태계 영향", "common_remediation": ["생태통로 설치", "야생동물 조사", "서식지 보전 계획"], "frequency": 0.67},
            {"issue": "토양 오염", "common_remediation": ["오염토양 정화", "유류 저장시설 안전관리", "토양 모니터링"], "frequency": 0.51},
            {"issue": "수질 오염", "common_remediation": ["오수처리시설", "비점오염 저감", "수질 모니터링"], "frequency": 0.58},
        ],
        "토석": [
            {"issue": "지형·지질 훼손", "common_remediation": ["단계적 복원 계획", "절개면 안정화", "복원 이행보증금"], "frequency": 0.88},
            {"issue": "비산먼지", "common_remediation": ["살수시설 운영", "분진억제 덮개", "세륜시설 설치"], "frequency": 0.80},
            {"issue": "소음·진동 (발파)", "common_remediation": ["제어발파 적용", "발파시간 제한", "진동 모니터링"], "frequency": 0.72},
            {"issue": "수질 오염", "common_remediation": ["침사지 설치", "탁수처리", "수질 모니터링"], "frequency": 0.65},
            {"issue": "경관 훼손", "common_remediation": ["차폐식재", "단계적 녹화", "복원 계획"], "frequency": 0.50},
        ],
        "간척": [
            {"issue": "해양 생태계 영향", "common_remediation": ["대체서식지 조성", "해양생태 모니터링", "갯벌 복원 계획"], "frequency": 0.90},
            {"issue": "수질 오염", "common_remediation": ["수질정화시설", "담·해수 순환시스템", "수질 모니터링"], "frequency": 0.80},
            {"issue": "철새 서식지", "common_remediation": ["대체습지 조성", "조류 모니터링", "서식지 보전 구역 지정"], "frequency": 0.60},
            {"issue": "어업 피해", "common_remediation": ["어업손실보상", "인공어초 설치", "어장 이전 지원"], "frequency": 0.52},
            {"issue": "조류 변화", "common_remediation": ["수치모델링 실시", "배수갑문 운영 최적화", "해안 침식 방지"], "frequency": 0.70},
        ],
        "물류": [
            {"issue": "교통량 증가", "common_remediation": ["교통영향분석", "진출입 도로 개선", "교통신호 최적화"], "frequency": 0.85},
            {"issue": "대기질 악화", "common_remediation": ["비산먼지 저감", "살수차 운영", "공사차량 세륜"], "frequency": 0.76},
            {"issue": "소음·진동", "common_remediation": ["방음벽 설치", "공사시간 제한", "저소음 장비"], "frequency": 0.68},
            {"issue": "수질 오염", "common_remediation": ["비점오염 저감시설", "오수처리시설", "우수저류시설"], "frequency": 0.56},
            {"issue": "농지 전용", "common_remediation": ["대체농지 조성", "농지보전부담금", "표토 보전"], "frequency": 0.48},
        ],
    }

    for k, v in new_entries.items():
        rp["by_type"][k] = v

    path.write_text(json.dumps(rp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"remediation_patterns.json: {len(rp['by_type'])} types")


def fix_case_names():
    """Add project_name to 27 cases (CASE-058 to CASE-084) that lack it."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    name_map = {
        "CASE-058": "한강하류 광역상수도 사업",
        "CASE-059": "금산무주권 광역상수도 사업",
        "CASE-060": "남한강 광역상수도 사업",
        "CASE-061": "충청권 광역급행철도 건설사업",
        "CASE-062": "부산형 급행철도 건설사업",
        "CASE-063": "여주~원주 철도건설 사업",
        "CASE-064": "금오산 케이블카 설치사업",
        "CASE-065": "강릉 청솔공원 장사시설 확충사업",
        "CASE-066": "신안 분재·유리공예공원 조성사업",
        "CASE-067": "경기도소방학교 북부캠퍼스 조성사업",
        "CASE-068": "곤지암스포츠밸리 교육시설 전환사업",
        "CASE-069": "순천향대 천안 제2병원 건립사업",
        "CASE-070": "무안 물류시설단지 조성사업",
        "CASE-071": "남이천 물류단지 조성사업",
        "CASE-072": "김해 상동스마트물류단지 조성사업",
        "CASE-073": "영암 삼호간척지 용도변경사업",
        "CASE-074": "제3차 연안정비기본계획 변경사업",
        "CASE-075": "제3차 연안정비기본계획 수립사업",
        "CASE-076": "경남권 공공어린이재활병원 건립사업",
        "CASE-077": "강북 어린이병원·공공청사 복합개발사업",
        "CASE-078": "수성의료지구 개발사업",
        "CASE-079": "용문 군사시설 이전지구 조성사업",
        "CASE-080": "국방군사시설 훈련장 사업",
        "CASE-081": "창녕군 생활폐기물처리시설 설치사업",
        "CASE-082": "광주 자원회수시설(소각) 설치사업",
        "CASE-083": "삼척오십천권역 하천기본계획 사업",
        "CASE-084": "울산 남구 소하천정비종합계획 사업",
    }

    updated = 0
    for case in cases:
        cid = case.get("case_id", "")
        if cid in name_map and not case.get("project_name"):
            case["project_name"] = name_map[cid]
            updated += 1

    CASES_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cases.json: {updated} cases updated with project_name")


if __name__ == "__main__":
    fix_patterns_by_type()
    fix_risk_matrix()
    fix_remediation_patterns()
    fix_case_names()
    print("All data fixes complete!")
