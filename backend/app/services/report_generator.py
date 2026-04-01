"""
PDF Report Generator for the EIA Pre-screening Tool.

Generates three types of PDF reports:
  1. Brief (1-page summary)
  2. Full Report (5-10 pages)
  3. Checklist PDF

All methods return raw PDF bytes via io.BytesIO.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Korean CID font registration (module-level, runs once on import)
# ---------------------------------------------------------------------------
_FONT_NAME = "HYGothic-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(_FONT_NAME))

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
_DISCLAIMER = "본 보고서는 AI 기반 사전검토 결과이며, 법적 효력이 없습니다."

_SEVERITY_ORDER = {"높음": 0, "중간": 1, "낮음": 2}
_SEVERITY_COLORS = {
    "높음": colors.HexColor("#E74C3C"),
    "중간": colors.HexColor("#F39C12"),
    "낮음": colors.HexColor("#27AE60"),
}

PAGE_WIDTH, PAGE_HEIGHT = A4

# A4 professional margins: top/bottom 2.5cm, left/right 2cm
_MARGIN_TOP = 2.5 * cm
_MARGIN_BOTTOM = 2.5 * cm
_MARGIN_LEFT = 2 * cm
_MARGIN_RIGHT = 2 * cm

# Severity mapping for the new risk card format (Critical/Major/Review/Info)
_CARD_SEVERITY_ORDER = {"critical": 0, "major": 1, "review": 2, "info": 3}
_CARD_SEVERITY_COLORS = {
    "critical": colors.HexColor("#E74C3C"),
    "major": colors.HexColor("#F39C12"),
    "review": colors.HexColor("#F1C40F"),
    "info": colors.HexColor("#3498DB"),
}
_CARD_SEVERITY_LABELS = {
    "critical": "심각 (Critical)",
    "major": "주요 (Major)",
    "review": "검토 (Review)",
    "info": "참고 (Info)",
}


# ---------------------------------------------------------------------------
# Reusable styles
# ---------------------------------------------------------------------------
def _build_styles() -> dict[str, ParagraphStyle]:
    """Return a dictionary of ParagraphStyles that use the Korean CID font."""
    base = getSampleStyleSheet()

    common = dict(fontName=_FONT_NAME)

    styles: dict[str, ParagraphStyle] = {}

    styles["title"] = ParagraphStyle(
        "KTitle",
        parent=base["Title"],
        fontSize=22,
        leading=28,
        spaceAfter=12 * mm,
        alignment=1,  # centre
        **common,
    )
    styles["subtitle"] = ParagraphStyle(
        "KSubtitle",
        parent=base["Title"],
        fontSize=14,
        leading=18,
        spaceAfter=6 * mm,
        alignment=1,
        **common,
    )
    styles["heading"] = ParagraphStyle(
        "KHeading",
        parent=base["Heading1"],
        fontSize=14,
        leading=18,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor("#2C3E50"),
        **common,
    )
    styles["subheading"] = ParagraphStyle(
        "KSubheading",
        parent=base["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=colors.HexColor("#34495E"),
        **common,
    )
    styles["body"] = ParagraphStyle(
        "KBody",
        parent=base["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=2 * mm,
        **common,
    )
    styles["body_small"] = ParagraphStyle(
        "KBodySmall",
        parent=base["BodyText"],
        fontSize=8,
        leading=11,
        spaceAfter=1 * mm,
        **common,
    )
    styles["disclaimer"] = ParagraphStyle(
        "KDisclaimer",
        parent=base["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.grey,
        alignment=1,
        **common,
    )
    styles["checklist_title"] = ParagraphStyle(
        "KChecklistTitle",
        parent=base["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=colors.HexColor("#2C3E50"),
        **common,
    )
    styles["cover_title"] = ParagraphStyle(
        "KCoverTitle",
        parent=base["Title"],
        fontSize=28,
        leading=36,
        spaceAfter=10 * mm,
        alignment=1,
        **common,
    )
    styles["cover_info"] = ParagraphStyle(
        "KCoverInfo",
        parent=base["BodyText"],
        fontSize=12,
        leading=16,
        alignment=1,
        spaceAfter=3 * mm,
        **common,
    )

    return styles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe(value: Any, default: str = "-") -> str:
    """Return *value* as a string, falling back to *default* when falsy/None."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _severity_sort_key(card: dict) -> int:
    return _SEVERITY_ORDER.get(_safe(card.get("severity"), "낮음"), 99)


