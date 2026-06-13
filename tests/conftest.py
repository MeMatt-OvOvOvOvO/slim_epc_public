"""Shared fixtures for all tests."""

import pytest
import epc.traffic as traffic_module
from epc.db import EPCRepository


@pytest.fixture
def repo(tmp_path):
    """Fresh in-file SQLite repo per test."""
    return EPCRepository(db_path=str(tmp_path / "test.db"))


@pytest.fixture(autouse=True)
def reset_traffic_manager():
    """Reset the global traffic_manager singleton before and after each test."""
    if traffic_module.traffic_manager:
        traffic_module.traffic_manager.stop_all()
    traffic_module.traffic_manager = None
    yield
    if traffic_module.traffic_manager:
        traffic_module.traffic_manager.stop_all()
    traffic_module.traffic_manager = None
