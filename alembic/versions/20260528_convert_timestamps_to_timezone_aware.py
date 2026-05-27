"""convert timestamps to timezone aware

Revision ID: 20260527_tz
Revises: c35cb850a20c
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa

revision = '20260527_tz'
down_revision = 'c35cb850a20c'
branch_labels = None
depends_on = None

# Tables and columns to migrate
TIMESTAMP_COLUMNS = [
    ("members", "created_at"),
    ("fitness_classes", "created_at"),
    ("fitness_classes", "schedule"),
    ("bookings", "created_at"),
    ("memberships", "start_date"),
    ("memberships", "end_date"),
    ("memberships", "created_at"),
    ("payments", "created_at"),
    ("attendances", "checked_in_at"),
    ("notification_requests", "created_at"),
    ("direct_messages", "created_at"),
    ("notification_delivery_attempts", "attempted_at"),
    ("instructor_reactions", "created_at"),
    ("suggestions", "created_at"),
    ("community_posts", "created_at"),
    ("community_reactions", "created_at"),
    ("content_reports", "created_at"),
    ("payment_webhook_events", "created_at"),
    ("center_memberships", "created_at"),
    ("center_memberships", "updated_at"),
]

def upgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE TIMESTAMP WITH TIME ZONE
            USING {column} AT TIME ZONE 'UTC';
            """
        )

def downgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING {column} AT TIME ZONE 'UTC';
            """
        )