Evidence from rulectl/cli.py (1,320 lines) and requirements.txt shows comprehensive CLI built with Click framework. Pattern emerged from initial commit by Ethan (2025-09-02, commit b4a0531a) with decorators (@click.group, @click.command, @click.option) defining commands for authentication setup, rate limiting configuration, and repository analysis. The CLI includes colorama for colored output, supporting multiple subcommands with extensive option parsing for API keys, verbosity flags, and force modes.

## Policies
- Use Click framework (click>=8.0.0) for all command-line interface implementation in Python applications
- Structure CLI with @click.group() decorator at the top level and @click.command() for subcommands
- Define command-line options using @click.option() with type hints, help text, and default values
- Use @click.argument() for required positional arguments with click.Choice() for enumerated values
- Include colorama>=0.4.6 for cross-platform colored terminal output in all CLI applications
- Implement --verbose/-v flag for debug output and --force/-f flag to skip confirmation prompts
- Provide clear help text for all commands and options using the help parameter

## Instructions
- Import click module and define main CLI group with @click.group() decorator
- Create subcommands using @click.command() decorator and add to group with @cli.command()
- Define options with @click.option() including name, type, default, and help parameters
- Use click.echo() for all output instead of print() for better CLI compatibility
- Implement click.Choice() for restricted argument values (e.g., provider choices)
- Add click.prompt() for interactive input when required values are not provided
- Test CLI commands using subprocess module to verify command-line behavior