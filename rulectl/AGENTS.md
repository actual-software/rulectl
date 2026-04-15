---

## Architecture Decision Records

<adr_governance source="docs/adr/">
ADRs govern validated architectural standards for this project.
Full ADR documents: @docs/adr/
</adr_governance>

<activation>
These directives are ALWAYS ACTIVE. All AI coding agents MUST apply all rules in this
document to every code generation, modification, and review action within this
project. No exceptions unless explicitly noted per-rule.
</activation>

---

### Verification Protocol

<verification_protocol>
All rules in this document follow the **Verify → Fix → Repeat** loop.
</verification_protocol>

After generating or modifying code for any rule, the agent MUST:

1. **RUN** the targeted verification command(s) in the rule's **Verify** block.
2. **CAPTURE** the full command output (stdout + stderr).
3. **EVALUATE** whether the **Accept when** criteria are satisfied.
4. **IF FAILING:** diagnose the root cause, apply a fix, and re-run from step 1.
5. **IF PASSING:** include the passing output as inline evidence before proposing further changes.
6. **MAX ITERATIONS:** 5 attempts per rule. If still failing after 5 attempts, STOP and report the failure with all captured outputs.

<enforcement>
Compliance is not optional. Agents must not skip verification steps, assume
correctness, or defer verification to a later task. Evidence of a passing
verification run must accompany every code change that touches a governed area.
</enforcement>

---

## Adopt External API Integration Pattern with Rate Limiting and Token Tracking

1. Implement a centralized external API integration pattern that includes: (1) dedicated rate limiting mechanisms to respect API quotas and prevent throttling, (2) token tracking to monitor and manage API usage across requests, (3) specialized utility modules for Git operations that abstract external service interactions, and (4) shared utility functions that provide consistent error handling and retry logic for external API calls. This pattern ensures all external API interactions follow a standardized approach with built-in safeguards.

---

## Adopt External API Client Pattern for Third-Party Service Integration

1. Implement dedicated external API client abstractions that encapsulate all interactions with third-party services. Each client provides a clean interface for external service operations, handles authentication and authorization, implements retry logic and rate limiting, and provides consistent error handling. The pattern separates external API concerns from business logic, making the codebase more modular and testable. Clients are designed with clear boundaries that isolate external dependencies and provide mock-friendly interfaces for testing.