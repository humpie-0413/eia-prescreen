"""
EIA 사례 태그 자동 생성/보강 스크립트

DeepSeek V3 (via OpenRouter)를 사용하여 기존 사례(cases.json)의 태그를 재생성하고 보강합니다.
각 사례의 summary를 LLM에 전달하여 관련 태그를 추천받고,
기존 태그와 병합하여 cases.json을 갱신합니다.

사용법:
    python scripts/generate_case_tags.py

환경 변수:
    OPENROUTER_API_KEY: OpenRouter API 키 (.env 파일에서 로드)
    LLM_MODEL: 사용할 모델 (기본값: deepseek/deepseek-chat)
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 프로젝트 루트 기준 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = PROJECT_ROOT / "data" / "cases" / "cases.json"
ENV_FILE = PROJECT_ROOT / ".env"

# 태그 생성 프롬프트 템플릿
TAG_PROMPT_TEMPLATE = """당신은 한국 환경영향평가(EIA) 전문가입니다.
아래 환경영향평가 사례 정보를 분석하여 관련 태그를 5~8개 추천해 주세요.

사례 정보:
- 사업 유형: {project_type}
- 입지 유형: {location_type}
- 지역: {region}
- 주요 쟁점: {key_issues}
- 보완 요구사항: {remediation_required}
- 주민 우려사항: {public_concerns}
- 협의 결과: {consultation_result}
- 요약: {summary}

태그 작성 규칙:
1. 한국어로 작성
2. 각 태그는 2~4글자의 핵심 키워드
3. 사업 유형, 입지 특성, 환경 이슈, 지역 특성을 포함
4. JSON 배열 형식으로만 응답 (예: ["태그1", "태그2", "태그3"])
5. 다른 설명이나 텍스트 없이 JSON 배열만 반환"""


def load_env():
    """환경 변수를 로드하고 API 키를 반환합니다."""
    load_dotenv(ENV_FILE)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("오류: OPENROUTER_API_KEY가 설정되지 않았습니다.")
        print(f".env 파일 경로: {ENV_FILE}")
        print("OPENROUTER_API_KEY=your_api_key_here 형식으로 .env 파일에 추가해 주세요.")
        sys.exit(1)
    return api_key


def load_cases() -> list[dict]:
    """cases.json 파일에서 사례 데이터를 로드합니다."""
    if not CASES_FILE.exists():
        print(f"오류: 사례 파일을 찾을 수 없습니다: {CASES_FILE}")
        sys.exit(1)
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)
    print(f"{len(cases)}개의 사례를 로드했습니다.")
    return cases


def save_cases(cases: list[dict]):
    """사례 데이터를 cases.json 파일에 저장합니다."""
    with open(CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"{len(cases)}개의 사례를 저장했습니다: {CASES_FILE}")


def generate_tags_for_case(client: OpenAI, model: str, case: dict) -> list[str]:
    """DeepSeek을 사용하여 단일 사례에 대한 태그를 생성합니다."""
    prompt = TAG_PROMPT_TEMPLATE.format(
        project_type=case.get("project_type", ""),
        location_type=case.get("location_type", ""),
        region=case.get("region", ""),
        key_issues=", ".join(case.get("key_issues", [])),
        remediation_required=", ".join(case.get("remediation_required", [])),
        public_concerns=", ".join(case.get("public_concerns", [])),
        consultation_result=case.get("consultation_result", ""),
        summary=case.get("summary", ""),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.choices[0].message.content.strip()

    # JSON 배열 파싱 (코드 블록 마커 제거)
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        tags = json.loads(response_text)
        if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
            return tags
    except json.JSONDecodeError:
        print(f"  경고: JSON 파싱 실패 - {response_text[:100]}")

    return []


def merge_tags(existing_tags: list[str], new_tags: list[str]) -> list[str]:
    """기존 태그와 새 태그를 병합하여 중복을 제거합니다."""
    seen = set()
    merged = []
    for tag in existing_tags + new_tags:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)
    return merged


def main():
    print("=" * 60)
    print("EIA 사례 태그 자동 생성/보강 스크립트")
    print("=" * 60)

    # 환경 변수 로드
    api_key = load_env()
    model = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
    print(f"OpenRouter API 키 로드 완료 (모델: {model})")

    # OpenRouter 클라이언트 초기화
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    print("OpenRouter 클라이언트 초기화 완료")

    # 사례 데이터 로드
    cases = load_cases()

    # 각 사례에 대해 태그 생성
    updated_count = 0
    for i, case in enumerate(cases):
        case_id = case.get("case_id", f"UNKNOWN-{i}")
        print(f"\n[{i + 1}/{len(cases)}] {case_id} 처리 중...")

        try:
            new_tags = generate_tags_for_case(client, model, case)
            if new_tags:
                existing_tags = case.get("tags", [])
                merged_tags = merge_tags(existing_tags, new_tags)
                case["tags"] = merged_tags
                updated_count += 1
                print(f"  기존 태그: {existing_tags}")
                print(f"  새 태그:   {new_tags}")
                print(f"  병합 결과: {merged_tags}")
            else:
                print("  태그 생성 결과 없음 - 기존 태그 유지")
        except Exception as e:
            print(f"  오류 발생: {e} - 기존 태그 유지")

        # API 요청 간 대기 (rate limit 방지)
        if i < len(cases) - 1:
            time.sleep(1)

    # 결과 저장
    print(f"\n{'=' * 60}")
    print(f"처리 완료: {updated_count}/{len(cases)}개 사례 태그 갱신")
    save_cases(cases)
    print("완료!")


if __name__ == "__main__":
    main()
