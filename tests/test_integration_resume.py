#!/usr/bin/env python3
"""
Integration tests for the resume functionality.
Tests end-to-end scenarios with real file system interactions.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from rulectl.state_manager import AnalysisStateManager
from rulectl.analysis_phases import AnalysisPhase, PhaseStatus
from rulectl.analyzer import RepoAnalyzer


@pytest.fixture
def integration_repo():
    """Create a more realistic test repository."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Create realistic project structure
    (repo_path / ".git").mkdir()
    (repo_path / ".gitignore").write_text("""
*.pyc
__pycache__/
.env
node_modules/
dist/
build/
""".strip())
    
    # Python source files
    (repo_path / "src").mkdir()
    (repo_path / "src" / "__init__.py").write_text("")
    (repo_path / "src" / "main.py").write_text("""
import os
from typing import List, Dict

def main():
    print("Hello World")
    
class DataProcessor:
    def __init__(self, config: Dict):
        self.config = config
    
    def process(self, data: List[str]) -> List[str]:
        return [item.upper() for item in data]
""")
    
    (repo_path / "src" / "utils").mkdir()
    (repo_path / "src" / "utils" / "__init__.py").write_text("")
    (repo_path / "src" / "utils" / "helpers.py").write_text("""
def validate_email(email: str) -> bool:
    return "@" in email and "." in email

def format_currency(amount: float) -> str:
    return f"${amount:.2f}"
""")
    
    # Test files
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "__init__.py").write_text("")
    (repo_path / "tests" / "test_main.py").write_text("""
import pytest
from src.main import DataProcessor

def test_data_processor():
    processor = DataProcessor({"debug": True})
    result = processor.process(["hello", "world"])
    assert result == ["HELLO", "WORLD"]
""")
    
    # Configuration files
    (repo_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = ""

[tool.poetry.dependencies]
python = "^3.8"
""")
    
    (repo_path / "README.md").write_text("""
# Test Project

This is a test project for integration testing.

## Installation

```bash
pip install -e .
```

## Usage

```python
from src.main import main
main()
```
""")
    
    yield str(repo_path)
    shutil.rmtree(temp_dir)


class TestEndToEndResumeScenarios:
    """Test complete resume scenarios from start to finish."""
    
    @pytest.mark.asyncio
    async def test_complete_analysis_without_interruption(self, integration_repo):
        """Test a complete analysis that doesn't need resume."""
        state_manager = AnalysisStateManager(integration_repo)
        
        # Initialize session
        session_id = await state_manager.initialize_new_session({
            "verbose": False,
            "batch_size": 2
        })
        
        # Simulate complete analysis flow
        phases = [
            AnalysisPhase.SETUP,
            AnalysisPhase.STRUCTURE_ANALYSIS,
            AnalysisPhase.FILE_DISCOVERY,
            AnalysisPhase.FILE_ANALYSIS,
            AnalysisPhase.GIT_ANALYSIS,
            AnalysisPhase.RULE_SYNTHESIS,
            AnalysisPhase.SAVE_COMPLETE
        ]
        
        for phase in phases:
            await state_manager.start_phase(phase)
            
            # Simulate some work
            if phase == AnalysisPhase.FILE_ANALYSIS:
                await state_manager.update_progress(phase, total=5)
                for i in range(5):
                    await state_manager.update_progress(
                        phase, 
                        completed=i+1, 
                        current_item=f"file_{i}.py"
                    )
            
            # Complete phase with mock data
            cache_data = {"phase": phase.value, "completed": True}
            await state_manager.complete_phase(phase, cache_data)
        
        # Cleanup
        await state_manager.cleanup_completed_session()
        
        # Verify cleanup
        assert not state_manager.progress_file.exists()
        assert not state_manager.cache_dir.exists() or not list(state_manager.cache_dir.iterdir())
    
    @pytest.mark.asyncio
    async def test_resume_from_file_analysis_interruption(self, integration_repo):
        """Test resuming from an interruption during file analysis."""
        # Step 1: Simulate initial analysis that gets interrupted
        initial_manager = AnalysisStateManager(integration_repo)
        session_id = await initial_manager.initialize_new_session({"batch_size": 2})
        
        # Complete early phases
        early_phases = [AnalysisPhase.SETUP, AnalysisPhase.STRUCTURE_ANALYSIS, AnalysisPhase.FILE_DISCOVERY]
        for phase in early_phases:
            await initial_manager.start_phase(phase)
            await initial_manager.complete_phase(phase, {"phase": phase.value})
        
        # Start file analysis but don't complete it (simulate interruption)
        await initial_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await initial_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, total=5, completed=2, failed=1)
        
        # Simulate partial results cache
        partial_results = [
            {"file": "src/main.py", "rules": ["rule1", "rule2"]},
            {"file": "src/utils/helpers.py", "rules": ["rule3"]}
        ]
        cache_file = initial_manager.cache_dir / "files.json"
        with open(cache_file, 'w') as f:
            json.dump(partial_results, f)
        
        # Step 2: Create new manager to simulate restart and resume
        resume_manager = AnalysisStateManager(integration_repo)
        
        # Detect incomplete analysis
        resume_info = await resume_manager.detect_incomplete_analysis()
        assert resume_info is not None
        assert resume_info['can_resume'] is True
        assert resume_info['session_id'] == session_id
        assert resume_info['current_phase'] == AnalysisPhase.FILE_ANALYSIS.value
        assert resume_info['progress']['completed'] == 2
        assert resume_info['progress']['failed'] == 1
        assert resume_info['progress']['total'] == 5
        
        # Resume from existing state
        resumed_state = await resume_manager.resume_from_existing_state()
        assert resumed_state.session_id == session_id
        assert resumed_state.current_phase == AnalysisPhase.FILE_ANALYSIS
        assert len(resumed_state.completed_phases) == 3  # Early phases completed
        
        # Load cached results
        cached_data = await resume_manager.load_cache_data(AnalysisPhase.FILE_ANALYSIS)
        assert cached_data == partial_results
        
        # Continue analysis from where it left off
        await resume_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, completed=5)
        await resume_manager.complete_phase(AnalysisPhase.FILE_ANALYSIS, partial_results + [{"file": "new.py"}])
        
        # Complete remaining phases
        remaining_phases = [AnalysisPhase.GIT_ANALYSIS, AnalysisPhase.RULE_SYNTHESIS, AnalysisPhase.SAVE_COMPLETE]
        for phase in remaining_phases:
            await resume_manager.start_phase(phase)
            await resume_manager.complete_phase(phase, {"phase": phase.value})
        
        # Cleanup
        await resume_manager.cleanup_completed_session()
        assert not resume_manager.progress_file.exists()
    
    @pytest.mark.asyncio
    async def test_multiple_resume_attempts(self, integration_repo):
        """Test multiple interruptions and resumes."""
        session_id = None
        
        # First attempt - interrupted during structure analysis
        manager1 = AnalysisStateManager(integration_repo)
        session_id = await manager1.initialize_new_session({"attempt": 1})
        await manager1.start_phase(AnalysisPhase.SETUP)
        await manager1.complete_phase(AnalysisPhase.SETUP, {"setup": "done"})
        await manager1.start_phase(AnalysisPhase.STRUCTURE_ANALYSIS)
        # Interrupted here
        
        # Second attempt - resume and continue further
        manager2 = AnalysisStateManager(integration_repo)
        resume_info = await manager2.detect_incomplete_analysis()
        assert resume_info['can_resume'] is True
        await manager2.resume_from_existing_state()
        
        # Complete structure analysis and start file analysis
        await manager2.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"structure": "done"})
        await manager2.start_phase(AnalysisPhase.FILE_DISCOVERY)
        await manager2.complete_phase(AnalysisPhase.FILE_DISCOVERY, {"discovery": "done"})
        await manager2.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await manager2.update_progress(AnalysisPhase.FILE_ANALYSIS, total=3, completed=1)
        # Interrupted again
        
        # Third attempt - complete the analysis
        manager3 = AnalysisStateManager(integration_repo)
        resume_info = await manager3.detect_incomplete_analysis()
        assert resume_info['can_resume'] is True
        assert resume_info['progress']['completed'] == 1
        await manager3.resume_from_existing_state()
        
        # Complete remaining work
        await manager3.update_progress(AnalysisPhase.FILE_ANALYSIS, completed=3)
        await manager3.complete_phase(AnalysisPhase.FILE_ANALYSIS, {"files": "done"})
        
        remaining_phases = [AnalysisPhase.GIT_ANALYSIS, AnalysisPhase.RULE_SYNTHESIS, AnalysisPhase.SAVE_COMPLETE]
        for phase in remaining_phases:
            await manager3.start_phase(phase)
            await manager3.complete_phase(phase, {"phase": phase.value})
        
        await manager3.cleanup_completed_session()
        assert not manager3.progress_file.exists()


