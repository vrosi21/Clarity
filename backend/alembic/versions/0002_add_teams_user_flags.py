"""add teams, team_members, user is_admin/is_active

Revision ID: 0002_teams_user_flags
Revises: 0001_initial
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op

revision = "0002_teams_user_flags"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type — idempotent via DO block.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE team_member_role AS ENUM ('manager', 'member');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add columns to users — IF NOT EXISTS makes this re-runnable.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin  BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true")

    # Create teams table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(120) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Create team_members table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            team_id   INTEGER     NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            user_id   INTEGER     NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
            role      team_member_role NOT NULL DEFAULT 'member',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (team_id, user_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS team_members")
    op.execute("DROP TABLE IF EXISTS teams")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")
    op.execute("DROP TYPE IF EXISTS team_member_role")
