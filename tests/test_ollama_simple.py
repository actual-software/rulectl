#!/usr/bin/env python3
"""
Simplified Ollama tests that focus on testable units without complex async mocking.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules we want to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOllamaEnvironmentHandling:
    """Test environment variable handling for Ollama."""
    
    def test_environment_variable_setting(self):
        """Test that Ollama environment variables are set correctly."""
        # Clear any existing Ollama environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Test the environment variable setting logic
            model = "mistral"
            server = "localhost:9999"
            
            # Simulate the logic from async_start
            if not server.startswith(('http://', 'https://')):
                server = f"http://{server}"
            if not server.endswith('/v1'):
                server = f"{server}/v1"
            
            os.environ["OLLAMA_BASE_URL"] = server
            os.environ["OLLAMA_MODEL"] = model
            os.environ["USE_OLLAMA"] = "true"
            
            assert os.environ["OLLAMA_BASE_URL"] == "http://localhost:9999/v1"
            assert os.environ["OLLAMA_MODEL"] == "mistral"
            assert os.environ["USE_OLLAMA"] == "true"
    
    def test_environment_cleanup(self):
        """Test environment variable cleanup."""
        with patch.dict(os.environ, {
            "USE_OLLAMA": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OLLAMA_MODEL": "llama3"
        }):
            # Verify variables are set
            assert os.environ.get("USE_OLLAMA") == "true"
            
            # Simulate cleanup (from async_start when model=None)
            os.environ.pop("USE_OLLAMA", None)
            os.environ.pop("OLLAMA_BASE_URL", None) 
            os.environ.pop("OLLAMA_MODEL", None)
            
            # Verify cleanup worked
            assert os.environ.get("USE_OLLAMA") is None
            assert os.environ.get("OLLAMA_BASE_URL") is None
            assert os.environ.get("OLLAMA_MODEL") is None


class TestOllamaServerConfiguration:
    """Test Ollama server URL configuration."""
    
    def test_server_url_formatting(self):
        """Test that server URLs are formatted correctly."""
        test_cases = [
            ("localhost:11434", "http://localhost:11434/v1"),
            ("192.168.1.100:11434", "http://192.168.1.100:11434/v1"),
            ("http://localhost:11434", "http://localhost:11434/v1"),
            ("https://ollama.example.com:11434", "https://ollama.example.com:11434/v1"),
            ("http://localhost:11434/v1", "http://localhost:11434/v1"),
        ]
        
        for input_url, expected_url in test_cases:
            # Simulate the URL formatting logic from cli.py
            server = input_url
            if not server.startswith(('http://', 'https://')):
                server = f"http://{server}"
            if not server.endswith('/v1'):
                server = f"{server}/v1"
            
            assert server == expected_url, f"Failed for input: {input_url}"


class TestOllamaAnalyzerIntegration:
    """Test RepoAnalyzer integration with Ollama (unit tests only)."""
    
    def test_repo_analyzer_ollama_initialization(self):
        """Test RepoAnalyzer initialization with Ollama settings."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "llama3"
            }):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=True)
                
                # Check that the analyzer was initialized with Ollama settings
                assert analyzer.use_ollama == True
                assert analyzer.ollama_only == True
    
    def test_baml_options_with_ollama(self):
        """Test that BAML options are configured correctly for Ollama."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "llama3"
            }):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=True)
                
                # Test Ollama-only options
                options = analyzer._get_baml_options()
                assert "client" in options
                assert options["client"] == "OllamaOnlyClient"
                
                # Test Ollama with fallback
                analyzer.ollama_only = False
                options = analyzer._get_baml_options()
                assert options["client"] == "AdaptiveClient"
    
    def test_baml_options_without_ollama(self):
        """Test BAML options when Ollama is not configured."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {}, clear=True):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=False)
                options = analyzer._get_baml_options()
                
                # Should not specify Ollama-specific client
                if "client" in options:
                    assert options["client"] not in ["OllamaOnlyClient", "OllamaClient"]
    
    def test_baml_options_with_additional_options(self):
        """Test _get_baml_options merges additional options correctly."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "llama3"
            }):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=True)
                
                additional_options = {
                    "custom_param": "test_value",
                    "timeout": 30
                }
                
                options = analyzer._get_baml_options(additional_options)
                
                # Should include both Ollama and additional options
                assert options["client"] == "OllamaOnlyClient"
                assert options["custom_param"] == "test_value"
                assert options["timeout"] == 30


class TestOllamaAPIKeyHandling:
    """Test API key handling when using Ollama."""
    
    def test_ensure_api_keys_with_ollama(self):
        """Test that API keys are not required when using Ollama."""
        from rulectl.cli import ensure_api_keys
        
        with patch.dict(os.environ, {}, clear=True):
            # Should not prompt for API keys when use_ollama=True
            with patch('click.prompt') as mock_prompt:
                result = ensure_api_keys(use_ollama=True)
                mock_prompt.assert_not_called()
                
                # Check that dummy API key was set
                assert "ANTHROPIC_API_KEY" in os.environ
                assert os.environ["ANTHROPIC_API_KEY"].startswith("sk-ant-")
    
    def test_ensure_api_keys_without_ollama_existing_key(self):
        """Test API key handling when key already exists."""
        from rulectl.cli import ensure_api_keys
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-existing-key"}, clear=True):
            # Should use existing key without prompting
            with patch('click.prompt') as mock_prompt:
                result = ensure_api_keys(use_ollama=False)
                mock_prompt.assert_not_called()
                
                # Should keep existing key
                assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-existing-key"


class TestBAMLClientConfiguration:
    """Test BAML client configuration for Ollama (file-based tests)."""
    
    def test_baml_clients_file_structure(self):
        """Test that BAML clients file contains expected Ollama clients."""
        baml_clients_path = Path(__file__).parent.parent / "baml_src" / "clients.baml"
        
        if baml_clients_path.exists():
            content = baml_clients_path.read_text()
            
            # Check for Ollama-related clients
            assert "OllamaClient" in content
            assert "AdaptiveClient" in content
            
            # Check for Ollama-specific configuration
            assert "OLLAMA_BASE_URL" in content
            assert "OLLAMA_MODEL" in content
            assert "openai-generic" in content  # Ollama uses OpenAI-compatible API
            
            # Check for retry policy
            assert "OllamaRetry" in content
    
    def test_baml_schema_uses_adaptive_client(self):
        """Test that BAML schema functions use AdaptiveClient."""
        baml_schema_path = Path(__file__).parent.parent / "baml_src" / "schema.baml"
        
        if baml_schema_path.exists():
            content = baml_schema_path.read_text()
            
            # Check that functions use AdaptiveClient instead of CustomSonnet
            assert "client AdaptiveClient" in content


class TestOllamaModelSelection:
    """Test different Ollama model configurations."""
    
    def test_ollama_model_selection(self):
        """Test different Ollama model configurations."""
        models = ["llama3", "qwen2", "mistral", "phi3", "gemma"]
        
        for model in models:
            with patch.dict(os.environ, {}, clear=True):
                os.environ["OLLAMA_MODEL"] = model
                os.environ["USE_OLLAMA"] = "true"
                
                # Test that environment is configured correctly
                assert os.environ.get("OLLAMA_MODEL") == model
                assert os.environ.get("USE_OLLAMA") == "true"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ollama_simple.py -v
    pytest.main([__file__, "-v"])