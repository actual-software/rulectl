"""
Token tracking utilities for AI model usage monitoring and cost estimation.

This module provides comprehensive token tracking for AI model usage in the Rules Engine.
It integrates with BAML's built-in Collector for accurate token counting when available,
and provides intelligent fallback estimation when collector data is unavailable.
"""

from pathlib import Path
import yaml


class TokenTracker:
    """Track token usage and costs with real-time monitoring and cost estimation.
    
    This class provides comprehensive token tracking for AI model usage in the Rules Engine.
    It integrates with BAML's built-in Collector for accurate token counting when available,
    and provides intelligent fallback estimation when collector data is unavailable.
    
    Features:
    - Real-time token accumulation across analysis phases
    - Dynamic cost calculation using configurable model pricing
    - BAML Collector integration for accurate token counts
    - Conservative fallback estimates when collector unavailable
    - Phase-based usage breakdown (file_analysis, rule_synthesis, etc.)
    - Configurable model pricing loaded from YAML configuration
    
    Usage:
        tracker = TokenTracker()
        
        # Track usage from BAML calls
        baml_options = tracker.get_baml_options()
        result = await client.AnalyzeFile(file=file_info, baml_options=baml_options)
        tracker.track_call_from_collector('file_analysis', 'claude-sonnet-4-20250514')
        
        # Get current totals
        total_tokens = tracker.get_total_tokens()
        current_cost = tracker.total_cost
        
        # Get detailed summary
        summary = tracker.get_detailed_summary()
    
    Configuration:
        Model pricing is loaded from config/model_pricing.yaml. If the config file
        is not found, falls back to hardcoded pricing. The config file supports:
        - Per-model input/output token pricing
        - Default model selection
        - Provider metadata and pricing sources
    
    Thread Safety:
        This class is not thread-safe. Create separate instances for concurrent usage.
    """
    
    def __init__(self):
        """Initialize the TokenTracker with BAML Collector integration and pricing config.
        
        Sets up:
        - Usage tracking dictionaries for phase-based breakdown
        - BAML Collector instance for accurate token counting (if available)
        - Model pricing configuration loaded from YAML file
        - Running totals for tokens, costs, and API call counts
        
        The initialization automatically:
        1. Attempts to import and initialize BAML Collector
        2. Loads model pricing from config/model_pricing.yaml
        3. Sets up fallback pricing if config is unavailable
        4. Initializes all tracking counters to zero
        
        Raises:
            No exceptions are raised. Missing dependencies or config files
            trigger fallback behavior with warning-free degradation.
        """
        self.usage_by_phase = {}
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
        self.collector = None
        
        # Initialize BAML Collector if available
        try:
            from baml_py import Collector
            self.collector = Collector(name="rulectl-tracker")
        except ImportError:
            # Fallback if Collector not available
            self.collector = None
        
        # Load model pricing from YAML config
        self.model_pricing = self._load_model_pricing()
        self.default_model = self.model_pricing.get('_default', 'claude-sonnet-4-20250514')

    
    def _load_model_pricing(self) -> dict:
        """Load model pricing configuration from YAML file with intelligent fallback.
        
        Searches for pricing configuration in multiple locations to support both
        development and bundled executable environments:
        
        Search Order:
        1. bundled_executable_dir/config/model_pricing.yaml (PyInstaller)
        2. bundled_executable_dir/model_pricing.yaml (PyInstaller fallback)
        3. project_root/config/model_pricing.yaml (development)
        
        YAML Structure Expected:
            models:
              model-id:
                name: "Human readable name"
                provider: "Provider name"  
                input_cost_per_1m: 15.0    # USD per 1M input tokens
                output_cost_per_1m: 75.0   # USD per 1M output tokens
                notes: "Optional description"
            default_model: "model-id"
        
        Returns:
            dict: Model pricing dictionary in format:
                {
                    'model-id': {'input': 15.0, 'output': 75.0},
                    '_default': 'model-id'  # Special key for default model
                }
                
        Fallback Behavior:
            If YAML file is not found or cannot be parsed, returns hardcoded
            pricing for common models (Claude 4, Claude 3 Haiku, GPT-4o, GPT-4o Mini).
            
        Note:
            This method never raises exceptions. Parsing errors or missing files
            trigger silent fallback to ensure system reliability.
        """
        import sys
        import os
        
        # Try to find the config file in multiple locations
        config_paths = []
        
        # For bundled executables, check if config is bundled
        if getattr(sys, 'frozen', False):
            # PyInstaller bundle - config should be in the same directory
            bundle_dir = Path(sys.executable).parent
            config_paths.append(bundle_dir / "config" / "model_pricing.yaml")
            config_paths.append(bundle_dir / "model_pricing.yaml")
        
        # For development, check relative to this file
        current_dir = Path(__file__).parent.parent  # Go up from rulectl/ to root
        config_paths.append(current_dir / "config" / "model_pricing.yaml")
        
        # Try each path until we find the config file
        pricing_data = None
        for config_path in config_paths:
            try:
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        pricing_data = yaml.safe_load(f)
                    break
            except Exception:
                continue
        
        if not pricing_data:
            # Fallback to hardcoded pricing if config file not found
            return self._get_fallback_pricing()
        
        # Convert YAML format to internal format
        model_pricing = {}
        
        if 'models' in pricing_data:
            for model_id, model_info in pricing_data['models'].items():
                model_pricing[model_id] = {
                    'input': model_info.get('input_cost_per_1m', 15.0),
                    'output': model_info.get('output_cost_per_1m', 75.0)
                }
        
        # Store default model
        if 'default_model' in pricing_data:
            model_pricing['_default'] = pricing_data['default_model']
        
        return model_pricing if model_pricing else self._get_fallback_pricing()
    
    def _get_fallback_pricing(self) -> dict:
        """Get fallback pricing when YAML config is not available.
        
        Returns:
            Dictionary with hardcoded pricing
        """
        return {
            'claude-sonnet-4-20250514': {'input': 15.0, 'output': 75.0},
            'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},
            'gpt-4o': {'input': 2.5, 'output': 10.0},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.6},
            '_default': 'claude-sonnet-4-20250514'
        }
    
    def get_baml_options(self):
        """Get BAML options dictionary for API calls with collector integration.
        
        Returns the appropriate options dictionary to pass to BAML API calls
        for automatic token tracking integration. When a BAML Collector is
        available, includes it in the options to enable precise usage tracking.
        
        Usage:
            baml_options = tracker.get_baml_options()
            result = await client.AnalyzeFile(file=file_info, baml_options=baml_options)
            tracker.track_call_from_collector('file_analysis')
        
        Returns:
            dict: BAML options dictionary. Contains:
                - {"collector": collector_instance} if collector available
                - {} (empty dict) if collector not available
                
        Integration:
            The returned options should be passed to all BAML API calls using
            the baml_options parameter. This enables the BAML framework to
            automatically capture token usage data in the collector.
            
        Note:
            Always returns a dictionary (never None) for safe unpacking in API calls.
        """
        if self.collector:
            return {"collector": self.collector}
        return {}
    
    def track_call_from_collector(self, phase: str, model: str = "claude-sonnet-4-20250514"):
        """Extract token usage from BAML Collector and update tracking with intelligent fallback.
        
        This is the primary method for tracking token usage after BAML API calls.
        It attempts to extract actual usage data from the BAML Collector, but
        gracefully falls back to conservative estimates if collector data is unavailable.
        
        Usage Pattern:
            # Before BAML call
            baml_options = tracker.get_baml_options()
            
            # Make BAML call  
            result = await client.AnalyzeFile(file=file_info, baml_options=baml_options)
            
            # Track usage after call
            tracker.track_call_from_collector('file_analysis', 'claude-sonnet-4-20250514')
        
        Args:
            phase (str): Analysis phase identifier for usage categorization.
                Common phases: 'file_analysis', 'rule_synthesis', 'rule_audit'
                Custom phases are supported for specialized tracking.
            model (str, optional): Model identifier for cost calculation.
                Must match a model in the pricing configuration.
                Defaults to 'claude-sonnet-4-20250514'.
        
        Behavior:
            1. If BAML Collector available and has usage data:
               - Extracts actual input/output token counts
               - Calculates precise cost using model pricing
            2. If Collector unavailable or no usage data:
               - Uses conservative estimates based on phase type
               - Ensures tracking continues even without exact data
            3. Updates phase-specific and overall totals
        
        Fallback Estimates:
            - file_analysis: 1500 input, 200 output tokens
            - rule_synthesis: 2000 input, 300 output tokens  
            - rule_audit: 800 input, 150 output tokens
            - default: 1000 input, 150 output tokens
            
        Thread Safety:
            Not thread-safe. Call from single thread or use separate tracker instances.
            
        Note:
            This method never raises exceptions. All errors trigger fallback estimation
            to ensure robust operation in production environments.
        """
        if not self.collector or not hasattr(self.collector, 'last'):
            # Fallback: estimate token usage if collector not available
            self.add_estimated_usage(phase, model)
            return
        
        try:
            # Get usage from the last call
            last_call = self.collector.last
            if hasattr(last_call, 'usage') and last_call.usage:
                input_tokens = getattr(last_call.usage, 'input_tokens', 0)
                output_tokens = getattr(last_call.usage, 'output_tokens', 0)
                
                if input_tokens > 0 or output_tokens > 0:
                    self.add_usage(phase, model, input_tokens, output_tokens)
                else:
                    # Fallback if no usage data
                    self.add_estimated_usage(phase, model)
            else:
                # Fallback if no usage object
                self.add_estimated_usage(phase, model)
        except Exception:
            # Fallback on any error
            self.add_estimated_usage(phase, model)
    
    def add_usage(self, phase: str, model: str, input_tokens: int, output_tokens: int):
        """Add token usage for a specific phase and model.
        
        Args:
            phase: Analysis phase (e.g., 'file_analysis', 'rule_synthesis')
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        if phase not in self.usage_by_phase:
            self.usage_by_phase[phase] = {
                'input_tokens': 0,
                'output_tokens': 0,
                'cost': 0.0,
                'calls': 0
            }
        
        # Update phase totals
        self.usage_by_phase[phase]['input_tokens'] += input_tokens
        self.usage_by_phase[phase]['output_tokens'] += output_tokens
        self.usage_by_phase[phase]['calls'] += 1
        
        # Calculate cost for this call
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        self.usage_by_phase[phase]['cost'] += cost
        
        # Update overall totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.call_count += 1

    
    def add_estimated_usage(self, phase: str, model: str = "claude-sonnet-4-20250514"):
        """Add conservative token usage estimates when precise data is unavailable.
        
        Provides fallback token tracking when BAML Collector is not available or
        fails to capture usage data. Uses phase-specific conservative estimates
        based on typical usage patterns for each analysis type.
        
        Args:
            phase (str): Analysis phase identifier. Supported phases:
                - 'file_analysis': Static analysis of individual source files
                - 'rule_synthesis': Combining multiple analysis results into rules
                - 'rule_audit': LLM-based review and cleanup of merged rules
                - Custom phases use default estimates
            model (str, optional): Model identifier for cost calculation.
                Defaults to 'claude-sonnet-4-20250514'.
        
        Estimation Logic:
            Estimates are intentionally conservative (slightly high) to avoid
            under-reporting costs. Based on analysis of typical BAML function calls:
            
            file_analysis: 1500 input + 200 output tokens
                - Handles individual file static analysis
                - Input: File content + analysis prompt (~1500 tokens)
                - Output: JSON rule candidates (~200 tokens)
                
            rule_synthesis: 2000 input + 300 output tokens  
                - Processes multiple file analyses into cohesive rules
                - Input: Multiple analysis results + synthesis prompt (~2000 tokens)
                - Output: Consolidated rule candidates (~300 tokens)
                
            rule_audit: 800 input + 150 output tokens
                - Reviews and cleans up merged rule clusters
                - Input: Cluster data + audit prompt (~800 tokens)
                - Output: Cleaned rule definition (~150 tokens)
                
            default: 1000 input + 150 output tokens
                - Generic estimate for unknown phases
                - Balanced for typical LLM operations
        
        Cost Calculation:
            Uses the same pricing logic as precise tracking, ensuring consistent
            cost estimates regardless of data source (collector vs estimation).
            
        Usage:
            Typically called automatically by track_call_from_collector() when
            collector data is unavailable. Can be called directly for manual
            tracking in custom scenarios.
            
        Note:
            Estimates are conservative and may overestimate actual usage by 10-20%.
            This is intentional to avoid surprise costs from under-reporting.
        """
        # Conservative estimates based on typical BAML function calls
        if phase == 'file_analysis':
            # Typical file analysis: ~1500 input tokens, ~200 output tokens
            estimated_input = 1500
            estimated_output = 200
        elif phase == 'rule_synthesis':
            # Rule synthesis: ~2000 input tokens, ~300 output tokens
            estimated_input = 2000
            estimated_output = 300
        elif phase == 'rule_audit':
            # Rule auditing: ~800 input tokens, ~150 output tokens
            estimated_input = 800
            estimated_output = 150
        else:
            # Default estimate: ~1000 input tokens, ~150 output tokens
            estimated_input = 1000
            estimated_output = 150
        
        self.add_usage(phase, model, estimated_input, estimated_output)
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model call.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        if model not in self.model_pricing:
            # Use default model pricing if model not found
            default_model = self.model_pricing.get('_default', 'claude-sonnet-4-20250514')
            pricing = self.model_pricing.get(default_model, {'input': 15.0, 'output': 75.0})
        else:
            pricing = self.model_pricing[model]
        
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        
        return input_cost + output_cost
    
    def get_total_tokens(self) -> int:
        """Get total token count across all phases and API calls.
        
        Calculates the sum of input and output tokens from all tracked usage,
        providing a single metric for overall analysis consumption.
        
        Returns:
            int: Total token count (input_tokens + output_tokens).
                Returns 0 if no usage has been tracked.
                
        Usage:
            total = tracker.get_total_tokens()
            if total > 50000:
                print("High token usage detected")
                
        Note:
            This is the primary metric for understanding analysis scope
            and is used in cost calculations and progress reporting.
        """
        return self.total_input_tokens + self.total_output_tokens
    
    def get_current_summary(self) -> str:
        """Get compact token usage summary for real-time progress display.
        
        Provides a concise, single-line summary of current token usage and cost,
        optimized for display in progress bars, status lines, and real-time updates.
        
        Returns:
            str: Compact summary in format "📊 Tokens: 12,450 ($1.87)" or
                "📊 Tokens: 0" when no usage has been recorded.
                
        Format:
            - Always starts with 📊 emoji for consistent visual identity
            - Token count with thousands separators (12,450)
            - Cost in USD with $ prefix and 2 decimal places ($1.87)
            - Single line, suitable for progress bar integration
            
        Usage:
            Perfect for real-time updates during analysis:
            
            # In progress bar callback
            def show_progress(current_file):
                tokens = tracker.get_current_summary()
                return f"Processing {current_file} | {tokens}"
                
            # In CLI status updates
            click.echo(f"Status: {tracker.get_current_summary()}")
            
        Difference from get_detailed_summary():
            - Single line vs multi-line
            - No phase breakdown
            - Optimized for frequent updates
            - Shorter format for UI constraints
        """
        total_tokens = self.get_total_tokens()
        if total_tokens == 0:
            return "📊 Tokens: 0"
        
        return f"📊 Tokens: {total_tokens:,} (${self.total_cost:.2f})"    
    def get_detailed_summary(self) -> str:
        """Generate comprehensive token usage summary with phase breakdown.
        
        Creates a detailed, multi-line summary report suitable for final analysis
        output. Includes per-phase token counts, costs, call counts, and overall totals.
        
        Returns:
            str: Formatted summary report with the following structure:
                📊 Token Usage Summary:
                  • File Analysis: 12,450 tokens ($1.87) - 8 calls
                  • Rule Synthesis: 4,200 tokens ($0.63) - 2 calls  
                  • Rule Audit: 1,850 tokens ($0.28) - 3 calls
                  • Total: 18,500 tokens ($2.78) - 13 API calls
                
                Returns "📊 No token usage recorded" if no usage has been tracked.
        
        Phase Information:
            Each phase line includes:
            - Phase name (human-readable, Title Case)
            - Total tokens (input + output, comma-separated)
            - Total cost in USD (2 decimal places)
            - Number of API calls made in this phase
            
        Usage:
            Typically called at the end of analysis for final reporting:
            
            print(tracker.get_detailed_summary())
            
        Format Notes:
            - Uses Unicode emoji (📊) and bullets (•) for visual appeal
            - Numbers formatted with thousand separators for readability
            - Costs displayed with $ prefix and 2 decimal precision
            - Consistent indentation and spacing for clean terminal output
        """
        if not self.usage_by_phase:
            return "📊 No token usage recorded"
        
        lines = ["📊 Token Usage Summary:"]
        
        # Phase breakdown
        for phase, stats in self.usage_by_phase.items():
            phase_total = stats['input_tokens'] + stats['output_tokens']
            phase_name = phase.replace('_', ' ').title()
            lines.append(f"  • {phase_name}: {phase_total:,} tokens (${stats['cost']:.2f}) - {stats['calls']} calls")
        
        # Overall totals
        total_tokens = self.get_total_tokens()
        lines.append(f"  • Total: {total_tokens:,} tokens (${self.total_cost:.2f}) - {self.call_count} API calls")
        
        return '\n'.join(lines)
    
    def get_phase_summary(self, phase: str) -> str:
        """Get summary for a specific phase."""
        if phase not in self.usage_by_phase:
            return f"📊 {phase.replace('_', ' ').title()}: 0 tokens"
        
        stats = self.usage_by_phase[phase]
        phase_total = stats['input_tokens'] + stats['output_tokens']
        phase_name = phase.replace('_', ' ').title()
        
        return f"📊 {phase_name}: {phase_total:,} tokens (${stats['cost']:.2f})"