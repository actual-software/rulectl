#!/usr/bin/env python3
"""
Test module for analyzer.py resume functionality.
Tests the RepoAnalyzer integration with AnalysisStateManager.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from rulectl.analyzer import RepoAnalyzer
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
    (repo_path / "src" / "main.py").write_text("def hello():\n    print('hello')")
    (repo_path / "src" / "utils.py").write_text("def util_func():\n    pass")
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_main.py").write_text("def test_hello():\n    assert True")
    (repo_path / "README.md").write_text("# Test Project")
    (repo_path / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
    
    yield str(repo_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
async def state_manager(temp_repo):
    """Create an initialized AnalysisStateManager for testing."""
    manager = AnalysisStateManager(temp_repo)
    await manager.initialize_new_session({"test": True})
    return manager


@pytest.fixture
def mock_baml_client():
    """Create a mock BAML client for testing."""
    client = Mock()
    client.AnalyzeFile = AsyncMock()
    client.SynthesizeRulesAdvanced = AsyncMock()
    client.ReviewSkippedFiles = AsyncMock()
    client.CategorizeAcceptedRules = AsyncMock()
    return client


class TestRepoAnalyzerStateManagerIntegration:
    """Test RepoAnalyzer integration with AnalysisStateManager."""
    
    def test_analyzer_initialization_with_state_manager(self, temp_repo, state_manager):
        """Test RepoAnalyzer initialization with state manager."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        
        assert analyzer.repo_path == Path(temp_repo).resolve()
        assert analyzer.state_manager == state_manager
        assert analyzer.client is not None
    
    def test_analyzer_initialization_without_state_manager(self, temp_repo):
        """Test RepoAnalyzer initialization without state manager."""
        analyzer = RepoAnalyzer(temp_repo)
        
        assert analyzer.repo_path == Path(temp_repo).resolve()
        assert analyzer.state_manager is None
    
    @pytest.mark.asyncio
    async def test_analyze_structure_with_state_manager(self, temp_repo, state_manager):
        """Test that analyze_structure method works with state manager."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        
        # Mock the BAML client call
        with patch.object(analyzer.client, 'AnalyzeRepoStructure', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "file_types": [{"extension": "py", "count": 3}],
                "directories": ["src", "tests"],
                "total_files": 5
            }
            
            result = await analyzer.analyze_structure()
            
            # Should return structure data
            assert "file_types" in result
            assert "directories" in result
            
            # Should have called BAML client
            mock_analyze.assert_called_once()


class TestResumableFileAnalysis:
    """Test resumable file analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_files_resumable_new_session(self, temp_repo, state_manager, mock_baml_client):
        """Test resumable file analysis starting from beginning."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        # Mock file analysis response
        mock_baml_client.AnalyzeFile.return_value = Mock(
            file="test.py",
            rules=[Mock(slug="test-rule", description="Test rule")]
        )
        
        files_to_analyze = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        
        with patch('rulectl.analyzer.AnalysisPhase', AnalysisPhase), \
             patch.object(state_manager, 'start_phase') as mock_start, \
             patch.object(state_manager, 'update_progress') as mock_update, \
             patch.object(state_manager, 'complete_phase') as mock_complete:
            
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should analyze all files
            assert len(results) == 3
            assert mock_baml_client.AnalyzeFile.call_count == 3
            
            # Should track progress
            mock_start.assert_called_with(AnalysisPhase.FILE_ANALYSIS)
            mock_update.assert_called()
            mock_complete.assert_called_with(AnalysisPhase.FILE_ANALYSIS, results)
    
    @pytest.mark.asyncio
    async def test_analyze_files_resumable_with_cached_results(self, temp_repo, state_manager, mock_baml_client):
        """Test resumable file analysis with cached results from previous run."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        # Simulate cached results from previous analysis
        cached_results = [
            {"file": "src/main.py", "rules": [{"slug": "cached-rule"}]},
            {"file": "src/utils.py", "rules": []}
        ]
        
        files_to_analyze = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        
        with patch.object(state_manager, 'load_cache_data', return_value=cached_results) as mock_load_cache, \
             patch.object(state_manager, 'start_phase') as mock_start, \
             patch.object(state_manager, 'update_progress') as mock_update, \
             patch.object(state_manager, 'complete_phase') as mock_complete:
            
            # Mock new file analysis
            mock_baml_client.AnalyzeFile.return_value = Mock(
                file="tests/test_main.py",
                rules=[Mock(slug="test-rule")]
            )
            
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should load cached results
            mock_load_cache.assert_called_with(AnalysisPhase.FILE_ANALYSIS)
            
            # Should only analyze new file (not cached ones)
            assert mock_baml_client.AnalyzeFile.call_count == 1
            
            # Should have results for all files (cached + new)
            assert len(results) == 3
            
            # Should start phase and track progress
            mock_start.assert_called_with(AnalysisPhase.FILE_ANALYSIS)
            mock_update.assert_called()
            mock_complete.assert_called()
    
    @pytest.mark.asyncio
    async def test_analyze_files_resumable_error_handling(self, temp_repo, state_manager, mock_baml_client):
        """Test error handling in resumable file analysis."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        files_to_analyze = ["src/main.py", "src/utils.py"]
        
        # Mock first file success, second file failure
        def side_effect(file_path, baml_options=None):
            if "main.py" in file_path:
                return Mock(file=file_path, rules=[])
            else:
                raise Exception("Analysis failed")
        
        mock_baml_client.AnalyzeFile.side_effect = side_effect
        
        with patch.object(state_manager, 'start_phase') as mock_start, \
             patch.object(state_manager, 'update_progress') as mock_update, \
             patch.object(state_manager, 'complete_phase') as mock_complete, \
             patch('rulectl.analyzer.logger') as mock_logger:
            
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should return only successful analysis
            assert len(results) == 1
            assert results[0].file.endswith("main.py")
            
            # Should log error for failed file
            mock_logger.error.assert_called()
            
            # Should still complete phase with partial results
            mock_complete.assert_called_with(AnalysisPhase.FILE_ANALYSIS, results)
    
    @pytest.mark.asyncio
    async def test_analyze_files_resumable_without_state_manager(self, temp_repo, mock_baml_client):
        """Test resumable file analysis fallback when no state manager."""
        analyzer = RepoAnalyzer(temp_repo)  # No state manager
        analyzer.client = mock_baml_client
        
        mock_baml_client.AnalyzeFile.return_value = Mock(
            file="test.py",
            rules=[]
        )
        
        files_to_analyze = ["src/main.py", "src/utils.py"]
        
        # Should use the regular analyze_file method
        with patch.object(analyzer, 'analyze_file', return_value=Mock()) as mock_analyze_file:
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should call analyze_file for each file
            assert mock_analyze_file.call_count == 2


class TestAnalyzeStructureWithStateManager:
    """Test analyze_structure integration with state management."""
    
    @pytest.mark.asyncio
    async def test_analyze_structure_caching(self, temp_repo, state_manager):
        """Test that analyze_structure caches results."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        
        structure_data = {
            "file_types": [{"extension": "py", "count": 3}],
            "directories": ["src", "tests"],
            "total_files": 5
        }
        
        with patch.object(analyzer.client, 'AnalyzeRepoStructure', new_callable=AsyncMock) as mock_analyze, \
             patch.object(state_manager, 'complete_phase') as mock_complete:
            
            mock_analyze.return_value = structure_data
            
            result = await analyzer.analyze_structure()
            
            # Should cache the result
            mock_complete.assert_called_once()
            call_args = mock_complete.call_args
            assert call_args[0][0] == AnalysisPhase.STRUCTURE_ANALYSIS
            # Cache data should contain structure information
            assert "file_types" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_analyze_structure_load_from_cache(self, temp_repo, state_manager):
        """Test loading structure analysis from cache."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        
        cached_structure = {
            "file_types": [{"extension": "py", "count": 3}],
            "directories": ["src", "tests"],
            "total_files": 5
        }
        
        with patch.object(state_manager, 'load_cache_data', return_value=cached_structure) as mock_load, \
             patch.object(analyzer.client, 'AnalyzeRepoStructure', new_callable=AsyncMock) as mock_analyze:
            
            result = await analyzer.analyze_structure()
            
            # Should load from cache
            mock_load.assert_called_with(AnalysisPhase.STRUCTURE_ANALYSIS)
            
            # Should not call BAML client
            mock_analyze.assert_not_called()
            
            # Should return cached data
            assert result == cached_structure


class TestStateManagerProgressTracking:
    """Test progress tracking through state manager."""
    
    @pytest.mark.asyncio
    async def test_progress_tracking_during_file_analysis(self, temp_repo, state_manager, mock_baml_client):
        """Test that progress is tracked during file analysis."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        mock_baml_client.AnalyzeFile.return_value = Mock(file="test.py", rules=[])
        
        files_to_analyze = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        
        with patch.object(state_manager, 'start_phase') as mock_start, \
             patch.object(state_manager, 'update_progress') as mock_update, \
             patch.object(state_manager, 'complete_phase') as mock_complete:
            
            await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should start the phase
            mock_start.assert_called_with(AnalysisPhase.FILE_ANALYSIS)
            
            # Should update progress multiple times
            assert mock_update.call_count >= 5  # At least once per file
            
            # Check that progress updates have reasonable values
            progress_calls = mock_update.call_args_list
            for call in progress_calls:
                args, kwargs = call
                assert args[0] == AnalysisPhase.FILE_ANALYSIS
                
                # Check keyword arguments for progress values
                if 'completed' in kwargs:
                    assert kwargs['completed'] >= 0
                if 'total' in kwargs:
                    assert kwargs['total'] == len(files_to_analyze)
    
    @pytest.mark.asyncio
    async def test_progress_tracking_with_failures(self, temp_repo, state_manager, mock_baml_client):
        """Test progress tracking when some files fail analysis."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        def analysis_side_effect(file_path, baml_options=None):
            if "fail" in file_path:
                raise Exception("Analysis failed")
            return Mock(file=file_path, rules=[])
        
        mock_baml_client.AnalyzeFile.side_effect = analysis_side_effect
        
        files_to_analyze = ["success1.py", "fail1.py", "success2.py", "fail2.py"]
        
        with patch.object(state_manager, 'update_progress') as mock_update:
            
            await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should track both successful and failed files
            progress_calls = mock_update.call_args_list
            
            # Find calls that update completed and failed counts
            completed_updates = [call for call in progress_calls if 'completed' in call.kwargs]
            failed_updates = [call for call in progress_calls if 'failed' in call.kwargs]
            
            # Should have updates for both completed and failed
            assert len(completed_updates) > 0
            assert len(failed_updates) > 0


class TestTokenTrackerIntegration:
    """Test integration with token tracker during resume."""
    
    @pytest.mark.asyncio
    async def test_token_tracking_with_resume(self, temp_repo, state_manager, mock_baml_client):
        """Test that token tracking works correctly with resume functionality."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        # Mock token tracker
        mock_token_tracker = Mock()
        mock_token_tracker.get_baml_options.return_value = {"timeout_ms": 30000}
        mock_token_tracker.track_call_from_collector = Mock()
        analyzer.token_tracker = mock_token_tracker
        
        mock_baml_client.AnalyzeFile.return_value = Mock(file="test.py", rules=[])
        
        files_to_analyze = ["file1.py", "file2.py"]
        
        await analyzer.analyze_files_resumable(files_to_analyze)
        
        # Should use token tracker options for BAML calls
        baml_calls = mock_baml_client.AnalyzeFile.call_args_list
        for call in baml_calls:
            args, kwargs = call
            assert 'baml_options' in kwargs
            assert kwargs['baml_options']['timeout_ms'] == 30000
        
        # Should track token usage
        assert mock_token_tracker.track_call_from_collector.call_count >= 2


