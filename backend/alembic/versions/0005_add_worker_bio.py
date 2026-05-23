"""add bio column to worker_profiles

Revision ID: 0005_add_worker_bio
Revises: 0004_rbac_role_system
Create Date: 2026-05-19

Adds a free-text bio column used by the LangChain skill extractor and the
SemanticEncoder pipeline (NLP embedding lives on WorkerSkillProfile).
"""
from __future__ import annotations

from alembic import op


revision = "0005_add_worker_bio"
down_revision = "0004_rbac_role_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE worker_profiles ADD COLUMN IF NOT EXISTS bio TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE worker_profiles DROP COLUMN IF EXISTS bio")
