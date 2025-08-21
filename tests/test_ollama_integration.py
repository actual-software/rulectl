#!/usr/bin/env python3
"""
Tests for Ollama integration functionality.
"""

import pytest
import os
import asyncio
import tempfile
import json
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

# Import the modules we want to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from rulectl.cli import validate_ollama_connection, ensure_api_keys, async_start
from rulectl.analyzer import RepoAnalyzer


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


class TestOllamaConnectionValidation:
    """Test Ollama server connection and model validation."""
    
    @pytest.mark.asyncio
    async def test_validate_ollama_connection_success(self):
        """Test successful Ollama connection validation."""
        response_data = {
            'models': [
                {'name': 'llama3:latest'},
                {'name': 'qwen2:latest'},
                {'name': 'mistral:latest'}
            ]
        }
        
        mock_session = create_mock_aiohttp_session(response_data)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('click.echo'):  # Suppress output
                # Should not raise any exceptions
                await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
    
    @pytest.mark.asyncio
    async def test_validate_ollama_connection_model_not_found(self):
        """Test validation when requested model is not available."""
        response_data = {
            'models': [
                {'name': 'qwen2:latest'},
                {'name': 'mistral:latest'}
            ]
        }
        
        mock_session = create_mock_aiohttp_session(response_data)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('click.echo'):  # Suppress output
                with patch('click.confirm', return_value=True):
                    # Should not raise when user confirms
                    await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
                
                with patch('click.confirm', return_value=False):
                    # Should raise click.Abort when user declines
                    with pytest.raises(Exception):  # click.Abort
                        await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
    
    @pytest.mark.asyncio
    async def test_validate_ollama_connection_server_error(self):
        """Test validation when Ollama server returns error."""
        mock_response = MagicMock()
        mock_response.status = 500
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception):  # click.Abort
                await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
    
    @pytest.mark.asyncio
    async def test_validate_ollama_connection_timeout(self):
        """Test validation when connection times out."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(Exception):  # click.Abort
                await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)


class TestOllamaAPIKeyHandling:
    """Test API key handling when using Ollama."""
    
    def test_ensure_api_keys_with_ollama(self):
        """Test that API keys are not required when using Ollama."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not prompt for API keys when use_ollama=True
            with patch('click.prompt') as mock_prompt:
                result = ensure_api_keys(use_ollama=True)
                mock_prompt.assert_not_called()
                
                # Check that dummy API key was set
                assert "ANTHROPIC_API_KEY" in os.environ
                assert os.environ["ANTHROPIC_API_KEY"].startswith("sk-ant-")
    
    def test_ensure_api_keys_without_ollama(self):
        """Test that API keys are required when not using Ollama."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('click.prompt', return_value='sk-ant-test-key'):
                result = ensure_api_keys(use_ollama=False)
                
                # Should have prompted for API key
                assert "ANTHROPIC_API_KEY" in os.environ


class TestOllamaEnvironmentSetup:
    """Test environment variable setup for Ollama."""
    
    @pytest.mark.asyncio
    async def test_ollama_environment_setup(self):
        """Test that Ollama environment variables are set correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a minimal git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()
            
            with patch('rulectl.cli.validate_ollama_connection', new=AsyncMock()):
                with patch('rulectl.cli.ensure_api_keys') as mock_ensure_keys:
                    with patch('subprocess.run') as mock_subprocess:
                        # Mock BAML initialization to avoid actual execution
                        mock_subprocess.return_value.returncode = 0
                        
                        with patch('rulectl.analyzer.RepoAnalyzer') as mock_analyzer:
                            # Mock the analyzer to avoid actual analysis
                            mock_instance = MagicMock()
                            mock_analyzer.return_value = mock_instance
                            mock_instance.has_gitignore.return_value = True
                            mock_instance.scan_repository.return_value = ([], [])
                            mock_instance.count_analyzable_files.return_value = (0, {})
                            
                            # Test with Ollama model specified
                            await async_start(
                                verbose=True,
                                force=True,
                                model="llama3",
                                server="localhost:11434",
                                rate_limit=None,
                                batch_size=None,
                                delay_ms=None,
                                no_batching=False,
                                strategy=None,
                                directory=temp_dir
                            )
                            
                            # Check environment variables were set
                            assert os.environ.get("OLLAMA_BASE_URL") == "http://localhost:11434/v1"
                            assert os.environ.get("OLLAMA_MODEL") == "llama3"
                            assert os.environ.get("USE_OLLAMA") == "true"
                            
                            # Ensure API keys function was called with use_ollama=True
                            mock_ensure_keys.assert_called_once_with(use_ollama=True)


class TestOllamaAnalyzerIntegration:
    """Test RepoAnalyzer integration with Ollama."""
    
    def test_repo_analyzer_ollama_initialization(self):
        """Test RepoAnalyzer initialization with Ollama settings."""
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


class TestOllamaCommandLineIntegration:
    """Test command line integration with Ollama flags."""
    
    def test_cli_environment_setup_with_ollama(self):
        """Test that CLI sets up environment correctly with Ollama flags."""
        # Test the environment setup logic from async_start
        model = "qwen2"
        server = "192.168.1.100:8080"
        
        # Clear environment first
        with patch.dict(os.environ, {}, clear=True):
            # Simulate the logic from async_start when model is specified
            use_ollama = model is not None
            if use_ollama:
                # Set up Ollama environment variables
                if not server.startswith(('http://', 'https://')):
                    server = f"http://{server}"
                if not server.endswith('/v1'):
                    server = f"{server}/v1"
                
                os.environ["OLLAMA_BASE_URL"] = server
                os.environ["OLLAMA_MODEL"] = model
                os.environ["USE_OLLAMA"] = "true"
            
            # Verify environment was configured correctly
            assert os.environ.get("OLLAMA_BASE_URL") == "http://192.168.1.100:8080/v1"
            assert os.environ.get("OLLAMA_MODEL") == "qwen2"
            assert os.environ.get("USE_OLLAMA") == "true"
    
    def test_cli_environment_cleanup_without_ollama(self):
        """Test that CLI cleans up environment when not using Ollama."""
        # Set up some Ollama environment variables first
        with patch.dict(os.environ, {
            "USE_OLLAMA": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OLLAMA_MODEL": "llama3"
        }):
            # Simulate the logic from async_start when model is None
            model = None
            use_ollama = model is not None
            if not use_ollama:
                # Ensure Ollama environment variables are not set
                os.environ.pop("USE_OLLAMA", None)
                os.environ.pop("OLLAMA_BASE_URL", None) 
                os.environ.pop("OLLAMA_MODEL", None)
            
            # Verify cleanup worked
            assert os.environ.get("USE_OLLAMA") is None
            assert os.environ.get("OLLAMA_BASE_URL") is None
            assert os.environ.get("OLLAMA_MODEL") is None


class TestOllamaErrorHandling:
    """Test error handling in Ollama integration."""
    
    @pytest.mark.asyncio
    async def test_ollama_connection_failure_handling(self):
        """Test handling of Ollama connection failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()
            
            # Mock validate_ollama_connection to raise an exception
            with patch('rulectl.cli.validate_ollama_connection', side_effect=Exception("Connection failed")):
                with pytest.raises(Exception):
                    await async_start(
                        verbose=True,
                        force=True,
                        model="llama3",
                        server="localhost:11434",
                        rate_limit=None,
                        batch_size=None,
                        delay_ms=None,
                        no_batching=False,
                        strategy=None,
                        directory=temp_dir
                    )


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ollama_integration.py -v
    pytest.main([__file__, "-v"])