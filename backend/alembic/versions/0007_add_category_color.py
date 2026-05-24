"""add color column to categories

Revision ID: 0007_add_category_color
Revises: 2fbd71e90f67
Create Date: 2026-05-23

Adds color field used for category badges in the UI.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_add_category_color"
down_revision = "2fbd71e90f67"
branch_labels = None
depends_on = None


_CANONICAL_COLORS = {
    "backend": "#3b82f6",
    "frontend": "#a855f7",
    "devops": "#f59e0b",
    "design": "#ec4899",
    "mobile": "#10b981",
    "data": "#06b6d4",
    "qa": "#eab308",
    "security": "#ef4444",
}


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("color", sa.String(length=16), nullable=False, server_default="#64748b"),
    )
    for name, color in _CANONICAL_COLORS.items():
        op.execute(
            sa.text("UPDATE categories SET color = :color WHERE name = :name").bindparams(
                color=color, name=name
            )
        )
    op.alter_column("categories", "color", server_default=None)


def downgrade() -> None:
    op.drop_column("categories", "color")
