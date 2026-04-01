"""Service to match project spatial data against regulation reference data."""

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RegulationMatchResult(BaseModel):
    regulation_name: str
    regulation_code: str | None = None
    legal_basis: str
    description: str | None = None
    restriction_level: str | None = None
    permit_required: bool = False
    related_authority: str | None = None
    evidence: dict | None = None


class RegulationMatcher:
    """Matches a project's spatial data against regulation reference data
    loaded from JSON files in data/regulations/."""

    def __init__(self, regulations_dir: Path | None = None) -> None:
        if regulations_dir is None:
            regulations_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "regulations"
            )
        self._regulations_dir = regulations_dir

        # Pre-load all reference data once at init time.
        self._zone_codes: list[dict] = self._load_json("zone_code_mapping.json")
        self._conservation_types: list[dict] = self._load_json(
            "conservation_type_mapping.json"
        )
        self._eia_thresholds: list[dict] = self._load_json("eia_thresholds.json")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_json(self, filename: str) -> list[dict]:
        """Load and return a JSON array from *filename* inside the regulations dir."""
        filepath = self._regulations_dir / filename
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Loaded %d entries from %s", len(data), filepath)
            return data
        except FileNotFoundError:
            logger.warning("Regulation file not found: %s", filepath)
            return []
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", filepath, exc)
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(
        self, project_info: dict, spatial_data: dict
    ) -> list[RegulationMatchResult]:
        """Match regulations based on project info and spatial data.

        Parameters
        ----------
        project_info:
            Dict with at least ``project_type`` (e.g. ``"power_plant"``).
        spatial_data:
            Dict keyed by connector name (``land_use``, ``ecology``,
            ``water_quality``, ``cultural``, etc.) with sub-dicts of
            spatial attributes.

        Returns
        -------
        list[RegulationMatchResult]
            All matched regulation entries.
        """
        results: list[RegulationMatchResult] = []
        results.extend(self._match_zone_regulations(spatial_data))
        results.extend(self._match_conservation_regulations(spatial_data))
        results.extend(self._match_eia_thresholds(project_info))
        return results

    # ------------------------------------------------------------------
    # Zone regulations  (zone_code_mapping.json)
    # ------------------------------------------------------------------

    @staticmethod
    def _zone_matches(zone_name: str, zone_type: str) -> bool:
        """Return True if *zone_type* (from spatial data) semantically
        matches *zone_name* (from the regulation file).

        Handles shortened forms such as ``관리지역(보전관리)`` matching
        ``관리지역(보전관리지역)`` by checking both plain substring
        containment and a "stripped core" comparison where parenthesised
        qualifiers are extracted and matched flexibly.
        """
        if not zone_name or not zone_type:
            return False
        # Direct substring check (fast path).
        if zone_name in zone_type or zone_type in zone_name:
            return True
        # Strip parentheses to extract the core qualifier.  For example
        # "관리지역(보전관리지역)" → outer="관리지역", inner="보전관리지역"
        def _split(s: str) -> tuple[str, str]:
            m = re.match(r"^([^(]+)\(([^)]+)\)$", s)
            if m:
                return m.group(1), m.group(2)
            return s, ""

        type_outer, type_inner = _split(zone_type)
        name_outer, name_inner = _split(zone_name)

        # Outer parts must match (or one contains the other).
        if not (type_outer in name_outer or name_outer in type_outer):
            return False
        # If either has no inner part, outer match is sufficient.
        if not type_inner or not name_inner:
            return True
        # Inner: one must contain the other.
        return type_inner in name_inner or name_inner in type_inner

    def _match_zone_regulations(
        self, spatial_data: dict
    ) -> list[RegulationMatchResult]:
        """Match zone_code_mapping entries based on ``land_use.zone_types``
        (list of specific zone names from V-world features)
        and overlay flags (military, greenbelt, agricultural)."""
        results: list[RegulationMatchResult] = []
        land_use = spatial_data.get("land_use") or {}

        # Prefer zone_types list (specific per-feature names); fall back to zone_type str
        zone_types: list[str] = land_use.get("zone_types") or []
        if not zone_types:
            zt = land_use.get("zone_type", "")
            if zt:
                zone_types = [zt]

        # --- Match each specific zone_type against zone_code_mapping ------
        matched_codes: set[str] = set()
        for zt in zone_types:
            for entry in self._zone_codes:
                zone_name: str = entry.get("zone_name", "")
                code = entry.get("zone_code", "")
                if code in matched_codes:
                    continue
                if self._zone_matches(zone_name, zt):
                    matched_codes.add(code)
                    results.append(
                        RegulationMatchResult(
                            regulation_name=zone_name,
                            regulation_code=code,
                            legal_basis=entry.get("legal_basis", ""),
                            description=entry.get("description"),
                            restriction_level=None,
                            permit_required=bool(entry.get("restricted_uses")),
                            related_authority=None,
                            evidence={
                                "matched_zone_type": zt,
                                "eia_trigger": entry.get("eia_trigger"),
                                "permitted_uses": entry.get("permitted_uses"),
                                "restricted_uses": entry.get("restricted_uses"),
                                "max_building_coverage_pct": entry.get(
                                    "max_building_coverage_pct"
                                ),
                                "max_floor_area_ratio_pct": entry.get(
                                    "max_floor_area_ratio_pct"
                                ),
                            },
                        )
                    )

        # --- Overlay flags ------------------------------------------------
        _OVERLAY_ZONE_KEYWORDS: list[tuple[str, str]] = [
            ("military_zone_overlap", "군사"),
            ("greenbelt_overlap", "개발제한"),
            ("agricultural_zone_overlap", "농림"),
        ]
        for flag, keyword in _OVERLAY_ZONE_KEYWORDS:
            if land_use.get(flag):
                for entry in self._zone_codes:
                    zone_name = entry.get("zone_name", "")
                    code = entry.get("zone_code", "")
                    if keyword in zone_name:
                        if code in matched_codes:
                            continue
                        matched_codes.add(code)
                        results.append(
                            RegulationMatchResult(
                                regulation_name=zone_name,
                                regulation_code=code,
                                legal_basis=entry.get("legal_basis", ""),
                                description=entry.get("description"),
                                restriction_level=None,
                                permit_required=True,
                                related_authority=None,
                                evidence={
                                    "trigger": flag,
                                    "eia_trigger": entry.get("eia_trigger"),
                                },
                            )
                        )

        return results

    # ------------------------------------------------------------------
    # Conservation regulations (conservation_type_mapping.json)
    # ------------------------------------------------------------------

    def _match_conservation_regulations(
        self, spatial_data: dict
    ) -> list[RegulationMatchResult]:
        """Match conservation_type_mapping entries based on ecology, water,
        cultural, and land-use spatial attributes."""
        results: list[RegulationMatchResult] = []
        ecology = spatial_data.get("ecology") or {}
        water = spatial_data.get("water_quality") or {}
        cultural = spatial_data.get("cultural") or {}
        land_use = spatial_data.get("land_use") or {}

        # Build a lookup from conservation_type -> entry for convenience.
        ct_map: dict[str, dict] = {
            e["conservation_type"]: e
            for e in self._conservation_types
            if "conservation_type" in e
        }

        matched_types: list[tuple[str, dict]] = []

        # 1. Eco-grade -------------------------------------------------
        eco_grade = ecology.get("eco_grade")
        if eco_grade is not None:
            key = f"eco_grade_{int(eco_grade)}"
            if key in ct_map:
                matched_types.append(
                    (key, {"eco_grade": eco_grade})
                )

        # 2. Protected area overlap ------------------------------------
        if ecology.get("protected_area_overlap"):
            if "wildlife_protection" in ct_map:
                matched_types.append(
                    (
                        "wildlife_protection",
                        {"protected_area_overlap": True},
                    )
                )

        # 3. Endangered species distance < 1000m -----------------------
        endangered_dist = ecology.get("endangered_species_distance_m")
        if endangered_dist is not None and endangered_dist < 1000:
            if "wildlife_special_protection" in ct_map:
                matched_types.append(
                    (
                        "wildlife_special_protection",
                        {"endangered_species_distance_m": endangered_dist},
                    )
                )

        # 4. Natural park distance < buffer_zone_m ---------------------
        park_dist = ecology.get("natural_park_distance_m")
        if park_dist is not None and "natural_park" in ct_map:
            buffer = ct_map["natural_park"].get("buffer_zone_m") or 300
            if park_dist < buffer:
                matched_types.append(
                    (
                        "natural_park",
                        {
                            "natural_park_distance_m": park_dist,
                            "buffer_zone_m": buffer,
                        },
                    )
                )

        # 5. Forest / wetland distance < 500m --------------------------
        wetland_dist = ecology.get("forest_wetland_distance_m")
        if wetland_dist is not None and wetland_dist < 500:
            if "wetland_protected" in ct_map:
                matched_types.append(
                    (
                        "wetland_protected",
                        {"forest_wetland_distance_m": wetland_dist},
                    )
                )

        # 6. Sensitive water zone / water source protection ------------
        if water.get("sensitive_water_zone"):
            if "water_source_protection" in ct_map:
                matched_types.append(
                    (
                        "water_source_protection",
                        {"sensitive_water_zone": True},
                    )
                )
            if "riparian_zone" in ct_map:
                matched_types.append(
                    (
                        "riparian_zone",
                        {"sensitive_water_zone": True},
                    )
                )

        water_src_dist = water.get("water_source_protection_distance_m")
        if water_src_dist is not None and "water_source_protection" in ct_map:
            buffer = ct_map["water_source_protection"].get("buffer_zone_m") or 1000
            if water_src_dist < buffer:
                # Only add if not already matched via sensitive_water_zone.
                if not any(t == "water_source_protection" for t, _ in matched_types):
                    matched_types.append(
                        (
                            "water_source_protection",
                            {
                                "water_source_protection_distance_m": water_src_dist,
                                "buffer_zone_m": buffer,
                            },
                        )
                    )

        # 7. Cultural heritage protection overlay ----------------------
        if cultural.get("heritage_protection_overlap"):
            if "cultural_heritage_protection" in ct_map:
                matched_types.append(
                    (
                        "cultural_heritage_protection",
                        {"heritage_protection_overlap": True},
                    )
                )

        # 8. Buried heritage distance < 300m ---------------------------
        buried_dist = cultural.get("buried_heritage_distance_m")
        if buried_dist is not None and buried_dist < 300:
            if "buried_cultural_heritage" in ct_map:
                matched_types.append(
                    (
                        "buried_cultural_heritage",
                        {"buried_heritage_distance_m": buried_dist},
                    )
                )

        # 9. Military zone overlap (conservation perspective) ----------
        if land_use.get("military_zone_overlap"):
            if "military_facility_protection" in ct_map:
                matched_types.append(
                    (
                        "military_facility_protection",
                        {"military_zone_overlap": True},
                    )
                )

        # 10. Greenbelt overlap ----------------------------------------
        if land_use.get("greenbelt_overlap"):
            if "greenbelt" in ct_map:
                matched_types.append(
                    (
                        "greenbelt",
                        {"greenbelt_overlap": True},
                    )
                )

        # 11. Agricultural zone overlap --------------------------------
        if land_use.get("agricultural_zone_overlap"):
            if "agricultural_promotion" in ct_map:
                matched_types.append(
                    (
                        "agricultural_promotion",
                        {"agricultural_zone_overlap": True},
                    )
                )

        # De-duplicate (first match wins per conservation_type).
        seen: set[str] = set()
        for ctype, evidence_extra in matched_types:
            if ctype in seen:
                continue
            seen.add(ctype)
            entry = ct_map[ctype]
            restriction_level = entry.get("restriction_level", "")
            results.append(
                RegulationMatchResult(
                    regulation_name=entry.get("name", ctype),
                    regulation_code=ctype,
                    legal_basis=entry.get("legal_basis", ""),
                    description=entry.get("eia_implications"),
                    restriction_level=restriction_level,
                    permit_required=restriction_level in ("absolute", "high"),
                    related_authority=entry.get("permit_authority"),
                    evidence={
                        "conservation_type": ctype,
                        "restrictions": entry.get("restrictions"),
                        "buffer_zone_m": entry.get("buffer_zone_m"),
                        "exceptions": entry.get("exceptions"),
                        **evidence_extra,
                    },
                )
            )

        return results

    # ------------------------------------------------------------------
    # EIA thresholds (eia_thresholds.json)
    # ------------------------------------------------------------------

    # Mapping from common project_type values in project_info to the
    # keys used in eia_thresholds.json.
    _PROJECT_TYPE_ALIAS: dict[str, str] = {
        "road": "road",
        "housing": "housing_development",
        "housing_development": "housing_development",
        "power_plant": "power_plant",
        "factory": "industrial_complex",
        "industrial_complex": "industrial_complex",
        "dam": "dam",
        "railway": "railway",
        "port": "port",
        "airport": "airport",
        "waste_facility": "waste_facility",
        "mining": "mining",
        "tourism_complex": "tourism_complex",
        "reclamation": "reclamation",
        "military_facility": "military_facility",
        "new_town": "new_town",
        "urban_park": "urban_park",
        "sports_facility": "sports_facility",
        "sewage_treatment": "sewage_treatment",
        "waterway": "waterway",
        "river_improvement": "river_improvement",
        "forest_road": "forest_road",
        "golf_course": "golf_course",
        "ski_resort": "ski_resort",
        "cemetery": "cemetery",
        "special_economic_zone": "special_economic_zone",
        "logistics_complex": "logistics_complex",
        "marine_fishery": "marine_fishery",
        "solar_power": "solar_power",
        "wind_power": "wind_power",
        "water_supply": "water_supply",
        "urban_redevelopment": "urban_redevelopment",
        # 17개 사업유형 (환경영향평가법 시행령 별표3) → EIA threshold 매핑
        "urban_dev": "housing_development",
        "industrial": "industrial_complex",
        "energy": "power_plant",
        "water_resource": "dam",
        "river": "river_improvement",
        "tourism": "tourism_complex",
        "mountain": "mining",
        "sports": "sports_facility",
        "waste": "waste_facility",
        "military": "military_facility",
        "etc": "logistics_complex",
        "other": "logistics_complex",
    }

    def _match_eia_thresholds(
        self, project_info: dict
    ) -> list[RegulationMatchResult]:
        """Match EIA thresholds based on ``project_type`` in *project_info*."""
        results: list[RegulationMatchResult] = []
        raw_type = (project_info.get("project_type") or "").strip()
        if not raw_type:
            return results

        canonical = self._PROJECT_TYPE_ALIAS.get(raw_type, raw_type)

        for entry in self._eia_thresholds:
            if entry.get("project_type") == canonical:
                results.append(
                    RegulationMatchResult(
                        regulation_name=entry.get("project_type_name", canonical),
                        regulation_code=entry.get("project_type"),
                        legal_basis=entry.get("legal_basis", ""),
                        description=entry.get("threshold"),
                        restriction_level=None,
                        permit_required=True,
                        related_authority=entry.get("competent_authority"),
                        evidence={
                            "assessment_type": entry.get("assessment_type"),
                            "threshold": entry.get("threshold"),
                            "threshold_detail": entry.get("threshold_detail"),
                            "small_scale_threshold": entry.get(
                                "small_scale_threshold"
                            ),
                            "small_scale_detail": entry.get("small_scale_detail"),
                            "small_scale_type": entry.get("small_scale_type"),
                            "key_assessment_items": entry.get(
                                "key_assessment_items"
                            ),
                        },
                    )
                )
                break  # project_type is unique; stop after first match.

        if not results:
            logger.info(
                "No EIA threshold entry found for project_type=%r (canonical=%r)",
                raw_type,
                canonical,
            )

        return results
