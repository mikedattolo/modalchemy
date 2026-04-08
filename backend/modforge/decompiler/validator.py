"""JAR validation — verify a file is a valid JAR and detect Forge mod metadata."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel


class JarInfo(BaseModel):
    """Metadata extracted from a mod JAR."""

    is_valid: bool
    has_classes: bool
    mod_loader: str  # "forge" | "unknown"
    minecraft_version: str  # "1.6.4" | "1.7.10" | "unknown"
    mod_id: str
    mod_name: str


def validate_jar(jar_path: Path) -> JarInfo:
    """Validate a JAR file and extract mod metadata.

    Raises HTTPException on invalid input.
    """
    if not jar_path.exists():
        raise HTTPException(status_code=400, detail="JAR file does not exist")

    if not zipfile.is_zipfile(jar_path):
        raise HTTPException(status_code=400, detail="File is not a valid JAR/ZIP")

    has_classes = False
    mod_loader = "unknown"
    minecraft_version = "unknown"
    mod_id = ""
    mod_name = ""

    with zipfile.ZipFile(jar_path, "r") as zf:
        names = zf.namelist()

        # Check for .class files
        has_classes = any(n.endswith(".class") for n in names)

        # Try to read mcmod.info (Forge 1.7.10 and some 1.6.4 mods)
        if "mcmod.info" in names:
            mod_loader = "forge"
            try:
                raw = zf.read("mcmod.info").decode("utf-8", errors="replace")
                info = json.loads(raw)
                # mcmod.info can be a list or dict with "modList"
                mod_list = info if isinstance(info, list) else info.get("modList", [])
                if mod_list:
                    first = mod_list[0]
                    mod_id = first.get("modid", "")
                    mod_name = first.get("name", "")
                    mc = first.get("mcversion", "")
                    if mc:
                        minecraft_version = mc
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        # Check for @Mod annotation in any class (heuristic via file listing)
        if mod_loader == "unknown":
            # If we see typical Forge package structure, assume Forge
            forge_indicators = [
                n
                for n in names
                if "cpw/mods/fml" in n or "net/minecraftforge" in n or "mcmod.info" in n
            ]
            if forge_indicators:
                mod_loader = "forge"

        # Heuristic for MC version based on Forge class paths
        if minecraft_version == "unknown":
            if any("cpw/mods/fml/common" in n for n in names):
                # cpw.mods.fml.common is the 1.6.4 / 1.7.10 era package
                minecraft_version = "1.7.10"  # default guess; could be 1.6.4

    if not has_classes:
        raise HTTPException(
            status_code=400,
            detail="JAR contains no .class files — is this a valid mod?",
        )

    return JarInfo(
        is_valid=True,
        has_classes=has_classes,
        mod_loader=mod_loader,
        minecraft_version=minecraft_version,
        mod_id=mod_id,
        mod_name=mod_name,
    )
