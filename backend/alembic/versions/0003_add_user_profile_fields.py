"""add full_name and years_experience to users

Revision ID: 0003_add_user_profile_fields
Revises: 0002_teams_user_flags
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op

revision = "0003_add_user_profile_fields"
down_revision = "0002_teams_user_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(200)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS years_experience INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS years_experience")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS full_name")
