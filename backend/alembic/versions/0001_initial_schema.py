"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


project_member_role = sa.Enum(
    "owner", "admin", "member", "viewer", name="project_member_role"
)
stage_type = sa.Enum("start", "normal", "final", name="stage_type")
ticket_priority = sa.Enum("p1", "p2", "p3", "p4", "p5", name="ticket_priority")
ticket_link_type = sa.Enum(
    "blocks",
    "is_blocked_by",
    "relates_to",
    "duplicates",
    "is_duplicated_by",
    name="ticket_link_type",
)
seniority_level = sa.Enum("junior", "mid", "senior", "lead", name="seniority_level")


def upgrade() -> None:
    bind = op.get_bind()
    project_member_role.create(bind, checkfirst=True)
    stage_type.create(bind, checkfirst=True)
    ticket_priority.create(bind, checkfirst=True)
    ticket_link_type.create(bind, checkfirst=True)
    seniority_level.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.create_table(
        "worker_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "seniority",
            PGEnum(name="seniority_level", create_type=False),
            nullable=False,
        ),
        sa.Column("years_experience", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "primary_category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "base_productivity", sa.Float(), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "burnout_threshold", sa.Integer(), nullable=False, server_default="2400"
        ),
        sa.Column(
            "is_available", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )

    op.create_table(
        "worker_skill_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("worker_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proficiency", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("efficiency", sa.Float(), nullable=True),
        sa.UniqueConstraint(
            "worker_id", "category_id", name="uq_worker_skill_profile_pair"
        ),
    )
    op.create_index(
        "ix_worker_skill_profiles_worker_id", "worker_skill_profiles", ["worker_id"]
    )
    op.create_index(
        "ix_worker_skill_profiles_category_id", "worker_skill_profiles", ["category_id"]
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            PGEnum(name="project_member_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "project_id", name="uq_project_members_user_project"
        ),
    )
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])

    op.create_table(
        "stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("type", PGEnum(name="stage_type", create_type=False), nullable=True),
        sa.Column("color", sa.String(32), nullable=True),
    )
    op.create_index("ix_stages_project_id", "stages", ["project_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("color", sa.String(32), nullable=True),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage_id",
            sa.Integer(),
            sa.ForeignKey("stages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            PGEnum(name="ticket_priority", create_type=False),
            nullable=False,
            server_default="p3",
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "assignee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("complexity", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("spent_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("complexity BETWEEN 1 AND 5", name="ck_ticket_complexity"),
    )
    op.create_index("ix_tickets_project_id", "tickets", ["project_id"])
    op.create_index("ix_tickets_stage_id", "tickets", ["stage_id"])
    op.create_index("ix_tickets_title", "tickets", ["title"])
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"])
    op.create_index("ix_tickets_parent_id", "tickets", ["parent_id"])
    op.create_index("ix_tickets_category_id", "tickets", ["category_id"])

    op.create_table(
        "ticket_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            PGEnum(name="ticket_link_type", create_type=False),
            nullable=False,
            server_default="relates_to",
        ),
        sa.UniqueConstraint(
            "source_ticket_id", "target_ticket_id", name="uq_ticket_link_pair"
        ),
    )
    op.create_index(
        "ix_ticket_links_source_ticket_id", "ticket_links", ["source_ticket_id"]
    )
    op.create_index(
        "ix_ticket_links_target_ticket_id", "ticket_links", ["target_ticket_id"]
    )

    op.create_table(
        "ticket_tags",
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_comments_ticket_id", "comments", ["ticket_id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])

    op.create_table(
        "assignment_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("worker_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("actual_minutes", sa.Integer(), nullable=True),
        sa.Column("rl_q_value", sa.Float(), nullable=True),
        sa.Column("rl_state_vector", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_assignment_records_ticket_id", "assignment_records", ["ticket_id"]
    )
    op.create_index(
        "ix_assignment_records_worker_id", "assignment_records", ["worker_id"]
    )

    op.create_table(
        "rl_project_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("w_priority", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("w_efficiency", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("w_overload", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("w_throughput", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("gamma", sa.Float(), nullable=False, server_default="0.95"),
        sa.Column(
            "fine_tune_every_n_completions",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "replay_buffer_max_size",
            sa.Integer(),
            nullable=False,
            server_default="5000",
        ),
    )


def downgrade() -> None:
    op.drop_table("rl_project_configs")
    op.drop_table("assignment_records")
    op.drop_table("comments")
    op.drop_table("ticket_tags")
    op.drop_table("ticket_links")
    op.drop_table("tickets")
    op.drop_table("tags")
    op.drop_table("stages")
    op.drop_table("project_members")
    op.drop_table("worker_skill_profiles")
    op.drop_table("worker_profiles")
    op.drop_table("categories")
    op.drop_table("projects")
    op.drop_table("users")

    bind = op.get_bind()
    seniority_level.drop(bind, checkfirst=True)
    ticket_link_type.drop(bind, checkfirst=True)
    ticket_priority.drop(bind, checkfirst=True)
    stage_type.drop(bind, checkfirst=True)
    project_member_role.drop(bind, checkfirst=True)
