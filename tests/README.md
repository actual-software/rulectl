# Rulectl Resume Functionality Tests

This test suite covers the new resume functionality introduced in the `feat/resume-incomplete-analysis` branch, which allows Rulectl to continue analysis from where it left off after an interruption.

## Test Structure

### Unit Tests

#### `test_analysis_phases.py`
Tests the core phase definitions and utilities:
- Phase enumerations and their values
- Phase status tracking
- Phase progress data structures
- Phase utilities (get_next_phase, can_resume_from_phase, etc.)
- Phase constants and configurations

#### `test_state_manager.py`
Tests the AnalysisStateManager class:
- Session initialization and management
- Incomplete analysis detection
- Phase lifecycle management (start, complete, fail)
- Progress tracking within phases
- Cache data management
- Session cleanup
- Resume from existing state
- State persistence and atomic writes
- Concurrency safety with locking

### Integration Tests

#### `test_cli_resume.py`
Tests CLI integration with resume features:
- Detection of incomplete analysis on startup
- `--continue` flag for automatic resume
- User prompts for resume confirmation
- Phase tracking during analysis
- Session cleanup on completion
- Error handling scenarios
- Verbose output with resume information

#### `test_analyzer_resume.py`
Tests RepoAnalyzer integration with state management:
- Analyzer initialization with state manager
- Resumable file analysis functionality
- Loading cached results from previous runs
- Error handling during file analysis
- Progress tracking integration
- Token tracker integration
- Backward compatibility without state manager

#### `test_integration_resume.py`
End-to-end integration tests:
- Complete analysis without interruption
- Resume from file analysis interruption
- Multiple interruptions and resumes
- Large repository simulation
- File system edge cases:
  - Concurrent state file access
  - Disk space exhaustion
  - Permission issues
  - Corrupted cache files
  - Atomic write interruptions

## Running the Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test Categories

Unit tests only:
```bash
python -m pytest tests/test_analysis_phases.py tests/test_state_manager.py -v
```

Integration tests only:
```bash
python -m pytest tests/test_cli_resume.py tests/test_analyzer_resume.py tests/test_integration_resume.py -v
```

### Run Tests for Specific Components

State manager tests:
```bash
python -m pytest tests/test_state_manager.py -v
```

CLI resume tests:
```bash
python -m pytest tests/test_cli_resume.py -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=rulectl --cov-report=html
```

## Test Coverage

The test suite provides comprehensive coverage for:

1. **State Management** - All aspects of saving, loading, and managing analysis state
2. **Resume Detection** - Identifying incomplete analysis and determining if resume is possible
3. **Progress Tracking** - Tracking progress within phases and persisting it across sessions
4. **Cache Management** - Saving and loading intermediate results for resume
5. **Error Handling** - Graceful handling of failures, corrupted files, and system issues
6. **CLI Integration** - User interaction for resume decisions and command-line flags
7. **File System Edge Cases** - Handling permission issues, disk space, concurrent access
8. **Backward Compatibility** - Ensuring functionality works without state management

## Key Test Scenarios

### Successful Resume
1. Analysis starts and processes some files
2. Interruption occurs (Ctrl+C, crash, etc.)
3. User restarts rulectl
4. System detects incomplete analysis
5. User confirms resume
6. Analysis continues from last checkpoint
7. Completion and cleanup

### Missing Cache Files
1. Incomplete analysis detected
2. Required cache files are missing
3. System reports inability to resume
4. Fresh analysis starts

### Multiple Resume Attempts
1. First interruption during structure analysis
2. Resume and continue to file analysis
3. Second interruption during file analysis
4. Resume and complete entire analysis

### Large Repository Handling
- Progress saving is optimized (every 10 files or 30 seconds)
- Memory-efficient state management
- Handles 1000+ file repositories

## Dependencies

The tests require:
- pytest
- pytest-asyncio
- pyyaml
- python-dotenv
- pathspec

Install with:
```bash
pip install pytest pytest-asyncio pyyaml python-dotenv pathspec
```

## Mocking

The test suite uses `conftest.py` to mock the BAML client modules, allowing tests to run without the actual BAML dependencies installed. This ensures tests can run in CI/CD environments without API keys or external dependencies.