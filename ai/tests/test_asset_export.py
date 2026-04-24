"""Integration tests for combined generate-and-save asset workflow."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from inference.server import app


def test_generate_and_save_block_assets(tmp_path: Path):
    client = TestClient(app)
    resp = client.post(
        "/api/assets/generate-and-save",
        json={
            "prompt": "copper block",
            "texture_prompt": "hammered copper",
            "size": 16,
            "model_type": "block",
            "output_dir": str(tmp_path),
            "namespace": "my_mod",
            "asset_name": "copper_machine",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    texture = Path(data["paths"]["texture"])
    model = Path(data["paths"]["model"])
    blockstate = Path(data["paths"]["blockstate"])

    assert texture.exists()
    assert model.exists()
    assert blockstate.exists()


def test_generate_and_save_item_assets(tmp_path: Path):
    client = TestClient(app)
    resp = client.post(
        "/api/assets/generate-and-save",
        json={
            "prompt": "crystal blade",
            "size": 16,
            "model_type": "item",
            "output_dir": str(tmp_path),
            "namespace": "my_mod",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["paths"]["blockstate"] is None
    assert Path(data["paths"]["texture"]).exists()
    assert Path(data["paths"]["model"]).exists()
