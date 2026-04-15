---

## Architecture Decision Records

<adr_governance source="docs/adr/">
ADRs govern validated architectural standards for this project.
Full ADR documents: @docs/adr/
</adr_governance>

<activation>
These directives are ALWAYS ACTIVE. Claude Code MUST apply all rules in this
document to every code generation, modification, and review action within this
project. No exceptions unless explicitly noted per-rule.
</activation>

---

### Verification Protocol

<verification_protocol>
All rules in this document follow the **Verify → Fix → Repeat** loop.
</verification_protocol>

After generating or modifying code for any rule, Claude Code MUST:

1. **RUN** the targeted verification command(s) in the rule's **Verify** block.
2. **CAPTURE** the full command output (stdout + stderr).
3. **EVALUATE** whether the **Accept when** criteria are satisfied.
4. **IF FAILING:** diagnose the root cause, apply a fix, and re-run from step 1.
5. **IF PASSING:** include the passing output as inline evidence before proposing further changes.
6. **MAX ITERATIONS:** 5 attempts per rule. If still failing after 5 attempts, STOP and report the failure with all captured outputs.

<enforcement>
Compliance is not optional. Claude Code must not skip verification steps, assume
correctness, or defer verification to a later task. Evidence of a passing
verification run must accompany every code change that touches a governed area.
</enforcement>

---

## ADR 1: YAML Configuration Management for Application Settings

1. Use YAML format for all application configuration files in Python projects (rate limiting, pricing, settings)
2. Include pyyaml>=6.0 dependency for YAML parsing and python-dotenv>=1.0.0 for environment variable loading
3. Load YAML configuration using yaml.safe_load() for security (prevents arbitrary code execution)
4. Store configuration files in dedicated 'config' directory at project root level
5. Use Path(__file__).parent.parent / 'config' / 'filename.yaml' for cross-platform config file paths
6. Load environment variables using python-dotenv's load_dotenv() at application startup
7. Implement fallback values when configuration files or environment variables are missing

---

## ADR 2: Token Usage Monitoring and Cost Tracking for AI Operations

1. Implement TokenTracker class for monitoring AI API token usage and cost across all Python applications using LLMs
2. Track both input and output tokens separately for accurate cost calculation and reporting
3. Load model pricing configuration from YAML files with per-model input/output token costs
4. Record token usage per analysis phase using track_call_from_collector() with phase identifiers
5. Calculate cumulative costs in real-time based on current token counts and model pricing
6. Set default model to 'claude-sonnet-4-20250514' from pricing configuration '_default' key
7. Provide get_total_tokens() method returning cumulative input/output token counts for reporting

---

## ADR 3: Token Bucket Rate Limiting for API Call Management

1. Implement token bucket algorithm for all API rate limiting in Python applications
2. Use RateLimiter class with configurable per-minute and per-day request limits for external API clients
3. Load rate limit configuration from YAML files (rate_limiting.yaml) in config directory
4. Implement async wait_if_needed() method that delays execution using asyncio.sleep() when limits are exceeded
5. Track request timestamps using time.time() and maintain sliding window of recent requests
6. Define RateLimitStrategy enum with ROLLING_WINDOW strategy for time-based rate limiting
7. Provide get_status() method returning current usage statistics (requests made, remaining, reset time)

---

## ADR 4: Git Repository Integration for Provenance Tracking

1. Use subprocess module with git commands for all Git repository operations in Python applications
2. Validate Git repository existence before performing any git operations using subprocess.run(['git', 'rev-parse', '--git-dir'])
3. Integrate gitignore patterns for file filtering using pathspec module with 'gitwildmatch' pattern type
4. Implement git blame analysis to track file provenance including author, date, and commit metadata
5. Detect repository main branch dynamically by checking for 'main', 'master', or current branch
6. Use Path.resolve() for absolute path resolution when working with Git repository paths
7. Extract git metadata (commit hash, author, email, date) for all analyzed files to support provenance tracking

---

## ADR 5: Asynchronous Programming with Asyncio for Concurrent Operations

1. Use async/await pattern for all I/O-bound operations including API calls and file processing in Python modules
2. Import asyncio module for event loop management and concurrency primitives
3. Define async functions with 'async def' for any operation that performs network requests or file I/O
4. Use 'await' keyword for all async function calls and use asyncio.sleep() instead of time.sleep() in async contexts
5. Implement async context managers for resource management in asynchronous code
6. Use asyncio.gather() or asyncio.create_task() for concurrent execution of multiple async operations
7. Call asyncio.run() at the entry point to execute async main functions from synchronous code

---

## ADR 6: Click Framework for CLI Application Architecture

1. Use Click framework (click>=8.0.0) for all command-line interface implementation in Python applications
2. Structure CLI with @click.group() decorator at the top level and @click.command() for subcommands
3. Define command-line options using @click.option() with type hints, help text, and default values
4. Use @click.argument() for required positional arguments with click.Choice() for enumerated values
5. Include colorama>=0.4.6 for cross-platform colored terminal output in all CLI applications
6. Implement --verbose/-v flag for debug output and --force/-f flag to skip confirmation prompts
7. Provide clear help text for all commands and options using the help parameter

---

## ADR 7: Anthropic Claude AI Integration for Code Analysis

1. Use Anthropic Claude API (via BAML client) for all AI-powered code analysis in Python files
2. Default to 'claude-sonnet-4-20250514' model for analysis tasks unless specific model requirements dictate otherwise
3. Store Anthropic API keys in environment variables (ANTHROPIC_API_KEY) and never hardcode credentials in Python source files
4. Validate BAML client initialization before performing any AI operations using check_baml_client() validation
5. Import AI functionality from baml_client.async_client module for all async AI operations
6. Track token usage for all Claude API calls to monitor costs and usage patterns
7. Set BAML_LOG environment variable to 'OFF' to disable verbose logging in production

---

## ADR 8: Use Python For All Development Purposes

1. use python for everything, and use python 3+