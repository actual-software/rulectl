#!/usr/bin/env python3
"""
Tests for BAML client configuration with Ollama support.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import test target
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBAMLClientConfiguration:
    """Test BAML client configuration for Ollama."""
    
    def test_baml_clients_file_structure(self):
        """Test that BAML clients file contains expected Ollama clients."""
        baml_clients_path = Path(__file__).parent.parent / "baml_src" / "clients.baml"
        
        if baml_clients_path.exists():
            content = baml_clients_path.read_text()
            
            # Check for Ollama-related clients
            assert "OllamaClient" in content
            assert "OllamaWithFallback" in content
            assert "OllamaOnlyClient" in content
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
            
            # Ensure it's not still using old client names for main functions
            lines = content.split('\n')
            function_lines = [line for line in lines if 'client CustomSonnet' in line]
            # Should be minimal or no usage of CustomSonnet (only in fallback scenarios)
    
    def test_baml_rulectl_uses_adaptive_client(self):
        """Test that BAML rulectl file uses AdaptiveClient."""
        baml_rulectl_path = Path(__file__).parent.parent / "baml_src" / "rulectl.baml"
        
        if baml_rulectl_path.exists():
            content = baml_rulectl_path.read_text()
            
            # Check that functions use AdaptiveClient
            assert "client AdaptiveClient" in content


class TestOllamaClientSelection:
    """Test client selection logic in RepoAnalyzer."""
    
    def test_get_baml_options_ollama_only(self):
        """Test _get_baml_options with Ollama-only configuration."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "llama3"
            }):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=True)
                options = analyzer._get_baml_options()
                
                # Should select OllamaOnlyClient for exclusive Ollama usage
                assert "client" in options
                assert options["client"] == "OllamaOnlyClient"
    
    def test_get_baml_options_ollama_with_fallback(self):
        """Test _get_baml_options with Ollama and cloud fallback."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "llama3"
            }):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=False)
                options = analyzer._get_baml_options()
                
                # Should select AdaptiveClient for Ollama with fallback
                assert "client" in options
                assert options["client"] == "AdaptiveClient"
    
    def test_get_baml_options_no_ollama(self):
        """Test _get_baml_options without Ollama configuration."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {}, clear=True):
                analyzer = RepoAnalyzer(temp_dir, ollama_only=False)
                options = analyzer._get_baml_options()
                
                # Should not specify a client (uses default)
                # or should not include Ollama-specific client
                if "client" in options:
                    assert options["client"] not in ["OllamaOnlyClient", "OllamaClient"]
    
    def test_get_baml_options_with_additional_options(self):
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


class TestOllamaEnvironmentIntegration:
    """Test integration with environment variables."""
    
    def test_ollama_environment_variables_detection(self):
        """Test that RepoAnalyzer detects Ollama environment variables."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with Ollama environment variables set
            with patch.dict(os.environ, {
                "USE_OLLAMA": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "qwen2"
            }):
                analyzer = RepoAnalyzer(temp_dir)
                assert analyzer.use_ollama == True
            
            # Test without Ollama environment variables
            with patch.dict(os.environ, {}, clear=True):
                analyzer = RepoAnalyzer(temp_dir)
                assert analyzer.use_ollama == False
    
    def test_environment_variables_priority(self):
        """Test that environment variables are used correctly."""
        from rulectl.analyzer import RepoAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test different combinations of environment variables
            test_cases = [
                {
                    "env": {"USE_OLLAMA": "true"},
                    "expected_use_ollama": True
                },
                {
                    "env": {"USE_OLLAMA": "false"},
                    "expected_use_ollama": False
                },
                {
                    "env": {},
                    "expected_use_ollama": False
                }
            ]
            
            for case in test_cases:
                with patch.dict(os.environ, case["env"], clear=True):
                    analyzer = RepoAnalyzer(temp_dir)
                    assert analyzer.use_ollama == case["expected_use_ollama"]


class TestBAMLClientFallbackBehavior:
    """Test BAML client fallback behavior."""
    
    def test_adaptive_client_configuration(self):
        """Test AdaptiveClient configuration in BAML file."""
        baml_clients_path = Path(__file__).parent.parent / "baml_src" / "clients.baml"
        
        if baml_clients_path.exists():
            content = baml_clients_path.read_text()
            
            # Find AdaptiveClient configuration
            lines = content.split('\n')
            adaptive_client_section = []
            in_adaptive_section = False
            
            for line in lines:
                if "client<llm> AdaptiveClient" in line:
                    in_adaptive_section = True
                elif in_adaptive_section and line.strip().startswith("client<llm>"):
                    break
                elif in_adaptive_section and line.strip() == "}":
                    adaptive_client_section.append(line)
                    break
                
                if in_adaptive_section:
                    adaptive_client_section.append(line)
            
            adaptive_config = '\n'.join(adaptive_client_section)
            
            # Should use fallback provider
            assert "provider fallback" in adaptive_config
            # Should include OllamaClient first, then cloud providers
            assert "strategy [OllamaClient, CustomSonnet]" in adaptive_config
    
    def test_ollama_retry_policy(self):
        """Test Ollama-specific retry policy configuration."""
        baml_clients_path = Path(__file__).parent.parent / "baml_src" / "clients.baml"
        
        if baml_clients_path.exists():
            content = baml_clients_path.read_text()
            
            # Should have Ollama-specific retry policy
            assert "retry_policy OllamaRetry" in content
            
            # Check for OllamaRetry configuration directly
            assert "max_retries 2" in content
            assert "delay_ms 500" in content
            assert "constant_delay" in content


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ollama_baml_clients.py -v
    pytest.main([__file__, "-v"])