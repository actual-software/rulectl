# Resume Incomplete Analysis Feature

This document describes the new resume functionality in Rulectl that allows users to continue from where they left off if an analysis is interrupted.

## Overview

Rulectl now automatically tracks analysis progress and can resume from interruptions caused by:
- Network failures
- API rate limits
- System crashes
- User interruption (Ctrl+C)
- Power outages
- Memory issues

## How It Works

### Analysis Phases

The analysis pipeline is divided into distinct phases:

1. **Setup** - API key validation and repository setup
2. **Structure Analysis** - Repository structure analysis  
3. **File Discovery** - File discovery and AI review
4. **File Analysis** - Individual file analysis (resumable)
5. **Git Analysis** - Git history and file importance analysis (resumable)
6. **Rule Synthesis** - Rule generation and clustering (resumable)
7. **Save Complete** - Saving results and cleanup (resumable)

### State Persistence

Progress is automatically saved to `.rulectl/` directory:

```
.rulectl/
├── progress.json      # Current analysis state
└── cache/            # Intermediate data cache
    ├── structure.json    # Repository structure
    ├── files.json        # File analysis results  
    ├── git_stats.json    # Git analysis data
    └── synthesis.json    # Rule synthesis data
```

### Resume Detection

When you run `rulectl start`, it automatically:

1. Checks for incomplete analysis in `.rulectl/progress.json`
2. Validates that required cache files exist
3. Shows a warning prompt if incomplete analysis is found
4. Offers to continue from where you left off

## Usage

### Interactive Resume (Default)

```bash
rulectl start
```

If an incomplete analysis is detected, you'll see:

```
======================================================
⚠️  WARNING ⚠️  
======================================================
We notice that the last time rulectl was run, analysis didn't complete.

📊 Previous session: 1a2b3c4d...
📅 Started: 2025-01-15T10:30:00Z
📋 Was working on: Individual file analysis
📈 Progress: 45/150 files completed
⚠️  2 files failed during analysis
🔄 Was processing: src/components/Button.tsx

💾 Found 3 completed phases
✅ Completed: setup, structure_analysis, file_discovery

======================================================

Would you like to continue where you left off? [Y/n]: 
```

### Automatic Resume

Use the `--continue` flag to automatically resume without prompting:

```bash
rulectl start --continue
```

This will:
- Automatically detect incomplete analysis
- Resume from the last checkpoint
- Show brief progress information
- Continue the analysis pipeline

### Fresh Start

If you want to start fresh instead of resuming:

1. Answer 'n' to the resume prompt, or
2. Delete the `.rulectl/` directory manually

## Resume Capabilities

### What Can Be Resumed

- **File Analysis**: Resumes from the last successfully analyzed file
- **Git Analysis**: Resumes git history processing  
- **Rule Synthesis**: Resumes rule generation and clustering
- **Save Complete**: Resumes final saving and cleanup

### What Cannot Be Resumed

- **Setup**: Quick phase, always restarts
- **Structure Analysis**: Fast phase, always restarts  
- **File Discovery**: Fast phase, always restarts

### Progress Tracking

During file analysis, progress is saved every 10 files to minimize overhead while ensuring recent progress isn't lost.

## Error Handling

### Missing Cache Files

If cache files are missing, you'll see:

```
⚠️  Found incomplete analysis but some cache files are missing:
   ❌ files.json
   ❌ git_stats.json
🔄 Starting fresh analysis...
```

### Corrupted State

If the state file is corrupted, Rulectl will:
- Log a warning
- Start fresh analysis
- Clean up corrupted files

### Resume Failures

If resume fails for any reason:
- The analysis will continue from the failed phase
- Progress will be preserved where possible
- Error details will be logged

## Technical Details

### State Management

The `AnalysisStateManager` class handles:
- Session initialization and tracking
- Phase progress updates
- Cache data persistence
- Resume validation and loading

### Thread Safety

- State updates use async locks
- Atomic file operations prevent corruption
- Temporary files used for safe writes

### Performance

- Minimal overhead during normal operation
- Progressive state saving during long operations
- Efficient cache file management

## Troubleshooting

### Clear Incomplete Analysis

To manually clear an incomplete analysis:

```bash
rm -rf .rulectl/
```

### Debug Resume Issues

Use verbose mode to see detailed resume information:

```bash
rulectl start --verbose
```

### Force Fresh Analysis

Use the force flag to skip confirmation prompts:

```bash
rulectl start --force
```

This will still detect and offer resume, but skip other confirmations.

## Examples

### Successful Resume

```bash
$ rulectl start
🔄 Continuing from previous incomplete analysis...
📊 Session: 1a2b3c4d...
📋 Phase: Individual file analysis
📈 Progress: 45/150 files completed, 2 failed

🔍 Starting repository analysis...
📁 Repository structure analyzed
📋 Final analysis list: 150 files
🔎 Analyzing files...
Resuming file analysis: 45 files already completed, 105 remaining
...
```

### Using --continue Flag

```bash
$ rulectl start --continue
🔄 Continuing from previous incomplete analysis...
📊 Session: 1a2b3c4d...  
📋 Phase: Individual file analysis
📈 Progress: 45/150 files completed, 2 failed
...
```

### No Resume Needed

```bash
$ rulectl start
✅ Valid repository detected
🔍 Starting repository analysis...
```

## Best Practices

1. **Let it Resume**: Generally accept resume prompts unless you have a specific reason to restart
2. **Use --continue for Automation**: In scripts or CI/CD, use `--continue` to avoid interactive prompts
3. **Monitor Progress**: Watch for progress updates during long file analysis phases
4. **Keep Cache Files**: Don't delete `.rulectl/` directory during analysis
5. **Check Disk Space**: Ensure adequate space for cache files in large repositories

## Limitations

- Resume data is stored locally (not shared across machines)
- Cache files can be large for very large repositories
- Resume is not available for pre-v2.0 analysis sessions
- Network failures during API calls may require retry of individual operations