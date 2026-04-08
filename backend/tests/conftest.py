"""Backend test configuration."""

import pytest


@pytest.fixture
def fixtures_dir():
    """Path to the test fixtures directory."""
    from pathlib import Path

    return Path(__file__).parent / "fixtures"
