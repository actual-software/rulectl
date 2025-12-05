# Development Guidelines

## Project Structure & Module Organization

The repository follows a standard Python project structure with:
- CLI commands implemented using the Click framework
- BAML client integration for AI-powered code analysis
- Environment-based configuration for API credentials

## Build, Test, and Development Commands

### CLI Implementation Standards

1. Use Click framework (click>=8.0.0) for all command-line interface implementation in Python applications
2. Structure CLI with @click.group() decorator at the top level and @click.command() for subcommands
3. Define command-line options using @click.option() with type hints, help text, and default values
4. Use @click.argument() for required positional arguments with click.Choice() for enumerated values
5. Include colorama>=0.4.6 for cross-platform colored terminal output in all CLI applications
6. Implement --verbose/-v flag for debug output and --force/-f flag to skip confirmation prompts
7. Provide clear help text for all commands and options using the help parameter

## Coding Style & Naming Conventions

### Language Standards

1. use python for everything, and use python 3+

### General Guidelines

1. Use TypeScript for all new code where applicable
2. Follow existing naming conventions in each package
3. Use descriptive variable names
4. Add docstrings for public APIs

## Testing Guidelines

1. Write unit tests for business logic
2. Include integration tests for CLI commands
3. Aim for meaningful test coverage
4. Test AI integration points with mocked responses

## Commit & Pull Request Guidelines

1. Write clear, descriptive commit messages
2. Reference issue numbers in commits
3. Keep PRs focused and reviewable
4. Ensure CI passes before requesting review

## Security & Configuration Tips

### AI Integration Standards

1. Use Anthropic Claude API (via BAML client) for all AI-powered code analysis in Python files
2. Default to 'claude-sonnet-4-20250514' model for analysis tasks unless specific model requirements dictate otherwise
3. Store Anthropic API keys in environment variables (ANTHROPIC_API_KEY) and never hardcode credentials in Python source files
4. Validate BAML client initialization before performing any AI operations using check_baml_client() validation
5. Import AI functionality from baml_client.async_client module for all async AI operations
6. Track token usage for all Claude API calls to monitor costs and usage patterns
7. Set BAML_LOG environment variable to 'OFF' to disable verbose logging in production

### General Security

1. Never commit API keys or sensitive credentials
2. Use environment variables for all configuration
3. Validate all external inputs
4. Follow principle of least privilege for API access