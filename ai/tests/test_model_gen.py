"""AI module tests."""

from ai.model_gen.generator import generate_model


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