def _make_table_style(
    header_bg: colors.Color = colors.HexColor("#2C3E50"),
    header_fg: colors.Color = colors.white,
) -> TableStyle:
    """Return a common TableStyle with header colouring."""
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_fg),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]
    )


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------
def _header_footer_factory(project_name: str = ""):
    """Return a callback that draws header & footer on every page (except p1)."""
    def _draw(canvas: Any, doc: Any) -> None:
        page_num = doc.page
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 8)

        if page_num > 1:
            # Header: left = tool name + project, right = page number
            header_y = PAGE_HEIGHT - 1.5 * cm
            canvas.setFillColor(colors.HexColor("#7F8C8D"))
            header_left = f"EIA Pre-Screen — {project_name}" if project_name else "EIA Pre-Screen"
            canvas.drawString(_MARGIN_LEFT, header_y, header_left)
            canvas.drawRightString(
                PAGE_WIDTH - _MARGIN_RIGHT, header_y, f"p.{page_num}",
            )
            # Header line
            canvas.setStrokeColor(colors.HexColor("#BDC3C7"))
            canvas.setLineWidth(0.5)
            canvas.line(
                _MARGIN_LEFT, header_y - 3,
                PAGE_WIDTH - _MARGIN_RIGHT, header_y - 3,
            )

        # Footer: center disclaimer + page
        footer_y = 1.2 * cm
        canvas.setFillColor(colors.HexColor("#95A5A6"))
        canvas.drawCentredString(
            PAGE_WIDTH / 2, footer_y,
            f"{_DISCLAIMER}  |  {page_num}",
        )
        canvas.restoreState()
    return _draw


