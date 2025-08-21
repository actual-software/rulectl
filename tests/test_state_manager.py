#!/usr/bin/env python3
"""
Test module for state_manager.py
Tests the AnalysisStateManager class and its functionality.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from rulectl.state_manager import (
    AnalysisStateManager, StateManagerError, InvalidStateError, ResumeError
)
from rulectl.analysis_phases import (
    AnalysisPhase, PhaseStatus, PhaseProgress, PhaseState, AnalysisState,
    PHASE_ORDER, PHASE_CACHE_FILES
)


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def state_manager(temp_directory):
    """Create a AnalysisStateManager instance for testing."""
    return AnalysisStateManager(str(temp_directory))


@pytest.fixture
def sample_analysis_options():
    """Sample analysis options for testing."""
    return {
        "verbose": True,
        "force": False,
        "rate_limit": 10,
        "batch_size": 5
    }


class TestAnalysisStateManagerInitialization:
    """Test AnalysisStateManager initialization."""
    
    def test_initialization(self, temp_directory):
        """Test basic initialization."""
        manager = AnalysisStateManager(str(temp_directory))
        
        assert manager.directory == temp_directory.resolve()
        assert manager.state_dir == temp_directory.resolve() / ".rulectl"
        assert manager.progress_file == temp_directory.resolve() / ".rulectl" / "progress.json"
        assert manager.cache_dir == temp_directory.resolve() / ".rulectl" / "cache"
        
        # Directories should be created
        assert manager.state_dir.exists()
        assert manager.cache_dir.exists()
        
        # Internal state should be None initially
        assert manager._current_state is None
    
    def test_directory_creation(self, temp_directory):
        """Test that required directories are created."""
        # Remove .rulectl directory if it exists
        rulectl_dir = temp_directory / ".rulectl"
        if rulectl_dir.exists():
            shutil.rmtree(rulectl_dir)
        
        manager = AnalysisStateManager(str(temp_directory))
        
        assert manager.state_dir.exists()
        assert manager.state_dir.is_dir()
        assert manager.cache_dir.exists()
        assert manager.cache_dir.is_dir()


class TestSessionManagement:
    """Test session initialization and management."""
    
    @pytest.mark.asyncio
    async def test_initialize_new_session(self, state_manager, sample_analysis_options):
        """Test initializing a new analysis session."""
        session_id = await state_manager.initialize_new_session(sample_analysis_options)
        
        # Session ID should be a valid UUID string
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID4 format
        
        # State should be set
        state = state_manager.get_current_state()
        assert state is not None
        assert state.session_id == session_id
        assert state.directory == str(state_manager.directory)
        assert state.current_phase == AnalysisPhase.SETUP
        assert state.completed_phases == []
        assert state.analysis_options == sample_analysis_options
        
        # All phases should be initialized as PENDING
        for phase in PHASE_ORDER:
            assert phase in state.phases
            assert state.phases[phase].status == PhaseStatus.PENDING
        
        # Progress file should be created
        assert state_manager.progress_file.exists()
    
    @pytest.mark.asyncio
    async def test_initialize_session_without_options(self, state_manager):
        """Test initializing session without analysis options."""
        session_id = await state_manager.initialize_new_session()
        
        state = state_manager.get_current_state()
        assert state.analysis_options == {}
    
    @pytest.mark.asyncio
    async def test_initialize_session_saves_state(self, state_manager):
        """Test that initializing a session saves state to disk."""
        await state_manager.initialize_new_session()
        
        # Verify state file exists and is valid JSON
        assert state_manager.progress_file.exists()
        with open(state_manager.progress_file, 'r') as f:
            data = json.load(f)
        
        assert 'session_id' in data
        assert 'started_at' in data
        assert 'current_phase' in data
        assert 'phases' in data


class TestIncompleteAnalysisDetection:
    """Test detection of incomplete analysis."""
    
    @pytest.mark.asyncio
    async def test_no_incomplete_analysis(self, state_manager):
        """Test when there's no incomplete analysis."""
        result = await state_manager.detect_incomplete_analysis()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_detect_incomplete_in_progress(self, state_manager):
        """Test detecting incomplete analysis in IN_PROGRESS phase."""
        # Initialize session and complete required phases with cache files
        await state_manager.initialize_new_session()
        
        # Complete prerequisite phases with cache files
        await state_manager.complete_phase(AnalysisPhase.SETUP, {})
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"structure": "data"})
        await state_manager.complete_phase(AnalysisPhase.FILE_DISCOVERY, {"files": []})
        
        # Start file analysis but don't complete it
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Create a new manager to simulate restart
        new_manager = AnalysisStateManager(str(state_manager.directory))
        result = await new_manager.detect_incomplete_analysis()
        
        assert result is not None
        assert result['can_resume'] is True
        assert result['current_phase'] == AnalysisPhase.FILE_ANALYSIS.value
        assert result['phase_description'] == "Individual file analysis"
        assert AnalysisPhase.SETUP.value in result['completed_phases']
    
    @pytest.mark.asyncio
    async def test_detect_incomplete_with_progress(self, state_manager):
        """Test detecting incomplete analysis with progress information."""
        await state_manager.initialize_new_session()
        
        # Complete prerequisite phases with cache files
        await state_manager.complete_phase(AnalysisPhase.SETUP, {})
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"structure": "data"})
        await state_manager.complete_phase(AnalysisPhase.FILE_DISCOVERY, {"files": []})
        
        # Start file analysis with progress
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await state_manager.update_progress(
            AnalysisPhase.FILE_ANALYSIS,
            completed=25,
            failed=2,
            total=100,
            current_item="test.py"
        )
        # Force save state
        await state_manager._save_state()
        
        # Create new manager to simulate restart
        new_manager = AnalysisStateManager(str(state_manager.directory))
        result = await new_manager.detect_incomplete_analysis()
        
        assert result is not None
        assert 'progress' in result
        progress = result['progress']
        assert progress['completed'] == 25
        assert progress['failed'] == 2
        assert progress['total'] == 100
        assert progress['current_item'] == "test.py"
    
    @pytest.mark.asyncio
    async def test_detect_incomplete_missing_cache_files(self, state_manager):
        """Test detecting incomplete analysis with missing cache files."""
        await state_manager.initialize_new_session()
        
        # Create required cache files
        for phase in [AnalysisPhase.STRUCTURE_ANALYSIS, AnalysisPhase.FILE_DISCOVERY]:
            cache_file = state_manager.cache_dir / PHASE_CACHE_FILES[phase]
            cache_file.write_text('{"test": "data"}')
            await state_manager.complete_phase(phase, {"test": "data"})
        
        # Start file analysis but don't create files.json
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Remove a required cache file
        (state_manager.cache_dir / "structure.json").unlink()
        
        # Create new manager to simulate restart
        new_manager = AnalysisStateManager(str(state_manager.directory))
        result = await new_manager.detect_incomplete_analysis()
        
        assert result is not None
        assert result['can_resume'] is False
        assert "structure.json" in result['missing_cache_files']
    
    @pytest.mark.asyncio
    async def test_detect_incomplete_corrupted_state(self, state_manager):
        """Test handling corrupted state file."""
        # Create invalid JSON state file
        with open(state_manager.progress_file, 'w') as f:
            f.write("invalid json {")
        
        result = await state_manager.detect_incomplete_analysis()
        assert result is None


