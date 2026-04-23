"""Mod library API.

Provides:
- Catalog search for Forge mods (1.6.4 / 1.7.10)
- One-click download and decompile into workspace
"""

from __future__ import annotations

import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from modforge.config import settings
from modforge.decompiler.pipeline import DecompilePipeline

router = APIRouter(tags=["library"])

ALLOWED_MC_VERSIONS = {"1.6.4", "1.7.10"}
MODRINTH_BASE = "https://api.modrinth.com/v2"


class LibraryImportRequest(BaseModel):
    project_id: str
    minecraft_version: str = "1.7.10"


@router.get("/library/catalog")
async def library_catalog(
    query: str = Query("", description="Search query"),
    minecraft_version: str = Query("1.7.10", description="Minecraft version (1.6.4/1.7.10)"),
    limit: int = Query(20, ge=1, le=50),
):
    """Search Modrinth catalog for Forge mods matching supported MC versions."""
    _validate_mc_version(minecraft_version)

    facets = [["project_type:mod"], ["categories:forge"], [f"versions:{minecraft_version}"]]
    params = {
        "query": query.strip(),
        "limit": str(limit),
        "index": "downloads",
        "facets": json.dumps(facets),
    }

    url = f"{MODRINTH_BASE}/search?{urllib.parse.urlencode(params)}"
    data = _http_get_json(url)

    hits = data.get("hits", []) if isinstance(data, dict) else []
    results = []
    for hit in hits:
        results.append(
            {
                "project_id": hit.get("project_id", ""),
                "slug": hit.get("slug", ""),
                "title": hit.get("title", ""),
                "description": hit.get("description", ""),
                "downloads": hit.get("downloads", 0),
                "author": hit.get("author", ""),
                "icon_url": hit.get("icon_url"),
                "latest_version": hit.get("latest_version"),
            }
        )

    return {
        "source": "modrinth",
        "minecraft_version": minecraft_version,
        "count": len(results),
        "results": results,
    }


@router.post("/library/import")
async def library_import(body: LibraryImportRequest):
    """Download selected mod JAR and run decompile pipeline."""
    _validate_mc_version(body.minecraft_version)

    version_obj = _fetch_modrinth_version(body.project_id, body.minecraft_version)
    file_obj = _pick_primary_file(version_obj)
    if file_obj is None:
        raise HTTPException(status_code=404, detail="No downloadable JAR file found for selected mod/version")

    file_url = str(file_obj.get("url", ""))
    filename = str(file_obj.get("filename", "mod.jar"))
    if not file_url:
        raise HTTPException(status_code=404, detail="Mod file URL missing from catalog response")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jar")
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        _download_file(file_url, tmp_path)

        pipeline = DecompilePipeline(
            jar_path=tmp_path,
            jar_name=filename,
            workspace_root=settings.workspace_dir,
            decompiler=settings.decompiler,
            java_path=settings.java_path,
            tools_dir=settings.tools_dir,
        )
        report = pipeline.run()
        return {
            "source": "modrinth",
            "project_id": body.project_id,
            "minecraft_version": body.minecraft_version,
            "download_url": file_url,
            "report": report.model_dump(),
        }
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except PermissionError:
            # Windows may still hold a transient lock briefly; non-fatal cleanup failure.
            pass


def _validate_mc_version(version: str) -> None:
    if version not in ALLOWED_MC_VERSIONS:
        raise HTTPException(status_code=400, detail="minecraft_version must be one of: 1.6.4, 1.7.10")


def _fetch_modrinth_version(project_id: str, minecraft_version: str) -> dict:
    params = {
        "loaders": json.dumps(["forge"]),
        "game_versions": json.dumps([minecraft_version]),
    }
    url = f"{MODRINTH_BASE}/project/{project_id}/version?{urllib.parse.urlencode(params)}"
    versions = _http_get_json(url)

    if not isinstance(versions, list) or not versions:
        raise HTTPException(status_code=404, detail="No compatible Forge version found for selected Minecraft version")

    # Modrinth returns newest first for this endpoint in practice.
    return versions[0]


def _pick_primary_file(version_obj: dict) -> dict | None:
    files = version_obj.get("files", []) if isinstance(version_obj, dict) else []
    if not isinstance(files, list):
        return None

    primary = None
    for file_obj in files:
        if not isinstance(file_obj, dict):
            continue
        filename = str(file_obj.get("filename", "")).lower()
        if not filename.endswith(".jar"):
            continue
        if bool(file_obj.get("primary", False)):
            return file_obj
        if primary is None:
            primary = file_obj

    return primary


def _download_file(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ModForge/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            target.write_bytes(resp.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to download mod file: {exc}") from exc


def _http_get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "ModForge/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return json.loads(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Catalog request failed: {exc}") from exc
