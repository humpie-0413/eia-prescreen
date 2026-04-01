/**
 * E2E 테스트용 API 스텁 데이터.
 *
 * 6개+ 외부 서비스/백엔드 API 카테고리:
 *   1. Screening (스크리닝 CRUD)
 *   2. Evaluation (리스크 평가 — 생태자연도, 토지이용, 수질, 대기질 데이터 포함)
 *   3. Cases (유사사례 라이브러리)
 *   4. Draft (Draft Copilot — 6장 18섹션)
 *   5. DataStatus (데이터 가용성 — AirKorea, V-world, Water 커넥터 상태)
 *   6. Patterns (과거 패턴 분석 — 9,973건)
 *   7. Review (검토의견 예측 + 품질 체크)
 *   8. Compare (부지 비교)
 *   9. LLM/DeepSeek (리스크 해석문)
 *  10. RAG (원문 검색)
 */

// ── 1. Screening ──

export const SCREENING_RESPONSE = {
  id: "test-001",
  project_name: "양평 국도 우회도로 건설사업",
  project_type: "road",
  status: "created",
};

export const SCREENINGS_LIST = [
  {
    id: "test-001",
    project_name: "양평 국도 우회도로",
    project_type: "road",
    status: "evaluated",
    critical_count: 1,
    major_count: 2,
    review_count: 1,
    info_count: 0,
  },
  {
    id: "test-002",
    project_name: "세종 주거단지",
    project_type: "housing",
    status: "evaluated",
    critical_count: 0,
    major_count: 3,
    review_count: 2,
    info_count: 1,
  },
  {
    id: "test-003",
    project_name: "보령 발전소",
    project_type: "power_plant",
    status: "evaluated",
    critical_count: 2,
    major_count: 1,
    review_count: 0,
    info_count: 2,
  },
];

/** Individual screening detail (GET /api/screening/:id) */
export const SCREENING_DETAIL_RESPONSE = {
  id: "test-001",
  project_name: "양평 국도 우회도로 건설사업",
  project_type: "road",
  project_scale: "L=4.2km",
  address: "경기도 양평군",
  lng: 127.49,
  lat: 37.49,
  status: "evaluated",
  llm_interpretation: null,
  created_at: "2026-03-29T00:00:00",
  updated_at: "2026-03-29T00:00:00",
  risk_cards: [],
  regulation_matches: [],
};

// ── 2. Evaluation (생태자연도 + 토지이용 + 대기질 + 수질 데이터 반영) ──

export const EVALUATION_RESPONSE = {
  screening_id: "test-001",
  status: "evaluated",
  summary: {
    total_risks: 4,
    critical_count: 1,
    major_count: 2,
    review_count: 1,
    info_count: 0,
    total_regulations: 1,
    permit_required_count: 1,
  },
  risk_cards: [
    {
      rule_id: "ECO-001",
      rule_version: "1.0",
      title: "생태자연도 1등급 권역 인접",
      severity: "major",
      rationale: "사업지 반경 1km 내 생태자연도 1등급 권역 존재",
      evidence: "생태자연도 서비스 조회 결과",
      next_action: "생태계 정밀조사 시행",
      legal_basis: "자연환경보전법 제34조",
      confidence: 0.85,
      human_review_required: true,
      trigger_dataset: "ecology_grade",
      source_snapshot_date: "2025-12-01",
    },
    {
      rule_id: "WTR-002",
      rule_version: "1.0",
      title: "상수원보호구역 인접",
      severity: "critical",
      rationale: "사업지 반경 500m 내 상수원보호구역",
      evidence: "토지이용규제정보 조회",
      next_action: "수질영향 정밀평가",
      legal_basis: "수도법 제7조",
      confidence: 0.92,
      human_review_required: true,
      trigger_dataset: "water_protection",
      source_snapshot_date: "2025-12-01",
    },
    {
      rule_id: "AIR-001",
      rule_version: "1.0",
      title: "대기질 관리지역",
      severity: "review",
      rationale: "대기관리권역 내 위치",
      evidence: "에어코리아 데이터",
      next_action: "대기질 모니터링 계획 수립",
      legal_basis: "대기환경보전법 제18조의2",
      confidence: 0.78,
      human_review_required: false,
      trigger_dataset: "air_quality",
      source_snapshot_date: "2025-11-15",
    },
    {
      rule_id: "NOS-001",
      rule_version: "1.0",
      title: "소음 민감지역",
      severity: "major",
      rationale: "인근 주거지역 500m 이내",
      evidence: "소음측정망 데이터",
      next_action: "방음대책 수립",
      legal_basis: "소음진동관리법 제21조",
      confidence: 0.8,
      human_review_required: false,
      trigger_dataset: "noise",
      source_snapshot_date: "2025-11-20",
    },
  ],
  regulation_matches: [
    {
      regulation_name: "자연환경보전법",
      regulation_code: "R-001",
      legal_basis: "제34조 생태자연도",
      description: "생태자연도 1등급 지역 영향 검토",
      restriction_level: "high",
      permit_required: true,
      related_authority: "환경부",
      evidence: "생태자연도 1등급 권역 인접",
    },
  ],
  priority_items: ["생태계 정밀조사", "수질영향평가", "방음대책"],
  checklist_generated: true,
  interpretation: null,
};

