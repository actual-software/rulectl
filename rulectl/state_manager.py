#!/usr/bin/env python3
"""
Analysis state management for Rulectl.
Handles saving, loading, and resuming analysis state across interruptions.
"""

import os
import json
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from .analysis_phases import (
    AnalysisPhase, PhaseStatus, PhaseProgress, PhaseState, AnalysisState,
    PHASE_ORDER, RESUMABLE_PHASES, PHASE_CACHE_FILES, can_resume_from_phase,
    get_required_cache_files, describe_phase
)

logger = logging.getLogger(__name__)


class StateManagerError(Exception):
    """Base exception for state manager errors."""
    pass


class InvalidStateError(StateManagerError):
    """Raised when analysis state is invalid or corrupted."""
    pass


class ResumeError(StateManagerError):
    """Raised when resume operation fails."""
    pass


class AnalysisStateManager:
    """Manages analysis state persistence and resume functionality."""
    
    def __init__(self, directory: str):
        """Initialize state manager for a specific directory.
        
        Args:
            directory: Repository directory path
        """
        self.directory = Path(directory).resolve()
        self.state_dir = self.directory / ".rulectl"
        self.progress_file = self.state_dir / "progress.json"
        self.cache_dir = self.state_dir / "cache"
        
        # Ensure directories exist
        self.state_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        self._current_state: Optional[AnalysisState] = None
        self._lock = asyncio.Lock()
    
    async def initialize_new_session(self, analysis_options: Dict[str, Any] = None) -> str:
        """Initialize a new analysis session.
        
        Args:
            analysis_options: Options for the analysis session
            
        Returns:
            Session ID
        """
        async with self._lock:
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Initialize phase states
            phases = {}
            for phase in PHASE_ORDER:
                phases[phase] = PhaseState(
                    status=PhaseStatus.PENDING,
                    cache_file=PHASE_CACHE_FILES.get(phase)
                )
            
            self._current_state = AnalysisState(
                session_id=session_id,
                started_at=now,
                directory=str(self.directory),
                current_phase=AnalysisPhase.SETUP,
                completed_phases=[],
                phases=phases,
                analysis_options=analysis_options or {}
            )
            
            await self._save_state()
            logger.info(f"Initialized new analysis session: {session_id}")
            return session_id
    
    async def detect_incomplete_analysis(self) -> Optional[Dict[str, Any]]:
        """Check if there's an incomplete analysis to resume.
        
        Returns:
            Dict with resume information if incomplete analysis found, None otherwise
        """
        if not self.progress_file.exists():
            return None
        
        try:
            with open(self.progress_file, 'r') as f:
                state_data = json.load(f)
            
            # Parse the state
            state = self._parse_state_data(state_data)
            
            # Check if analysis is incomplete
            current_phase_state = state.phases.get(state.current_phase)
            if not current_phase_state:
                return None
            
            # Analysis is incomplete if current phase is in progress or failed
            if current_phase_state.status in [PhaseStatus.IN_PROGRESS, PhaseStatus.FAILED]:
                # Verify we can resume from this phase
                if can_resume_from_phase(state.current_phase):
                    # Check if required cache files exist
                    required_files = get_required_cache_files(state.current_phase)
                    missing_files = []
                    for cache_file in required_files:
                        cache_path = self.cache_dir / cache_file
                        if not cache_path.exists():
                            missing_files.append(cache_file)
                    
                    resume_info = {
                        "session_id": state.session_id,
                        "started_at": state.started_at.isoformat(),
                        "current_phase": state.current_phase.value,
                        "phase_description": describe_phase(state.current_phase),
                        "completed_phases": [p.value for p in state.completed_phases],
                        "total_files": state.total_files,
                        "can_resume": len(missing_files) == 0,
                        "missing_cache_files": missing_files
                    }
                    
                    # Add progress info if available
                    if current_phase_state.progress:
                        resume_info["progress"] = {
                            "completed": current_phase_state.progress.completed,
                            "failed": current_phase_state.progress.failed,
                            "total": current_phase_state.progress.total,
                            "current_item": current_phase_state.progress.current_item
                        }
                    
                    return resume_info
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse existing progress file: {e}")
            return None
    
    async def resume_from_existing_state(self) -> AnalysisState:
        """Resume analysis from existing state.
        
        Returns:
            Loaded analysis state
            
        Raises:
            ResumeError: If resume operation fails
        """
        async with self._lock:
            try:
                with open(self.progress_file, 'r') as f:
                    state_data = json.load(f)
                
                self._current_state = self._parse_state_data(state_data)
                logger.info(f"Resumed analysis session: {self._current_state.session_id}")
                return self._current_state
                
            except Exception as e:
                raise ResumeError(f"Failed to resume from existing state: {e}")
    
    async def start_phase(self, phase: AnalysisPhase) -> None:
        """Mark a phase as started.
        
        Args:
            phase: Phase to start
        """
        async with self._lock:
            if not self._current_state:
                raise InvalidStateError("No active analysis session")
            
            self._current_state.current_phase = phase
            phase_state = self._current_state.phases[phase]
            phase_state.status = PhaseStatus.IN_PROGRESS
            phase_state.started_at = datetime.now(timezone.utc)
            
            await self._save_state()
            logger.debug(f"Started phase: {phase.value}")
    
    async def complete_phase(self, phase: AnalysisPhase, cache_data: Any = None) -> None:
        """Mark a phase as completed and save cache data.
        
        Args:
            phase: Phase to complete
            cache_data: Data to cache for this phase
        """
        async with self._lock:
            if not self._current_state:
                raise InvalidStateError("No active analysis session")
            
            phase_state = self._current_state.phases[phase]
            phase_state.status = PhaseStatus.COMPLETED
            phase_state.completed_at = datetime.now(timezone.utc)
            
            # Add to completed phases if not already there
            if phase not in self._current_state.completed_phases:
                self._current_state.completed_phases.append(phase)
            
            # Save cache data if provided
            if cache_data is not None and phase in PHASE_CACHE_FILES:
                cache_file = self.cache_dir / PHASE_CACHE_FILES[phase]
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2, default=self._json_serializer)
                logger.debug(f"Saved cache data for phase {phase.value} to {cache_file}")
            
            await self._save_state()
            logger.debug(f"Completed phase: {phase.value}")
    
    async def fail_phase(self, phase: AnalysisPhase, error_message: str) -> None:
        """Mark a phase as failed.
        
        Args:
            phase: Phase that failed
            error_message: Error description
        """
        async with self._lock:
            if not self._current_state:
                raise InvalidStateError("No active analysis session")
            
            phase_state = self._current_state.phases[phase]
            phase_state.status = PhaseStatus.FAILED
            if phase_state.progress:
                phase_state.progress.error_message = error_message
            else:
                phase_state.progress = PhaseProgress(error_message=error_message)
            
            await self._save_state()
            logger.error(f"Failed phase {phase.value}: {error_message}")
    
    async def update_progress(self, phase: AnalysisPhase, completed: int = None, 
                            failed: int = None, total: int = None, 
                            current_item: str = None) -> None:
        """Update progress within a phase.
        
        Args:
            phase: Phase to update
            completed: Number of completed items
            failed: Number of failed items
            total: Total number of items
            current_item: Currently processing item
        """
        async with self._lock:
            if not self._current_state:
                raise InvalidStateError("No active analysis session")
            
            phase_state = self._current_state.phases[phase]
            if not phase_state.progress:
                phase_state.progress = PhaseProgress()
            
            if completed is not None:
                phase_state.progress.completed = completed
            if failed is not None:
                phase_state.progress.failed = failed
            if total is not None:
                phase_state.progress.total = total
                # Also update the overall total files count
                if phase == AnalysisPhase.FILE_ANALYSIS:
                    self._current_state.total_files = total
            if current_item is not None:
                phase_state.progress.current_item = current_item
            
            # Save state less frequently during progress updates to avoid I/O overhead
            # Only save every 10 items or if it's been more than 30 seconds
            should_save = False
            if completed is not None and completed % 10 == 0:
                should_save = True
            elif phase_state.started_at:
                elapsed = datetime.now(timezone.utc) - phase_state.started_at
                if elapsed.total_seconds() > 30:
                    should_save = True
            
            if should_save:
                await self._save_state()
    
    async def load_cache_data(self, phase: AnalysisPhase) -> Optional[Any]:
        """Load cached data for a phase.
        
        Args:
            phase: Phase to load cache for
            
        Returns:
            Cached data or None if not available
        """
        if phase not in PHASE_CACHE_FILES:
            return None
        
        cache_file = self.cache_dir / PHASE_CACHE_FILES[phase]
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache data for {phase.value}: {e}")
            return None
    
    async def cleanup_completed_session(self) -> None:
        """Clean up state files after successful completion."""
        async with self._lock:
            try:
                if self.progress_file.exists():
                    self.progress_file.unlink()
                
                # Clean up cache directory
                if self.cache_dir.exists():
                    for cache_file in self.cache_dir.iterdir():
                        if cache_file.is_file():
                            cache_file.unlink()
                    
                    # Remove cache directory if empty
                    if not any(self.cache_dir.iterdir()):
                        self.cache_dir.rmdir()
                
                logger.info("Cleaned up completed analysis session")
                
            except Exception as e:
                logger.warning(f"Failed to cleanup session files: {e}")
    
    async def cleanup_failed_session(self) -> None:
        """Clean up state files after user chooses not to resume."""
        await self.cleanup_completed_session()
    
    def get_current_state(self) -> Optional[AnalysisState]:
        """Get the current analysis state."""
        return self._current_state
    
    async def _save_state(self) -> None:
        """Save current state to disk."""
        if not self._current_state:
            return
        
        state_dict = self._state_to_dict(self._current_state)
        
        # Write to temporary file first, then rename for atomic operation
        temp_file = self.progress_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(state_dict, f, indent=2, default=self._json_serializer)
            
            # Atomic rename
            temp_file.replace(self.progress_file)
            
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise StateManagerError(f"Failed to save state: {e}")
    
    def _parse_state_data(self, state_data: Dict[str, Any]) -> AnalysisState:
        """Parse state data from JSON into AnalysisState object."""
        try:
            # Parse phases
            phases = {}
            for phase_name, phase_data in state_data['phases'].items():
                phase = AnalysisPhase(phase_name)
                
                progress = None
                if phase_data.get('progress'):
                    prog_data = phase_data['progress']
                    progress = PhaseProgress(
                        completed=prog_data.get('completed', 0),
                        failed=prog_data.get('failed', 0),
                        total=prog_data.get('total', 0),
                        current_item=prog_data.get('current_item'),
                        error_message=prog_data.get('error_message')
                    )
                
                phase_state = PhaseState(
                    status=PhaseStatus(phase_data['status']),
                    started_at=self._parse_datetime(phase_data.get('started_at')),
                    completed_at=self._parse_datetime(phase_data.get('completed_at')),
                    cache_file=phase_data.get('cache_file'),
                    progress=progress,
                    metadata=phase_data.get('metadata', {})
                )
                
                phases[phase] = phase_state
            
            # Parse completed phases
            completed_phases = [AnalysisPhase(p) for p in state_data['completed_phases']]
            
            return AnalysisState(
                session_id=state_data['session_id'],
                started_at=self._parse_datetime(state_data['started_at']),
                directory=state_data['directory'],
                current_phase=AnalysisPhase(state_data['current_phase']),
                completed_phases=completed_phases,
                phases=phases,
                total_files=state_data.get('total_files', 0),
                analysis_options=state_data.get('analysis_options', {})
            )
            
        except Exception as e:
            raise InvalidStateError(f"Failed to parse state data: {e}")
    
    def _state_to_dict(self, state: AnalysisState) -> Dict[str, Any]:
        """Convert AnalysisState to dictionary for JSON serialization."""
        phases_dict = {}
        for phase, phase_state in state.phases.items():
            phase_dict = {
                'status': phase_state.status.value,
                'cache_file': phase_state.cache_file,
                'metadata': phase_state.metadata
            }
            
            if phase_state.started_at:
                phase_dict['started_at'] = phase_state.started_at.isoformat()
            if phase_state.completed_at:
                phase_dict['completed_at'] = phase_state.completed_at.isoformat()
            
            if phase_state.progress:
                phase_dict['progress'] = {
                    'completed': phase_state.progress.completed,
                    'failed': phase_state.progress.failed,
                    'total': phase_state.progress.total,
                    'current_item': phase_state.progress.current_item,
                    'error_message': phase_state.progress.error_message
                }
            
            phases_dict[phase.value] = phase_dict
        
        return {
            'session_id': state.session_id,
            'started_at': state.started_at.isoformat(),
            'directory': state.directory,
            'current_phase': state.current_phase.value,
            'completed_phases': [p.value for p in state.completed_phases],
            'phases': phases_dict,
            'total_files': state.total_files,
            'analysis_options': state.analysis_options
        }
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")