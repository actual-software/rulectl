Evidence from rulectl/rate_limiter.py (219 lines) and rulectl/cli.py shows sophisticated rate limiting using token bucket algorithm. Implementation by Ethan (2025-09-02, commit b4a0531a) includes RateLimiter class with per-minute and per-day limits, async wait_if_needed() method, and execute_with_rate_limiting() wrapper. Configuration loaded from YAML file (rate_limiting.yaml) allows customizable limits. This pattern prevents API throttling and manages costs for Anthropic Claude API calls across concurrent async operations.

## Policies
- Implement token bucket algorithm for all API rate limiting in Python applications
- Use RateLimiter class with configurable per-minute and per-day request limits for external API clients
- Load rate limit configuration from YAML files (rate_limiting.yaml) in config directory
- Implement async wait_if_needed() method that delays execution using asyncio.sleep() when limits are exceeded
- Track request timestamps using time.time() and maintain sliding window of recent requests
- Define RateLimitStrategy enum with ROLLING_WINDOW strategy for time-based rate limiting
- Provide get_status() method returning current usage statistics (requests made, remaining, reset time)

## Instructions
- Create @dataclass RateLimitConfig with requests_per_minute and requests_per_day fields
- Implement RateLimiter class with __init__ accepting RateLimitConfig and storing request history
- Use collections.deque or list to track timestamps of recent API requests
- Implement async wait_if_needed() that calculates delay based on token replenishment rate
- Load configuration from YAML using yaml.safe_load() and create RateLimitConfig instance
- Wrap API calls with execute_with_rate_limiting() to automatically enforce limits
- Calculate time until next available slot by examining oldest request in sliding window