---
title: Architectural Decisions
type: steering
inclusion: always
---

# Repository-Wide ADRs (All Files)

## ADR: Use Python For All Development Purposes

1. use python for everything, and use python 3+

---

# Python File ADRs (*.py)

## ADR: Git Repository Integration for Provenance Tracking

1. Use subprocess module with git commands for all Git repository operations in Python applications
2. Validate Git repository existence before performing any git operations using subprocess.run(['git', 'rev-parse', '--git-dir'])
3. Integrate gitignore patterns for file filtering using pathspec module with 'gitwildmatch' pattern type
4. Implement git blame analysis to track file provenance including author, date, and commit metadata
5. Detect repository main branch dynamically by checking for 'main', 'master', or current branch
6. Use Path.resolve() for absolute path resolution when working with Git repository paths
7. Extract git metadata (commit hash, author, email, date) for all analyzed files to support provenance tracking

---

## ADR: Asynchronous Programming with Asyncio for Concurrent Operations

1. Use async/await pattern for all I/O-bound operations including API calls and file processing in Python modules
2. Import asyncio module for event loop management and concurrency primitives
3. Define async functions with 'async def' for any operation that performs network requests or file I/O
4. Use 'await' keyword for all async function calls and use asyncio.sleep() instead of time.sleep() in async contexts
5. Implement async context managers for resource management in asynchronous code
6. Use asyncio.gather() or asyncio.create_task() for concurrent execution of multiple async operations
7. Call asyncio.run() at the entry point to execute async main functions from synchronous code

---

## ADR: Click Framework for CLI Application Architecture

1. Use Click framework (click>=8.0.0) for all command-line interface implementation in Python applications
2. Structure CLI with @click.group() decorator at the top level and @click.command() for subcommands
3. Define command-line options using @click.option() with type hints, help text, and default values
4. Use @click.argument() for required positional arguments with click.Choice() for enumerated values
5. Include colorama>=0.4.6 for cross-platform colored terminal output in all CLI applications
6. Implement --verbose/-v flag for debug output and --force/-f flag to skip confirmation prompts
7. Provide clear help text for all commands and options using the help parameter

---

## ADR: Anthropic Claude AI Integration for Code Analysis

1. Use Anthropic Claude API (via BAML client) for all AI-powered code analysis in Python files
2. Default to 'claude-sonnet-4-20250514' model for analysis tasks unless specific model requirements dictate otherwise
3. Store Anthropic API keys in environment variables (ANTHROPIC_API_KEY) and never hardcode credentials in Python source files
4. Validate BAML client initialization before performing any AI operations using check_baml_client() validation
5. Import AI functionality from baml_client.async_client module for all async AI operations
6. Track token usage for all Claude API calls to monitor costs and usage patterns
7. Set BAML_LOG environment variable to 'OFF' to disable verbose logging in production