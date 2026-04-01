import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.core.config import settings
from backend.app.models.base import Base

# 모든 모델을 import하여 Base.metadata에 등록
import backend.app.models.screening  # noqa: F401
import backend.app.models.user  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Settings에서 DB URL을 가져와 alembic config에 주입
_db_url = settings.DATABASE_URL
if "?" not in _db_url:
    _db_url += "?ssl=disable"
elif "ssl=" not in _db_url:
    _db_url += "&ssl=disable"
config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata

# PostGIS tiger geocoder 등 시스템 테이블 제외
_EXCLUDE_TABLES = {"spatial_ref_sys"}
_EXCLUDE_SCHEMAS = {"tiger", "tiger_data", "topology"}


def _include_object(obj, name, type_, reflected, compare_to) -> bool:  # noqa: ANN001
    if type_ == "table":
        if name in _EXCLUDE_TABLES:
            return False
        schema = getattr(obj, "schema", None)
        if schema in _EXCLUDE_SCHEMAS:
            return False
        # PostGIS tiger tables in public schema
        if hasattr(obj, "schema") and obj.schema is None:
            from sqlalchemy import inspect as sa_inspect
            table_name = name
            # Exclude known PostGIS/tiger tables
            tiger_tables = {
                "addr", "addrfeat", "bg", "county", "county_lookup",
                "countysub_lookup", "cousub", "direction_lookup", "edges",
                "faces", "featnames", "geocode_settings", "geocode_settings_default",
                "layer", "loader_lookuptables", "loader_platform", "loader_variables",
                "pagc_gaz", "pagc_lex", "pagc_rules", "place", "place_lookup",
                "secondary_unit_lookup", "state", "state_lookup",
                "street_type_lookup", "tabblock", "tabblock20", "topology",
                "tract", "zcta5", "zip_lookup", "zip_lookup_all",
                "zip_lookup_base", "zip_state", "zip_state_loc",
            }
            if table_name in tiger_tables:
                return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # noqa: ANN001
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
