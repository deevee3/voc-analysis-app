"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture
def anyio_backend():
    """Configure async test backend."""
    return "asyncio"