class TestPhaseManagement:
    """Test phase lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_phase(self, state_manager):
        """Test starting a phase."""
        await state_manager.initialize_new_session()
        
        start_time = datetime.now(timezone.utc)
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        state = state_manager.get_current_state()
        assert state.current_phase == AnalysisPhase.FILE_ANALYSIS
        
        phase_state = state.phases[AnalysisPhase.FILE_ANALYSIS]
        assert phase_state.status == PhaseStatus.IN_PROGRESS
        assert phase_state.started_at >= start_time
    
    @pytest.mark.asyncio
    async def test_complete_phase(self, state_manager):
        """Test completing a phase."""
        await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.STRUCTURE_ANALYSIS)
        
        cache_data = {"files": ["test.py"], "directories": ["src/"]}
        completion_time = datetime.now(timezone.utc)
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, cache_data)
        
        state = state_manager.get_current_state()
        phase_state = state.phases[AnalysisPhase.STRUCTURE_ANALYSIS]
        
        assert phase_state.status == PhaseStatus.COMPLETED
        assert phase_state.completed_at >= completion_time
        assert AnalysisPhase.STRUCTURE_ANALYSIS in state.completed_phases
        
        # Cache file should be created
        cache_file = state_manager.cache_dir / PHASE_CACHE_FILES[AnalysisPhase.STRUCTURE_ANALYSIS]
        assert cache_file.exists()
        
        with open(cache_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == cache_data
    
    @pytest.mark.asyncio
    async def test_fail_phase(self, state_manager):
        """Test failing a phase."""
        await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        error_message = "Network timeout"
        await state_manager.fail_phase(AnalysisPhase.FILE_ANALYSIS, error_message)
        
        state = state_manager.get_current_state()
        phase_state = state.phases[AnalysisPhase.FILE_ANALYSIS]
        
        assert phase_state.status == PhaseStatus.FAILED
        assert phase_state.progress.error_message == error_message
    
    @pytest.mark.asyncio
    async def test_start_phase_without_session(self, state_manager):
        """Test starting a phase without an active session."""
        with pytest.raises(InvalidStateError):
            await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
    
    @pytest.mark.asyncio
    async def test_complete_phase_without_session(self, state_manager):
        """Test completing a phase without an active session."""
        with pytest.raises(InvalidStateError):
            await state_manager.complete_phase(AnalysisPhase.FILE_ANALYSIS)


class TestProgressTracking:
    """Test progress tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_update_progress(self, state_manager):
        """Test updating progress within a phase."""
        await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        await state_manager.update_progress(
            AnalysisPhase.FILE_ANALYSIS,
            completed=10,
            failed=1,
            total=50,
            current_item="component.tsx"
        )
        
        state = state_manager.get_current_state()
        progress = state.phases[AnalysisPhase.FILE_ANALYSIS].progress
        
        assert progress.completed == 10
        assert progress.failed == 1
        assert progress.total == 50
        assert progress.current_item == "component.tsx"
        assert state.total_files == 50  # Should update total_files for FILE_ANALYSIS
    
    @pytest.mark.asyncio
    async def test_update_progress_partial(self, state_manager):
        """Test updating only some progress fields."""
        await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Initial update
        await state_manager.update_progress(
            AnalysisPhase.FILE_ANALYSIS,
            completed=5,
            total=20
        )
        
        # Partial update
        await state_manager.update_progress(
            AnalysisPhase.FILE_ANALYSIS,
            completed=10,
            current_item="new_file.py"
        )
        
        state = state_manager.get_current_state()
        progress = state.phases[AnalysisPhase.FILE_ANALYSIS].progress
        
        assert progress.completed == 10
        assert progress.failed == 0  # Should remain unchanged
        assert progress.total == 20  # Should remain unchanged
        assert progress.current_item == "new_file.py"
    
    @pytest.mark.asyncio
    async def test_update_progress_without_session(self, state_manager):
        """Test updating progress without an active session."""
        with pytest.raises(InvalidStateError):
            await state_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, completed=5)


