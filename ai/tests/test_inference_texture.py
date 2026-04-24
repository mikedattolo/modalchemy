"""Tests for fallback texture generation logic used by inference server."""

from inference.server import _placeholder_texture


def test_placeholder_texture_is_deterministic():
    a = _placeholder_texture(16, "emerald ore")
    b = _placeholder_texture(16, "emerald ore")
    assert a.tobytes() == b.tobytes()


def test_placeholder_texture_changes_with_prompt():
    a = _placeholder_texture(16, "oak planks")
    b = _placeholder_texture(16, "diamond ore")
    assert a.tobytes() != b.tobytes()


def test_placeholder_texture_respects_size():
    img = _placeholder_texture(32, "copper block")
    assert img.size == (32, 32)
