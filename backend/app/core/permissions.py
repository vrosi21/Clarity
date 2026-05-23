"""Single source of truth for permission strings.

Adding a new permission = add a constant here + update relevant built-in role
seeds in app/services/bootstrap.py. No other code changes required (Open/Closed).
"""
from __future__ import annotations


class Permission:
    # ── Org-level ──────────────────────────────────────────────────────────────
    ORG_MANAGE_USERS = "org:manage_users"
    ORG_READ_USERS = "org:read_users"
    ORG_MANAGE_ROLES = "org:manage_roles"
    ORG_MANAGE_SETTINGS = "org:manage_settings"

    # ── Projects ───────────────────────────────────────────────────────────────
    PROJECTS_CREATE = "projects:create"
    PROJECTS_READ = "projects:read"
    PROJECTS_UPDATE = "projects:update"
    PROJECTS_DELETE = "projects:delete"
    PROJECTS_MANAGE_MEMBERS = "projects:manage_members"
    PROJECTS_MANAGE_SETTINGS = "projects:manage_settings"

    # ── Stages ─────────────────────────────────────────────────────────────────
    STAGES_CREATE = "stages:create"
    STAGES_UPDATE = "stages:update"
    STAGES_DELETE = "stages:delete"
    STAGES_REORDER = "stages:reorder"

    # ── Tickets ────────────────────────────────────────────────────────────────
    TICKETS_CREATE = "tickets:create"
    TICKETS_READ = "tickets:read"
    TICKETS_UPDATE = "tickets:update"
    TICKETS_DELETE = "tickets:delete"
    TICKETS_MOVE = "tickets:move"
    TICKETS_ASSIGN = "tickets:assign"
    TICKETS_BE_ASSIGNED = "tickets:be_assigned"

    # ── Comments ───────────────────────────────────────────────────────────────
    COMMENTS_CREATE = "comments:create"
    COMMENTS_READ = "comments:read"
    COMMENTS_DELETE_OWN = "comments:delete_own"
    COMMENTS_DELETE_ANY = "comments:delete_any"

    # ── Categories ─────────────────────────────────────────────────────────────
    # Org-level. Governs creating and deleting global task categories.
    # Admins and org PMs hold this; project-scoped roles do not.
    CATEGORIES_MANAGE = "categories:manage"

    ALL: list[str] = [
        ORG_MANAGE_USERS, ORG_READ_USERS, ORG_MANAGE_ROLES, ORG_MANAGE_SETTINGS,
        PROJECTS_CREATE, PROJECTS_READ, PROJECTS_UPDATE, PROJECTS_DELETE,
        PROJECTS_MANAGE_MEMBERS, PROJECTS_MANAGE_SETTINGS,
        STAGES_CREATE, STAGES_UPDATE, STAGES_DELETE, STAGES_REORDER,
        TICKETS_CREATE, TICKETS_READ, TICKETS_UPDATE, TICKETS_DELETE,
        TICKETS_MOVE, TICKETS_ASSIGN, TICKETS_BE_ASSIGNED,
        COMMENTS_CREATE, COMMENTS_READ, COMMENTS_DELETE_OWN, COMMENTS_DELETE_ANY,
        CATEGORIES_MANAGE,
    ]