export const CHECKLIST_RESPONSE = {
  screening_id: "test-001",
  total_items: 2,
  generated_at: "2025-12-01T00:00:00",
  sections: [
    {
      section_name: "현장조사 준비",
      priority: "필수",
      items: [
        {
          id: 1,
          category: "생태",
          title: "생태 현황 확인",
          description: "사업지 주변 생태현황 확인",
          legal_basis: "자연환경보전법 제34조",
          priority: "필수",
          checked: false,
          related_rule_id: "ECO-001",
        },
        {
          id: 2,
          category: "수질",
          title: "수질 측정 지점 선정",
          description: "상류/하류 수질측정 지점 사전 선정",
          legal_basis: "수질환경보전법",
          priority: "권고",
          checked: false,
          related_rule_id: "WTR-002",
        },
      ],
    },
  ],
};

// ── 3. Cases ──

export const CASES_RESPONSE = {
  total: 3,
  cases: [
    {
      case_id: "CASE-001",
      project_name: "○○ 국도건설사업",
      project_type: "road",
      region: "경기도",
      year: 2023,
      summary: "국도 우회도로 건설사업의 환경영향평가",
      key_issues: ["생태계", "수질", "소음"],
      similarity_score: 0.89,
      review_result: "조건부 동의",
      source_report_id: "RPT-001",
    },
    {
      case_id: "CASE-002",
      project_name: "△△ 도로확장사업",
      project_type: "road",
      region: "강원도",
      year: 2022,
      summary: "기존 도로 확장에 따른 환경영향평가",
      key_issues: ["대기질", "소음", "경관"],
      similarity_score: 0.82,
      review_result: "동의",
      source_report_id: "RPT-002",
    },
    {
      case_id: "CASE-003",
      project_name: "□□ 우회도로사업",
      project_type: "road",
      region: "충청남도",
      year: 2021,
      summary: "우회도로 신설에 따른 환경영향평가",
      key_issues: ["생태계", "토양", "수질"],
      similarity_score: 0.76,
      review_result: "조건부 동의",
      source_report_id: "RPT-003",
    },
  ],
  ai_interpretation:
    "도로건설 사업은 생태계와 수질 영향이 핵심 평가 항목입니다.",
};

// ── 4. Draft Copilot ──

export const DRAFT_RESPONSE = {
  screening_id: "test-001",
  project_info: { project_name: "양평 국도 우회도로 건설사업" },
  total_sections: 18,
  disclaimer:
    "이 초안은 AI가 생성한 참고 자료이며, 법적 효력이 없습니다. 전문가 검토가 필수적입니다.",
  sections: [
    {
      section_id: "1.1",
      chapter: "제1장 사업의 개요",
      title: "사업의 목적",
      badge: "자동 생성",
      content:
        "## 사업의 목적\n\n본 사업은 양평군 일대의 교통 혼잡 해소를 위한 국도 우회도로 건설사업입니다.\n\n- 총 연장: L=4.2km\n- 차로수: 4차로 (W=20m)",
    },
    {
      section_id: "1.2",
      chapter: "제1장 사업의 개요",
      title: "사업의 내용",
      badge: "자동 생성",
      content: "## 사업의 내용\n\n도로 신설 구간의 상세 계획입니다.",
    },
    {
      section_id: "3.1",
      chapter: "제3장 환경현황",
      title: "자연환경",
      badge: "현장조사 필요",
      content:
        "## 자연환경 현황\n\n> [현장조사 필요] 사업지 일대의 정밀 생태조사가 필요합니다.\n\n현장조사를 통해 보완이 필요한 항목입니다.",
    },
    {
      section_id: "4.1",
      chapter: "제4장 환경영향 예측",
      title: "대기질 영향",
      badge: "전문가 검토 필요",
      content: "## 대기질 영향 예측\n\n전문 모델링이 필요한 항목입니다.",
    },
  ],
};

