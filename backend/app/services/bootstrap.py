"""Bootstrap helpers — idempotent setup of defaults.

* Per-project: default stages (BACKLOG / TODO / IN_PROGRESS / REVIEW / DONE)
  with proper FSM types, and a default RLProjectConfig row.
* Global: canonical categories, built-in roles, root user.

These functions never raise on existing data. Called from main.py lifespan.
The migration also seeds roles + root user, but these are kept as a runtime
safety net (idempotent) for dev DBs and re-seeded permission sets after
adding new built-in roles.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Permission
from app.core.security import hash_password
from app.ml.simulation.worker import CANONICAL_CATEGORIES
from app.models.category import Category
from app.models.enums import RoleScope, StageType
from app.models.rl_project_config import RLProjectConfig
from app.models.role import Role
from app.models.stage import Stage
from app.models.tag import Tag
from app.models.user import User
from app.models.user_org_role import UserOrgRole

log = logging.getLogger(__name__)


# (name, order, type, color)
DEFAULT_STAGE_TEMPLATE: tuple[tuple[str, int, StageType, str], ...] = (
    ("Backlog", 0, StageType.START, "#94a3b8"),
    ("To Do", 1, StageType.NORMAL, "#3b82f6"),
    ("In Progress", 2, StageType.NORMAL, "#f59e0b"),
    ("In Review", 3, StageType.NORMAL, "#a855f7"),
    ("Done", 4, StageType.FINAL, "#22c55e"),
)


P = Permission

ADMIN_PERMS = [p for p in P.ALL if p != P.ORG_MANAGE_SETTINGS]
ORG_PM_PERMS = [
    P.ORG_READ_USERS,
    P.PROJECTS_CREATE, P.PROJECTS_READ, P.PROJECTS_UPDATE, P.PROJECTS_DELETE,
    P.PROJECTS_MANAGE_MEMBERS, P.PROJECTS_MANAGE_SETTINGS,
    P.STAGES_CREATE, P.STAGES_UPDATE, P.STAGES_DELETE, P.STAGES_REORDER,
    P.TICKETS_CREATE, P.TICKETS_READ, P.TICKETS_UPDATE, P.TICKETS_DELETE,
    P.TICKETS_MOVE, P.TICKETS_ASSIGN,
    P.COMMENTS_CREATE, P.COMMENTS_READ, P.COMMENTS_DELETE_OWN, P.COMMENTS_DELETE_ANY,
    P.CATEGORIES_MANAGE,
]
ORG_MEMBER_PERMS = [P.PROJECTS_READ, P.TICKETS_READ, P.COMMENTS_READ]
PROJECT_PM_PERMS = [
    P.PROJECTS_READ, P.PROJECTS_UPDATE,
    P.PROJECTS_MANAGE_MEMBERS, P.PROJECTS_MANAGE_SETTINGS,
    P.STAGES_CREATE, P.STAGES_UPDATE, P.STAGES_DELETE, P.STAGES_REORDER,
    P.TICKETS_CREATE, P.TICKETS_READ, P.TICKETS_UPDATE, P.TICKETS_DELETE,
    P.TICKETS_MOVE, P.TICKETS_ASSIGN,
    P.COMMENTS_CREATE, P.COMMENTS_READ, P.COMMENTS_DELETE_OWN, P.COMMENTS_DELETE_ANY,
]
CONTRIBUTOR_PERMS = [
    P.PROJECTS_READ,
    P.TICKETS_CREATE, P.TICKETS_READ, P.TICKETS_UPDATE, P.TICKETS_MOVE, P.TICKETS_BE_ASSIGNED,
    P.COMMENTS_CREATE, P.COMMENTS_READ, P.COMMENTS_DELETE_OWN,
]
WORKER_PERMS = [
    P.PROJECTS_READ,
    P.TICKETS_READ, P.TICKETS_UPDATE, P.TICKETS_MOVE, P.TICKETS_BE_ASSIGNED,
    P.COMMENTS_CREATE, P.COMMENTS_READ, P.COMMENTS_DELETE_OWN,
]
COMMENTER_PERMS = [
    P.PROJECTS_READ, P.TICKETS_READ,
    P.COMMENTS_CREATE, P.COMMENTS_READ, P.COMMENTS_DELETE_OWN,
]
VIEWER_PERMS = [P.PROJECTS_READ, P.TICKETS_READ, P.COMMENTS_READ]


BUILTIN_ROLES: list[tuple[str, str, RoleScope, list[str]]] = [
    ("root_user",   "Full system access. Reserved for bootstrap.",    RoleScope.ORG,     list(P.ALL)),
    ("admin",       "Organisation administrator.",                    RoleScope.ORG,     ADMIN_PERMS),
    ("org_pm",      "Org-wide project manager.",                      RoleScope.ORG,     ORG_PM_PERMS),
    ("member",      "Default org member with read access.",           RoleScope.ORG,     ORG_MEMBER_PERMS),
    ("project_pm",  "Project manager for a single project.",          RoleScope.PROJECT, PROJECT_PM_PERMS),
    ("contributor", "Standard contributor — creates and works on tickets.", RoleScope.PROJECT, CONTRIBUTOR_PERMS),
    ("worker",      "Worker — receives assignments, no creation.",    RoleScope.PROJECT, WORKER_PERMS),
    ("commenter",   "Comment-only collaborator.",                     RoleScope.PROJECT, COMMENTER_PERMS),
    ("viewer",      "Read-only viewer.",                              RoleScope.PROJECT, VIEWER_PERMS),
]


def ensure_default_stages(db: Session, project_id: int) -> list[Stage]:
    existing = db.query(Stage).filter(Stage.project_id == project_id).count()
    if existing > 0:
        return (
            db.query(Stage)
            .filter(Stage.project_id == project_id)
            .order_by(Stage.order.asc())
            .all()
        )
    created: list[Stage] = []
    for name, order, stage_type, color in DEFAULT_STAGE_TEMPLATE:
        stage = Stage(
            project_id=project_id,
            name=name,
            order=order,
            type=stage_type,
            color=color,
        )
        db.add(stage)
        created.append(stage)
    db.flush()
    return created


def ensure_default_rl_config(db: Session, project_id: int) -> RLProjectConfig:
    existing = (
        db.query(RLProjectConfig)
        .filter(RLProjectConfig.project_id == project_id)
        .one_or_none()
    )
    if existing is not None:
        return existing
    config = RLProjectConfig(project_id=project_id)
    db.add(config)
    db.flush()
    return config


SEED_TAGS: tuple[str, ...] = (
    "bug", "feature", "enhancement", "clarification needed",
    "blocked", "urgent", "tech-debt", "refactor",
    "question", "duplicate", "wont-fix", "good first issue",
)


def ensure_default_tags(db: Session) -> list[Tag]:
    """Seed the UX-tag vocabulary on first run. Idempotent."""
    existing_names = {t.name for t in db.query(Tag).all()}
    created: list[Tag] = []
    for name in SEED_TAGS:
        if name in existing_names:
            continue
        tag = Tag(name=name)
        db.add(tag)
        created.append(tag)
    if created:
        db.flush()
    return created


def ensure_canonical_categories(db: Session) -> list[Category]:
    existing_names = {c.name for c in db.query(Category).all()}
    created: list[Category] = []
    for name in CANONICAL_CATEGORIES:
        if name in existing_names:
            continue
        cat = Category(name=name, description=f"Default {name} category")
        db.add(cat)
        created.append(cat)
    if created:
        db.flush()
    return created


def ensure_builtin_roles(db: Session) -> dict[str, Role]:
    """Upsert built-in roles. Returns name → Role mapping."""
    existing = {r.name: r for r in db.execute(select(Role)).scalars().all()}
    out: dict[str, Role] = {}
    for name, desc, scope, perms in BUILTIN_ROLES:
        role = existing.get(name)
        if role is None:
            role = Role(
                name=name, description=desc, scope=scope,
                is_builtin=True, permissions=list(perms),
            )
            db.add(role)
        else:
            # Refresh permission list + flags for builtins so deployments
            # automatically pick up new permissions.
            role.description = desc
            role.scope = scope
            role.is_builtin = True
            role.permissions = list(perms)
        out[name] = role
    db.flush()
    return out


def ensure_root_user(db: Session, roles: dict[str, Role]) -> User:
    """Create + assign root_user org role if no root exists. Idempotent."""
    root_email = os.environ.get("ROOT_EMAIL", "root@example.com")
    root_password = os.environ.get("ROOT_PASSWORD", "ChangeMe123!")

    if root_password == "ChangeMe123!":
        log.warning(
            "ROOT_PASSWORD is set to the default 'ChangeMe123!' — change it in env."
        )

    user = db.execute(select(User).where(User.email == root_email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=root_email,
            username="root",
            full_name="Root User",
            years_experience=0,
            hashed_password=hash_password(root_password),
            is_active=True,
        )
        db.add(user)
        db.flush()

    root_role = roles.get("root_user")
    if root_role is None:
        return user

    existing = db.execute(
        select(UserOrgRole).where(UserOrgRole.user_id == user.id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserOrgRole(user_id=user.id, role_id=root_role.id))
    elif existing.role_id != root_role.id:
        existing.role_id = root_role.id
    db.flush()
    return user
