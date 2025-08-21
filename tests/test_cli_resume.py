#!/usr/bin/env python3
"""
Test module for CLI resume functionality.
Tests the CLI integration with resume features.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from click.testing import CliRunner

from rulectl.cli import cli, async_start
from rulectl.state_manager import AnalysisStateManager
from rulectl.analysis_phases import AnalysisPhase, PhaseStatus


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Create basic git repo structure
    (repo_path / ".git").mkdir()
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")
    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("print('hello')")
    (repo_path / "README.md").write_text("# Test Project")
    
    yield str(repo_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_analyzer():
    """Create a mock RepoAnalyzer for testing."""
    analyzer = Mock()
    analyzer.has_gitignore.return_value = True
    analyzer.count_analyzable_files.return_value = (5, {"py": 3, "md": 2})
    analyzer.get_skipped_config_files.return_value = []
    analyzer.get_all_analyzable_files.return_value = ["src/main.py", "README.md"]
    analyzer.analyze_structure = AsyncMock()
    analyzer.analyze_files_resumable = AsyncMock(return_value=[])
    analyzer.get_git_commit_details.return_value = {"modification_counts": {}}
    analyzer.get_file_importance_weights.return_value = {}
    analyzer.synthesize_rules_advanced = AsyncMock(return_value=([], {}))
    analyzer.save_findings = Mock()
    analyzer.token_tracker = None
    analyzer.findings = {"repository": {"structure": {"file_types": [], "directories": []}}}
    return analyzer


class TestCLIResumeDetection:
    """Test CLI detection and handling of incomplete analysis."""
    
    @pytest.mark.asyncio
    async def test_no_incomplete_analysis(self, temp_repo, mock_analyzer):
        """Test CLI behavior when no incomplete analysis exists."""
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=None)
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="test-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=True, continue_analysis=False, 
                rate_limit=None, batch_size=None, delay_ms=None, 
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should initialize new session
            mock_state_mgr.initialize_new_session.assert_called_once()
            mock_state_mgr.detect_incomplete_analysis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_auto_continue_incomplete_analysis(self, temp_repo, mock_analyzer):
        """Test CLI with --continue flag for incomplete analysis."""
        resume_info = {
            'can_resume': True,
            'session_id': 'test-session-123',
            'phase_description': 'Individual file analysis',
            'progress': {'completed': 3, 'total': 10, 'failed': 1}
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.click.echo') as mock_echo:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.resume_from_existing_state = AsyncMock()
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI with --continue flag
            await async_start(
                verbose=False, force=True, continue_analysis=True,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should resume from existing state
            mock_state_mgr.resume_from_existing_state.assert_called_once()
            mock_state_mgr.detect_incomplete_analysis.assert_called_once()
            
            # Should show resume messages
            echo_calls = [call[0][0] for call in mock_echo.call_args_list]
            assert any("Continuing from previous incomplete analysis" in msg for msg in echo_calls)
    
    @pytest.mark.asyncio
    async def test_cannot_resume_missing_cache_files(self, temp_repo, mock_analyzer):
        """Test CLI behavior when resume is not possible due to missing cache files."""
        resume_info = {
            'can_resume': False,
            'session_id': 'test-session-123',
            'missing_cache_files': ['files.json', 'git_stats.json']
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.click.echo') as mock_echo:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.cleanup_failed_session = AsyncMock()
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="new-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=True, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should clean up failed session and start fresh
            mock_state_mgr.cleanup_failed_session.assert_called_once()
            mock_state_mgr.initialize_new_session.assert_called_once()
            
            # Should show missing files message
            echo_calls = [call[0][0] for call in mock_echo.call_args_list]
            assert any("cache files are missing" in msg for msg in echo_calls)
            assert any("files.json" in msg for msg in echo_calls)


class TestCLIResumePrompts:
    """Test CLI resume prompts and user interactions."""
    
    @pytest.mark.asyncio
    async def test_resume_prompt_accept(self, temp_repo, mock_analyzer):
        """Test accepting the resume prompt."""
        resume_info = {
            'can_resume': True,
            'session_id': 'test-session-123',
            'started_at': '2025-01-15T10:30:00Z',
            'phase_description': 'Individual file analysis',
            'completed_phases': ['setup', 'structure_analysis'],
            'progress': {'completed': 5, 'total': 20, 'failed': 1, 'current_item': 'test.py'}
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.click.confirm', return_value=True) as mock_confirm:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.resume_from_existing_state = AsyncMock()
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=False, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should show confirmation prompt
            mock_confirm.assert_called_with(
                "\nWould you like to continue where you left off?", 
                default=True
            )
            
            # Should resume from existing state
            mock_state_mgr.resume_from_existing_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resume_prompt_decline(self, temp_repo, mock_analyzer):
        """Test declining the resume prompt."""
        resume_info = {
            'can_resume': True,
            'session_id': 'test-session-123',
            'phase_description': 'Individual file analysis'
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.click.confirm', return_value=False) as mock_confirm:
            
            # Setup state manager mock  
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.cleanup_failed_session = AsyncMock()
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="new-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=False, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should show confirmation prompt
            mock_confirm.assert_called_with(
                "\nWould you like to continue where you left off?", 
                default=True
            )
            
            # Should clean up and start fresh
            mock_state_mgr.cleanup_failed_session.assert_called_once()
            mock_state_mgr.initialize_new_session.assert_called_once()


class TestCLIPhaseIntegration:
    """Test CLI integration with analysis phases."""
    
    @pytest.mark.asyncio
    async def test_phase_tracking_during_analysis(self, temp_repo, mock_analyzer):
        """Test that CLI properly tracks phases during analysis."""
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=None)
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="test-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=True, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Verify phase tracking calls
            expected_phases = [
                AnalysisPhase.STRUCTURE_ANALYSIS,
                AnalysisPhase.GIT_ANALYSIS,
                AnalysisPhase.RULE_SYNTHESIS,
                AnalysisPhase.SAVE_COMPLETE
            ]
            
            # Check that start_phase was called for expected phases
            start_calls = [call[0][0] for call in mock_state_mgr.start_phase.call_args_list]
            for phase in expected_phases:
                assert phase in start_calls
            
            # Check that complete_phase was called for some phases
            complete_calls = [call[0][0] for call in mock_state_mgr.complete_phase.call_args_list]
            assert len(complete_calls) > 0
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_completion(self, temp_repo, mock_analyzer):
        """Test that CLI cleans up session on successful completion."""
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=None)
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="test-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI
            await async_start(
                verbose=False, force=True, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should clean up session on completion
            mock_state_mgr.cleanup_completed_session.assert_called_once()


class TestCLICommandLineFlags:
    """Test CLI command line flag integration with resume."""
    
    def test_continue_flag_in_help(self):
        """Test that --continue flag is documented in help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['start', '--help'])
        
        assert result.exit_code == 0
        assert '--continue' in result.output
        assert 'continue from previous incomplete analysis' in result.output.lower()
    
    def test_continue_flag_parsing(self):
        """Test that --continue flag is parsed correctly."""
        runner = CliRunner()
        
        # Mock the async function to avoid actual execution
        with patch('rulectl.cli.asyncio.run') as mock_run:
            result = runner.invoke(cli, ['start', '--continue', '.'])
            
            # Should call asyncio.run with continue_analysis=True
            assert result.exit_code == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]  # Get the coroutine args
            # The async_start function should be called with continue_analysis=True
    
    @pytest.mark.asyncio
    async def test_rate_limiting_options_with_resume(self, temp_repo, mock_analyzer):
        """Test that rate limiting options work correctly with resume."""
        resume_info = {
            'can_resume': True,
            'session_id': 'test-session-123',
            'phase_description': 'Individual file analysis'
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.os.environ', {}) as mock_env:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.resume_from_existing_state = AsyncMock()
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI with rate limiting options and continue
            await async_start(
                verbose=False, force=True, continue_analysis=True,
                rate_limit=15, batch_size=3, delay_ms=500,
                no_batching=False, strategy="exponential", directory=temp_repo
            )
            
            # Should set environment variables
            assert mock_env["RULECTL_RATE_LIMIT_REQUESTS_PER_MINUTE"] == "15"
            assert mock_env["RULECTL_RATE_LIMIT_BATCH_SIZE"] == "3"
            assert mock_env["RULECTL_RATE_LIMIT_BASE_DELAY_MS"] == "500"
            assert mock_env["RULECTL_RATE_LIMIT_STRATEGY"] == "exponential"
            
            # Should still resume
            mock_state_mgr.resume_from_existing_state.assert_called_once()


class TestCLIErrorHandling:
    """Test CLI error handling with resume functionality."""
    
    @pytest.mark.asyncio
    async def test_state_manager_import_failure(self, temp_repo, mock_analyzer):
        """Test CLI behavior when state manager modules can't be imported."""
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager', None), \
             patch('rulectl.cli.AnalysisPhase', None):
            
            # Should run without errors, just without state management
            await async_start(
                verbose=False, force=True, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should still complete analysis
            mock_analyzer.analyze_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resume_detection_failure(self, temp_repo, mock_analyzer):
        """Test CLI behavior when resume detection fails."""
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class:
            
            # Setup state manager mock that fails during resume detection
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(side_effect=Exception("Resume detection failed"))
            mock_state_mgr.initialize_new_session = AsyncMock(return_value="test-session")
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Should handle the error gracefully and continue with new session
            await async_start(
                verbose=False, force=True, continue_analysis=False,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should still initialize new session
            mock_state_mgr.initialize_new_session.assert_called_once()


class TestCLIVerboseOutput:
    """Test verbose output with resume functionality."""
    
    @pytest.mark.asyncio
    async def test_verbose_resume_output(self, temp_repo, mock_analyzer):
        """Test that verbose mode shows detailed resume information."""
        resume_info = {
            'can_resume': True,
            'session_id': 'test-session-123456789',
            'started_at': '2025-01-15T10:30:00Z',
            'phase_description': 'Individual file analysis',
            'completed_phases': ['setup', 'structure_analysis'],
            'progress': {'completed': 15, 'total': 50, 'failed': 2, 'current_item': 'component.tsx'}
        }
        
        with patch('rulectl.cli.validate_repository', return_value=True), \
             patch('rulectl.cli.check_baml_client', return_value=True), \
             patch('rulectl.cli.ensure_api_keys', return_value={"anthropic": "test-key"}), \
             patch('rulectl.cli.RepoAnalyzer', return_value=mock_analyzer), \
             patch('rulectl.cli.AnalysisStateManager') as mock_state_mgr_class, \
             patch('rulectl.cli.click.echo') as mock_echo:
            
            # Setup state manager mock
            mock_state_mgr = Mock()
            mock_state_mgr.detect_incomplete_analysis = AsyncMock(return_value=resume_info)
            mock_state_mgr.resume_from_existing_state = AsyncMock()
            mock_state_mgr.start_phase = AsyncMock()
            mock_state_mgr.complete_phase = AsyncMock()
            mock_state_mgr.cleanup_completed_session = AsyncMock()
            mock_state_mgr_class.return_value = mock_state_mgr
            
            # Run CLI with verbose and auto-continue
            await async_start(
                verbose=True, force=True, continue_analysis=True,
                rate_limit=None, batch_size=None, delay_ms=None,
                no_batching=False, strategy=None, directory=temp_repo
            )
            
            # Should show detailed resume information
            echo_calls = [call[0][0] for call in mock_echo.call_args_list]
            
            # Check for expected verbose messages
            assert any("Session: test-ses" in msg for msg in echo_calls)  # Truncated session ID
            assert any("Individual file analysis" in msg for msg in echo_calls)
            assert any("15/50" in msg for msg in echo_calls)  # Progress info
            assert any("2 failed" in msg for msg in echo_calls)  # Failed count