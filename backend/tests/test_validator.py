"""Tests for JAR validation."""

import zipfile
from pathlib import Path

import pytest

from modforge.decompiler.validator import validate_jar


def _make_jar(tmp_path: Path, files: dict[str, bytes], name: str = "test.jar") -> Path:
    """Helper to create a minimal JAR for testing."""
    jar_path = tmp_path / name
    with zipfile.ZipFile(jar_path, "w") as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)
    return jar_path


def test_validate_valid_jar_with_classes(tmp_path):
    jar = _make_jar(tmp_path, {"com/example/Mod.class": b"\xca\xfe\xba\xbe"})
    info = validate_jar(jar)
    assert info.is_valid
    assert info.has_classes


def test_validate_jar_with_mcmod_info(tmp_path):
    import json

    mcmod = json.dumps(
        [{"modid": "testmod", "name": "Test Mod", "mcversion": "1.7.10"}]
    )
    jar = _make_jar(
        tmp_path,
        {
            "com/example/Mod.class": b"\xca\xfe\xba\xbe",
            "mcmod.info": mcmod.encode(),
        },
    )
    info = validate_jar(jar)
    assert info.mod_loader == "forge"
    assert info.minecraft_version == "1.7.10"
    assert info.mod_id == "testmod"
    assert info.mod_name == "Test Mod"


def test_validate_rejects_non_zip(tmp_path):
    bad = tmp_path / "bad.jar"
    bad.write_bytes(b"this is not a zip")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        validate_jar(bad)
    assert exc_info.value.status_code == 400


def test_validate_rejects_no_classes(tmp_path):
    jar = _make_jar(tmp_path, {"readme.txt": b"hello"})
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        validate_jar(jar)
    assert exc_info.value.status_code == 400
    assert "class" in exc_info.value.detail.lower()
