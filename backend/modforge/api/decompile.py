"""Decompile API — upload a JAR, get a decompiled workspace."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from modforge.config import settings
from modforge.decompiler.pipeline import DecompilePipeline

router = APIRouter(tags=["decompile"])

MAX_SIZE = settings.max_jar_size_mb * 1024 * 1024


@router.post("/decompile")
async def decompile_jar(file: UploadFile):
    """Accept a mod JAR, validate, extract, decompile, and return a report."""
    if not file.filename or not file.filename.endswith(".jar"):
        raise HTTPException(status_code=400, detail="File must be a .jar")

    # Save upload to a temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jar")
    try:
        size = 0
        while chunk := await file.read(1024 * 64):
            size += len(chunk)
            if size > MAX_SIZE:
                raise HTTPException(status_code=413, detail="JAR exceeds size limit")
            tmp.write(chunk)
        tmp.close()

        pipeline = DecompilePipeline(
            jar_path=Path(tmp.name),
            jar_name=file.filename,
            workspace_root=settings.workspace_dir,
            decompiler=settings.decompiler,
            java_path=settings.java_path,
            tools_dir=settings.tools_dir,
        )
        report = pipeline.run()
        return report.model_dump()
    finally:
        Path(tmp.name).unlink(missing_ok=True)
