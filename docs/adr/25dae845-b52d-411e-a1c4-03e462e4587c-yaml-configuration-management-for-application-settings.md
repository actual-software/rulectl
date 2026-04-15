Evidence from 5 files (rulectl/cli.py, rulectl/analyzer.py, rulectl/token_tracker.py, rulectl/utils.py, requirements.txt) totaling 1,984 lines shows comprehensive YAML-based configuration. Pattern implemented by Ethan (2025-09-02, commit b4a0531a) includes rate_limiting.yaml for API limits, model pricing configuration, and YAML frontmatter for rule output. PyYAML (pyyaml>=6.0) and python-dotenv (>=1.0.0) handle configuration loading with yaml.safe_load() and environment variable integration via os.getenv().

## Policies
- Use YAML format for all application configuration files in Python projects (rate limiting, pricing, settings)
- Include pyyaml>=6.0 dependency for YAML parsing and python-dotenv>=1.0.0 for environment variable loading
- Load YAML configuration using yaml.safe_load() for security (prevents arbitrary code execution)
- Store configuration files in dedicated 'config' directory at project root level
- Use Path(__file__).parent.parent / 'config' / 'filename.yaml' for cross-platform config file paths
- Load environment variables using python-dotenv's load_dotenv() at application startup
- Implement fallback values when configuration files or environment variables are missing

## Instructions
- Create config directory at project root and place all YAML configuration files there
- Import yaml module and load configuration with 'with open(config_path) as f: yaml.safe_load(f)'
- Import dotenv and call load_dotenv() before accessing environment variables
- Use os.getenv('KEY_NAME', 'default_value') for environment variable access with fallbacks
- Structure YAML with nested dictionaries for logical grouping of related settings
- Validate configuration after loading using conditional checks or Pydantic models
- Generate YAML output using yaml.dump(data, default_flow_style=False) for readable formatting