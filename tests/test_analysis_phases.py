#!/usr/bin/env python3
"""
Test module for analysis_phases.py
Tests the phase definitions, utilities, and state classes.
"""

import pytest
from datetime import datetime, timezone

from rulectl.analysis_phases import (
    AnalysisPhase, PhaseStatus, PhaseProgress, PhaseState, AnalysisState,
    PHASE_ORDER, RESUMABLE_PHASES, PHASE_CACHE_FILES,
    get_next_phase, get_previous_phase, can_resume_from_phase,
    get_required_cache_files, describe_phase
)


class TestAnalysisPhase:
    """Test AnalysisPhase enum."""
    
    def test_phase_values(self):
        """Test that all phases have expected string values."""
        assert AnalysisPhase.SETUP.value == "setup"
        assert AnalysisPhase.STRUCTURE_ANALYSIS.value == "structure_analysis"
        assert AnalysisPhase.FILE_DISCOVERY.value == "file_discovery"
        assert AnalysisPhase.FILE_ANALYSIS.value == "file_analysis"
        assert AnalysisPhase.GIT_ANALYSIS.value == "git_analysis"
        assert AnalysisPhase.RULE_SYNTHESIS.value == "rule_synthesis"
        assert AnalysisPhase.SAVE_COMPLETE.value == "save_complete"
    
    def test_phase_order_completeness(self):
        """Test that PHASE_ORDER contains all phases."""
        all_phases = set(AnalysisPhase)
        order_phases = set(PHASE_ORDER)
        assert all_phases == order_phases
    
    def test_phase_order_sequence(self):
        """Test that phases are in logical order."""
        expected_order = [
            AnalysisPhase.SETUP,
            AnalysisPhase.STRUCTURE_ANALYSIS,
            AnalysisPhase.FILE_DISCOVERY,
            AnalysisPhase.FILE_ANALYSIS,
            AnalysisPhase.GIT_ANALYSIS,
            AnalysisPhase.RULE_SYNTHESIS,
            AnalysisPhase.SAVE_COMPLETE
        ]
        assert PHASE_ORDER == expected_order


class TestPhaseStatus:
    """Test PhaseStatus enum."""
    
    def test_status_values(self):
        """Test that all statuses have expected string values."""
        assert PhaseStatus.PENDING.value == "pending"
        assert PhaseStatus.IN_PROGRESS.value == "in_progress"
        assert PhaseStatus.COMPLETED.value == "completed"
        assert PhaseStatus.FAILED.value == "failed"
        assert PhaseStatus.SKIPPED.value == "skipped"


class TestPhaseProgress:
    """Test PhaseProgress dataclass."""
    
    def test_default_initialization(self):
        """Test default values for PhaseProgress."""
        progress = PhaseProgress()
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.total == 0
        assert progress.current_item is None
        assert progress.error_message is None
    
    def test_custom_initialization(self):
        """Test custom values for PhaseProgress."""
        progress = PhaseProgress(
            completed=10,
            failed=2,
            total=50,
            current_item="test.py",
            error_message="API timeout"
        )
        assert progress.completed == 10
        assert progress.failed == 2
        assert progress.total == 50
        assert progress.current_item == "test.py"
        assert progress.error_message == "API timeout"


class TestPhaseState:
    """Test PhaseState dataclass."""
    
    def test_default_initialization(self):
        """Test default values for PhaseState."""
        state = PhaseState()
        assert state.status == PhaseStatus.PENDING
        assert state.started_at is None
        assert state.completed_at is None
        assert state.cache_file is None
        assert state.progress is None
        assert state.metadata == {}
    
    def test_custom_initialization(self):
        """Test custom values for PhaseState."""
        now = datetime.now(timezone.utc)
        progress = PhaseProgress(completed=5, total=10)
        
        state = PhaseState(
            status=PhaseStatus.IN_PROGRESS,
            started_at=now,
            cache_file="test.json",
            progress=progress,
            metadata={"test": "value"}
        )
        
        assert state.status == PhaseStatus.IN_PROGRESS
        assert state.started_at == now
        assert state.cache_file == "test.json"
        assert state.progress == progress
        assert state.metadata == {"test": "value"}


class TestAnalysisState:
    """Test AnalysisState dataclass."""
    
    def test_initialization(self):
        """Test AnalysisState initialization."""
        now = datetime.now(timezone.utc)
        phases = {
            AnalysisPhase.SETUP: PhaseState(status=PhaseStatus.COMPLETED),
            AnalysisPhase.FILE_ANALYSIS: PhaseState(status=PhaseStatus.IN_PROGRESS)
        }
        
        state = AnalysisState(
            session_id="test-session",
            started_at=now,
            directory="/test/path",
            current_phase=AnalysisPhase.FILE_ANALYSIS,
            completed_phases=[AnalysisPhase.SETUP],
            phases=phases,
            total_files=100,
            analysis_options={"verbose": True}
        )
        
        assert state.session_id == "test-session"
        assert state.started_at == now
        assert state.directory == "/test/path"
        assert state.current_phase == AnalysisPhase.FILE_ANALYSIS
        assert state.completed_phases == [AnalysisPhase.SETUP]
        assert state.phases == phases
        assert state.total_files == 100
        assert state.analysis_options == {"verbose": True}
    
    def test_default_analysis_options(self):
        """Test that analysis_options defaults to empty dict."""
        now = datetime.now(timezone.utc)
        state = AnalysisState(
            session_id="test",
            started_at=now,
            directory="/test",
            current_phase=AnalysisPhase.SETUP,
            completed_phases=[],
            phases={}
        )
        assert state.analysis_options == {}


