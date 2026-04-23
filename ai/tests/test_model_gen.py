"""AI module tests."""

import json

from model_gen.generator import generate_model


def test_generate_block_model():
    result = generate_model("cobblestone block", model_type="block")
    assert result["model_type"] == "block"
    assert "model_json" in result
    assert "cube_all" in result["model_json"]


def test_generate_column_block():
    result = generate_model("oak log column", model_type="block")
    assert "cube_column" in result["model_json"]


def test_generate_item_model():
    result = generate_model("diamond sword", model_type="item")
    assert result["model_type"] == "item"
    assert "handheld" in result["model_json"]


def test_generate_default_item():
    result = generate_model("ruby gem", model_type="item")
    assert "generated" in result["model_json"]


def test_generate_giraffe_block_has_elements():
    result = generate_model("giraffe statue block", model_type="block")
    assert "elements" in result["model_json"]


def test_generate_gun_block_has_elements():
    result = generate_model("steampunk gun block", model_type="block")
    assert "elements" in result["model_json"]


def test_generate_from_custom_model_corpus(tmp_path, monkeypatch):
    dataset = tmp_path / "models.jsonl"
    custom_completion = {
        "parent": "block/cube_all",
        "textures": {"all": "modid:blocks/custom_ore"},
    }
    row = {
        "prompt": "Generate a Minecraft block model for: custom ore",
        "model_type": "block",
        "completion": custom_completion,
    }
    dataset.write_text(json.dumps(row) + "\n", encoding="utf-8")

    monkeypatch.setenv("MODFORGE_MODEL_DATASET", str(dataset))
    result = generate_model("custom ore block", model_type="block")
    assert "custom_ore" in result["model_json"]
