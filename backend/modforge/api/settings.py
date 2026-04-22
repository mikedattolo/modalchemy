"""Settings API — read/write app settings."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from modforge.config import resolve_project_path, settings

router = APIRouter(tags=["settings"])


class SettingsResponse(BaseModel):
    backend_port: int
    ai_port: int
    workspace_dir: str
    decompiler: str
    java_path: str
    theme: str = "dark"
    auto_decompile: bool


class SettingsUpdate(BaseModel):
    backend_port: int | None = None
    ai_port: int | None = None
    workspace_dir: str | None = None
    decompiler: str | None = None
    java_path: str | None = None
    theme: str | None = None
    auto_decompile: bool | None = None


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    return SettingsResponse(
        backend_port=settings.port,
        ai_port=settings.ai_port,
        workspace_dir=str(settings.workspace_dir),
        decompiler=settings.decompiler,
        java_path=settings.java_path,
        auto_decompile=settings.auto_decompile,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate):
    # In a production app this would persist to a config file.
    # For the scaffold we just update the in-memory settings.
    if body.decompiler is not None:
        settings.decompiler = body.decompiler
    if body.java_path is not None:
        settings.java_path = body.java_path
    if body.auto_decompile is not None:
        settings.auto_decompile = body.auto_decompile
    if body.workspace_dir is not None:
        settings.workspace_dir = resolve_project_path(body.workspace_dir)
    if body.ai_port is not None:
        settings.ai_port = body.ai_port

    return await get_settings()
