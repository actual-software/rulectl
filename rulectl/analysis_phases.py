#!/usr/bin/env python3
"""
Analysis phases and state definitions for Rulectl.
Defines the pipeline phases and their state management.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime


class AnalysisPhase(Enum):
    """Enumeration of analysis pipeline phases."""
    SETUP = "setup"
    STRUCTURE_ANALYSIS = "structure_analysis"
    FILE_DISCOVERY = "file_discovery"
    FILE_ANALYSIS = "file_analysis"
    GIT_ANALYSIS = "git_analysis"
    RULE_SYNTHESIS = "rule_synthesis"
    SAVE_COMPLETE = "save_complete"


class PhaseStatus(Enum):
    """Status of an analysis phase."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseProgress:
    """Progress tracking for a specific analysis phase."""
    completed: int = 0
    failed: int = 0
    total: int = 0
    current_item: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PhaseState:
    """State information for an analysis phase."""
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cache_file: Optional[str] = None
    progress: Optional[PhaseProgress] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisState:
    """Complete analysis session state."""
    session_id: str
    started_at: datetime
    directory: str
    current_phase: AnalysisPhase
    completed_phases: List[AnalysisPhase]
    phases: Dict[AnalysisPhase, PhaseState]
    total_files: int = 0
    analysis_options: Dict[str, Any] = None

    def __post_init__(self):
        if self.analysis_options is None:
            self.analysis_options = {}


# Phase dependencies and resume logic
PHASE_ORDER = [
    AnalysisPhase.SETUP,
    AnalysisPhase.STRUCTURE_ANALYSIS,
    AnalysisPhase.FILE_DISCOVERY,
    AnalysisPhase.FILE_ANALYSIS,
    AnalysisPhase.GIT_ANALYSIS,
    AnalysisPhase.RULE_SYNTHESIS,
    AnalysisPhase.SAVE_COMPLETE
]

# Which phases can be resumed from (vs. requiring restart)
RESUMABLE_PHASES = {
    AnalysisPhase.FILE_ANALYSIS,
    AnalysisPhase.GIT_ANALYSIS,
    AnalysisPhase.RULE_SYNTHESIS,
    AnalysisPhase.SAVE_COMPLETE
}

# Cache file patterns for each phase
PHASE_CACHE_FILES = {
    AnalysisPhase.STRUCTURE_ANALYSIS: "structure.json",
    AnalysisPhase.FILE_DISCOVERY: "file_discovery.json",
    AnalysisPhase.FILE_ANALYSIS: "files.json",
    AnalysisPhase.GIT_ANALYSIS: "git_stats.json",
    AnalysisPhase.RULE_SYNTHESIS: "synthesis.json"
}


def get_next_phase(current_phase: AnalysisPhase) -> Optional[AnalysisPhase]:
    """Get the next phase in the analysis pipeline."""
    try:
        current_index = PHASE_ORDER.index(current_phase)
        if current_index + 1 < len(PHASE_ORDER):
            return PHASE_ORDER[current_index + 1]
    except ValueError:
        pass
    return None


def get_previous_phase(current_phase: AnalysisPhase) -> Optional[AnalysisPhase]:
    """Get the previous phase in the analysis pipeline."""
    try:
        current_index = PHASE_ORDER.index(current_phase)
        if current_index > 0:
            return PHASE_ORDER[current_index - 1]
    except ValueError:
        pass
    return None


def can_resume_from_phase(phase: AnalysisPhase) -> bool:
    """Check if analysis can be resumed from the given phase."""
    return phase in RESUMABLE_PHASES


def get_required_cache_files(phase: AnalysisPhase) -> List[str]:
    """Get list of cache files required to resume from a given phase."""
    required_files = []
    
    # Add cache files for all previous completed phases
    phase_index = PHASE_ORDER.index(phase)
    for prev_phase in PHASE_ORDER[:phase_index]:
        if prev_phase in PHASE_CACHE_FILES:
            required_files.append(PHASE_CACHE_FILES[prev_phase])
    
    return required_files


def describe_phase(phase: AnalysisPhase) -> str:
    """Get human-readable description of an analysis phase."""
    descriptions = {
        AnalysisPhase.SETUP: "API key validation and repository setup",
        AnalysisPhase.STRUCTURE_ANALYSIS: "Repository structure analysis",
        AnalysisPhase.FILE_DISCOVERY: "File discovery and AI review",
        AnalysisPhase.FILE_ANALYSIS: "Individual file analysis",
        AnalysisPhase.GIT_ANALYSIS: "Git history and file importance analysis",
        AnalysisPhase.RULE_SYNTHESIS: "Rule generation and clustering",
        AnalysisPhase.SAVE_COMPLETE: "Saving results and cleanup"
    }
    return descriptions.get(phase, f"Unknown phase: {phase}")