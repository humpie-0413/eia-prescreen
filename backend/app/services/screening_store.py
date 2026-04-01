"""스크리닝 데이터 통합 조회 — DB 또는 인메모리 + 파일 영속화.

여러 API 라우트(evaluation, draft, review, data_status)가 screening 데이터를
참조할 때 동일한 로직을 사용할 수 있도록 중앙화한다.

인메모리 dict를 1차 캐시로 사용하되, 파일(data/screenings/{id}.json)에도
기록하여 서버 재시작(--reload 등) 후에도 데이터를 복원할 수 있게 한다.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from backend.app.core.database import check_db_connection, get_session

logger = logging.getLogger(__name__)

_in_memory: dict[str, dict[str, Any]] = {}

# 파일 영속화 디렉터리
_SCREENINGS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "screenings"
_SCREENINGS_DIR.mkdir(parents=True, exist_ok=True)


# ── JSON 직렬화 헬퍼 ──────────────────────────────────────────

def _json_serializer(obj: Any) -> Any:
    """datetime, UUID 등 JSON 비표준 타입 처리."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def _save_to_file(screening_id: str, record: dict[str, Any]) -> None:
    """스크리닝 데이터를 JSON 파일로 저장한다."""
    try:
        path = _SCREENINGS_DIR / f"{screening_id}.json"
        path.write_text(
            json.dumps(record, default=_json_serializer, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.warning("Failed to save screening %s to file", screening_id, exc_info=True)


def _load_from_file(screening_id: str) -> Optional[dict[str, Any]]:
    """JSON 파일에서 스크리닝 데이터를 로드한다."""
    try:
        path = _SCREENINGS_DIR / f"{screening_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        # datetime 문자열 복원
        for key in ("created_at", "updated_at"):
            if isinstance(data.get(key), str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    pass
        # UUID 복원
        if isinstance(data.get("id"), str):
            try:
                data["id"] = UUID(data["id"])
            except ValueError:
                pass
        return data
    except Exception:
        logger.warning("Failed to load screening %s from file", screening_id, exc_info=True)
        return None


def _list_from_files() -> list[dict[str, Any]]:
    """파일 시스템에서 모든 스크리닝을 로드한다."""
    items: list[dict[str, Any]] = []
    try:
        for path in _SCREENINGS_DIR.glob("*.json"):
            sid = path.stem
            data = _load_from_file(sid)
            if data is not None:
                items.append(data)
    except Exception:
        logger.warning("Failed to list screenings from files", exc_info=True)
    return items


# ── 공개 API ──────────────────────────────────────────────────

async def create(data: dict[str, Any]) -> dict[str, Any]:
    """새 스크리닝을 생성한다 (DB 또는 인메모리)."""
    db_ok = await check_db_connection()

    if db_ok:
        from backend.app.models.screening import ProjectType, ScreeningRequest

        session_gen = get_session()
        session = await session_gen.__anext__()
        try:
            screening = ScreeningRequest(
                project_name=data["project_name"],
                project_type=ProjectType(data["project_type"]),
                project_scale=data.get("project_scale"),
                address=data.get("address"),
                status="pending",
            )
            lng = data.get("lng")
            lat = data.get("lat")
            if lng is not None and lat is not None:
                from geoalchemy2.elements import WKTElement

                screening.location = WKTElement(
                    f"POINT({lng} {lat})", srid=4326
                )
            session.add(screening)
            await session.commit()
            await session.refresh(
                screening, attribute_names=["risk_cards", "regulation_matches"]
            )
            return {
                "id": screening.id,
                "project_name": screening.project_name,
                "project_type": screening.project_type.value,
                "project_scale": screening.project_scale,
                "address": screening.address,
                "lng": lng,
                "lat": lat,
                "status": screening.status,
                "created_at": screening.created_at,
                "updated_at": screening.updated_at,
                "risk_cards": [],
                "regulation_matches": [],
            }
        finally:
            await session_gen.aclose()

    # 인메모리 + 파일 모드
    now = datetime.now(timezone.utc)
    new_id = uuid.uuid4()
    record = {
        "id": new_id,
        "project_name": data["project_name"],
        "project_type": data["project_type"],
        "project_scale": data.get("project_scale"),
        "address": data.get("address"),
        "lng": data.get("lng"),
        "lat": data.get("lat"),
        "status": "completed",
        "llm_interpretation": None,
        "created_at": now,
        "updated_at": now,
        "risk_cards": [],
        "regulation_matches": [],
    }
    sid = str(new_id)
    _in_memory[sid] = record
    _save_to_file(sid, record)
    return record


async def get(screening_id: str) -> Optional[dict[str, Any]]:
    """screening_id로 데이터를 조회한다 (인메모리 → 파일 → DB 순서)."""
    # 1) 인메모리 캐시
    if screening_id in _in_memory:
        return _in_memory[screening_id]

    # 2) 파일에서 복원 (서버 재시작 후 복구)
    from_file = _load_from_file(screening_id)
    if from_file is not None:
        _in_memory[screening_id] = from_file  # 캐시에 올려놓기
        return from_file

    # 3) DB 조회
    db_ok = await check_db_connection()
    if not db_ok:
        return None

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.app.models.screening import ScreeningRequest

    session_gen = get_session()
    session = await session_gen.__anext__()
    try:
        stmt = (
            select(ScreeningRequest)
            .where(ScreeningRequest.id == UUID(screening_id))
            .options(
                selectinload(ScreeningRequest.risk_cards),
                selectinload(ScreeningRequest.regulation_matches),
            )
        )
        result = await session.execute(stmt)
        screening = result.scalar_one_or_none()
        if screening is None:
            return None

        # location 추출
        lng, lat = None, None
        if screening.location is not None:
            try:
                from geoalchemy2.shape import to_shape

                point = to_shape(screening.location)
                lng, lat = point.x, point.y
            except Exception:
                pass

        return {
            "id": screening.id,
            "project_name": screening.project_name,
            "project_type": screening.project_type.value,
            "project_scale": screening.project_scale,
            "address": screening.address,
            "lng": lng,
            "lat": lat,
            "status": screening.status,
            "created_at": screening.created_at,
            "updated_at": screening.updated_at,
            "risk_cards": screening.risk_cards,
            "regulation_matches": screening.regulation_matches,
        }
    finally:
        await session_gen.aclose()


async def list_all() -> list[dict[str, Any]]:
    """모든 스크리닝 목록을 반환한다."""
    # 인메모리 + 파일에서 병합
    seen_ids: set[str] = set()
    items: list[dict[str, Any]] = []

    for sid, record in _in_memory.items():
        items.append(record)
        seen_ids.add(sid)

    # 파일에서 인메모리에 없는 것 추가
    for record in _list_from_files():
        sid = str(record.get("id", ""))
        if sid and sid not in seen_ids:
            _in_memory[sid] = record  # 캐시에 올려놓기
            items.append(record)
            seen_ids.add(sid)

    db_ok = await check_db_connection()
    if db_ok:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from backend.app.models.screening import ScreeningRequest

        session_gen = get_session()
        session = await session_gen.__anext__()
        try:
            stmt = (
                select(ScreeningRequest)
                .options(selectinload(ScreeningRequest.risk_cards))
                .order_by(ScreeningRequest.created_at.desc())
                .limit(50)
            )
            result = await session.execute(stmt)
            for s in result.scalars().all():
                sid = str(s.id)
                if sid not in seen_ids:
                    items.append(
                        {
                            "id": s.id,
                            "project_name": s.project_name,
                            "project_type": s.project_type.value,
                            "status": s.status,
                            "created_at": s.created_at,
                            "risk_cards": s.risk_cards,
                        }
                    )
                    seen_ids.add(sid)
        finally:
            await session_gen.aclose()

    items.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    return items


async def update_evaluation(
    screening_id: str,
    risk_cards: list[dict],
    regulation_matches: list[dict],
) -> None:
    """평가 결과를 저장한다."""
    if screening_id in _in_memory:
        _in_memory[screening_id]["risk_cards"] = risk_cards
        _in_memory[screening_id]["regulation_matches"] = regulation_matches
        _in_memory[screening_id]["status"] = "evaluated"
        _save_to_file(screening_id, _in_memory[screening_id])
    else:
        # 파일에서 복원 후 업데이트
        record = _load_from_file(screening_id)
        if record is not None:
            record["risk_cards"] = risk_cards
            record["regulation_matches"] = regulation_matches
            record["status"] = "evaluated"
            _in_memory[screening_id] = record
            _save_to_file(screening_id, record)
