Evidence from rulectl/token_tracker.py (235 lines) and rulectl/cli.py demonstrates real-time token tracking implemented by Ethan (2025-09-02, commit b4a0531a). TokenTracker class monitors input/output tokens (total_input_tokens, total_output_tokens), calculates costs using model pricing loaded from YAML, and provides cumulative statistics via get_total_tokens(). The track_call_from_collector() method records tokens per analysis phase, enabling cost monitoring across multi-phase analysis pipelines.

## Policies
- Implement TokenTracker class for monitoring AI API token usage and cost across all Python applications using LLMs
- Track both input and output tokens separately for accurate cost calculation and reporting
- Load model pricing configuration from YAML files with per-model input/output token costs
- Record token usage per analysis phase using track_call_from_collector() with phase identifiers
- Calculate cumulative costs in real-time based on current token counts and model pricing
- Set default model to 'claude-sonnet-4-20250514' from pricing configuration '_default' key
- Provide get_total_tokens() method returning cumulative input/output token counts for reporting

## Instructions
- Create TokenTracker class with __init__ initializing total_input_tokens and total_output_tokens to 0
- Load pricing YAML file using yaml.safe_load() and store in self.model_pricing dictionary
- Implement track_call_from_collector(phase, model) method to record token usage by phase
- Store pricing as nested dict with model names as keys and 'input'/'output' cost per 1M tokens
- Calculate costs by multiplying token count by price per million tokens
- Implement get_total_tokens() returning dictionary with 'input', 'output', and 'total' keys
- Update token counters after each API call by extracting usage from API response metadata