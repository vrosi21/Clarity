from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.database import SessionLocal
from app.services.bootstrap import (
    ensure_builtin_roles,
    ensure_canonical_categories,
    ensure_root_user,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_canonical_categories(db)
        roles = ensure_builtin_roles(db)
        ensure_root_user(db, roles)
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="Clarity API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
