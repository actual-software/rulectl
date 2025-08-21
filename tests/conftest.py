#!/usr/bin/env python3
"""
Pytest configuration for Ollama tests.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables before and after each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Clean up Ollama-related environment variables before test
    ollama_vars = [
        "USE_OLLAMA",
        "OLLAMA_BASE_URL", 
        "OLLAMA_MODEL",
        "ANTHROPIC_API_KEY"
    ]
    
    for var in ollama_vars:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    
    # Create .git directory to simulate git repo
    git_dir = repo_path / ".git"
    git_dir.mkdir()
    
    # Create some sample files
    src_dir = repo_path / "src"
    src_dir.mkdir()
    
    (src_dir / "main.py").write_text("""
def main():
    print("Hello World")

if __name__ == "__main__":
    main()
    """)
    
    (src_dir / "utils.py").write_text("""
class Helper:
    def __init__(self):
        pass
    
    def process(self, data):
        return data.upper()
    """)
    
    return str(repo_path)


@pytest.fixture
def mock_ollama_server():
    """Mock Ollama server responses."""
    from unittest.mock import MagicMock, AsyncMock
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        'models': [
            {'name': 'llama3:latest'},
            {'name': 'qwen2:latest'},
            {'name': 'mistral:latest'}
        ]
    })
    
    return mock_response


@pytest.fixture
def ollama_environment():
    """Set up Ollama environment variables."""
    env_vars = {
        "USE_OLLAMA": "true",
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "OLLAMA_MODEL": "llama3"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


# Configure pytest to handle async tests
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add 'unit' marker to all tests by default
        if not any(marker.name in ['integration', 'unit'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)