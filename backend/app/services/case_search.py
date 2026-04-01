"""유사 사례 검색 서비스.

과거 환경영향평가 사례 데이터를 로드하고, 프로젝트 유형·위치유형·키워드·태그
기반 검색 및 Jaccard 유사도 기반 유사 사례 추천 기능을 제공한다.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# English code → Korean label mapping for project type search
_PROJECT_TYPE_MAP: dict[str, str] = {
    "urban_dev": "도시개발",
    "industrial": "산업단지",
    "energy": "발전소",
    "port": "항만",
    "road": "도로",
    "water_resource": "상하수도",
    "railway": "철도",
    "airport": "공항",
    "river": "하천",
    "tourism": "관광단지",
    "mountain": "산지",
    "sports": "체육시설",
    "waste": "폐기물",
    "military": "군사시설",
    "mining": "광물",
    "reclamation": "매립/간척",
    "etc": "기타",
    "housing": "주거단지",
    "power_plant": "발전소",
    "factory": "산업단지",
    "other": "기타",
}

# 유사사례 검색용 유형별 별칭 — 매칭률이 낮은 유형에 대해 키워드를 확장하여 검색
_TYPE_ALIASES: dict[str, list[str] | None] = {
    "urban_dev": ["주거단지", "도시계획", "택지", "도시개발"],
    "mountain": ["채석", "토석", "산지", "산지개발"],
    "sports": ["관광단지", "공원", "체육", "체육시설"],
    "mining": ["채석", "토석", "광산", "광물"],
    "other": None,  # None이면 전체 검색 (필터 없음)
}

# Reverse mapping: Korean → English (for response normalization)
_PROJECT_TYPE_REVERSE: dict[str, str] = {v: k for k, v in _PROJECT_TYPE_MAP.items()}

CASES_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "cases"
    / "cases.json"
)


# ── 응답 모델 ──


class CaseResult(BaseModel):
    """단일 사례 검색 결과."""

    case_id: str
    project_name: Optional[str] = None
    year: Optional[str] = None
    project_type: str
    location_type: str
    region: str
    key_issues: list[str] = Field(default_factory=list)
    remediation_required: list[str] = Field(default_factory=list)
    public_concerns: list[str] = Field(default_factory=list)
    consultation_result: Optional[str] = None
    source_document: Optional[str] = None
    summary: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    lessons_learned: Optional[str] = None
    similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Jaccard 유사도 점수 (find_similar 호출 시에만 포함)",
    )


class CaseSearchResponse(BaseModel):
    """사례 검색 응답 (목록 + 전체 건수)."""

    total: int = Field(..., description="필터 조건에 매칭된 전체 사례 수")
    results: list[CaseResult] = Field(default_factory=list)


# ── 서비스 ──


class CaseSearchService:
    """JSON 파일 기반 과거 환경영향평가 사례 검색 서비스."""

    def __init__(self, cases_path: Path = CASES_PATH) -> None:
        self._cases_path = cases_path
        self._cases: list[dict] = []
        self._load_cases()

    def _load_cases(self) -> None:
        """JSON 파일에서 사례 데이터를 로드한다."""
        if not self._cases_path.exists():
            logger.warning("Cases file not found: %s", self._cases_path)
            return

        try:
            with open(self._cases_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error("Cases file is not a JSON array: %s", self._cases_path)
                return

            self._cases = data
            logger.info("Loaded %d cases from %s", len(self._cases), self._cases_path.name)
        except Exception:
            logger.exception("Failed to load cases from %s", self._cases_path)

    @property
    def cases(self) -> list[dict]:
        return self._cases

    # ── 검색 ──

    def search(
        self,
        project_type: Optional[str] = None,
        location_type: Optional[str] = None,
        keyword: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 10,
    ) -> CaseSearchResponse:
        """
        사례를 필터 조건으로 검색한다.

        Args:
            project_type: 사업유형 정확 일치
            location_type: 입지유형 정확 일치
            keyword: summary, key_issues, tags 부분 문자열 매칭 (대소문자 무시)
            tags: 교집합 기반 태그 매칭 (하나 이상 겹치면 포함)
            limit: 최대 반환 건수 (기본 10)

        Returns:
            CaseSearchResponse (매칭 결과 + 전체 건수)
        """
        filtered = self._cases

        if project_type is not None:
            # Support both English codes and Korean labels
            korean_type = _PROJECT_TYPE_MAP.get(project_type, project_type)
            # Use type aliases for broader matching on low-match types
            aliases = _TYPE_ALIASES.get(project_type)
            if aliases is None and project_type in _TYPE_ALIASES:
                # None means search all (no project_type filter)
                pass
            else:
                match_labels = {project_type, korean_type}
                if aliases:
                    match_labels.update(aliases)
                filtered = [
                    c for c in filtered
                    if c.get("project_type") in match_labels
                    or any(alias in (c.get("project_type") or "") for alias in match_labels)
                ]

        if location_type is not None:
            filtered = [c for c in filtered if c.get("location_type") == location_type]

        if keyword is not None:
            keyword_lower = keyword.lower()
            filtered = [c for c in filtered if self._matches_keyword(c, keyword_lower)]

        if tags is not None and len(tags) > 0:
            tag_set = set(tags)
            filtered = [
                c for c in filtered
                if tag_set & set(c.get("tags", []))
            ]

        total = len(filtered)
        results = [
            self._to_case_result(c) for c in filtered[:limit]
        ]

        return CaseSearchResponse(total=total, results=results)

    # ── 유사 사례 추천 ──

    def find_similar(
        self,
        risk_card_tags: list[str],
        project_type: Optional[str] = None,
        location_type: Optional[str] = None,
        limit: int = 5,
    ) -> CaseSearchResponse:
        """
        리스크 카드 태그를 기반으로 유사 사례를 추천한다.

        다중 요인 유사도 점수 (0.0 ~ 1.0):
          - 사업유형 일치: 0.30 기본 점수
          - 입지유형 일치: 0.20 추가
          - 태그/키워드 오버랩: 최대 0.50 (부분 문자열 매칭 포함)

        Args:
            risk_card_tags: 리스크 카드에서 추출한 태그 목록
            project_type: 사업유형 필터 (선택)
            location_type: 입지유형 필터 (선택)
            limit: 최대 반환 건수 (기본 5)

        Returns:
            CaseSearchResponse (유사도 내림차순 정렬)
        """
        candidates = self._cases
        type_matched = False

        if project_type is not None:
            korean_type = _PROJECT_TYPE_MAP.get(project_type, project_type)
            aliases = _TYPE_ALIASES.get(project_type)
            if aliases is None and project_type in _TYPE_ALIASES:
                # "other" type: search all, no filter
                type_matched = False
            else:
                match_labels = {project_type, korean_type}
                if aliases:
                    match_labels.update(aliases)
                candidates = [
                    c for c in candidates
                    if c.get("project_type") in match_labels
                    or any(alias in (c.get("project_type") or "") for alias in match_labels)
                ]
                type_matched = True

        scored: list[tuple[float, dict]] = []
        for case in candidates:
            score = self._compute_similarity(
                risk_card_tags=risk_card_tags,
                case=case,
                type_matched=type_matched,
                query_location_type=location_type,
            )
            scored.append((score, case))

        # 유사도 내림차순 정렬
        scored.sort(key=lambda pair: pair[0], reverse=True)

        total = len(scored)
        results = [
            self._to_case_result(case, similarity_score=round(score, 4))
            for score, case in scored[:limit]
        ]

        return CaseSearchResponse(total=total, results=results)

    # ── 내부 유틸 ──

    @staticmethod
    def _compute_similarity(
        risk_card_tags: list[str],
        case: dict,
        type_matched: bool = False,
        query_location_type: Optional[str] = None,
    ) -> float:
        """다중 요인 유사도 점수를 계산한다.

        점수 구성:
          - 사업유형 일치 (type_matched): 0.30
          - 입지유형 일치: 0.20
          - 태그/키워드 오버랩: 최대 0.50

        태그 오버랩은 정확 일치 + 부분 문자열 매칭을 결합하여
        risk card 제목(긴 문장)과 case 태그(짧은 키워드) 간의
        불일치 문제를 해결한다.
        """
        score = 0.0

        # 1) 사업유형 일치: 0.30 기본 점수
        if type_matched:
            score += 0.30

        # 2) 입지유형 일치: 0.20
        if query_location_type:
            case_location = case.get("location_type", "")
            if case_location and (
                query_location_type == case_location
                or query_location_type in case_location
                or case_location in query_location_type
            ):
                score += 0.20

        # 3) 태그/키워드 오버랩: 최대 0.50
        if risk_card_tags:
            case_tags = set(case.get("tags", []))
            case_issues = set(case.get("key_issues", []))
            case_all_text = case_tags | case_issues

            # Build query keywords: split long tags into individual words too
            query_keywords: set[str] = set()
            for tag in risk_card_tags:
                query_keywords.add(tag)
                # Also extract individual Korean/alphanumeric tokens (2+ chars)
                for token in re.split(r'[\s,·()（）\[\]]+', tag):
                    token = token.strip()
                    if len(token) >= 2:
                        query_keywords.add(token)

            if query_keywords and case_all_text:
                # Count matches: exact match or substring containment
                match_count = 0
                for q_kw in query_keywords:
                    q_lower = q_kw.lower()
                    for c_text in case_all_text:
                        c_lower = c_text.lower()
                        if q_lower == c_lower or q_lower in c_lower or c_lower in q_lower:
                            match_count += 1
                            break  # Count each query keyword at most once

                # Normalize: ratio of matched query keywords
                overlap_ratio = match_count / len(query_keywords)
                score += 0.50 * min(overlap_ratio, 1.0)

        return min(score, 1.0)

    @staticmethod
    def _matches_keyword(case: dict, keyword_lower: str) -> bool:
        """summary, key_issues, tags 필드에서 키워드 부분 문자열 매칭."""
        summary = (case.get("summary") or "").lower()
        if keyword_lower in summary:
            return True

        for issue in case.get("key_issues", []):
            if keyword_lower in issue.lower():
                return True

        for tag in case.get("tags", []):
            if keyword_lower in tag.lower():
                return True

        return False

    @staticmethod
    def _jaccard(set_a: set, set_b: set) -> float:
        """두 집합의 Jaccard 유사도를 계산한다."""
        if not set_a and not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    @staticmethod
    def _to_case_result(
        case: dict,
        similarity_score: Optional[float] = None,
    ) -> CaseResult:
        """딕셔너리를 CaseResult 모델로 변환한다."""
        # project_name / year: 명시된 필드 우선, 없으면 source_document에서 추출
        project_name = case.get("project_name")
        year = case.get("year")

        if (not project_name or not year) and case.get("source_document"):
            m = re.match(
                r"(?:.+?\s)?(.+?)\s*환경영향평가서\s*\((\d{4})\)",
                case["source_document"],
            )
            if m:
                if not project_name:
                    project_name = m.group(1).strip()
                if not year:
                    year = m.group(2)

        return CaseResult(
            case_id=case.get("case_id", ""),
            project_name=project_name,
            year=year,
            project_type=case.get("project_type", ""),
            location_type=case.get("location_type", ""),
            region=case.get("region", ""),
            key_issues=case.get("key_issues", []),
            remediation_required=case.get("remediation_required", []),
            public_concerns=case.get("public_concerns", []),
            consultation_result=case.get("consultation_result"),
            source_document=case.get("source_document"),
            summary=case.get("summary"),
            tags=case.get("tags", []),
            lessons_learned=case.get("lessons_learned"),
            similarity_score=similarity_score,
        )