class TestResumeWithRepoAnalyzer:
    """Test resume functionality integrated with RepoAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_repo_analyzer_with_resume(self, integration_repo):
        """Test RepoAnalyzer working with state manager for resume."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session({"integration_test": True})
        
        # Create analyzer with state manager
        analyzer = RepoAnalyzer(integration_repo, state_manager=state_manager)
        
        # Mock BAML client to avoid real API calls
        mock_client = Mock()
        mock_client.AnalyzeRepoStructure = AsyncMock(return_value={
            "file_types": [{"extension": "py", "count": 5}],
            "directories": ["src", "tests"],
            "total_files": 8
        })
        mock_client.AnalyzeFile = AsyncMock(return_value=Mock(
            file="test.py",
            rules=[Mock(slug="test-rule", description="Test rule")]
        ))
        analyzer.client = mock_client
        
        # Analyze structure
        await analyzer.analyze_structure()
        
        # Verify state was updated
        state = state_manager.get_current_state()
        structure_phase = state.phases[AnalysisPhase.STRUCTURE_ANALYSIS]
        assert structure_phase.status == PhaseStatus.COMPLETED
        
        # Test resumable file analysis
        files = ["src/main.py", "src/utils/helpers.py", "tests/test_main.py"]
        with patch.object(analyzer, 'get_all_analyzable_files', return_value=files):
            results = await analyzer.analyze_files_resumable(files)
        
        # Verify file analysis was tracked
        file_phase = state.phases[AnalysisPhase.FILE_ANALYSIS]
        assert file_phase.status == PhaseStatus.COMPLETED
        assert len(results) == 3
        
        # Verify cache files were created
        assert (state_manager.cache_dir / "structure.json").exists()
        assert (state_manager.cache_dir / "files.json").exists()
    
    @pytest.mark.asyncio 
    async def test_repo_analyzer_resume_from_cache(self, integration_repo):
        """Test RepoAnalyzer loading from cached state."""
        # First run - create cache
        state_manager1 = AnalysisStateManager(integration_repo)
        await state_manager1.initialize_new_session()
        
        analyzer1 = RepoAnalyzer(integration_repo, state_manager=state_manager1)
        
        # Mock structure analysis
        structure_data = {
            "file_types": [{"extension": "py", "count": 5}],
            "directories": ["src", "tests"],
            "total_files": 8
        }
        
        with patch.object(analyzer1.client, 'AnalyzeRepoStructure', return_value=structure_data):
            result1 = await analyzer1.analyze_structure()
        
        # Interrupt before completing
        await state_manager1.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Second run - resume from cache
        state_manager2 = AnalysisStateManager(integration_repo)
        await state_manager2.resume_from_existing_state()
        
        analyzer2 = RepoAnalyzer(integration_repo, state_manager=state_manager2)
        
        # Should load from cache without calling BAML
        with patch.object(analyzer2.client, 'AnalyzeRepoStructure') as mock_analyze:
            result2 = await analyzer2.analyze_structure()
            
            # Should not call BAML client (loaded from cache)
            mock_analyze.assert_not_called()
            
            # Should return cached data
            assert result2 == structure_data


