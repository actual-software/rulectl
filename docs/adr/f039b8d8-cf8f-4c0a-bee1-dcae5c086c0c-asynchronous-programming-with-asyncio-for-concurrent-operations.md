Evidence from 3 files (rulectl/cli.py, rulectl/analyzer.py, rulectl/rate_limiter.py) totaling 2,205 lines demonstrates comprehensive async/await implementation. Pattern introduced by Ethan (2025-09-02, commit b4a0531a) includes async functions for file analysis (async def analyze_file), rate limiting (async def wait_if_needed), and batch processing (async def execute_batch_with_rate_limiting). The asyncio pattern enables concurrent AI API calls while respecting rate limits, significantly improving performance for repository-wide analysis operations.

## Policies
- Use async/await pattern for all I/O-bound operations including API calls and file processing in Python modules
- Import asyncio module for event loop management and concurrency primitives
- Define async functions with 'async def' for any operation that performs network requests or file I/O
- Use 'await' keyword for all async function calls and use asyncio.sleep() instead of time.sleep() in async contexts
- Implement async context managers for resource management in asynchronous code
- Use asyncio.gather() or asyncio.create_task() for concurrent execution of multiple async operations
- Call asyncio.run() at the entry point to execute async main functions from synchronous code

## Instructions
- Add 'async' keyword before 'def' for functions that perform I/O operations
- Add 'await' before calling async functions, API clients, or asyncio.sleep()
- Wrap synchronous entry points with asyncio.run(async_main_function())
- Use 'async with' for async context managers (e.g., async API clients)
- Batch API requests and use asyncio.gather() for concurrent execution
- Implement rate limiting with async delays using asyncio.sleep() between requests
- Handle exceptions in async code with try/except around await statements