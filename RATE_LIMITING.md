# Rate Limiting Guide for Rulectl

This guide explains how to use Rulectl's built-in rate limiting features to work within API rate limits and avoid hitting "429 Too Many Requests" errors.

## Overview

Rulectl now includes intelligent rate limiting that helps you:

- **Stay within API rate limits** - Automatically delays requests to respect provider limits
- **Process files efficiently** - Uses batch processing to reduce the number of API calls
- **Handle errors gracefully** - Automatically retries with exponential backoff
- **Configure behavior** - Customize rate limiting strategy and timing

## Quick Start

### Basic Usage

The rate limiting is enabled by default and will automatically:

- Limit requests to 5 per minute (Anthropic's default limit)
- Add delays between requests to stay within limits
- Use batch processing to analyze multiple files efficiently

```bash
# Basic usage with automatic rate limiting
rulectl start

# Show current rate limiting configuration
rulectl config show

# Configure rate limiting settings
rulectl config rate-limit --requests 10 --delay 500
```

### Command Line Options

You can override rate limiting settings directly when starting analysis:

```bash
# Increase rate limit to 10 requests/minute
rulectl start --rate-limit 10

# Set custom delay between requests (500ms)
rulectl start --delay-ms 500

# Use exponential backoff strategy
rulectl start --strategy exponential

# Process files in batches of 5
rulectl start --batch-size 5

# Disable batch processing (process files one by one)
rulectl start --no-batching
```

## Configuration

### Configuration File

Rate limiting settings are stored in `config/rate_limiting.yaml`:

```yaml
# Basic rate limiting settings
rate_limits:
  anthropic:
    requests_per_minute: 5 # Default for most plans
    base_delay_ms: 1000 # 1 second base delay
    max_delay_ms: 60000 # 1 minute max delay

  openai:
    requests_per_minute: 60 # Default for most plans
    base_delay_ms: 500 # 0.5 second base delay
    max_delay_ms: 30000 # 30 seconds max delay

# Rate limiting strategy
strategy:
  type: "adaptive" # Options: constant, exponential, adaptive
  exponential_multiplier: 2.0
  jitter_ms: 100

# Batch processing
batching:
  enabled: true
  max_batch_size: 3
  delay_between_batches_ms: 2000
```

### Environment Variables

You can override settings using environment variables:

```bash
# Set rate limit to 10 requests/minute
export RULECTL_RATE_LIMIT_REQUESTS_PER_MINUTE=10

# Set base delay to 500ms
export RULECTL_RATE_LIMIT_BASE_DELAY_MS=500

# Use exponential strategy
export RULECTL_RATE_LIMIT_STRATEGY=exponential

# Disable batching
export RULECTL_RATE_LIMIT_BATCHING_ENABLED=false
```

## Rate Limiting Strategies

### 1. Constant Delay

- **Use case**: Predictable, consistent timing
- **Behavior**: Always waits the same amount of time between requests
- **Best for**: Stable API connections, predictable workloads

```bash
rulectl start --strategy constant
```

### 2. Exponential Backoff

- **Use case**: Handling failures and rate limit errors
- **Behavior**: Increases delay exponentially on failures
- **Best for**: Unstable connections, when you expect occasional errors

```bash
rulectl start --strategy exponential
```

### 3. Adaptive (Default)

- **Use case**: Automatic optimization based on conditions
- **Behavior**: Starts with base delay, increases on failures, resets on success
- **Best for**: Most use cases, automatically adjusts to conditions

```bash
rulectl start --strategy adaptive
```

## Batch Processing

Batch processing reduces the number of API calls by processing multiple files together:

### How It Works

1. Files are grouped into batches (default: 3 files per batch)
2. Each batch is processed with rate limiting applied
3. Delays are added between batches to stay within limits
4. Progress is shown for each batch

### Configuration

```bash
# Set batch size to 5 files
rulectl start --batch-size 5

# Disable batching (process files one by one)
rulectl start --no-batching
```

### Benefits

- **Fewer API calls**: Reduces total requests by grouping files
- **Better rate limit compliance**: Easier to stay within limits
- **Progress visibility**: See batch progress and timing
- **Error handling**: Failed files don't stop the entire batch

## Troubleshooting

### Common Issues

#### 1. Still Getting Rate Limit Errors

```bash
# Increase delays between requests
rulectl start --delay-ms 2000

# Reduce batch size to process fewer files at once
rulectl start --batch-size 2

# Use exponential backoff strategy
rulectl start --strategy exponential
```

#### 2. Analysis Taking Too Long

```bash
# Increase rate limit (if your plan allows it)
rulectl start --rate-limit 10

# Reduce delays between requests
rulectl start --delay-ms 500

# Increase batch size for efficiency
rulectl start --batch-size 5
```

#### 3. Want More Control

```bash
# Disable automatic batching
rulectl start --no-batching

# Use constant delay strategy
rulectl start --strategy constant

# Set custom timing
rulectl start --rate-limit 8 --delay-ms 1500
```

### Monitoring Rate Limiting

Check current status:

```bash
# Show configuration and status
rulectl config show

# Show rate limiting status specifically
rulectl config rate-limit --show
```

### Debug Information

Enable verbose mode to see rate limiting in action:

```bash
rulectl start --verbose
```

This will show:

- Rate limiting status updates
- Batch processing progress
- Delay timing information
- Error handling details

## Advanced Configuration

### Custom Rate Limiting Config

Create a custom `config/rate_limiting.yaml`:

```yaml
rate_limits:
  anthropic:
    requests_per_minute: 8 # Custom limit
    base_delay_ms: 800 # Custom delay
    max_delay_ms: 45000 # Custom max delay

strategy:
  type: "exponential"
  exponential_multiplier: 1.8
  jitter_ms: 50

batching:
  enabled: true
  max_batch_size: 4
  delay_between_batches_ms: 1500

fallback:
  enabled: true
  delay_before_fallback_ms: 3000

advanced:
  show_status: true
  log_events: true
  auto_fallback: true
```

### Provider-Specific Settings

The configuration automatically detects your API provider and applies appropriate settings:

- **Anthropic**: Default 5 requests/minute, 1 second delays
- **OpenAI**: Default 60 requests/minute, 0.5 second delays
- **Custom**: Configurable limits and delays

## Best Practices

### 1. Start Conservative

```bash
# Start with default settings
rulectl start

# Gradually increase if needed
rulectl start --rate-limit 6
rulectl start --rate-limit 8
```

### 2. Monitor Your Usage

- Check your API provider's dashboard for usage
- Use `rulectl config show` to see current settings
- Enable verbose mode to monitor progress

### 3. Use Batch Processing

- Enable batching for repositories with many files
- Adjust batch size based on your rate limits
- Monitor batch timing and adjust delays if needed

### 4. Handle Large Repositories

```bash
# For very large repositories, use smaller batches
rulectl start --batch-size 2 --delay-ms 2000

# Or process in stages by limiting files
rulectl start --max-files 100
```

## Examples

### Small Repository (5-10 files)

```bash
# Default settings work well
rulectl start
```

### Medium Repository (10-50 files)

```bash
# Slight optimization
rulectl start --batch-size 4 --delay-ms 800
```

### Large Repository (50+ files)

```bash
# Conservative settings to avoid rate limits
rulectl start --batch-size 3 --delay-ms 1500 --strategy exponential
```

### Very Large Repository (100+ files)

```bash
# Very conservative to stay within limits
rulectl start --batch-size 2 --delay-ms 3000 --strategy exponential
```

## Troubleshooting Commands

```bash
# Check if rate limiter is working
rulectl config show

# Test rate limiting configuration
python test_rate_limiting.py

# Reset to default settings
unset RULECTL_RATE_LIMIT_REQUESTS_PER_MINUTE
unset RULECTL_RATE_LIMIT_BASE_DELAY_MS
unset RULECTL_RATE_LIMIT_STRATEGY
unset RULECTL_RATE_LIMIT_BATCHING_ENABLED

# Show help for all options
rulectl start --help
rulectl config rate-limit --help
```

## Support

If you're still experiencing rate limiting issues:

1. **Check your API plan limits** - Verify your current rate limits
2. **Use more conservative settings** - Increase delays, reduce batch sizes
3. **Process in smaller chunks** - Analyze fewer files at once
4. **Contact support** - If issues persist, check the logs and report details

The rate limiting system is designed to be self-healing and will automatically adjust to your API provider's limits.