class TestCacheManagement:
    """Test cache data management."""
    
    @pytest.mark.asyncio
    async def test_load_cache_data(self, state_manager):
        """Test loading cache data for a phase."""
        # Initially no cache data
        result = await state_manager.load_cache_data(AnalysisPhase.STRUCTURE_ANALYSIS)
        assert result is None
        
        # Create cache data
        cache_data = {"test": "data", "files": ["a.py", "b.py"]}
        await state_manager.initialize_new_session()
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, cache_data)
        
        # Load cache data
        loaded_data = await state_manager.load_cache_data(AnalysisPhase.STRUCTURE_ANALYSIS)
        assert loaded_data == cache_data
    
    @pytest.mark.asyncio
    async def test_load_cache_data_no_cache_file_defined(self, state_manager):
        """Test loading cache data for phase without cache file."""
        result = await state_manager.load_cache_data(AnalysisPhase.SETUP)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_load_cache_data_corrupted_file(self, state_manager):
        """Test loading corrupted cache data."""
        await state_manager.initialize_new_session()
        
        # Create corrupted cache file
        cache_file = state_manager.cache_dir / PHASE_CACHE_FILES[AnalysisPhase.STRUCTURE_ANALYSIS]
        with open(cache_file, 'w') as f:
            f.write("invalid json {")
        
        result = await state_manager.load_cache_data(AnalysisPhase.STRUCTURE_ANALYSIS)
        assert result is None


