"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modforge.api.decompile import router as decompile_router
from modforge.api.workspace import router as workspace_router
from modforge.api.settings import router as settings_router

app = FastAPI(
    title="ModForge Backend",
    version="0.1.0",
    description="Decompile Minecraft Forge mod JARs and manage workspaces.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:5173", "https://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decompile_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