// ── 5. DataStatus (AirKorea, V-world, Water 커넥터 상태 포함) ──

export const DATA_STATUS_RESPONSE = {
  screening_id: "test-001",
  total: 9,
  available: 7,
  coverage_pct: 78,
  freshness_summary: { live: 3, cached: 4, unknown: 2 },
  connectors: [
    {
      name: "land_use_regulation",
      description: "토지이용규제정보",
      tier: "A",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "live",
        fetched_at: "2026-03-29T10:00:00",
        snapshot_at: "2026-03-29T10:00:00",
      },
    },
    {
      name: "vworld_wfs",
      description: "V-world 공간정보",
      tier: "A",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "live",
        fetched_at: "2026-03-29T10:00:00",
        snapshot_at: "2026-03-29T10:00:00",
      },
    },
    {
      name: "air_korea",
      description: "에어코리아 대기오염",
      tier: "B",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "cached",
        fetched_at: "2026-03-28T12:00:00",
        snapshot_at: "2026-03-28T12:00:00",
      },
    },
    {
      name: "water_quality",
      description: "수질 DB",
      tier: "B",
      status: "unstable",
      has_data: true,
      freshness: {
        freshness: "cached",
        fetched_at: "2026-03-27T08:00:00",
        snapshot_at: "2026-03-27T08:00:00",
      },
    },
    {
      name: "ecology_grade",
      description: "생태자연도",
      tier: "B",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "cached",
        fetched_at: "2026-03-28T15:00:00",
        snapshot_at: "2026-03-28T15:00:00",
      },
    },
    {
      name: "weather_asos",
      description: "기상청 ASOS",
      tier: "B",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "live",
        fetched_at: "2026-03-29T09:00:00",
        snapshot_at: "2026-03-29T09:00:00",
      },
    },
    {
      name: "traffic",
      description: "교통량 통계",
      tier: "B",
      status: "stable",
      has_data: true,
      freshness: {
        freshness: "cached",
        fetched_at: "2026-03-25T10:00:00",
        snapshot_at: "2026-03-25T10:00:00",
      },
    },
    {
      name: "soil_monitoring",
      description: "토양측정망",
      tier: "B",
      status: "unavailable",
      has_data: false,
      freshness: { freshness: "unknown", fetched_at: null, snapshot_at: null },
    },
    {
      name: "noise_monitoring",
      description: "소음측정망",
      tier: "B",
      status: "unavailable",
      has_data: false,
      freshness: { freshness: "unknown", fetched_at: null, snapshot_at: null },
    },
  ],
};

// ── 6. Patterns (과거 패턴 분석) ──

export const PREDICTION_RESPONSE = {
  project_type: "road",
  korean_type: "도로",
  total_in_type: 42,
  predicted_issues: [
    {
      issue: "생태계 훼손",
      probability_pct: 85,
      past_count: 36,
      total_in_type: 42,
      description: "도로 건설로 인한 생태계 단절 우려",
    },
  ],
  consultation_prediction: {
    "조건부협의": 62,
    "협의": 28,
    "재검토": 10,
  },
  avg_review_months: 8.5,
  supplement_required_pct: 45,
  risk_assessment: null,
  remediation_suggestions: [
    {
      issue: "생태계 훼손",
      common_remediation: ["생태통로 설치", "대체 서식지 조성"],
      frequency: 0.85,
    },
  ],
};

// ── 7. Review (검토의견 예측 + 품질 체크) ──

export const REVIEW_PREDICTION_RESPONSE = {
  project_type: "road",
  korean_type: "도로",
  total_past_cases: 42,
  predicted_comments: [
    {
      category: "생태",
      comment: "야생동물 이동 경로에 대한 추가 조사가 필요합니다.",
      probability_pct: 82,
      past_count: 34,
      total_past_cases: 42,
      risk_matched: true,
      severity: "high" as const,
    },
  ],
  avg_review_months: 8.5,
  supplement_required_pct: 45,
  disclaimer: "AI 분석 참고용",
};