class ReportGenerator:
    """Generates PDF reports for EIA pre-screening results."""

    def __init__(self) -> None:
        self._styles = _build_styles()

    # ------------------------------------------------------------------ #
    #  1. Brief (1-page summary)                                          #
    # ------------------------------------------------------------------ #
    def generate_brief(
        self,
        project_info: dict | None,
        risk_cards: list[dict] | None,
        regulations: list[dict] | None,
        interpretation: str | None,
    ) -> bytes:
        """Return a 1-page brief PDF as bytes."""
        project_info = project_info or {}
        risk_cards = risk_cards or []
        regulations = regulations or []
        interpretation = interpretation or ""

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        S = self._styles
        story: list[Any] = []

        # Title
        story.append(Paragraph("환경영향평가 사전검토 브리프", S["title"]))
        story.append(Spacer(1, 2 * mm))

        # -- 사업 개요 --
        story.append(Paragraph("사업 개요", S["heading"]))
        overview_data = [
            ["항목", "내용"],
            ["사업명", _safe(project_info.get("project_name"))],
            ["사업유형", _safe(project_info.get("project_type"))],
            ["사업규모", _safe(project_info.get("project_scale"))],
            ["소재지", _safe(project_info.get("address"))],
        ]
        tbl = Table(overview_data, colWidths=[4 * cm, 12 * cm])
        tbl.setStyle(_make_table_style())
        story.append(tbl)
        story.append(Spacer(1, 3 * mm))

        # -- 리스크 요약 --
        story.append(Paragraph("리스크 요약", S["heading"]))
        counts = {"높음": 0, "중간": 0, "낮음": 0}
        for card in risk_cards:
            sev = _safe(card.get("severity"), "낮음")
            if sev in counts:
                counts[sev] += 1
        risk_summary_data = [
            ["심각도", "건수"],
            ["높음", str(counts["높음"])],
            ["중간", str(counts["중간"])],
            ["낮음", str(counts["낮음"])],
        ]
        tbl = Table(risk_summary_data, colWidths=[4 * cm, 4 * cm])
        ts = _make_table_style()
        # Colour-code severity rows
        for row_idx, sev in enumerate(["높음", "중간", "낮음"], start=1):
            ts.add("TEXTCOLOR", (0, row_idx), (0, row_idx), _SEVERITY_COLORS[sev])
        tbl.setStyle(ts)
        story.append(tbl)
        story.append(Spacer(1, 3 * mm))

        # -- 주요 규제 (top 3) --
        story.append(Paragraph("주요 규제", S["heading"]))
        top_regs = regulations[:3]
        if top_regs:
            reg_data = [["규제명", "근거법령", "허가필요"]]
            for reg in top_regs:
                permit = "예" if reg.get("permit_required") else "아니오"
                reg_data.append([
                    _safe(reg.get("regulation_name")),
                    _safe(reg.get("legal_basis")),
                    permit,
                ])
            tbl = Table(reg_data, colWidths=[5.5 * cm, 7 * cm, 3.5 * cm])
            tbl.setStyle(_make_table_style())
            story.append(tbl)
        else:
            story.append(Paragraph("해당 규제 없음", S["body"]))
        story.append(Spacer(1, 3 * mm))

        # -- 결론 --
        story.append(Paragraph("결론", S["heading"]))
        snippet = interpretation[:500] + ("..." if len(interpretation) > 500 else "")
        story.append(Paragraph(_safe(snippet, "AI 해석 결과가 없습니다."), S["body"]))
        story.append(Spacer(1, 4 * mm))

        # Disclaimer
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))

        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------ #
    #  2. Full Report (5-10 pages)                                        #
    # ------------------------------------------------------------------ #
    def generate_full_report(
        self,
        project_info: dict | None,
        risk_cards: list[dict] | None,
        regulations: list[dict] | None,
        cases: list[dict] | None,
        interpretation: str | None,
        checklist: dict | None,
    ) -> bytes:
        """Return a full-length report PDF as bytes."""
        project_info = project_info or {}
        risk_cards = risk_cards or []
        regulations = regulations or []
        cases = cases or []
        interpretation = interpretation or ""
        checklist = checklist or {}

        project_name = _safe(project_info.get("project_name"), "")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=_MARGIN_TOP,
            bottomMargin=_MARGIN_BOTTOM,
            leftMargin=_MARGIN_LEFT,
            rightMargin=_MARGIN_RIGHT,
        )

        S = self._styles
        story: list[Any] = []
        on_page = _header_footer_factory(project_name)

        # ---- 1. 표지 (Cover Page) ----
        story.append(Spacer(1, 5 * cm))
        story.append(Paragraph("EIA Pre-Screen", S["subtitle"]))
        story.append(Paragraph("환경현황 요약 보고서", S["cover_title"]))
        story.append(Spacer(1, 1.5 * cm))
        story.append(
            Paragraph(
                f"사업명: {_safe(project_info.get('project_name'))}",
                S["cover_info"],
            )
        )
        story.append(
            Paragraph(
                f"사업유형: {_safe(project_info.get('project_type'))}",
                S["cover_info"],
            )
        )
        story.append(
            Paragraph(
                f"소재지: {_safe(project_info.get('address'))}",
                S["cover_info"],
            )
        )
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"작성일: {_today_str()}", S["cover_info"]))
        story.append(Paragraph("생성 도구: EIA Pre-Screen v1.0", S["cover_info"]))
        story.append(Spacer(1, 2 * cm))
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))
        story.append(PageBreak())

        # ---- 2. 목차 ----
        story.append(Paragraph("목차", S["title"]))
        story.append(Spacer(1, 4 * mm))
        toc_items = [
            ("1.", "사업 개요"),
            ("2.", "리스크 분석 결과"),
            ("  2.1", "리스크 요약표"),
            ("  2.2", "리스크 상세"),
            ("3.", "규제 매칭 결과"),
            ("4.", "유사사례"),
            ("5.", "AI 종합 해석"),
            ("6.", "현장조사 체크리스트"),
        ]
        for num, label in toc_items:
            indent = 10 * mm if num.startswith("  ") else 0
            toc_style = ParagraphStyle(
                f"TOC_{num.strip()}",
                parent=S["body"],
                leftIndent=indent,
                fontName=_FONT_NAME,
            )
            story.append(Paragraph(f"{num.strip()}  {label}", toc_style))
        story.append(PageBreak())

        # ---- 3. 사업 개요 ----
        story.append(Paragraph("1. 사업 개요", S["heading"]))
        content_width = PAGE_WIDTH - _MARGIN_LEFT - _MARGIN_RIGHT
        overview_data = [
            ["항목", "내용"],
            ["사업명", _safe(project_info.get("project_name"))],
            ["사업유형", _safe(project_info.get("project_type"))],
            ["사업규모", _safe(project_info.get("project_scale"))],
            ["소재지", _safe(project_info.get("address"))],
            ["좌표", f"({_safe(project_info.get('lng'))}, {_safe(project_info.get('lat'))})"],
        ]
        tbl = Table(overview_data, colWidths=[4 * cm, content_width - 4 * cm])
        tbl.setStyle(_make_table_style())
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

        # ---- 4. 리스크 분석 결과 ----
        story.append(Paragraph("2. 리스크 분석 결과", S["heading"]))

        # 2.1 Risk summary table (severity color-coded)
        story.append(Paragraph("2.1 리스크 요약", S["subheading"]))
        sev_counts: dict[str, int] = {"critical": 0, "major": 0, "review": 0, "info": 0}
        for card in risk_cards:
            sev = card.get("severity", "info")
            if sev in sev_counts:
                sev_counts[sev] += 1

        summary_data = [["심각도", "건수", "비율"]]
        total_risks = max(len(risk_cards), 1)
        for sev_key in ("critical", "major", "review", "info"):
            cnt = sev_counts[sev_key]
            pct = f"{cnt / total_risks * 100:.0f}%"
            summary_data.append([
                _CARD_SEVERITY_LABELS.get(sev_key, sev_key),
                str(cnt),
                pct,
            ])
        summary_data.append(["합계", str(len(risk_cards)), "100%"])

        tbl = Table(summary_data, colWidths=[6 * cm, 4 * cm, 4 * cm])
        ts = _make_table_style()
        # Color-code severity rows
        for row_idx, sev_key in enumerate(("critical", "major", "review", "info"), start=1):
            c = _CARD_SEVERITY_COLORS.get(sev_key, colors.black)
            ts.add("TEXTCOLOR", (0, row_idx), (0, row_idx), c)
        ts.add("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECF0F1"))
        tbl.setStyle(ts)
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

        # 2.2 Risk details
        story.append(Paragraph("2.2 리스크 상세", S["subheading"]))
        sorted_cards = sorted(
            risk_cards,
            key=lambda c: _CARD_SEVERITY_ORDER.get(c.get("severity", "info"), 99),
        )

        if sorted_cards:
            risk_table_data = [["규칙 ID", "심각도", "제목", "법적 근거"]]
            severity_row_cmds: list[tuple] = []
            for row_idx, card in enumerate(sorted_cards, start=1):
                sev = card.get("severity", "info")
                risk_table_data.append([
                    _safe(card.get("rule_id")),
                    _CARD_SEVERITY_LABELS.get(sev, sev),
                    Paragraph(_safe(card.get("title")), S["body_small"]),
                    Paragraph(_safe(card.get("legal_basis")), S["body_small"]),
                ])
                c = _CARD_SEVERITY_COLORS.get(sev, colors.black)
                severity_row_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), c))

            tbl = Table(
                risk_table_data,
                colWidths=[2.2 * cm, 3.5 * cm, 5.5 * cm, 5 * cm],
                repeatRows=1,
            )
            ts2 = _make_table_style()
            for cmd in severity_row_cmds:
                ts2.add(*cmd)
            tbl.setStyle(ts2)
            story.append(tbl)
        else:
            story.append(Paragraph("분석된 리스크가 없습니다.", S["body"]))

        story.append(PageBreak())

        # ---- 5. 규제 매칭 결과 ----
        story.append(Paragraph("3. 규제 매칭 결과", S["heading"]))

        if regulations:
            reg_table_data = [["규제명", "근거법령", "인허가 필요", "관련기관"]]
            for reg in regulations:
                permit = "필요" if reg.get("permit_required") else "-"
                reg_table_data.append([
                    Paragraph(_safe(reg.get("regulation_name")), S["body_small"]),
                    Paragraph(_safe(reg.get("legal_basis")), S["body_small"]),
                    permit,
                    Paragraph(_safe(reg.get("related_authority")), S["body_small"]),
                ])
            col_widths = [4 * cm, 5 * cm, 2.5 * cm, 4.7 * cm]
            tbl = Table(reg_table_data, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(_make_table_style())
            story.append(tbl)
        else:
            story.append(Paragraph("매칭된 규제가 없습니다.", S["body"]))

        story.append(PageBreak())

        # ---- 6. 유사사례 ----
        story.append(Paragraph("4. 유사사례", S["heading"]))

        if cases:
            for case in cases:
                story.append(
                    Paragraph(
                        f"사례 ID: {_safe(case.get('case_id'))}",
                        S["subheading"],
                    )
                )
                case_data = [
                    ["항목", "내용"],
                    ["사업유형", _safe(case.get("project_type"))],
                    ["요약", _safe(case.get("summary"))],
                    ["협의결과", _safe(case.get("consultation_result"))],
                ]
                tbl = Table(case_data, colWidths=[3.5 * cm, 12.5 * cm])
                tbl.setStyle(_make_table_style())
                story.append(tbl)
                story.append(Spacer(1, 3 * mm))
        else:
            story.append(Paragraph("유사사례가 없습니다.", S["body"]))

        story.append(PageBreak())

        # ---- 7. AI 종합 해석 ----
        story.append(Paragraph("5. AI 종합 해석", S["heading"]))
        story.append(
            Paragraph(
                "<i>* 아래 내용은 AI가 생성한 해석이며 참고용입니다.</i>",
                S["body_small"],
            )
        )
        story.append(Spacer(1, 2 * mm))

        if interpretation:
            # Split into paragraphs for readability
            for para_text in interpretation.split("\n"):
                stripped = para_text.strip()
                if stripped:
                    story.append(Paragraph(stripped, S["body"]))
        else:
            story.append(Paragraph("AI 해석 결과가 없습니다.", S["body"]))

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))
        story.append(PageBreak())

        # ---- 8. 현장조사 체크리스트 ----
        story.append(Paragraph("6. 현장조사 체크리스트", S["heading"]))
        self._render_checklist_sections(story, checklist, S)

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        return buf.getvalue()

    # ------------------------------------------------------------------ #
    #  3. Checklist PDF                                                    #
    # ------------------------------------------------------------------ #
    def generate_checklist_pdf(
        self,
        checklist: dict | None,
    ) -> bytes:
        """Return a checklist-only PDF as bytes."""
        checklist = checklist or {}

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        S = self._styles
        story: list[Any] = []

        story.append(Paragraph("현장조사 체크리스트", S["title"]))
        story.append(Paragraph(f"작성일: {_today_str()}", S["body"]))
        story.append(Spacer(1, 4 * mm))

        self._render_checklist_sections(story, checklist, S)

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))

        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------ #
    #  4. Comparison Report (up to 3 sites)                                #
    # ------------------------------------------------------------------ #
    _COMPARE_SEVERITY_COLORS = {
        "critical": colors.HexColor("#E74C3C"),
        "major": colors.HexColor("#F39C12"),
        "review": colors.HexColor("#F1C40F"),
        "info": colors.HexColor("#3498DB"),
    }

    def generate_comparison_report(
        self,
        sites: list[dict] | None,
        risk_matrix: list[dict] | None,
        recommendation: str | None,
    ) -> bytes:
        """Return a PDF comparing up to 3 screening sites as bytes."""
        sites = sites or []
        risk_matrix = risk_matrix or []
        recommendation = recommendation or ""

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        S = self._styles
        story: list[Any] = []

        # Title
        story.append(Paragraph("부지 비교 보고서", S["title"]))
        story.append(Paragraph(f"작성일: {_today_str()}", S["body"]))
        story.append(Spacer(1, 4 * mm))

        # -- 1. 부지별 요약 --
        story.append(Paragraph("1. 부지별 요약", S["heading"]))

        site_names = [_safe(s.get("project_name"), f"부지 {i+1}") for i, s in enumerate(sites)]
        header_row = ["항목"] + site_names
        summary_rows = [
            ["사업유형"] + [_safe(s.get("project_type")) for s in sites],
            ["소재지"] + [_safe(s.get("address")) for s in sites],
            ["총 리스크"] + [_safe(s.get("total_risks")) for s in sites],
            ["Critical"] + [_safe(s.get("critical_count")) for s in sites],
            ["Major"] + [_safe(s.get("major_count")) for s in sites],
            ["Review"] + [_safe(s.get("review_count")) for s in sites],
            ["Info"] + [_safe(s.get("info_count")) for s in sites],
            ["총 규제"] + [_safe(s.get("total_regulations")) for s in sites],
            ["인허가 필요"] + [_safe(s.get("permit_required_count")) for s in sites],
        ]
        summary_data = [header_row] + summary_rows

        num_cols = len(header_row)
        available = PAGE_WIDTH - 4 * cm  # left + right margins
        first_col = 3 * cm
        remaining = (available - first_col) / max(num_cols - 1, 1)
        col_widths = [first_col] + [remaining] * (num_cols - 1)

        tbl = Table(summary_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(_make_table_style())
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

        # -- 2. 리스크 비교 매트릭스 --
        story.append(Paragraph("2. 리스크 비교 매트릭스", S["heading"]))

        if risk_matrix:
            screening_ids = [s.get("screening_id") for s in sites]
            matrix_header = ["규칙ID", "리스크명"] + site_names
            matrix_data = [matrix_header]

            severity_cell_cmds: list[tuple] = []

            for row_idx, rm in enumerate(risk_matrix, start=1):
                row = [
                    _safe(rm.get("rule_id")),
                    Paragraph(_safe(rm.get("title")), S["body_small"]),
                ]
                severity_by_site = rm.get("severity_by_site") or {}
                for col_offset, sid in enumerate(screening_ids):
                    sev = severity_by_site.get(sid) if sid is not None else None
                    cell_text = _safe(sev)
                    row.append(cell_text)
                    if sev and sev.lower() in self._COMPARE_SEVERITY_COLORS:
                        bg = self._COMPARE_SEVERITY_COLORS[sev.lower()]
                        col_idx = 2 + col_offset
                        severity_cell_cmds.append(
                            ("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), bg)
                        )
                        severity_cell_cmds.append(
                            ("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), colors.white)
                        )
                matrix_data.append(row)

            m_num_cols = len(matrix_header)
            m_first = 2 * cm
            m_second = 4 * cm
            m_remaining = (available - m_first - m_second) / max(m_num_cols - 2, 1)
            m_col_widths = [m_first, m_second] + [m_remaining] * (m_num_cols - 2)

            tbl = Table(matrix_data, colWidths=m_col_widths, repeatRows=1)
            ts = _make_table_style()
            for cmd in severity_cell_cmds:
                ts.add(*cmd)
            tbl.setStyle(ts)
            story.append(tbl)
        else:
            story.append(Paragraph("리스크 매트릭스 데이터가 없습니다.", S["body"]))

        story.append(Spacer(1, 6 * mm))

        # -- 3. 종합 추천 --
        story.append(Paragraph("3. 종합 추천", S["heading"]))
        if recommendation:
            for para_text in recommendation.split("\n"):
                stripped = para_text.strip()
                if stripped:
                    story.append(Paragraph(stripped, S["body"]))
        else:
            story.append(Paragraph("추천 내용이 없습니다.", S["body"]))

        story.append(Spacer(1, 6 * mm))

        # Disclaimer
        story.append(Paragraph(_DISCLAIMER, S["disclaimer"]))

        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _render_checklist_sections(
        story: list[Any],
        checklist: dict,
        S: dict[str, ParagraphStyle],
    ) -> None:
        """Append checklist sections with checkbox squares to *story*."""
        sections = checklist.get("sections") or []

        if not sections:
            story.append(Paragraph("체크리스트 항목이 없습니다.", S["body"]))
            return

        _CHECKBOX = "\u2610"  # Unicode ballot box (☐)

        priority_colors = {
            "높음": _SEVERITY_COLORS["높음"],
            "중간": _SEVERITY_COLORS["중간"],
            "낮음": _SEVERITY_COLORS["낮음"],
        }

        for section in sections:
            section_name = _safe(section.get("section_name"), "섹션")
            story.append(Paragraph(section_name, S["checklist_title"]))

            items = section.get("items") or []
            if not items:
                story.append(Paragraph("  항목 없음", S["body"]))
                continue

            table_data = [["", "항목", "설명", "우선순위"]]
            for item in items:
                priority = _safe(item.get("priority"), "낮음")
                p_color = priority_colors.get(priority, colors.black)
                priority_style = ParagraphStyle(
                    "PriorityCell",
                    parent=S["body_small"],
                    textColor=p_color,
                    fontName=_FONT_NAME,
                )
                table_data.append([
                    _CHECKBOX,
                    Paragraph(_safe(item.get("title")), S["body_small"]),
                    Paragraph(_safe(item.get("description")), S["body_small"]),
                    Paragraph(priority, priority_style),
                ])

            col_widths = [1 * cm, 4 * cm, 8.5 * cm, 2.5 * cm]
            tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
            ts = _make_table_style()
            ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
            ts.add("FONTSIZE", (0, 1), (0, -1), 14)  # larger checkbox
            tbl.setStyle(ts)
            story.append(tbl)
            story.append(Spacer(1, 4 * mm))
