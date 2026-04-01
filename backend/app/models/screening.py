import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

import enum


class ProjectType(str, enum.Enum):
    """환경영향평가법 시행령 별표3 기준 17개 사업유형."""
    URBAN_DEV = "urban_dev"
    INDUSTRIAL = "industrial"
    ENERGY = "energy"
    PORT = "port"
    ROAD = "road"
    WATER_RESOURCE = "water_resource"
    RAILWAY = "railway"
    AIRPORT = "airport"
    RIVER = "river"
    TOURISM = "tourism"
    MOUNTAIN = "mountain"
    SPORTS = "sports"
    WASTE = "waste"
    MILITARY = "military"
    MINING = "mining"
    RECLAMATION = "reclamation"
    ETC = "etc"
    # 이전 호환
    HOUSING = "housing"
    POWER_PLANT = "power_plant"
    FACTORY = "factory"
    OTHER = "other"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    REVIEW = "review"
    INFO = "info"


class ScreeningRequest(TimestampMixin, Base):
    """사업 입력 정보 — 위치, 사업유형, 규모 등."""

    __tablename__ = "screening_requests"

    # 사업 기본 정보
    project_name: Mapped[str] = mapped_column(String(200))
    project_type: Mapped[ProjectType] = mapped_column(
        Enum(ProjectType, name="project_type"),
    )
    project_scale: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 공간 정보 (PostGIS)
    location: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    boundary: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=True,
    )

    # 메타
    status: Mapped[str] = mapped_column(String(20), default="pending")
    llm_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 관계
    risk_cards: Mapped[list["RiskCard"]] = relationship(
        back_populates="screening_request",
        cascade="all, delete-orphan",
    )
    regulation_matches: Mapped[list["RegulationMatch"]] = relationship(
        back_populates="screening_request",
        cascade="all, delete-orphan",
    )


class RiskCard(TimestampMixin, Base):
    """리스크 카드 결과 — 룰 엔진이 생성하는 개별 리스크 항목."""

    __tablename__ = "risk_cards"

    screening_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("screening_requests.id", ondelete="CASCADE"),
    )

    rule_id: Mapped[str] = mapped_column(String(50))
    rule_version: Mapped[str] = mapped_column(String(10), default="v1")
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"))
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legal_basis: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    human_review_required: Mapped[bool] = mapped_column(default=False)
    trigger_dataset: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_snapshot_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # 관계
    screening_request: Mapped["ScreeningRequest"] = relationship(
        back_populates="risk_cards",
    )


class RegulationMatch(TimestampMixin, Base):
    """규제 매칭 결과 — 해당 부지에 적용되는 법적 규제/인허가."""

    __tablename__ = "regulation_matches"

    screening_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("screening_requests.id", ondelete="CASCADE"),
    )

    regulation_name: Mapped[str] = mapped_column(String(200))
    regulation_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_basis: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    restriction_level: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
    )
    permit_required: Mapped[bool] = mapped_column(default=False)
    related_authority: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # 관계
    screening_request: Mapped["ScreeningRequest"] = relationship(
        back_populates="regulation_matches",
    )
