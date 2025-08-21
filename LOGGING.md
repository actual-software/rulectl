# Rulectl Logging Implementation

This document describes the comprehensive logging system implemented for Rulectl, providing detailed observability for analysis runs, API calls, and debugging.

## Overview

The logging system provides:
- **Structured JSON logging** for machine-readable logs
- **Multiple log types** (main, API, analysis, debug)
- **Automatic log rotation** to prevent disk space issues
- **CLI integration** with configurable log levels
- **Real-time log viewing** with follow mode

## Log Structure

### Log Directory
- Default location: `~/.rulectl/logs/`
- Configurable via `--log-dir` option
- Created automatically with proper permissions (700)

### Log Files

1. **Main Log** (`rulectl.log`)
   - General application events
   - User actions and command execution
   - High-level analysis flow
   - Rotating: 10MB max, 5 backups

2. **API Calls Log** (`api-calls-YYYY-MM.log`)
   - Detailed API call tracking
   - Rate limiting events
   - Token usage and costs
   - Request/response timing
   - Monthly rotation: 20MB max, 10 backups

3. **Analysis Log** (`analysis-YYYY-MM-DD.log`)
   - Daily analysis run summaries
   - File processing results
   - Rule generation statistics
   - User-friendly format for review

4. **Debug Log** (`debug.log`)
   - Structured JSON format
   - Detailed technical information
   - Exception traces
   - Rotating: 50MB max, 3 backups

## CLI Integration

### New Command Line Options

```bash
# Logging level control
rulectl start --log-level VERBOSE         # Enable detailed API call logging
rulectl start --log-level DEBUG           # Enable full debug logging
rulectl start --log-dir /custom/path      # Custom log directory

# View logs
rulectl config logs                       # Show recent main logs
rulectl config logs --log-type api        # Show API logs
rulectl config logs --follow             # Follow logs in real-time
rulectl config logs --lines 100          # Show more lines
```

### Available Log Levels
- `ERROR`: Only critical errors
- `WARNING`: Warnings and errors
- `INFO`: General information, warnings, and errors (default)
- `VERBOSE`: Detailed API call tracking + INFO level
- `DEBUG`: Full technical debugging information

### Available Log Types
- `main`: General application logs
- `api`: API call details and timing
- `analysis`: Analysis run summaries
- `debug`: Technical debugging information

## Structured Logging Features

### API Call Tracking
```json
{
  "timestamp": "2025-08-21T10:30:45.123456",
  "level": "INFO",
  "logger": "rulectl.api",
  "message": "API call completed successfully",
  "function": "AnalyzeFileForConventions",
  "execution_time_seconds": 2.34,
  "result_type": "StaticAnalysisResult"
}
```

### Rate Limiting Events
```json
{
  "timestamp": "2025-08-21T10:30:45.123456",
  "level": "WARNING", 
  "logger": "rulectl.api",
  "message": "Rate limit reached - applying delay",
  "delay_seconds": 12.5,
  "current_requests": 5,
  "max_requests": 5,
  "strategy": "adaptive"
}
```

### Token Usage Tracking
```json
{
  "timestamp": "2025-08-21T10:30:45.123456",
  "level": "INFO",
  "logger": "rulectl.api", 
  "message": "Token usage tracked from BAML collector",
  "phase": "file_analysis",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 1234,
  "output_tokens": 567,
  "source": "collector"
}
```

### File Analysis Events
```json
{
  "timestamp": "2025-08-21T10:30:45.123456",
  "level": "INFO",
  "logger": "rulectl.analyzer",
  "message": "File analysis completed successfully", 
  "file_path": "src/components/Button.tsx",
  "rules_found": 3
}
```

## Error Handling

### Comprehensive Error Logging
- All exceptions are logged with full context
- Error types and stack traces captured
- Fallback logging if main system fails
- User-friendly error messages with log location hints

### Rate Limit Error Handling
- Automatic retry logic with exponential backoff
- Detailed rate limit violation tracking
- Provider-specific error detection (Anthropic, OpenAI)

## Log Rotation and Cleanup

### Automatic Rotation
- **Main logs**: 10MB files, 5 backups
- **API logs**: 20MB files, 10 backups  
- **Debug logs**: 50MB files, 3 backups
- **Analysis logs**: New file daily

### Cleanup Features
- `cleanup_old_logs()` method for maintenance
- Configurable retention periods
- Safe cleanup with error handling

## Performance Considerations

### Efficient Logging
- Structured logging avoids string formatting overhead
- Conditional debug logging
- Separate handlers prevent cross-contamination
- JSON format enables efficient parsing

### Console Output Control
- Warning/Error level to console by default
- Verbose mode shows INFO level
- Debug information only to files
- User-facing messages remain clean

## Integration Points

### Rate Limiter Integration
- All API calls logged with timing
- Rate limit violations tracked
- Backoff strategy events recorded
- Success/failure metrics captured

### Token Tracker Integration  
- Real-time token usage logging
- Cost tracking per API call
- Phase-based usage breakdown
- Fallback estimation logging

### Analyzer Integration
- File analysis progress tracking
- Rule synthesis statistics
- Git analysis metrics
- Error context preservation

## Usage Examples

### Basic Analysis with Logging
```bash
# Run analysis with detailed API logging
rulectl start --log-level VERBOSE

# Run analysis with full debug logging
rulectl start --log-level DEBUG

# View the results
rulectl config logs --log-type analysis
```

### API Monitoring
```bash
# Monitor API calls in real-time
rulectl config logs --log-type api --follow

# Check recent API errors
rulectl config logs --log-type debug --lines 100
```

### Debugging Issues
```bash
# Enable maximum logging detail
rulectl start --log-level DEBUG --verbose

# Review all logs after failure
rulectl config logs --log-type main
rulectl config logs --log-type api
rulectl config logs --log-type debug
```

### Custom Log Directory
```bash
# Use project-specific logs
rulectl start --log-dir ./project-logs --log-level VERBOSE

# View project logs (note: --log-dir not needed for viewing, uses current config)
rulectl config logs
```

## Implementation Files

### Core Logging Module
- `rulectl/logging_config.py` - Centralized logging configuration
- `JSONFormatter` class for structured output
- `StructuredLogger` wrapper for enhanced logging
- `LoggingConfig` class for setup and management

### Integration Updates
- `rulectl/cli.py` - CLI options and initialization
- `rulectl/analyzer.py` - Analysis event logging  
- `rulectl/rate_limiter.py` - API call tracking
- `rulectl/token_tracker.py` - Usage monitoring

## Benefits

### For Users
- **Transparency**: Full visibility into what Rulectl is doing
- **Debugging**: Easy troubleshooting with detailed logs
- **Monitoring**: Track API usage and costs
- **Audit Trail**: Complete record of analysis runs

### For Developers
- **Observability**: Deep insights into system behavior
- **Performance**: Identify bottlenecks and optimization opportunities
- **Reliability**: Comprehensive error tracking and recovery
- **Maintenance**: Structured data for automated monitoring

## Future Enhancements

### Potential Additions
- Log aggregation to external systems (ELK, Splunk)
- Metrics export (Prometheus, Grafana)
- Alert integration for critical errors
- Log analysis tools and dashboards
- Performance profiling integration
- Cloud logging service integration

### Configuration Improvements
- Environment variable configuration
- YAML configuration files
- Log level per component
- Custom log format templates
- Log filtering and sampling