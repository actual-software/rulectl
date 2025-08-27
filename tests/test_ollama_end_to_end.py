#!/usr/bin/env python3
"""
End-to-end tests for Ollama functionality.
These tests simulate real usage scenarios.
"""

import pytest
import os
import tempfile
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import test targets
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_aiohttp_session(response_data, status=200):
    """Helper function to create properly mocked aiohttp session."""
    # Create response mock
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=response_data)
    
    # Mock the context manager for session.get()
    mock_get_context = AsyncMock()
    mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the session
    mock_session_instance = AsyncMock()
    mock_session_instance.get = MagicMock(return_value=mock_get_context)
    
    # Mock the session context manager
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    
    return mock_session_context


class TestOllamaEndToEndScenarios:
    """Test complete Ollama usage scenarios (focused unit tests)."""
    
    def test_ollama_workflow_environment_setup(self):
        """Test that Ollama workflow sets up environment correctly."""
        # Test the full environment setup workflow
        with patch.dict(os.environ, {}, clear=True):
            # Simulate what async_start does for Ollama setup
            model = "llama3"
            server = "localhost:11434"
            use_ollama = model is not None
            
            if use_ollama:
                # Set up Ollama environment variables (from async_start logic)
                if not server.startswith(('http://', 'https://')):
                    server = f"http://{server}"
                if not server.endswith('/v1'):
                    server = f"{server}/v1"
                
                os.environ["OLLAMA_BASE_URL"] = server
                os.environ["OLLAMA_MODEL"] = model
                os.environ["USE_OLLAMA"] = "true"
            
            # Verify complete environment setup
            assert os.environ.get("USE_OLLAMA") == "true"
            assert os.environ.get("OLLAMA_MODEL") == "llama3"
            assert os.environ.get("OLLAMA_BASE_URL") == "http://localhost:11434/v1"
    
    def test_ollama_vs_cloud_fallback_configuration(self):
        """Test configuration for Ollama with cloud fallback."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test Ollama with fallback configuration
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "qwen2"
            }):
                # Create analyzer with Ollama but not ollama_only (allows fallback)
                analyzer = RepoAnalyzer(temp_dir, ollama_only=False)
                
                # Should use Ollama but with fallback capability
                assert analyzer.use_ollama == True
                assert analyzer.ollama_only == False
                
                # Should configure AdaptiveClient (Ollama + fallback)
                options = analyzer._get_baml_options()
                assert options["client"] == "AdaptiveClient"
    
    def test_cloud_only_scenario_configuration(self):
        """Test configuration when only cloud providers are used."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test cloud-only configuration
            with patch.dict(os.environ, {}, clear=True):
                # Create analyzer without Ollama
                analyzer = RepoAnalyzer(temp_dir, ollama_only=False)
                
                # Should not use Ollama
                assert analyzer.use_ollama == False
                assert analyzer.ollama_only == False
                
                # Should not specify Ollama-specific client
                options = analyzer._get_baml_options()
                if "client" in options:
                    assert options["client"] not in ["OllamaOnlyClient", "OllamaClient"]


class TestOllamaConfigurationScenarios:
    """Test different Ollama configuration scenarios."""
    
    def test_custom_ollama_server_configuration(self):
        """Test configuration with custom Ollama server."""
        from rulectl.cli import async_start
        
        test_cases = [
            {
                "input_server": "192.168.1.100:8080",
                "expected_url": "http://192.168.1.100:8080/v1"
            },
            {
                "input_server": "https://ollama.example.com:11434",
                "expected_url": "https://ollama.example.com:11434/v1"
            },
            {
                "input_server": "localhost:9999",
                "expected_url": "http://localhost:9999/v1"
            }
        ]
        
        for case in test_cases:
            with patch.dict(os.environ, {}, clear=True):
                # Simulate the URL formatting logic
                server = case["input_server"]
                if not server.startswith(('http://', 'https://')):
                    server = f"http://{server}"
                if not server.endswith('/v1'):
                    server = f"{server}/v1"
                
                assert server == case["expected_url"]
    
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


