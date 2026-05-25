"""Pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add project root to path so 'services' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")

@pytest.fixture
def sample_kline_data():
    """Sample K-line data for testing."""
    return [
        {"date": "2024-01-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
        {"date": "2024-01-02", "open": 10.2, "high": 10.8, "low": 10.1, "close": 10.6, "volume": 1200000},
        {"date": "2024-01-03", "open": 10.6, "high": 11.0, "low": 10.5, "close": 10.8, "volume": 800000},
        {"date": "2024-01-04", "open": 10.8, "high": 11.2, "low": 10.7, "close": 11.0, "volume": 950000},
        {"date": "2024-01-05", "open": 11.0, "high": 11.5, "low": 10.9, "close": 10.5, "volume": 1100000},
    ]
