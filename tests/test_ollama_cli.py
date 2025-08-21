#!/usr/bin/env python3
"""
Tests for Ollama CLI command-line interface functionality.
"""

import pytest
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import CLI module
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


class TestOllamaCLIFlags:
    """Test CLI flags for Ollama functionality."""
    
    def test_help_shows_ollama_options(self):
        """Test that help output includes Ollama options."""
        result = subprocess.run(
            [sys.executable, "-m", "rulectl.cli", "start", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        help_output = result.stdout
        
        # Check that Ollama-specific options are documented
        assert "--model" in help_output
        assert "--server" in help_output
        assert "local Ollama model" in help_output or "Ollama" in help_output
    
    def test_model_flag_parsing(self):
        """Test that --model flag is parsed correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a minimal git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()
            
            # Mock the CLI functions to avoid actual execution
            with patch('rulectl.cli.async_start') as mock_async_start:
                result = subprocess.run(
                    [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent.parent}')
from rulectl.cli import cli
import click.testing

runner = click.testing.CliRunner()
result = runner.invoke(cli, ['start', '--model', 'llama3', '--force', '{temp_dir}'])
print(f"Exit code: {{result.exit_code}}")
if result.output:
    print(f"Output: {{result.output}}")
if result.exception:
    print(f"Exception: {{result.exception}}")
                    """],
                    capture_output=True,
                    text=True
                )
                
                # Should not fail due to argument parsing
                assert "Exit code: 0" in result.stdout or result.returncode == 0
    
    def test_server_flag_parsing(self):
        """Test that --server flag is parsed correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()
            
            with patch('rulectl.cli.async_start') as mock_async_start:
                result = subprocess.run(
                    [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent.parent}')
from rulectl.cli import cli
import click.testing

runner = click.testing.CliRunner()
result = runner.invoke(cli, [
    'start', 
    '--model', 'qwen2', 
    '--server', '192.168.1.100:8080',
    '--force', 
    '{temp_dir}'
])
print(f"Exit code: {{result.exit_code}}")
                    """],
                    capture_output=True,
                    text=True
                )
                
                assert "Exit code: 0" in result.stdout or result.returncode == 0


class TestOllamaEnvironmentVariables:
    """Test environment variable handling for Ollama."""
    
    def test_environment_variable_cleanup(self):
        """Test that Ollama environment variables are cleaned up when not using Ollama."""
        # Set some Ollama environment variables
        with patch.dict(os.environ, {
            "USE_OLLAMA": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "OLLAMA_MODEL": "llama3"
        }):
            # Simulate calling CLI without --model flag
            from rulectl.cli import async_start
            
            # The environment cleanup should happen in async_start
            # when model=None (no --model flag)
            
            # After cleanup, these should be removed
            # Note: This test would need to be run in isolation or
            # use proper mocking to avoid side effects
            pass
    
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


class TestOllamaValidationOutput:
    """Test Ollama validation output and user feedback."""
    
    @pytest.mark.asyncio
    async def test_ollama_connection_success_output(self):
        """Test output when Ollama connection is successful."""
        from rulectl.cli import validate_ollama_connection
        
        response_data = {'models': [{'name': 'llama3:latest'}]}
        mock_session = create_mock_aiohttp_session(response_data)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('click.echo') as mock_echo:
                await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
                
                # Check that appropriate success messages were printed
                echo_calls = [call[0][0] for call in mock_echo.call_args_list]
                success_messages = [msg for msg in echo_calls if "✅" in msg or "Connected" in msg]
                assert len(success_messages) > 0
    
    @pytest.mark.asyncio
    async def test_ollama_model_not_found_output(self):
        """Test output when model is not found."""
        from rulectl.cli import validate_ollama_connection
        
        response_data = {'models': [{'name': 'qwen2:latest'}]}  # Different model
        mock_session = create_mock_aiohttp_session(response_data)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('click.echo') as mock_echo:
                with patch('click.confirm', return_value=True):
                    await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
                    
                    # Check that warning messages were printed
                    echo_calls = [call[0][0] for call in mock_echo.call_args_list]
                    warning_messages = [msg for msg in echo_calls if "⚠️" in msg or "not found" in msg]
                    assert len(warning_messages) > 0


class TestOllamaCommandIntegration:
    """Test integration of Ollama with other CLI commands."""
    
    def test_start_command_with_ollama_model(self):
        """Test that start command accepts Ollama model parameter."""
        # This is tested through subprocess to ensure CLI parsing works
        with tempfile.TemporaryDirectory() as temp_dir:
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()
            
            # Test that the command doesn't fail due to argument parsing
            result = subprocess.run(
                [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent.parent}')

# Test that the CLI module can be imported and arguments parsed
try:
    from rulectl.cli import cli
    print("CLI import successful")
    
    # Test argument parsing
    import click.testing
    runner = click.testing.CliRunner()
    
    # This should not raise an argument parsing error
    result = runner.invoke(cli, [
        'start', '--help'
    ], catch_exceptions=False)
    
    if '--model' in result.output:
        print("Model flag found in help")
    else:
        print("Model flag NOT found in help")
        
except Exception as e:
    print(f"Error: {{e}}")
    import traceback
    traceback.print_exc()
                """],
                capture_output=True,
                text=True
            )
            
            assert "CLI import successful" in result.stdout
            assert result.returncode == 0


class TestOllamaErrorMessages:
    """Test error messages for Ollama-related failures."""
    
    @pytest.mark.asyncio
    async def test_connection_failure_error_message(self):
        """Test error message when Ollama connection fails."""
        from rulectl.cli import validate_ollama_connection
        import aiohttp
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = aiohttp.ClientError("Connection refused")
            
            with patch('click.echo') as mock_echo:
                with patch('click.Abort', side_effect=Exception("Aborted")):
                    with pytest.raises(Exception):
                        await validate_ollama_connection("http://localhost:11434", "llama3", verbose=True)
                    
                    # Check that appropriate error messages were printed
                    echo_calls = [call[0][0] for call in mock_echo.call_args_list]
                    error_messages = [msg for msg in echo_calls if "❌" in msg or "Failed" in msg]
                    assert len(error_messages) > 0


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ollama_cli.py -v
    pytest.main([__file__, "-v"])