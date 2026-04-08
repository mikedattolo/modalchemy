"""Tests for the decompile pipeline."""

import json
import zipfile
from pathlib import Path

import pytest

from modforge.decompiler.pipeline import DecompilePipeline


def _make_mod_jar(tmp_path: Path) -> Path:
    """Create a minimal Forge mod JAR for testing."""
    jar_path = tmp_path / "testmod-1.0.jar"
    mcmod = json.dumps(
        [{"modid": "testmod", "name": "Test Mod", "mcversion": "1.7.10"}]
    )
    with zipfile.ZipFile(jar_path, "w") as zf:
        zf.writestr("com/example/TestMod.class", b"\xca\xfe\xba\xbe\x00\x00\x00\x34")
        zf.writestr("com/example/TestBlock.class", b"\xca\xfe\xba\xbe\x00\x00\x00\x34")
        zf.writestr("mcmod.info", mcmod)
        zf.writestr("assets/testmod/textures/blocks/test.png", b"\x89PNG\r\n\x1a\nfakeimage")
        zf.writestr("assets/testmod/lang/en_US.lang", b"tile.test.name=Test Block")
    return jar_path


def test_pipeline_extracts_resources(tmp_path):
    jar = _make_mod_jar(tmp_path)
    workspace_root = tmp_path / "workspaces"

    pipeline = DecompilePipeline(
        jar_path=jar,
        jar_name="testmod-1.0.jar",
        workspace_root=workspace_root,
        decompiler="cfr",  # CFR won't be available but extraction should work
    )
    report = pipeline.run()

    assert report.jar_name == "testmod-1.0.jar"
    assert report.mod_loader == "forge"
    assert report.minecraft_version == "1.7.10"
    assert report.resource_files >= 3  # mcmod.info + texture + lang

    # Check workspace structure
    ws = workspace_root / report.workspace_id
    assert ws.exists()
    assert (ws / "classes").exists()
    assert (ws / "resources").exists()
    assert (ws / "sources").exists()
    assert (ws / "report.json").exists()

    # Check resources were extracted
    assert (ws / "resources" / "mcmod.info").exists()
    assert (ws / "resources" / "assets" / "testmod" / "textures" / "blocks" / "test.png").exists()


def test_pipeline_handles_missing_cfr(tmp_path):
    jar = _make_mod_jar(tmp_path)
    workspace_root = tmp_path / "workspaces"

    pipeline = DecompilePipeline(
        jar_path=jar,
        jar_name="testmod-1.0.jar",
        workspace_root=workspace_root,
        decompiler="cfr",
        tools_dir=tmp_path / "no_tools",  # CFR won't exist here
    )
    report = pipeline.run()

    # Should still succeed but with 0 source files and an error
    assert report.source_files == 0
    assert any("CFR" in e or "cfr" in e.lower() for e in report.errors)
