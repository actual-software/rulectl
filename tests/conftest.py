#!/usr/bin/env python3
"""
Pytest configuration and fixtures for all tests.
"""

import sys
from unittest.mock import Mock, MagicMock

# Mock the baml_client module before any imports
sys.modules['baml_client'] = Mock()
sys.modules['baml_client.async_client'] = Mock()
sys.modules['baml_client.types'] = Mock()

# Create mock classes for BAML types
mock_types = sys.modules['baml_client.types']
mock_types.FileInfo = Mock
mock_types.StaticAnalysisResult = Mock
mock_types.RuleCandidate = Mock
mock_types.StaticAnalysisRule = Mock
mock_types.RuleCategory = Mock

# Create mock BAML client
mock_client = sys.modules['baml_client.async_client']
mock_client.b = MagicMock()

# Mock the pathspec module if not available
try:
    import pathspec
except ImportError:
    sys.modules['pathspec'] = Mock()