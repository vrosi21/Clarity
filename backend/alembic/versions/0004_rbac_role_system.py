"""rbac role system

Revision ID: 0004_rbac_role_system
Revises: 0003_add_user_profile_fields
Create Date: 2026-05-15

Replaces ProjectMemberRole enum + is_admin flag with a full RBAC model:
- roles table with permissions JSONB
- user_org_roles for org-level assignment (replaces is_admin)
- project_members.role enum → role_id FK
- project_role_constraints + project_category_configs for per-project rules
- worker_skill_profiles gain nlp_embedding + nlp_ticket_count
- projects gain created_by_id
- teams + team_members tables and related enums dropped

Seeds built-in roles + root user inline so the DB is always usable post-migration.
"""
from __future__ import annotations

import json
import os

from alembic import op
from passlib.context import CryptContext
from sqlalchemy.sql import column, table

revision = "0004_rbac_role_system"
down_revision = "0003_add_user_profile_fields"
branch_labels = None
depends_on = None


# ── Permission constants (kept in sync with app/core/permissions.py) ─────────
ORG_MANAGE_USERS = "org:manage_users"
ORG_READ_USERS = "org:read_users"
ORG_MANAGE_ROLES = "org:manage_roles"
ORG_MANAGE_SETTINGS = "org:manage_settings"

PROJECTS_CREATE = "projects:create"
PROJECTS_READ = "projects:read"
PROJECTS_UPDATE = "projects:update"
PROJECTS_DELETE = "projects:delete"
PROJECTS_MANAGE_MEMBERS = "projects:manage_members"
PROJECTS_MANAGE_SETTINGS = "projects:manage_settings"

STAGES_CREATE = "stages:create"
STAGES_UPDATE = "stages:update"
STAGES_DELETE = "stages:delete"
STAGES_REORDER = "stages:reorder"

TICKETS_CREATE = "tickets:create"
TICKETS_READ = "tickets:read"
TICKETS_UPDATE = "tickets:update"
TICKETS_DELETE = "tickets:delete"
TICKETS_MOVE = "tickets:move"
TICKETS_ASSIGN = "tickets:assign"
TICKETS_BE_ASSIGNED = "tickets:be_assigned"

COMMENTS_CREATE = "comments:create"
COMMENTS_READ = "comments:read"
COMMENTS_DELETE_OWN = "comments:delete_own"
COMMENTS_DELETE_ANY = "comments:delete_any"

ALL_PERMS = [
    ORG_MANAGE_USERS, ORG_READ_USERS, ORG_MANAGE_ROLES, ORG_MANAGE_SETTINGS,
    PROJECTS_CREATE, PROJECTS_READ, PROJECTS_UPDATE, PROJECTS_DELETE,
    PROJECTS_MANAGE_MEMBERS, PROJECTS_MANAGE_SETTINGS,
    STAGES_CREATE, STAGES_UPDATE, STAGES_DELETE, STAGES_REORDER,
    TICKETS_CREATE, TICKETS_READ, TICKETS_UPDATE, TICKETS_DELETE,
    TICKETS_MOVE, TICKETS_ASSIGN, TICKETS_BE_ASSIGNED,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN, COMMENTS_DELETE_ANY,
]

ADMIN_PERMS = [p for p in ALL_PERMS if p != ORG_MANAGE_SETTINGS]
ORG_PM_PERMS = [
    ORG_READ_USERS,
    PROJECTS_CREATE, PROJECTS_READ, PROJECTS_UPDATE, PROJECTS_DELETE,
    PROJECTS_MANAGE_MEMBERS, PROJECTS_MANAGE_SETTINGS,
    STAGES_CREATE, STAGES_UPDATE, STAGES_DELETE, STAGES_REORDER,
    TICKETS_CREATE, TICKETS_READ, TICKETS_UPDATE, TICKETS_DELETE,
    TICKETS_MOVE, TICKETS_ASSIGN,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN, COMMENTS_DELETE_ANY,
]
ORG_MEMBER_PERMS = [PROJECTS_READ, TICKETS_READ, COMMENTS_READ]