class TestFileSystemInteractions:
    """Test file system edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_state_file_access(self, integration_repo):
        """Test handling of concurrent access to state files."""
        # Create two state managers for the same directory
        manager1 = AnalysisStateManager(integration_repo)
        manager2 = AnalysisStateManager(integration_repo)
        
        # Initialize from first manager
        await manager1.initialize_new_session({"manager": 1})
        
        # Second manager should detect existing analysis
        resume_info = await manager2.detect_incomplete_analysis()
        assert resume_info is not None
        
        # Both managers should be able to load the same state
        state1 = await manager1.get_current_state()
        await manager2.resume_from_existing_state()
        state2 = manager2.get_current_state()
        
        assert state1.session_id == state2.session_id
    
    @pytest.mark.asyncio
    async def test_disk_space_exhaustion_simulation(self, integration_repo):
        """Test behavior when disk space is exhausted during state saving."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session()
        
        # Mock disk space exhaustion
        original_open = open
        def failing_open(file, mode='r', **kwargs):
            if str(file).endswith('.tmp') and 'w' in mode:
                raise OSError("No space left on device")
            return original_open(file, mode, **kwargs)
        
        with patch('builtins.open', side_effect=failing_open):
            # Should raise StateManagerError when saving fails
            with pytest.raises(Exception):  # Could be StateManagerError or OSError
                await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
    
    @pytest.mark.asyncio
    async def test_permission_denied_cache_directory(self, integration_repo):
        """Test handling of permission issues with cache directory."""
        state_manager = AnalysisStateManager(integration_repo)
        
        # Make cache directory read-only after creation
        state_manager.cache_dir.chmod(0o444)
        
        try:
            await state_manager.initialize_new_session()
            
            # Should handle permission error gracefully when trying to write cache
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                await state_manager.start_phase(AnalysisPhase.STRUCTURE_ANALYSIS)
                # Should not crash, may log error
                
        finally:
            # Restore permissions for cleanup
            state_manager.cache_dir.chmod(0o755)
    
    @pytest.mark.asyncio
    async def test_corrupted_cache_file_recovery(self, integration_repo):
        """Test recovery from corrupted cache files."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session()
        
        # Create valid state
        await state_manager.start_phase(AnalysisPhase.STRUCTURE_ANALYSIS)
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"valid": "data"})
        
        # Corrupt the cache file
        cache_file = state_manager.cache_dir / "structure.json"
        with open(cache_file, 'w') as f:
            f.write("invalid json {")
        
        # Should handle corrupted cache gracefully
        cached_data = await state_manager.load_cache_data(AnalysisPhase.STRUCTURE_ANALYSIS)
        assert cached_data is None  # Should return None for corrupted cache
    
    @pytest.mark.asyncio
    async def test_state_file_atomic_write_interruption(self, integration_repo):
        """Test atomic write behavior when interrupted."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session()
        
        # Create initial valid state
        await state_manager.start_phase(AnalysisPhase.STRUCTURE_ANALYSIS)
        
        # Verify initial state file exists and is valid
        assert state_manager.progress_file.exists()
        with open(state_manager.progress_file, 'r') as f:
            initial_data = json.load(f)
        assert initial_data['current_phase'] == AnalysisPhase.STRUCTURE_ANALYSIS.value
        
        # Mock write failure during state update
        original_replace = Path.replace
        def failing_replace(self, target):
            if str(target).endswith('progress.json'):
                raise OSError("Write interrupted")
            return original_replace(self, target)
        
        with patch.object(Path, 'replace', failing_replace):
            # Should raise error but not corrupt existing file
            with pytest.raises(Exception):
                await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"test": "data"})
        
        # Original file should still be valid
        assert state_manager.progress_file.exists()
        with open(state_manager.progress_file, 'r') as f:
            preserved_data = json.load(f)
        assert preserved_data == initial_data