class TestSessionCleanup:
    """Test session cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_session(self, state_manager):
        """Test cleaning up completed session."""
        await state_manager.initialize_new_session()
        
        # Create some cache files
        cache_data = {"test": "data"}
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, cache_data)
        await state_manager.complete_phase(AnalysisPhase.FILE_DISCOVERY, cache_data)
        
        # Verify files exist
        assert state_manager.progress_file.exists()
        assert (state_manager.cache_dir / "structure.json").exists()
        assert (state_manager.cache_dir / "file_discovery.json").exists()
        
        # Cleanup
        await state_manager.cleanup_completed_session()
        
        # Files should be removed
        assert not state_manager.progress_file.exists()
        assert not (state_manager.cache_dir / "structure.json").exists()
        assert not (state_manager.cache_dir / "file_discovery.json").exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_session(self, state_manager):
        """Test cleaning up failed session."""
        await state_manager.initialize_new_session()
        cache_data = {"test": "data"}
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, cache_data)
        
        # Verify files exist
        assert state_manager.progress_file.exists()
        assert (state_manager.cache_dir / "structure.json").exists()
        
        # Cleanup failed session
        await state_manager.cleanup_failed_session()
        
        # Files should be removed
        assert not state_manager.progress_file.exists()
        assert not (state_manager.cache_dir / "structure.json").exists()


class TestResumeFromState:
    """Test resuming from existing state."""
    
    @pytest.mark.asyncio
    async def test_resume_from_existing_state(self, state_manager):
        """Test resuming from existing state."""
        # Create initial session
        original_session_id = await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await state_manager.update_progress(AnalysisPhase.FILE_ANALYSIS, completed=10, total=50)
        
        # Create new manager and resume
        new_manager = AnalysisStateManager(str(state_manager.directory))
        resumed_state = await new_manager.resume_from_existing_state()
        
        assert resumed_state.session_id == original_session_id
        assert resumed_state.current_phase == AnalysisPhase.FILE_ANALYSIS
        assert resumed_state.phases[AnalysisPhase.FILE_ANALYSIS].progress.completed == 10
        assert new_manager.get_current_state() == resumed_state
    
    @pytest.mark.asyncio
    async def test_resume_from_missing_state(self, state_manager):
        """Test resuming when no state file exists."""
        with pytest.raises(ResumeError):
            await state_manager.resume_from_existing_state()
    
    @pytest.mark.asyncio
    async def test_resume_from_corrupted_state(self, state_manager):
        """Test resuming from corrupted state file."""
        # Create corrupted state file
        with open(state_manager.progress_file, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(ResumeError):
            await state_manager.resume_from_existing_state()


class TestStatePersistence:
    """Test state persistence and serialization."""
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_restarts(self, state_manager, sample_analysis_options):
        """Test that state persists correctly across manager restarts."""
        # Create session with progress
        session_id = await state_manager.initialize_new_session(sample_analysis_options)
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        await state_manager.update_progress(
            AnalysisPhase.FILE_ANALYSIS,
            completed=25,
            failed=3,
            total=100,
            current_item="test.py"
        )
        await state_manager.complete_phase(AnalysisPhase.STRUCTURE_ANALYSIS, {"test": "data"})
        
        # Create new manager and load state
        new_manager = AnalysisStateManager(str(state_manager.directory))
        loaded_state = await new_manager.resume_from_existing_state()
        
        # Verify all data is preserved
        assert loaded_state.session_id == session_id
        assert loaded_state.analysis_options == sample_analysis_options
        assert loaded_state.current_phase == AnalysisPhase.FILE_ANALYSIS
        assert AnalysisPhase.STRUCTURE_ANALYSIS in loaded_state.completed_phases
        
        file_analysis_progress = loaded_state.phases[AnalysisPhase.FILE_ANALYSIS].progress
        assert file_analysis_progress.completed == 25
        assert file_analysis_progress.failed == 3
        assert file_analysis_progress.total == 100
        assert file_analysis_progress.current_item == "test.py"
        
        structure_phase = loaded_state.phases[AnalysisPhase.STRUCTURE_ANALYSIS]
        assert structure_phase.status == PhaseStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_atomic_state_saving(self, state_manager):
        """Test that state saving is atomic (uses temporary file)."""
        await state_manager.initialize_new_session()
        
        # Patch open to simulate failure during write
        original_open = open
        
        def failing_open(file, mode='r', **kwargs):
            if str(file).endswith('.tmp') and 'w' in mode:
                raise IOError("Simulated write failure")
            return original_open(file, mode, **kwargs)
        
        with patch('builtins.open', side_effect=failing_open):
            with pytest.raises(StateManagerError):
                await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Original progress file should still exist and be valid
        assert state_manager.progress_file.exists()
        with open(state_manager.progress_file, 'r') as f:
            data = json.load(f)
        assert data['current_phase'] == AnalysisPhase.SETUP.value


class TestConcurrencyAndLocking:
    """Test concurrency safety and locking."""
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self, state_manager):
        """Test that concurrent state updates are properly serialized."""
        await state_manager.initialize_new_session()
        await state_manager.start_phase(AnalysisPhase.FILE_ANALYSIS)
        
        # Create multiple concurrent progress updates
        async def update_progress(value):
            await state_manager.update_progress(
                AnalysisPhase.FILE_ANALYSIS,
                completed=value
            )
        
        # Run concurrent updates
        await asyncio.gather(
            update_progress(10),
            update_progress(20),
            update_progress(30)
        )
        
        # Final state should be consistent (last update wins)
        state = state_manager.get_current_state()
        progress = state.phases[AnalysisPhase.FILE_ANALYSIS].progress
        assert progress.completed in [10, 20, 30]  # One of the values should be final