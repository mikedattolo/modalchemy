"""Workspace browsing API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from modforge.config import settings

router = APIRouter(tags=["workspace"])


@router.get("/workspaces")
async def list_workspaces():
    """List all decompiled workspaces."""
    root = settings.workspace_dir
    if not root.exists():
        return []

    workspaces = []
    for ws_dir in sorted(root.iterdir()):
        if not ws_dir.is_dir():
            continue
        report_file = ws_dir / "report.json"
        meta: dict = {}
        if report_file.exists():
            meta = json.loads(report_file.read_text(encoding="utf-8"))
        workspaces.append(
            {
                "id": ws_dir.name,
                "jar_name": meta.get("jar_name", ws_dir.name),
                "created_at": meta.get("created_at", ""),
            }
        )
    return workspaces


@router.get("/workspaces/{workspace_id}/tree")
async def workspace_tree(workspace_id: str):
    """Return a recursive file tree for a workspace."""
    ws_path = _resolve_workspace(workspace_id)
    return _build_tree(ws_path, ws_path)


@router.get("/workspaces/{workspace_id}/file")
async def workspace_file(
    workspace_id: str,
    path: str = Query(..., description="Relative path inside the workspace"),
):
    """Return the text content of a file inside a workspace."""
    ws_path = _resolve_workspace(workspace_id)
    # Prevent path traversal
    file_path = (ws_path / path).resolve()
    if not str(file_path).startswith(str(ws_path.resolve())):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return PlainTextResponse(content)


def _resolve_workspace(workspace_id: str) -> Path:
    """Resolve and validate a workspace path."""
    # Sanitize: only allow simple directory names
    safe_id = Path(workspace_id).name
    ws_path = (settings.workspace_dir / safe_id).resolve()
    if not str(ws_path).startswith(str(settings.workspace_dir.resolve())):
        raise HTTPException(status_code=403, detail="Invalid workspace ID")
    if not ws_path.is_dir():
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws_path


def _build_tree(path: Path, root: Path) -> dict:
    """Recursively build a tree dict."""
    node: dict = {
        "name": path.name,
        "path": str(path.relative_to(root)),
        "is_dir": path.is_dir(),
    }
    if path.is_dir():
        children = []
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            children.append(_build_tree(child, root))
        node["children"] = children
    return node
