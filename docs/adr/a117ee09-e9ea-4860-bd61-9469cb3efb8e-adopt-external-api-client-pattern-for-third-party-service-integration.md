The codebase requires integration with external third-party services and APIs across multiple utility modules (utils.py, token_tracker.py, git_utils.py). These integrations need to handle authentication, rate limiting, error handling, and network failures consistently. Without a standardized approach, each module would implement its own client logic, leading to code duplication, inconsistent error handling, and maintenance challenges. The pattern emerged to address the need for reliable, maintainable, and testable external service interactions.

## Policies
- Implement dedicated external API client abstractions that encapsulate all interactions with third-party services. Each client provides a clean interface for external service operations, handles authentication and authorization, implements retry logic and rate limiting, and provides consistent error handling. The pattern separates external API concerns from business logic, making the codebase more modular and testable. Clients are designed with clear boundaries that isolate external dependencies and provide mock-friendly interfaces for testing.

## Instructions
- Positive: Consistent error handling and retry logic across all external API interactions
- Positive: Improved testability through clear abstraction boundaries and mock-friendly interfaces
- Positive: Centralized authentication and rate limiting logic reduces code duplication
- Positive: Easier to swap or upgrade external service integrations without affecting business logic
- Positive: Better observability and monitoring of external API calls through centralized client code
- Negative: Additional abstraction layer adds initial development overhead
- Negative: May introduce over-engineering for simple API calls
- Negative: Requires developers to understand the client abstraction pattern
- Trade-off: More code to maintain but significantly better separation of concerns