class TestErrorHandlingWithStateManager:
    """Test error handling in analyzer methods with state manager."""
    
    @pytest.mark.asyncio
    async def test_structure_analysis_error_handling(self, temp_repo, state_manager):
        """Test error handling in structure analysis with state manager."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        
        # Mock BAML client to raise an error
        with patch.object(analyzer.client, 'AnalyzeRepoStructure', side_effect=Exception("BAML error")), \
             patch.object(state_manager, 'fail_phase') as mock_fail, \
             patch('rulectl.analyzer.logger') as mock_logger:
            
            # Should handle error gracefully
            result = await analyzer.analyze_structure()
            
            # Should log the error
            mock_logger.error.assert_called()
            
            # Should return a basic structure
            assert "file_types" in result
            assert "directories" in result
    
    @pytest.mark.asyncio
    async def test_file_analysis_batch_error_handling(self, temp_repo, state_manager, mock_baml_client):
        """Test error handling when entire batch fails in file analysis."""
        analyzer = RepoAnalyzer(temp_repo, state_manager=state_manager)
        analyzer.client = mock_baml_client
        
        # Mock BAML client to always fail
        mock_baml_client.AnalyzeFile.side_effect = Exception("Network error")
        
        files_to_analyze = ["file1.py", "file2.py"]
        
        with patch.object(state_manager, 'fail_phase') as mock_fail, \
             patch('rulectl.analyzer.logger') as mock_logger:
            
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should return empty results
            assert results == []
            
            # Should log errors for all files
            assert mock_logger.error.call_count >= 2
            
            # Should not fail the entire phase for individual file failures
            mock_fail.assert_not_called()


class TestBackwardCompatibility:
    """Test backward compatibility when state manager is not available."""
    
    def test_analyzer_without_state_manager_modules(self, temp_repo):
        """Test analyzer works when state manager modules are not available."""
        with patch('rulectl.analyzer.AnalysisStateManager', None), \
             patch('rulectl.analyzer.AnalysisPhase', None):
            
            # Should initialize without errors
            analyzer = RepoAnalyzer(temp_repo)
            assert analyzer.state_manager is None
    
    @pytest.mark.asyncio
    async def test_file_analysis_fallback_without_state_manager(self, temp_repo, mock_baml_client):
        """Test that file analysis falls back to regular method without state manager."""
        analyzer = RepoAnalyzer(temp_repo)  # No state manager
        analyzer.client = mock_baml_client
        
        mock_baml_client.AnalyzeFile.return_value = Mock(file="test.py", rules=[])
        
        with patch.object(analyzer, 'analyze_file') as mock_analyze_file:
            mock_analyze_file.return_value = Mock()
            
            files_to_analyze = ["file1.py", "file2.py"]
            results = await analyzer.analyze_files_resumable(files_to_analyze)
            
            # Should call regular analyze_file method
            assert mock_analyze_file.call_count == 2
            
            # Should return results
            assert len(results) == 2