class TestPhaseUtilities:
    """Test phase utility functions."""
    
    def test_get_next_phase(self):
        """Test get_next_phase function."""
        assert get_next_phase(AnalysisPhase.SETUP) == AnalysisPhase.STRUCTURE_ANALYSIS
        assert get_next_phase(AnalysisPhase.FILE_ANALYSIS) == AnalysisPhase.GIT_ANALYSIS
        assert get_next_phase(AnalysisPhase.SAVE_COMPLETE) is None
    
    def test_get_previous_phase(self):
        """Test get_previous_phase function."""
        assert get_previous_phase(AnalysisPhase.SETUP) is None
        assert get_previous_phase(AnalysisPhase.STRUCTURE_ANALYSIS) == AnalysisPhase.SETUP
        assert get_previous_phase(AnalysisPhase.SAVE_COMPLETE) == AnalysisPhase.RULE_SYNTHESIS
    
    def test_can_resume_from_phase(self):
        """Test can_resume_from_phase function."""
        # Resumable phases
        assert can_resume_from_phase(AnalysisPhase.FILE_ANALYSIS) is True
        assert can_resume_from_phase(AnalysisPhase.GIT_ANALYSIS) is True
        assert can_resume_from_phase(AnalysisPhase.RULE_SYNTHESIS) is True
        assert can_resume_from_phase(AnalysisPhase.SAVE_COMPLETE) is True
        
        # Non-resumable phases
        assert can_resume_from_phase(AnalysisPhase.SETUP) is False
        assert can_resume_from_phase(AnalysisPhase.STRUCTURE_ANALYSIS) is False
        assert can_resume_from_phase(AnalysisPhase.FILE_DISCOVERY) is False
    
    def test_get_required_cache_files(self):
        """Test get_required_cache_files function."""
        # Setup phase - no previous phases
        assert get_required_cache_files(AnalysisPhase.SETUP) == []
        
        # Structure analysis - only setup before it (no cache file)
        assert get_required_cache_files(AnalysisPhase.STRUCTURE_ANALYSIS) == []
        
        # File analysis - should include structure and file_discovery cache files
        expected_files = ["structure.json", "file_discovery.json"]
        assert get_required_cache_files(AnalysisPhase.FILE_ANALYSIS) == expected_files
        
        # Git analysis - should include all previous cache files
        expected_files = ["structure.json", "file_discovery.json", "files.json"]
        assert get_required_cache_files(AnalysisPhase.GIT_ANALYSIS) == expected_files
        
        # Rule synthesis - should include all previous cache files
        expected_files = ["structure.json", "file_discovery.json", "files.json", "git_stats.json"]
        assert get_required_cache_files(AnalysisPhase.RULE_SYNTHESIS) == expected_files
    
    def test_describe_phase(self):
        """Test describe_phase function."""
        assert describe_phase(AnalysisPhase.SETUP) == "API key validation and repository setup"
        assert describe_phase(AnalysisPhase.STRUCTURE_ANALYSIS) == "Repository structure analysis"
        assert describe_phase(AnalysisPhase.FILE_DISCOVERY) == "File discovery and AI review"
        assert describe_phase(AnalysisPhase.FILE_ANALYSIS) == "Individual file analysis"
        assert describe_phase(AnalysisPhase.GIT_ANALYSIS) == "Git history and file importance analysis"
        assert describe_phase(AnalysisPhase.RULE_SYNTHESIS) == "Rule generation and clustering"
        assert describe_phase(AnalysisPhase.SAVE_COMPLETE) == "Saving results and cleanup"


class TestPhaseConstants:
    """Test phase constants and configurations."""
    
    def test_resumable_phases_subset(self):
        """Test that RESUMABLE_PHASES is a subset of all phases."""
        all_phases = set(AnalysisPhase)
        assert RESUMABLE_PHASES.issubset(all_phases)
    
    def test_phase_cache_files_mapping(self):
        """Test that PHASE_CACHE_FILES maps to valid phases."""
        all_phases = set(AnalysisPhase)
        cache_phases = set(PHASE_CACHE_FILES.keys())
        assert cache_phases.issubset(all_phases)
    
    def test_phase_cache_files_content(self):
        """Test that cache file names are reasonable."""
        expected_cache_files = {
            AnalysisPhase.STRUCTURE_ANALYSIS: "structure.json",
            AnalysisPhase.FILE_DISCOVERY: "file_discovery.json",
            AnalysisPhase.FILE_ANALYSIS: "files.json",
            AnalysisPhase.GIT_ANALYSIS: "git_stats.json",
            AnalysisPhase.RULE_SYNTHESIS: "synthesis.json"
        }
        
        assert PHASE_CACHE_FILES == expected_cache_files
        
        # Verify all cache file names end with .json
        for cache_file in PHASE_CACHE_FILES.values():
            assert cache_file.endswith('.json')