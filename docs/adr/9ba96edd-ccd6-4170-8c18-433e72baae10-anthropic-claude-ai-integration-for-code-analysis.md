Evidence from 5 Python files (rulectl/cli.py, rulectl/analyzer.py, rulectl/token_tracker.py, fix_dependencies.py, requirements.txt) shows consistent integration with Anthropic's Claude AI API. Implementation committed by Ethan (2025-09-02, commit b4a0531a) includes BAML client setup, API key management via environment variables, and Claude Sonnet 4 model configuration. This pattern spans 2,573 lines across core analysis modules, indicating a fundamental architectural decision to use Claude AI for repository analysis and rule generation.

## Policies
- Use Anthropic Claude API (via BAML client) for all AI-powered code analysis in Python files
- Default to 'claude-sonnet-4-20250514' model for analysis tasks unless specific model requirements dictate otherwise
- Store Anthropic API keys in environment variables (ANTHROPIC_API_KEY) and never hardcode credentials in Python source files
- Validate BAML client initialization before performing any AI operations using check_baml_client() validation
- Import AI functionality from baml_client.async_client module for all async AI operations
- Track token usage for all Claude API calls to monitor costs and usage patterns
- Set BAML_LOG environment variable to 'OFF' to disable verbose logging in production

## Instructions
- Add baml-py>=0.202.1 dependency to requirements.txt for Claude AI integration
- Initialize BAML client at application startup before any analysis operations
- Load ANTHROPIC_API_KEY from environment using os.getenv() with fallback to credentials.json
- Configure rate limiting and token tracking for all Claude API calls
- Use async/await pattern with BAML client for concurrent AI operations
- Import types from baml_client.types (e.g., StaticAnalysisRule, FileInfo) for type safety
- Implement error handling for missing API keys with user-friendly error messages