class TestLargeRepositorySimulation:
    """Test resume functionality with simulated large repository scenarios."""
    
    @pytest.mark.asyncio
    async def test_large_file_list_resume(self, integration_repo):
        """Test resume with a large number of files."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session()
        
        # Simulate large file list
        large_file_list = [f"file_{i:04d}.py" for i in range(1000)]
        
        # Start file analysis
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await state_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, total=len(large_file_list))
        
        # Process some files
        batch_size = 100
        for i in range(0, 300, batch_size):  # Process first 300 files
            end_idx = min(i + batch_size, 300)
            await state_manager.update_progress(
                AnalysisPhase.FILE_ANALYSIS,
                completed=end_idx,
                current_item=large_file_list[end_idx-1]
            )
        
        # Simulate interruption and resume
        new_manager = AnalysisStateManager(integration_repo)
        resume_info = await new_manager.detect_incomplete_analysis()
        
        assert resume_info['can_resume'] is True
        assert resume_info['progress']['completed'] == 300
        assert resume_info['progress']['total'] == 1000
        
        # Resume and complete
        await new_manager.resume_from_existing_state()
        await new_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, completed=1000)
        await new_manager.complete_phase(AnalysisPhase.FILE_ANALYSIS, {"completed": True})
    
    @pytest.mark.asyncio
    async def test_memory_efficient_progress_saving(self, integration_repo):
        """Test that progress saving doesn't consume excessive memory."""
        state_manager = AnalysisStateManager(integration_repo)
        await state_manager.initialize_new_session()
        
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Simulate many small progress updates
        for i in range(1000):
            await state_manager.update_progress(
                AnalysisPhase.FILE_ANALYSIS,
                completed=i,
                current_item=f"processing_file_{i}.py"
            )
        
        # Verify state file isn't excessively large
        state_file_size = state_manager.progress_file.stat().st_size
        assert state_file_size < 100000  # Less than 100KB for reasonable state
        
        # Verify final state is correct
        state = state_manager.get_current_state()
        progress = state.phases[AnalysisPhase.FILE_ANALYSIS].progress
        assert progress.completed == 999
        assert "processing_file_999.py" in progress.current_item