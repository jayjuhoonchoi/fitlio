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
            if insp.has_table("notification_requests"):
                ncols = {c["name"] for c in insp.get_columns("notification_requests")}
                if "channel" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN channel VARCHAR(16) DEFAULT 'email'"
                        )
                    )
                if "retry_count" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN retry_count INTEGER DEFAULT 0"
                        )
                    )
                if "max_retries" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN max_retries INTEGER DEFAULT 3"
                        )
                    )
                if "next_attempt_at" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN next_attempt_at TIMESTAMP"
                        )
                    )
                if "last_error" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN last_error VARCHAR(512)"
                        )
                    )
                if "sent_at" not in ncols:
                    conn.execute(
                        text(
                            "ALTER TABLE notification_requests ADD COLUMN sent_at TIMESTAMP"
                        )
                    )
                conn.execute(
                    text(
                        "UPDATE notification_requests SET channel='email' "
                        "WHERE channel IS NULL OR channel=''"
                    )
                )
                conn.execute(
                    text(
                        "UPDATE notification_requests SET retry_count=0 WHERE retry_count IS NULL"
                    )
                )
                conn.execute(
                    text(
                        "UPDATE notification_requests SET max_retries=3 WHERE max_retries IS NULL"
                    )
                )
            if not insp.has_table("notification_delivery_attempts"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE notification_delivery_attempts (
                            id INTEGER PRIMARY KEY,
                            notification_id INTEGER NOT NULL,
                            channel VARCHAR(16) NOT NULL,
                            status VARCHAR(32) NOT NULL,
                            provider_message_id VARCHAR(128),
                            error_message VARCHAR(512),
                            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
    except Exception:
        pass
