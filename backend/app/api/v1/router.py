from fastapi import APIRouter

from app.api.v1.routers.admin import global_admin_router, router as admin_router
from app.api.v1.routers.assignment import router as assignment_router
from app.api.v1.routers.suggest import (
    skill_suggest_router,
    ticket_suggest_router,
)
from app.api.v1.routers.simulation import router as simulation_router
from app.api.v1.routers.tags import router as tags_router
from app.api.v1.routers.auth import router as auth_router, users_router
from app.api.v1.routers.categories import router as categories_router
from app.api.v1.routers.comments import router as comments_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.members import router as members_router
from app.api.v1.routers.project_settings import router as project_settings_router
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.rl_config import router as rl_config_router
from app.api.v1.routers.roles import router as roles_router
from app.api.v1.routers.sandbox import router as sandbox_router
from app.api.v1.routers.stages import router as stages_router
from app.api.v1.routers.tickets import router as tickets_router
from app.api.v1.routers.worker_profiles import router as worker_profiles_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(project_settings_router)
router.include_router(roles_router)
router.include_router(members_router)
router.include_router(stages_router)
router.include_router(tickets_router)
router.include_router(comments_router)
router.include_router(worker_profiles_router)
router.include_router(rl_config_router)
router.include_router(categories_router)
router.include_router(admin_router)
router.include_router(global_admin_router)
router.include_router(sandbox_router)
router.include_router(assignment_router)
router.include_router(simulation_router)
router.include_router(tags_router)
router.include_router(ticket_suggest_router)
router.include_router(skill_suggest_router)