export const QUALITY_CHECK_RESPONSE = {
  overall_status: "warning",
  score: 72,
  total_checks: 2,
  passed: 1,
  warnings: 1,
  failed: 0,
  checks: [
    {
      check_id: "QC-001",
      category: "데이터 완전성",
      title: "필수 환경 데이터 확보",
      status: "pass",
      detail: "9개 중 7개 커넥터 정상",
    },
    {
      check_id: "QC-002",
      category: "규제 검토",
      title: "핵심 규제 검토 완료",
      status: "warning",
      detail: "상수원보호구역 추가 검토 필요",
    },
  ],
  summary: {
    "데이터 완전성": "pass",
    "규제 검토": "warning",
  },
};

// ── 8. Compare ──

export const COMPARE_RESPONSE = {
  sites: SCREENINGS_LIST.map((s) => ({
    screening_id: s.id,
    project_name: s.project_name,
    project_type: s.project_type,
    address: "",
    total_risks:
      s.critical_count + s.major_count + s.review_count + s.info_count,
    critical_count: s.critical_count,
    major_count: s.major_count,
    review_count: s.review_count,
    info_count: s.info_count,
    total_regulations: 3,
    permit_required_count: 1,
  })),
  risk_matrix: [
    {
      rule_id: "ECO-001",
      title: "생태자연도 1등급 인접",
      severity_by_site: {
        "test-001": "major",
        "test-002": "review",
        "test-003": "critical",
      },
    },
  ],
  recommendation: "양평 부지가 상대적으로 리스크가 낮습니다.",
};

// ── 9. LLM / DeepSeek (리스크 해석문) ──

export const INTERPRETATION_RESPONSE = {
  screening_id: "test-001",
  interpretation:
    "본 사업지는 생태자연도 1등급 권역과 상수원보호구역에 인접하여 환경 리스크가 높습니다.",
  disclaimer: "AI 생성 참고용",
};

// ── 10. RAG (원문 검색) ──

export const RAG_RESPONSE = {
  answer:
    "도로 사업의 비산먼지 저감방안으로는 포장, 살수, 방진망 설치 등이 있습니다.",
  sources: [
    {
      report_id: "EIASS_2024_001",
      project_name: "경주 도로 사업",
      project_type: "road",
      year: "2024",
      chapter: "3",
      section: "3.1",
      page_range: "45-47",
      similarity: 0.94,
      excerpt: "시공 단계에서는 포장을 통한 저감...",
    },
  ],
  total_indexed: 6103,
  generated_at: "2026-03-29T12:00:00",
  disclaimer:
    "이 답변은 실제 환경영향평가서 원문을 참조한 AI 생성 결과이며, 참고용입니다.",
};

// ── Empty / Error 응답 ──

export const EMPTY_EVALUATION = {
  screening_id: "test-001",
  status: "evaluated",
  summary: {
    total_risks: 0,
    critical_count: 0,
    major_count: 0,
    review_count: 0,
    info_count: 0,
    total_regulations: 0,
    permit_required_count: 0,
  },
  risk_cards: [],
  regulation_matches: [],
  priority_items: [],
  checklist_generated: false,
  interpretation: null,
};

export const EMPTY_CASES = {
  total: 0,
  cases: [],
  ai_interpretation: null,
};

export const EMPTY_DRAFT = {
  screening_id: "test-001",
  project_info: { project_name: "" },
  total_sections: 0,
  disclaimer: "데이터가 부족하여 초안을 생성할 수 없습니다.",
  sections: [],
};

export const EMPTY_DATA_STATUS = {
  screening_id: "test-001",
  total: 0,
  available: 0,
  coverage_pct: 0,
  freshness_summary: { live: 0, cached: 0, unknown: 0 },
  connectors: [],
};

export const EMPTY_PREDICTION = {
  project_type: "road",
  korean_type: "도로",
  total_in_type: 0,
  predicted_issues: [],
  consultation_prediction: {},
  avg_review_months: 0,
  supplement_required_pct: 0,
  risk_assessment: null,
  remediation_suggestions: [],
};

export const EMPTY_REVIEW_PREDICTION = {
  project_type: "road",
  korean_type: "도로",
  total_past_cases: 0,
  predicted_comments: [],
  avg_review_months: 0,
  supplement_required_pct: 0,
  disclaimer: "AI 분석 참고용",
};

export const EMPTY_QUALITY_CHECK = {
  overall_status: "pass",
  score: 0,
  total_checks: 0,
  passed: 0,
  warnings: 0,
  failed: 0,
  checks: [],
  summary: {},
};

export const EMPTY_COMPARE = {
  sites: [],
  risk_matrix: [],
  recommendation: "",
};

export const MOCK_PDF_BODY = Buffer.from("%PDF-1.4 mock");
