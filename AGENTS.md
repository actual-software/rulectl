## Project Structure & Module Organization

1. All Python library packages MUST include an __init__.py file to define the package namespace and public API surface
2. Distributable libraries MUST include a setup.py or pyproject.toml file with complete package metadata including name, version, dependencies, and entry points
3. Library initialization code SHOULD handle runtime warnings and error conditions gracefully through dedicated utility modules
4. Package structure MUST follow Python namespace conventions with clear separation between public API and internal implementation
5. Library __init__.py files SHOULD NOT contain complex business logic or perform expensive operations at import time
6. Libraries MAY include utility modules for cross-cutting concerns such as warning suppression, logging configuration, or environment setup
7. Libraries intended for command-line execution SHOULD provide a __main__.py file to enable 'python -m package_name' invocation

## Build, Test, and Development Commands

1. All Python build scripts and CLI tools MUST follow the established configuration pattern detected in analyzer.py, baml_init.py, build.py, fix_dependencies.py, and cli.py
2. Dependency management and initialization logic MUST be centralized and follow consistent import and setup patterns across all tooling modules
3. Build automation scripts SHOULD separate configuration, execution, and error handling concerns following the pattern established in build.py
4. Dependency resolution and fixing utilities MUST NOT introduce alternative patterns that conflict with the established fix_dependencies.py approach
5. Teams MAY extend the base patterns with additional functionality provided core architectural principles are preserved

## Coding Style & Naming Conventions

1. Use Jotai for global state management
2. All Python CLI scripts MUST use argparse for command-line argument parsing
3. CLI scripts MUST separate argument parsing logic from business logic through modular function design
4. Scripts MUST implement a main() function that serves as the primary entry point
5. CLI tools SHOULD provide help text and descriptions for all arguments using argparse help parameter
6. Scripts SHOULD organize related functionality into separate functions that can be tested independently
7. Error handling SHOULD be implemented with clear error messages and appropriate exit codes
8. Scripts MAY use subparsers for complex multi-command CLI tools
9. New CLI commands SHOULD be structured using the same command registration and argument parsing patterns as existing tools in rulectl/cli.py
10. Components SHOULD use naming conventions (e.g., underscore prefix) or visibility modifiers to distinguish private implementation from public API

## Testing Guidelines

1. External API integrations SHOULD provide mock implementations or test doubles to enable offline development and testing

## Commit & Pull Request Guidelines

1. Breaking changes to public API contracts MUST follow semantic versioning with major version increments

## Security & Configuration Tips

1. All design system theme configuration MUST be sourced from centralized runtime configuration sources rather than hardcoded values
2. Runtime configuration sources MUST support hierarchical precedence (e.g., environment variables > user preferences > defaults)
3. Configuration sources MUST be accessible through a consistent API or interface across all modules that require theming
4. Theme configuration SHOULD be validated at runtime to ensure type safety and prevent invalid values from propagating
5. Configuration changes SHOULD be reactive, allowing theme updates without full application reload where technically feasible
6. Configuration sources MAY include remote configuration services for enterprise deployments requiring centralized theme management
7. Components MUST NOT directly access environment variables or configuration files; they MUST use the centralized configuration API
8. API credentials and tokens MUST be stored in environment variables or secure credential stores, never hardcoded in source files

## Public API Design & Contracts

1. All design system components MUST explicitly declare their public API surface through documented interfaces, type definitions, or API contracts
2. Public API contracts MUST include component props, events, slots, methods, and CSS custom properties exposed for external use
3. Internal implementation details, private methods, and undocumented properties MUST NOT be considered part of the public API contract
4. Public API contracts SHOULD be validated through automated tooling in the build pipeline to detect unintended exposure
5. Components MAY expose experimental APIs with explicit unstable markers that are exempt from semantic versioning guarantees

## External API Integration & Rate Limiting

1. All external API clients MUST implement explicit authentication token management with tracking and refresh capabilities
2. External API client modules MUST handle rate limiting, timeouts, and transient failures with exponential backoff retry logic
3. All external API calls MUST be wrapped in try-except blocks with specific exception handling for network, authentication, and API-specific errors
4. External API clients SHOULD implement usage tracking and logging to monitor API consumption, costs, and performance metrics
5. External API client modules SHOULD expose consistent interfaces (e.g., common base classes or protocols) to enable polymorphic usage and dependency injection
6. External API clients MAY implement caching strategies to reduce API calls and improve performance where appropriate
7. All external API clients MUST implement rate limiting using a centralized rate limiter component to enforce provider-specific rate limits
8. Token consumption MUST be tracked and monitored using a dedicated token tracker for APIs with token-based billing or quota systems
9. Rate limiters MUST implement exponential backoff with jitter when rate limits are exceeded to prevent thundering herd problems
10. API clients SHOULD pre-emptively throttle requests when approaching known rate limits rather than waiting for 429 responses
11. Token tracking SHOULD provide visibility into consumption patterns through logging and metrics for capacity planning
12. Rate limiting configuration MUST be externalized and configurable per API provider without code changes
13. Utility functions interacting with external APIs SHOULD encapsulate rate limiting and token tracking logic to ensure consistent application
14. Systems MAY implement circuit breakers in conjunction with rate limiters to fail fast when external APIs are consistently unavailable

## Public API Endpoint Development

1. All public-facing API endpoints MUST implement rate limiting to prevent resource exhaustion and abuse
2. API rate limiters MUST track consumption on a per-client or per-token basis to enforce individual quotas
3. Token tracking mechanisms MUST be implemented to monitor API usage patterns and enforce quota limits
4. Rate limiting logic SHOULD be centralized in dedicated utility modules (e.g., rate_limiter.py, token_tracker.py) to ensure consistency
5. Rate limit violations SHOULD return HTTP 429 (Too Many Requests) with appropriate retry-after headers
6. API responses SHOULD include rate limit status headers (e.g., X-RateLimit-Remaining, X-RateLimit-Reset) to inform clients
7. Different API endpoints MAY have different rate limit tiers based on resource intensity and business requirements