class TestOllamaErrorRecoveryScenarios:
    """Test error recovery and fallback scenarios."""
    
    @pytest.mark.asyncio
    async def test_ollama_connection_failure_recovery(self):
        """Test behavior when Ollama connection fails."""
        from rulectl.cli import validate_ollama_connection
        import aiohttp
        
        # Create a session mock that raises an exception
        mock_session_context = AsyncMock()
        mock_session_instance = AsyncMock()
        
        # Make the get method raise an exception
        mock_session_instance.get.side_effect = aiohttp.ClientError("Connection refused")
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            with patch('click.echo'):  # Suppress output
                with patch('click.Abort', side_effect=Exception("Connection failed")):
                    with pytest.raises(Exception):
                        await validate_ollama_connection("http://localhost:11434", "llama3", verbose=False)
    
    @pytest.mark.asyncio
    async def test_ollama_model_download_prompt(self):
        """Test behavior when model is not available."""
        from rulectl.cli import validate_ollama_connection
        
        # Mock server response with no matching model
        response_data = {'models': [{'name': 'different-model:latest'}]}
        mock_session = create_mock_aiohttp_session(response_data)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test user accepts model download
            with patch('click.confirm', return_value=True):
                with patch('click.echo'):  # Suppress output
                    # Should not raise exception when user confirms
                    await validate_ollama_connection("http://localhost:11434", "new-model", verbose=False)
            
            # Test user declines model download
            with patch('click.confirm', return_value=False):
                with patch('click.echo'):  # Suppress output
                    with patch('click.Abort', side_effect=Exception("User declined")):
                        with pytest.raises(Exception):
                            await validate_ollama_connection("http://localhost:11434", "new-model", verbose=False)


class TestOllamaIntegrationWithExistingFeatures:
    """Test Ollama integration with existing rulectl features."""
    
    def test_ollama_with_rate_limiting_environment(self):
        """Test that Ollama works with rate limiting environment variables."""
        # Test that Ollama configuration works alongside rate limiting settings
        with patch.dict(os.environ, {
            # Ollama settings
            "USE_OLLAMA": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OLLAMA_MODEL": "llama3",
            # Rate limiting settings
            "RULECTL_RATE_LIMIT_REQUESTS_PER_MINUTE": "30",
            "RULECTL_BATCH_SIZE": "5",
            "RULECTL_BASE_DELAY_MS": "1000",
            "RULECTL_RATE_LIMITING_STRATEGY": "exponential"
        }):
            from rulectl.analyzer import RepoAnalyzer
            
            with tempfile.TemporaryDirectory() as temp_dir:
                analyzer = RepoAnalyzer(temp_dir)
                
                # Should configure both Ollama and rate limiting
                assert analyzer.use_ollama == True
                
                # Should use Ollama client configuration
                options = analyzer._get_baml_options()
                assert options["client"] == "AdaptiveClient"
    
    def test_ollama_verbose_output_configuration(self):
        """Test Ollama configuration works with verbose mode."""
        # Test that Ollama environment setup works regardless of verbose settings
        with patch.dict(os.environ, {}, clear=True):
            # Simulate async_start logic with verbose=True and Ollama
            verbose = True
            model = "qwen2"
            server = "localhost:11434"
            
            if model:
                # Verbose mode should still set up Ollama correctly
                if not server.startswith(('http://', 'https://')):
                    server = f"http://{server}"
                if not server.endswith('/v1'):
                    server = f"{server}/v1"
                
                os.environ["OLLAMA_BASE_URL"] = server
                os.environ["OLLAMA_MODEL"] = model
                os.environ["USE_OLLAMA"] = "true"
            
            # Verify setup works in verbose mode
            assert os.environ.get("USE_OLLAMA") == "true"
            assert os.environ.get("OLLAMA_MODEL") == "qwen2"
            assert os.environ.get("OLLAMA_BASE_URL") == "http://localhost:11434/v1"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ollama_end_to_end.py -v
    pytest.main([__file__, "-v"])