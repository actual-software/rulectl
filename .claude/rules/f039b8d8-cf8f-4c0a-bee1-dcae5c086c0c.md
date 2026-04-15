<rule_activation id="f039b8d8-cf8f-4c0a-bee1-dcae5c086c0c" title="Asynchronous Programming with Asyncio for Concurrent Operations" applies_to="**/*.py">
These rules are ALWAYS ACTIVE for all Python files matching `**/*.py`. Apply async/await patterns for I/O-bound operations including API calls and file processing.
</rule_activation>

### Rules

- **R-ASYNCIO-001** MUST: Use async/await pattern for all I/O-bound operations including API calls and file processing in Python modules.
- **R-ASYNCIO-002** MUST: Import asyncio module for event loop management and concurrency primitives.
- **R-ASYNCIO-003** MUST: Define async functions with 'async def' for any operation that performs network requests or file I/O.
- **R-ASYNCIO-004** MUST: Use 'await' keyword for all async function calls and use asyncio.sleep() instead of time.sleep() in async contexts.
- **R-ASYNCIO-005** MUST: Implement async context managers for resource management in asynchronous code.
- **R-ASYNCIO-006** SHOULD: Use asyncio.gather() or asyncio.create_task() for concurrent execution of multiple async operations.
- **R-ASYNCIO-007** MUST: Call asyncio.run() at the entry point to execute async main functions from synchronous code.
- **R-ASYNCIO-008** MUST: Add 'async' keyword before 'def' for functions that perform I/O operations.
- **R-ASYNCIO-009** MUST: Add 'await' before calling async functions, API clients, or asyncio.sleep().
- **R-ASYNCIO-010** MUST: Wrap synchronous entry points with asyncio.run(async_main_function()).
- **R-ASYNCIO-011** MUST: Use 'async with' for async context managers (e.g., async API clients).
- **R-ASYNCIO-012** SHOULD: Batch API requests and use asyncio.gather() for concurrent execution.
- **R-ASYNCIO-013** SHOULD: Implement rate limiting with async delays using asyncio.sleep() between requests.
- **R-ASYNCIO-014** MUST: Handle exceptions in async code with try/except around await statements.

### Verify

```bash
# Check for async def usage in Python files
grep -r "async def" --include="*.py" . || echo "No async functions found"

# Check for asyncio imports
grep -r "import asyncio" --include="*.py" . || echo "No asyncio imports found"

# Check for await keyword usage
grep -r "await " --include="*.py" . || echo "No await statements found"

# Check for asyncio.run() at entry points
grep -r "asyncio.run(" --include="*.py" . || echo "No asyncio.run() calls found"

# Check for async context managers
grep -r "async with" --include="*.py" . || echo "No async context managers found"

# Check for asyncio.gather() usage
grep -r "asyncio.gather(" --include="*.py" . || echo "No asyncio.gather() calls found"

# Check for asyncio.sleep() usage (should be used instead of time.sleep in async contexts)
grep -r "asyncio.sleep(" --include="*.py" . || echo "No asyncio.sleep() calls found"

# Verify no time.sleep in async functions (anti-pattern)
if grep -r "async def" --include="*.py" . > /dev/null; then
  echo "Checking for time.sleep() anti-pattern in async functions..."
  python3 -c "
import re
import sys
from pathlib import Path

for py_file in Path('.').rglob('*.py'):
    content = py_file.read_text()
    # Simple check: if file has 'async def' and 'time.sleep', flag it
    if 'async def' in content and 'time.sleep(' in content:
        print(f'WARNING: {py_file} contains both async def and time.sleep()')
" || true
fi
```

**Accept when:**
- All I/O-bound functions are defined with `async def`
- All async function calls use the `await` keyword
- The asyncio module is imported in files using async/await
- Entry points use `asyncio.run()` to execute async main functions
- Async context managers are used with `async with` syntax
- Multiple concurrent operations use `asyncio.gather()` or `asyncio.create_task()`
- Async functions use `asyncio.sleep()` instead of `time.sleep()`
- Exception handling wraps `await` statements with try/except blocks
- Rate limiting is implemented using async delays when making API calls

<enforcement>
Claude Code MUST NOT skip or defer verification of async/await patterns. All I/O-bound operations MUST use async/await, and verification commands MUST be executed to ensure proper asyncio implementation.
</enforcement>