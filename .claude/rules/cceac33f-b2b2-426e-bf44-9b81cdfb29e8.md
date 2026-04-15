<rule_activation id="cceac33f-b2b2-426e-bf44-9b81cdfb29e8" title="Click Framework for CLI Application Architecture" applies_to="**/*.py">
These rules are ALWAYS ACTIVE for all Python files matching `**/*.py` that implement CLI functionality.
</rule_activation>

### Rules

- **R-CLICK-001** MUST: Use Click framework (click>=8.0.0) for all command-line interface implementation in Python applications.
- **R-CLICK-002** MUST: Structure CLI with @click.group() decorator at the top level and @click.command() for subcommands.
- **R-CLICK-003** MUST: Define command-line options using @click.option() with type hints, help text, and default values.
- **R-CLICK-004** MUST: Use @click.argument() for required positional arguments with click.Choice() for enumerated values.
- **R-CLICK-005** MUST: Include colorama>=0.4.6 for cross-platform colored terminal output in all CLI applications.
- **R-CLICK-006** SHOULD: Implement --verbose/-v flag for debug output and --force/-f flag to skip confirmation prompts.
- **R-CLICK-007** MUST: Provide clear help text for all commands and options using the help parameter.
- **R-CLICK-008** MUST: Use click.echo() for all output instead of print() for better CLI compatibility.
- **R-CLICK-009** SHOULD: Implement click.Choice() for restricted argument values (e.g., provider choices).
- **R-CLICK-010** SHOULD: Add click.prompt() for interactive input when required values are not provided.

### Verify

```bash
# Check for Click framework import and decorators
grep -r "import click" **/*.py 2>/dev/null | head -5
grep -r "@click.group\|@click.command\|@click.option\|@click.argument" **/*.py 2>/dev/null | head -10

# Verify Click version in requirements
grep "click>=8.0.0" requirements.txt 2>/dev/null || grep "click" requirements.txt 2>/dev/null

# Check for colorama in requirements
grep "colorama>=0.4.6" requirements.txt 2>/dev/null || grep "colorama" requirements.txt 2>/dev/null

# Verify click.echo() usage instead of print() in CLI files
if [ -n "$(find . -name '*cli*.py' -o -name '*command*.py' 2>/dev/null)" ]; then
  grep -l "print(" *cli*.py *command*.py 2>/dev/null && echo "Warning: Found print() calls in CLI files, should use click.echo()" || echo "OK: Using click.echo() in CLI files"
fi

# Check for help text in options
grep -r "@click.option.*help=" **/*.py 2>/dev/null | wc -l

# Verify common CLI flags
grep -r "\-\-verbose\|\-v.*help=" **/*.py 2>/dev/null | head -3
grep -r "\-\-force\|\-f.*help=" **/*.py 2>/dev/null | head -3
```

**Accept when:**
- Click framework is imported in CLI implementation files
- CLI commands are structured using @click.group() and @click.command() decorators
- Options are defined with @click.option() including help text
- Arguments use @click.argument() with appropriate type constraints
- click>=8.0.0 and colorama>=0.4.6 are listed in requirements.txt or pyproject.toml
- Output uses click.echo() instead of print() in CLI files
- Common flags (--verbose, --force) are implemented where appropriate
- All commands and options include descriptive help text

<enforcement>
Claude Code MUST verify Click framework patterns when creating or modifying CLI implementations. Claude Code MUST NOT skip or defer verification of these patterns.
</enforcement>