PROJECT_PM_PERMS = [
    PROJECTS_READ, PROJECTS_UPDATE,
    PROJECTS_MANAGE_MEMBERS, PROJECTS_MANAGE_SETTINGS,
    STAGES_CREATE, STAGES_UPDATE, STAGES_DELETE, STAGES_REORDER,
    TICKETS_CREATE, TICKETS_READ, TICKETS_UPDATE, TICKETS_DELETE,
    TICKETS_MOVE, TICKETS_ASSIGN,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN, COMMENTS_DELETE_ANY,
]
CONTRIBUTOR_PERMS = [
    PROJECTS_READ,
    TICKETS_CREATE, TICKETS_READ, TICKETS_UPDATE, TICKETS_MOVE, TICKETS_BE_ASSIGNED,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN,
]
WORKER_PERMS = [
    PROJECTS_READ,
    TICKETS_READ, TICKETS_UPDATE, TICKETS_MOVE, TICKETS_BE_ASSIGNED,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN,
]
COMMENTER_PERMS = [
    PROJECTS_READ, TICKETS_READ,
    COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN,
]
VIEWER_PERMS = [PROJECTS_READ, TICKETS_READ, COMMENTS_READ]


# Map old project_member_role values → new role name for data migration.
OLD_ROLE_MAP = {
    "owner": "project_pm",
    "admin": "project_pm",
    "member": "contributor",
    "viewer": "viewer",
}


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Create role_scope enum ──────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE role_scope AS ENUM ('org', 'project', 'both');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # ── 2. roles table ─────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id            SERIAL PRIMARY KEY,
            name          VARCHAR(100) NOT NULL UNIQUE,
            description   TEXT,
            scope         role_scope NOT NULL,
            is_builtin    BOOLEAN NOT NULL DEFAULT false,
            permissions   JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_roles_name ON roles(name)")

    # ── 3. Seed built-in roles ────────────────────────────────────────────────
    roles_def = [
        ("root_user", "Full system access. Reserved for bootstrap.", "org", ALL_PERMS),
        ("admin", "Organisation administrator.", "org", ADMIN_PERMS),
        ("org_pm", "Org-wide project manager.", "org", ORG_PM_PERMS),
        ("member", "Default org member with read access.", "org", ORG_MEMBER_PERMS),
        ("project_pm", "Project manager for a single project.", "project", PROJECT_PM_PERMS),
        ("contributor", "Standard contributor — creates and works on tickets.", "project", CONTRIBUTOR_PERMS),
        ("worker", "Worker — receives assignments, no creation.", "project", WORKER_PERMS),
        ("commenter", "Comment-only collaborator.", "project", COMMENTER_PERMS),
        ("viewer", "Read-only viewer.", "project", VIEWER_PERMS),
    ]
    for name, desc, scope, perms in roles_def:
        op.execute(
            f"""
            INSERT INTO roles (name, description, scope, is_builtin, permissions)
            VALUES ('{name}', {_sqlstr(desc)}, '{scope}', true, '{json.dumps(perms)}'::jsonb)
            ON CONFLICT (name) DO NOTHING
            """
        )

    # ── 4. user_org_roles table ────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_org_roles (
            user_id        INTEGER NOT NULL PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            role_id        INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
            assigned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            assigned_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_org_roles_role_id ON user_org_roles(role_id)")

    # ── 5. Migrate is_admin → org_role ────────────────────────────────────────
    op.execute(
        """
        INSERT INTO user_org_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.is_admin = true AND r.name = 'admin'
        ON CONFLICT (user_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO user_org_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.is_admin = false AND r.name = 'member'
        ON CONFLICT (user_id) DO NOTHING
        """
    )

    # ── 6. Drop is_admin column ────────────────────────────────────────────────
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")

    # ── 7. Seed root user (idempotent) ─────────────────────────────────────────
    root_email = os.environ.get("ROOT_EMAIL", "root@example.com")
    root_password = os.environ.get("ROOT_PASSWORD", "ChangeMe123!")
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_ctx.hash(root_password)
    op.execute(
        f"""
        INSERT INTO users (email, username, hashed_password, full_name, years_experience, is_active)
        VALUES ({_sqlstr(root_email)}, 'root', {_sqlstr(hashed)}, 'Root User', 0, true)
        ON CONFLICT (email) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO user_org_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.email = {_sqlstr(root_email)} AND r.name = 'root_user'
        ON CONFLICT (user_id) DO UPDATE SET role_id = EXCLUDED.role_id
        """
    )

    # ── 8. project_members.role enum → role_id ────────────────────────────────
    op.execute("ALTER TABLE project_members ADD COLUMN IF NOT EXISTS role_id INTEGER")
    for old, new in OLD_ROLE_MAP.items():
        op.execute(
            f"""
            UPDATE project_members pm
            SET role_id = r.id
            FROM roles r
            WHERE pm.role = '{old}' AND r.name = '{new}'
            """
        )
    op.execute(
        """
        UPDATE project_members pm
        SET role_id = r.id
        FROM roles r
        WHERE pm.role_id IS NULL AND r.name = 'viewer'
        """
    )
    op.execute("ALTER TABLE project_members ALTER COLUMN role_id SET NOT NULL")
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE project_members
                ADD CONSTRAINT project_members_role_id_fkey
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT;
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_role_id ON project_members(role_id)")
    op.execute("ALTER TABLE project_members DROP COLUMN IF EXISTS role")
    op.execute("DROP TYPE IF EXISTS project_member_role")

    # ── 9. Drop teams + team_members ──────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS team_members")
    op.execute("DROP TABLE IF EXISTS teams")
    op.execute("DROP TYPE IF EXISTS team_member_role")

    # ── 10. projects.created_by_id ────────────────────────────────────────────
    op.execute(
        """
        ALTER TABLE projects
            ADD COLUMN IF NOT EXISTS created_by_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_created_by_id ON projects(created_by_id)")

    # ── 11. worker_skill_profiles new columns ─────────────────────────────────
    op.execute("ALTER TABLE worker_skill_profiles ADD COLUMN IF NOT EXISTS nlp_embedding JSONB")
    op.execute(
        "ALTER TABLE worker_skill_profiles "
        "ADD COLUMN IF NOT EXISTS nlp_ticket_count INTEGER NOT NULL DEFAULT 0"
    )

    # ── 12. project_role_constraints ──────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_role_constraints (
            id                  SERIAL PRIMARY KEY,
            project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            role_id             INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            allowed_transitions JSONB,
            editable_fields     JSONB,
            assignee_only       BOOLEAN NOT NULL DEFAULT false,
            view_scope          VARCHAR(20) NOT NULL DEFAULT 'all',
            CONSTRAINT uq_prc_project_role UNIQUE (project_id, role_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_prc_project_id ON project_role_constraints(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prc_role_id ON project_role_constraints(role_id)")

    # ── 13. project_category_configs ──────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_category_configs (
            id                SERIAL PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            category_id       INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            min_proficiency   FLOAT NOT NULL DEFAULT 0.0,
            allowed_role_ids  JSONB,
            CONSTRAINT uq_pcc_project_category UNIQUE (project_id, category_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pcc_project_id ON project_category_configs(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pcc_category_id ON project_category_configs(category_id)")


def downgrade() -> None:
    """Best-effort downgrade. Data loss is expected."""
    op.execute("DROP TABLE IF EXISTS project_category_configs")
    op.execute("DROP TABLE IF EXISTS project_role_constraints")
    op.execute("ALTER TABLE worker_skill_profiles DROP COLUMN IF EXISTS nlp_ticket_count")
    op.execute("ALTER TABLE worker_skill_profiles DROP COLUMN IF EXISTS nlp_embedding")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS created_by_id")

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE team_member_role AS ENUM ('manager', 'member');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(120) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_members (
            team_id   INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role      team_member_role NOT NULL DEFAULT 'member',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (team_id, user_id)
        )
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE project_member_role AS ENUM ('owner', 'admin', 'member', 'viewer');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute("ALTER TABLE project_members ADD COLUMN IF NOT EXISTS role project_member_role")
    op.execute("UPDATE project_members SET role = 'viewer' WHERE role IS NULL")
    op.execute("ALTER TABLE project_members ALTER COLUMN role SET NOT NULL")
    op.execute("ALTER TABLE project_members DROP COLUMN IF EXISTS role_id")

    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false")
    op.execute(
        """
        UPDATE users u
        SET is_admin = true
        FROM user_org_roles uor
        JOIN roles r ON r.id = uor.role_id
        WHERE u.id = uor.user_id AND r.name IN ('admin', 'root_user')
        """
    )

    op.execute("DROP TABLE IF EXISTS user_org_roles")
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TYPE IF EXISTS role_scope")


def _sqlstr(s: str) -> str:
    """Single-quote a string literal for inline SQL, escaping embedded quotes."""
    if s is None:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"
