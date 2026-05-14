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
            if "birth_date" not in col_names:
                conn.execute(text("ALTER TABLE members ADD COLUMN birth_date DATE"))
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
            if insp.has_table("payments"):
                pcols = {c["name"] for c in insp.get_columns("payments")}
                if "center_id" not in pcols:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN center_id INTEGER"))
                if "source" not in pcols:
                    conn.execute(
                        text("ALTER TABLE payments ADD COLUMN source VARCHAR(32) DEFAULT 'online'")
                    )
                if "memo" not in pcols:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN memo VARCHAR(512)"))
                if "recorded_by_member_id" not in pcols:
                    conn.execute(
                        text("ALTER TABLE payments ADD COLUMN recorded_by_member_id INTEGER")
                    )
                if "payment_method" not in pcols:
                    conn.execute(
                        text("ALTER TABLE payments ADD COLUMN payment_method VARCHAR(32) DEFAULT 'card'")
                    )
                if "external_ref" not in pcols:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN external_ref VARCHAR(128)"))
                conn.execute(
                    text("UPDATE payments SET source='online' WHERE source IS NULL OR source=''")
                )
                conn.execute(
                    text("UPDATE payments SET payment_method='card' WHERE payment_method IS NULL OR payment_method=''")
                )
            if insp.has_table("fitness_classes"):
                fcols = {c["name"] for c in insp.get_columns("fitness_classes")}
                if "center_id" not in fcols:
                    conn.execute(text("ALTER TABLE fitness_classes ADD COLUMN center_id INTEGER"))
                if "level_required" not in fcols:
                    conn.execute(
                        text("ALTER TABLE fitness_classes ADD COLUMN level_required VARCHAR(32) DEFAULT 'starter'")
                    )
                conn.execute(
                    text("UPDATE fitness_classes SET level_required='starter' WHERE level_required IS NULL OR level_required=''")
                )
            if insp.has_table("instructor_profiles"):
                icols = {c["name"] for c in insp.get_columns("instructor_profiles")}
                if "avatar_url" not in icols:
                    conn.execute(text("ALTER TABLE instructor_profiles ADD COLUMN avatar_url VARCHAR(512)"))
                if "bio" not in icols:
                    conn.execute(text("ALTER TABLE instructor_profiles ADD COLUMN bio VARCHAR(1000)"))
                if "specialties" not in icols:
                    conn.execute(text("ALTER TABLE instructor_profiles ADD COLUMN specialties VARCHAR(500)"))
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
            if not insp.has_table("centers"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE centers (
                            id INTEGER PRIMARY KEY,
                            name VARCHAR(128) NOT NULL,
                            slug VARCHAR(128) UNIQUE NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            tablet_welcome_text VARCHAR(256) DEFAULT 'Welcome to Fitlio.',
                            tablet_theme VARCHAR(64) DEFAULT 'premium-green',
                            tablet_logo_url VARCHAR(512),
                            created_by_member_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("center_memberships"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE center_memberships (
                            id INTEGER PRIMARY KEY,
                            center_id INTEGER NOT NULL,
                            member_id INTEGER NOT NULL,
                            role VARCHAR(32) DEFAULT 'member',
                            status VARCHAR(32) DEFAULT 'pending',
                            invited_by_member_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("instructor_reactions"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE instructor_reactions (
                            id INTEGER PRIMARY KEY,
                            instructor_id INTEGER NOT NULL,
                            member_id INTEGER NOT NULL,
                            type VARCHAR(16) DEFAULT 'like',
                            content VARCHAR(1000),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("suggestions"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE suggestions (
                            id INTEGER PRIMARY KEY,
                            member_id INTEGER,
                            center_id INTEGER,
                            content VARCHAR(2000) NOT NULL,
                            is_anonymous BOOLEAN DEFAULT TRUE,
                            status VARCHAR(32) DEFAULT 'open',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("community_posts"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE community_posts (
                            id INTEGER PRIMARY KEY,
                            author_member_id INTEGER NOT NULL,
                            center_id INTEGER,
                            content VARCHAR(2000),
                            media_url VARCHAR(1024),
                            media_type VARCHAR(16) DEFAULT 'image',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("community_reactions"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE community_reactions (
                            id INTEGER PRIMARY KEY,
                            post_id INTEGER NOT NULL,
                            member_id INTEGER NOT NULL,
                            type VARCHAR(16) DEFAULT 'like',
                            content VARCHAR(1000),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if insp.has_table("centers"):
                ccols = {c["name"] for c in insp.get_columns("centers")}
                if "tablet_accent_color" not in ccols:
                    conn.execute(
                        text("ALTER TABLE centers ADD COLUMN tablet_accent_color VARCHAR(32) DEFAULT '#2f855a'")
                    )
                if "tablet_background_url" not in ccols:
                    conn.execute(text("ALTER TABLE centers ADD COLUMN tablet_background_url VARCHAR(1024)"))
                conn.execute(
                    text(
                        "UPDATE centers SET tablet_accent_color='#2f855a' "
                        "WHERE tablet_accent_color IS NULL OR tablet_accent_color=''"
                    )
                )
            if insp.has_table("community_posts"):
                cpcols = {c["name"] for c in insp.get_columns("community_posts")}
                if "is_hidden" not in cpcols:
                    conn.execute(
                        text("ALTER TABLE community_posts ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE")
                    )
                if "hidden_reason" not in cpcols:
                    conn.execute(text("ALTER TABLE community_posts ADD COLUMN hidden_reason VARCHAR(255)"))
            if insp.has_table("community_reactions"):
                crcols = {c["name"] for c in insp.get_columns("community_reactions")}
                if "is_hidden" not in crcols:
                    conn.execute(
                        text("ALTER TABLE community_reactions ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE")
                    )
            if not insp.has_table("content_reports"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE content_reports (
                            id INTEGER PRIMARY KEY,
                            reporter_member_id INTEGER NOT NULL,
                            target_type VARCHAR(32) NOT NULL,
                            target_id INTEGER NOT NULL,
                            reason VARCHAR(255) NOT NULL,
                            status VARCHAR(32) DEFAULT 'open',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            if not insp.has_table("payment_webhook_events"):
                conn.execute(
                    text(
                        """
                        CREATE TABLE payment_webhook_events (
                            id INTEGER PRIMARY KEY,
                            provider VARCHAR(32) NOT NULL,
                            event_type VARCHAR(64) NOT NULL,
                            external_ref VARCHAR(128),
                            payload VARCHAR(4000),
                            processed BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
    except Exception:
        pass
