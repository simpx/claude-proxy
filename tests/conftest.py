"""
Shared test configuration and fixtures.
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment from project root .env file
project_env_file = project_root / ".env"
if project_env_file.exists():
    load_dotenv(project_env_file)


def pytest_configure():
    """Configure pytest with custom markers."""
    pass


def pytest_collection_modifyitems(items):
    """Add integration marker to tests in integration directory."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Check if we have required environment variables for integration tests
    # Only show warning for integration tests that will actually run
    yield