"""Lightweight runtime DDL for small deployments without Alembic."""
from sqlalchemy import inspect, text


def ensure_columns(engine) -> None:
    try:
        insp = inspect(engine)
        if not insp.has_table("members"):
            return
        col_names = {c["name"] for c in insp.get_columns("members")}
        with engine.begin() as conn:
            if "role" not in col_names:
                dialect = engine.dialect.name
                stmt = "ALTER TABLE members ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'member'"
                if dialect == "sqlite":
                    stmt = "ALTER TABLE members ADD COLUMN role VARCHAR(32) DEFAULT 'member'"
                conn.execute(text(stmt))
            if "member_no" not in col_names:
                conn.execute(text("ALTER TABLE members ADD COLUMN member_no VARCHAR(64)"))
            if "member_level" not in col_names:
                dialect = engine.dialect.name
                stmt = (
                    "ALTER TABLE members ADD COLUMN member_level VARCHAR(32) NOT NULL DEFAULT 'starter'"
                )
                if dialect == "sqlite":
                    stmt = "ALTER TABLE members ADD COLUMN member_level VARCHAR(32) DEFAULT 'starter'"
                conn.execute(text(stmt))
            conn.execute(
                text("UPDATE members SET role = 'member' WHERE role IS NULL OR role = ''")
            )
            conn.execute(
                text(
                    "UPDATE members SET member_level = 'starter' "
                    "WHERE member_level IS NULL OR member_level = ''"
                )
            )
    except Exception:
        pass
