#!/usr/bin/env python3
"""
Main CLI module for the Rules Engine tool.
"""

import click
import sys
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import json
import os
import subprocess
import yaml

def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment or fallback file."""
    # First check if it's already in the environment
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
        
    # Try fallback file
    fallback_file = Path.home() / ".rules_engine" / "credentials.json"
    if fallback_file.exists():
        try:
            with open(fallback_file) as f:
                creds = json.load(f)
                return creds.get("openai-api-key")
        except:
            pass
            
    return None

def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from environment or fallback file."""
    # First check if it's already in the environment
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key
        
    # Try fallback file
    fallback_file = Path.home() / ".rules_engine" / "credentials.json"
    if fallback_file.exists():
        try:
            with open(fallback_file) as f:
                creds = json.load(f)
                return creds.get("anthropic-api-key")
        except:
            pass
            
    return None

def store_anthropic_api_key(key: str) -> None:
    """Store Anthropic API key in fallback file."""
    _store_api_key("anthropic-api-key", key)

def store_openai_api_key(key: str) -> None:
    """Store OpenAI API key in fallback file."""
    _store_api_key("openai-api-key", key)

def _store_api_key(key_name: str, key: str) -> None:
    """Store API key in fallback file."""
    # Create directory with restricted permissions
    fallback_dir = Path.home() / ".rules_engine"
    fallback_file = fallback_dir / "credentials.json"
    
    # Create directory with restricted permissions
    fallback_dir.mkdir(mode=0o700, exist_ok=True)
    
    # Read existing credentials or create new
    creds = {}
    if fallback_file.exists():
        try:
            with open(fallback_file) as f:
                creds = json.load(f)
        except:
            pass
            
    # Update credentials
    creds[key_name] = key
    
    # Write with restricted permissions
    with open(fallback_file, "w", opener=lambda p, f: os.open(p, f, 0o600)) as f:
        json.dump(creds, f)

def mask_api_key(key: str) -> str:
    """Mask an API key for display, showing only first/last few characters."""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

def ensure_api_keys() -> dict:
    """Ensure we have required API keys, prompting user if needed."""
    # Load environment variables with override to ensure .env takes precedence
    load_dotenv(override=True)
    
    # Set BAML_LOG to OFF
    os.environ["BAML_LOG"] = "OFF"
    
    keys = {}
    
    # Check for Anthropic key (primary)
    anthropic_key = get_anthropic_api_key()
    if not anthropic_key:
        click.echo("\n🔑 Anthropic API key required for analysis")
        click.echo("You can get your API key from: https://console.anthropic.com/")
        anthropic_key = click.prompt("Please enter your Anthropic API key", type=str, hide_input=True)
        store_anthropic_api_key(anthropic_key)
        click.echo("✅ Anthropic API key stored securely")
    else:
        click.echo(f"🔑 Using stored Anthropic key: {mask_api_key(anthropic_key)}")
    
    # Validate key format
    if not anthropic_key.startswith("sk-ant-"):
        click.echo("⚠️  Warning: Anthropic API key doesn't match expected format (should start with 'sk-ant-')")
    
    # Set in environment for BAML
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    keys["anthropic"] = anthropic_key
    
    # Optional: Check for OpenAI key for fallback clients
    openai_key = get_openai_api_key()
    if openai_key:
        click.echo(f"🔑 Using stored OpenAI key: {mask_api_key(openai_key)}")
        os.environ["OPENAI_API_KEY"] = openai_key
        keys["openai"] = openai_key
    
    return keys

@click.group()
def cli():
    """Rules Engine CLI - Manage cursor rules in your repository."""
    pass

@cli.group()
def config():
    """Manage API keys and configuration."""
    pass

@config.command("set-key")
@click.argument("provider", type=click.Choice(["anthropic", "openai"], case_sensitive=False))
@click.option("--key", type=str, help="API key (will prompt if not provided)")
def set_key(provider: str, key: str):
    """Set API key for a provider."""
    provider = provider.lower()
    
    if not key:
        click.echo(f"\n🔑 Setting {provider.title()} API key")
        if provider == "anthropic":
            click.echo("You can get your API key from: https://console.anthropic.com/")
        else:
            click.echo("You can get your API key from: https://platform.openai.com/api-keys")
        key = click.prompt(f"Please enter your {provider.title()} API key", type=str, hide_input=True)
    
    # Store the key
    if provider == "anthropic":
        store_anthropic_api_key(key)
    else:
        store_openai_api_key(key)
    
    click.echo(f"✅ {provider.title()} API key stored securely")
    click.echo(f"🔑 Key: {mask_api_key(key)}")

@config.command("show")
def show_config():
    """Show current configuration (with masked keys)."""
    click.echo("\n🔧 Current Configuration:")
    
    # Check stored keys
    anthropic_key = get_anthropic_api_key()
    openai_key = get_openai_api_key()
    
    if anthropic_key:
        click.echo(f"🔑 Anthropic API Key: {mask_api_key(anthropic_key)}")
    else:
        click.echo("🔑 Anthropic API Key: Not set")
    
    if openai_key:
        click.echo(f"🔑 OpenAI API Key: {mask_api_key(openai_key)}")
    else:
        click.echo("🔑 OpenAI API Key: Not set")
    
    # Show storage location
    creds_file = Path.home() / ".rules_engine" / "credentials.json"
    click.echo(f"\n📁 Credentials stored in: {creds_file}")

@config.command("clear")
@click.argument("provider", type=click.Choice(["anthropic", "openai", "all"], case_sensitive=False))
@click.option("--force", is_flag=True, help="Skip confirmation")
def clear_key(provider: str, force: bool):
    """Clear stored API key(s)."""
    provider = provider.lower()
    
    if not force:
        if provider == "all":
            if not click.confirm("Are you sure you want to clear ALL stored API keys?"):
                click.echo("Cancelled.")
                return
        else:
            if not click.confirm(f"Are you sure you want to clear the {provider.title()} API key?"):
                click.echo("Cancelled.")
                return
    
    # Clear the key(s)
    creds_file = Path.home() / ".rules_engine" / "credentials.json"
    if creds_file.exists():
        try:
            with open(creds_file) as f:
                creds = json.load(f)
        except:
            creds = {}
        
        if provider == "all":
            creds.pop("anthropic-api-key", None)
            creds.pop("openai-api-key", None)
            click.echo("🗑️  Cleared all API keys")
        elif provider == "anthropic":
            creds.pop("anthropic-api-key", None)
            click.echo("🗑️  Cleared Anthropic API key")
        else:
            creds.pop("openai-api-key", None)
            click.echo("🗑️  Cleared OpenAI API key")
        
        # Write back the updated credentials
        with open(creds_file, "w", opener=lambda p, f: os.open(p, f, 0o600)) as f:
            json.dump(creds, f)
    else:
        click.echo("No stored keys found.")

@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".")
def start(verbose: bool, force: bool, directory: str):
    """Start the Rules Engine service.
    
    DIRECTORY: Path to the repository to analyze (default: current directory)
    """
    try:
        # Run the async main function
        asyncio.run(async_start(verbose, force, directory))
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}")
        sys.exit(1)

async def async_start(verbose: bool, force: bool, directory: str):
    """Async implementation of the start command."""
    # Convert directory to absolute path
    directory = str(Path(directory).resolve())
    
    # Ensure we have required API keys before proceeding
    api_keys = ensure_api_keys()
    
    # Import non-BAML dependent modules first
    try:
        from rules_engine.utils import validate_repository, check_baml_client
    except ImportError:
        try:
            from .utils import validate_repository, check_baml_client
        except ImportError:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from rules_engine.utils import validate_repository, check_baml_client

    # Check if we're in a git repo
    if not validate_repository(directory):
        click.echo("❌ Not a valid git repository")
        raise click.Abort()
    
    click.echo("✅ Valid repository detected")

    # Check if baml_client exists and initialize if needed
    if not check_baml_client(directory):
        # For bundled executables, we include the baml_client directly
        if getattr(sys, 'frozen', False):  # PyInstaller bundle
            click.echo("✅ Using bundled BAML client")
            # The baml_client should be available from the bundle
        # Skip BAML initialization during builds
        elif os.environ.get("RULES_ENGINE_BUILD") == "1":
            click.echo("⚠️ Skipping BAML initialization during build")
        else:
            click.echo("\n🔄 BAML client not found. Initializing...")
            try:
                # Get the path to baml_init.py - handle both development and bundled scenarios
                if getattr(sys, 'frozen', False):  # PyInstaller bundle
                    # In a PyInstaller bundle, use sys._MEIPASS
                    bundle_dir = Path(sys._MEIPASS)
                    init_script = bundle_dir / "baml_init.py"
                else:
                    # Development mode
                    init_script = Path(__file__).parent.parent / "baml_init.py"
                
                if not init_script.exists():
                    click.echo("❌ Could not find baml_init.py")
                    click.echo(f"Looked for: {init_script}")
                    raise click.Abort()
                
                # Run baml_init.py
                result = subprocess.run(
                    [sys.executable, str(init_script)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                click.echo("✅ BAML initialization completed")
                
                # Reload BAML modules
                if "baml_client" in sys.modules:
                    del sys.modules["baml_client"]
                if "baml_client.async_client" in sys.modules:
                    del sys.modules["baml_client.async_client"]
                if "baml_client.types" in sys.modules:
                    del sys.modules["baml_client.types"]
                    
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ BAML initialization failed: {e.stderr}")
                raise click.Abort()
            except Exception as e:
                click.echo(f"❌ BAML initialization failed: {e}")
                raise click.Abort()
    
    # Now that BAML is initialized, import BAML-dependent modules
    try:
        from rules_engine.analyzer import RepoAnalyzer, MAX_ANALYZABLE_LINES
    except ImportError:
        try:
            from .analyzer import RepoAnalyzer, MAX_ANALYZABLE_LINES
        except ImportError:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from rules_engine.analyzer import RepoAnalyzer, MAX_ANALYZABLE_LINES

    # Initialize analyzer with the specified directory
    analyzer = RepoAnalyzer(directory)
    
    # Check for .gitignore
    if not analyzer.has_gitignore():
        click.echo("\n⚠️  WARNING: No .gitignore file found! ⚠️")
        click.echo("\n🚨 Without a .gitignore, files will be analyzed that you almost certainly don't want to be!")
        click.echo("\nThis includes but is not limited to:")
        click.echo("- 📦 All node_modules and virtual environment files")
        click.echo("- 🏗️  Build artifacts and cache directories")
        click.echo("- 🔒 Environment files with sensitive information")
        click.echo("- 📝 Log files and temporary files")
        click.echo("- 🗑️  System files like .DS_Store")
        click.echo("\nThis will:")
        click.echo("- 🐌 Significantly slow down the analysis")
        click.echo("- 💰 Potentially increase API costs")
        click.echo("- 🎯 Reduce the quality of the generated rules")
        
        if not force:
            click.echo("\n💡 Recommendation: Create a .gitignore file first!")
            if not click.confirm("\nAre you absolutely sure you want to continue without a .gitignore?", default=False):
                click.echo("\n✨ Tip: You can find good .gitignore templates at https://github.com/github/gitignore")
                raise click.Abort()
    
    # Count files to be analyzed  
    total_files, extension_counts = analyzer.count_analyzable_files()
    
    # Optional: Review skipped config files with AI to expand analysis
    skipped_configs = analyzer.get_skipped_config_files()
    ai_reviewed_configs = False
    
    if skipped_configs and not force:
        click.echo(f"\n🤖 Found {len(skipped_configs)} config files that were skipped by default")
        click.echo("We skip config files aggressively, but some might contain useful patterns:")
        for i, file_path in enumerate(skipped_configs[:5], 1):
            click.echo(f"  {i}. {file_path}")
        if len(skipped_configs) > 5:
            click.echo(f"  ... and {len(skipped_configs) - 5} more")
        
        if click.confirm("Would you like AI to review these and add promising ones to the analysis?"):
            ai_reviewed_configs = True
            click.echo("🔍 AI is reviewing skipped config files...")
            try:
                additional_files, reasoning = await analyzer.review_skipped_files(skipped_configs)
                if additional_files:
                    click.echo(f"\n🎯 AI recommends also analyzing {len(additional_files)} config files:")
                    for file_path in additional_files:
                        click.echo(f"  • {file_path}")
                    click.echo(f"\n💭 {reasoning}")
                    
                    # Update counts for display
                    total_files += len(additional_files)
                    for file_path in additional_files:
                        ext = Path(file_path).suffix or 'no extension'
                        extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    
                    click.echo(f"\n📋 Updated analysis plan with AI recommendations")
                else:
                    click.echo("🤷 AI didn't find any config files worth analyzing")
                    if reasoning:
                        click.echo(f"💭 {reasoning}")
            except Exception as e:
                click.echo(f"⚠️  AI review failed: {e}")
                click.echo("Continuing with original file list...")
                ai_reviewed_configs = False
    
    # Display analysis plan
    click.echo(f"\n📊 Analysis Plan:")
    click.echo(f"\n🎯 Files to be analyzed: {total_files}")
    if extension_counts:
        click.echo("\nBreakdown by file type:")
        for ext, count in sorted(extension_counts.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {ext}: {count} files")
    
    
    # Show skipped files info
    if len(analyzer.skipped_large) > 0:
        click.echo(f"\n⚠️  Skipping {len(analyzer.skipped_large)} files that exceed {MAX_ANALYZABLE_LINES:,} lines")
    
    if len(analyzer.skipped_binary) > 0:
        click.echo(f"\n📝 Skipping {len(analyzer.skipped_binary)} binary/non-text files")
    
    if len(analyzer.skipped_config) > 0:
        if ai_reviewed_configs:
            click.echo(f"\n⚙️  Skipping {len(analyzer.skipped_config)} config files (reviewed by AI above)")
        else:
            click.echo(f"\n⚙️  Skipping {len(analyzer.skipped_config)} config files (not reviewed by AI)")
    
    if len(analyzer.skipped_unreadable) > 0:
        click.echo(f"\n⚠️  {len(analyzer.skipped_unreadable)} files could not be read")
    
    if not force and not click.confirm("\nDo you want to proceed with the analysis?"):
        click.echo("\n👋 Analysis cancelled!")
        raise click.Abort()
    
    # Check for rules directory
    rules_dir = Path(directory) / ".cursor" / "rules"
    analysis_dir = Path(directory) / ".rules_engine"
    analysis_file = analysis_dir / "analysis.json"
    
    # Create directories if they don't exist
    rules_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(exist_ok=True)
    
    # Start the analysis
    click.echo("\n🔍 Starting repository analysis...")
    
    # Step 1: Analyze structure
    analyzer.analyze_structure()
    if verbose:
        click.echo("\n📁 Repository structure analyzed")
    
    # Step 2: Get all analyzable files (including any AI-recommended ones)
    all_files = analyzer.get_all_analyzable_files()
    
    # Add any AI-recommended files from the earlier review
    if 'additional_files' in locals():
        all_files.extend(additional_files)
    
    if verbose:
        click.echo(f"\n📋 Final analysis list: {len(all_files)} files")
    
    # Step 3: Analyze files one by one
    click.echo("\n🔎 Analyzing files...")
    all_static_analyses = []
    
    def get_progress_info(file_path):
        if not file_path:
            return ""
        
        # Always show token info, even if 0
        token_info = " | 📊 0 tokens ($0.00)"  # Default
        
        if analyzer.token_tracker:
            current_tokens = analyzer.token_tracker.get_total_tokens()
            current_cost = analyzer.token_tracker.total_cost
            token_info = f" | 📊 {current_tokens:,} tokens (${current_cost:.2f})"
        
        return f"Current: {file_path}{token_info}"
    
    with click.progressbar(
        all_files,
        label="Analyzing files",
        item_show_func=get_progress_info
    ) as bar:
        for file_path in bar:
            # Analyze individual file
            result = await analyzer.analyze_file(file_path)
            if result:  # Only add successful analyses
                all_static_analyses.append(result)
            
            if verbose:
                status = "✓" if result else "⚠"
                
                # Always show token info in verbose mode
                token_info = " | 📊 0 tokens ($0.00)"  # Default
                if analyzer.token_tracker:
                    current_tokens = analyzer.token_tracker.get_total_tokens()
                    current_cost = analyzer.token_tracker.total_cost
                    token_info = f" | 📊 {current_tokens:,} tokens (${current_cost:.2f})"
                    # Debug: Additional info in verbose mode

                

    
    # Display file analysis results with token tracking
    if analyzer.token_tracker:
        token_summary = analyzer.token_tracker.get_current_summary()
        click.echo(f"\n✅ Successfully analyzed {len(all_static_analyses)} files | {token_summary}")
    else:
        click.echo(f"\n✅ Successfully analyzed {len(all_static_analyses)} files")
    
    # Step 4: Analyze git history for file importance
    click.echo("\n📊 Analyzing git history for file importance...")
    try:
        # Get detailed git statistics first
        git_details = analyzer.get_git_commit_details()
        
        # Get list of analyzed file paths for filtering
        analyzed_file_paths = [analysis.file for analysis in all_static_analyses]
        
        importance_weights = analyzer.get_file_importance_weights(analyzed_file_paths)
        if importance_weights:
            click.echo(f"✅ Found git history for {len(importance_weights)} files")
            
            # Show top 10 files by raw commit count (filtered to analyzed files)
            if git_details and 'modification_counts' in git_details:
                modification_counts = git_details['modification_counts']
                # Filter to only analyzed files
                analyzed_set = set(analyzed_file_paths)
                filtered_counts = {path: count for path, count in modification_counts.items() 
                                 if path in analyzed_set}
                sorted_commits = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)
                
                click.echo("\n🔥 Top 10 files by git commits:")
                for i, (file_path, count) in enumerate(sorted_commits[:10], 1):
                    click.echo(f"  {i:2d}. {count:3d} commits - {file_path}")
                
                if len(sorted_commits) > 10:
                    click.echo(f"       ... and {len(sorted_commits) - 10} more files")
            
            # Calculate some statistics
            weighted_files = [f for f in all_static_analyses if f.file in importance_weights]
            avg_weight = sum(importance_weights.values()) / len(importance_weights) if importance_weights else 0
            
            click.echo(f"\n📈 Git analysis summary:")
            click.echo(f"   • Average importance score: {avg_weight:.3f}")
            click.echo(f"   • {len(weighted_files)}/{len(all_static_analyses)} analyzed files have git history")
            
            if verbose:
                # Show top 10 most important files by weighted score
                sorted_files = sorted(importance_weights.items(), key=lambda x: x[1], reverse=True)
                click.echo("\n⚖️  Top 10 files by weighted importance score:")
                for i, (file_path, weight) in enumerate(sorted_files[:10], 1):
                    click.echo(f"  {i:2d}. {weight:.3f} - {file_path}")
        else:
            click.echo("⚠️  No git history weights calculated (using equal importance)")
            importance_weights = {}
    except Exception as e:
        click.echo(f"⚠️  Git analysis failed: {e}")
        click.echo("📝 Continuing with equal file importance...")
        importance_weights = {}
    
    # Step 5: Synthesize rules with advanced clustering
    click.echo("\n🧮 Synthesizing and clustering rules...")
    try:
        mdc_files, synthesis_stats = await analyzer.synthesize_rules_advanced(all_static_analyses, importance_weights)
        
        # Show detailed synthesis statistics
        if synthesis_stats:
            project_maturity = synthesis_stats.get('project_maturity', 'unknown')
            threshold = synthesis_stats.get('score_threshold', 3.0)
            avg_commits = synthesis_stats.get('avg_commits_per_file', 0)
            
            click.echo(f"\n📊 Rule synthesis breakdown:")
            click.echo(f"   • Raw rules extracted: {synthesis_stats.get('total_raw_rules', 0)}")
            click.echo(f"   • Files with rules: {synthesis_stats.get('files_with_rules', 0)}")
            click.echo(f"   • Rule clusters created: {synthesis_stats.get('total_clusters', 0)}")
            click.echo(f"   • Project maturity: {project_maturity} (avg {avg_commits:.1f} commits/file)")
            click.echo(f"   • Score threshold used: {threshold} (adaptive)")
            click.echo(f"   • Clusters above threshold: {synthesis_stats.get('filtered_clusters', 0)}")
            click.echo(f"   • Rules audited by LLM: {synthesis_stats.get('audited_rules', 0)}")
            click.echo(f"   • Final rule files generated: {synthesis_stats.get('final_rule_files', 0)}")
            
            # Show rules per file breakdown
            if verbose and 'rules_per_file' in synthesis_stats:
                rules_per_file = synthesis_stats['rules_per_file']
                sorted_file_rules = sorted(rules_per_file.items(), key=lambda x: x[1], reverse=True)
                
                click.echo(f"\n📋 Top 10 files by rules extracted:")
                for i, (file_path, count) in enumerate(sorted_file_rules[:10], 1):
                    click.echo(f"  {i:2d}. {count:2d} rules - {file_path}")
                
                if len(sorted_file_rules) > 10:
                    click.echo(f"       ... and {len(sorted_file_rules) - 10} more files")
            
            # Show top clusters
            if 'top_clusters' in synthesis_stats:
                top_clusters = synthesis_stats['top_clusters']
                if top_clusters:
                    click.echo(f"\n🏆 Top rule clusters by score:")
                    for i, cluster in enumerate(top_clusters[:5], 1):
                        cluster_type = "🔍 audited" if any(c['key'] == cluster['key'] for c in top_clusters if cluster['rule_count'] > 1) else "✓ single"
                        click.echo(f"  {i}. '{cluster['key']}' (score: {cluster['score']:.1f}, {cluster['support_files']} files, {cluster['rule_count']} raw rules) {cluster_type}")
        
        if mdc_files:
            click.echo(f"\n✅ Generated {len(mdc_files)} high-quality rule files")
            
            if verbose:
                click.echo("\n📋 Generated rules:")
                for i, content in enumerate(mdc_files[:3]):  # Show first 3 rules
                    try:
                        # Extract description from YAML
                        yaml_end = content.find('---', 3)
                        if yaml_end > 0:
                            front_matter = content[3:yaml_end].strip()
                            parsed = yaml.safe_load(front_matter)
                            description = parsed.get('description', f'Rule {i+1}')
                            click.echo(f"  • {description}")
                    except:
                        click.echo(f"  • Rule {i+1}")
                if len(mdc_files) > 3:
                    click.echo(f"  ... and {len(mdc_files) - 3} more")
        else:
            click.echo("⚠️  No rules met the quality threshold")
            click.echo("💡 Try analyzing more files or adjusting the scoring criteria")
            
            # Show why no rules were generated
            if synthesis_stats:
                total_raw = synthesis_stats.get('total_raw_rules', 0)
                total_clusters = synthesis_stats.get('total_clusters', 0)
                filtered_clusters = synthesis_stats.get('filtered_clusters', 0)
                threshold = synthesis_stats.get('score_threshold', 3.0)
                
                if total_raw == 0:
                    click.echo("   → No rules were extracted from the analyzed files")
                elif total_clusters == 0:
                    click.echo("   → No rule clusters could be formed")
                elif filtered_clusters == 0:
                    project_maturity = synthesis_stats.get('project_maturity', 'unknown')
                    if project_maturity == 'greenfield':
                        click.echo(f"   → No clusters scored above {threshold} threshold (greenfield project)")
                        click.echo("   → This is normal for new projects - patterns need more examples to establish strong rules")
                        click.echo("   → As you develop more code, patterns will emerge and stronger rules will be generated")
                    else:
                        click.echo(f"   → No clusters scored above threshold ({threshold})")
                        click.echo("   → Consider analyzing more files or checking if patterns are too diverse")
            
    except Exception as e:
        click.echo(f"❌ Rule synthesis failed: {e}")
        if verbose:
            import traceback
            click.echo(f"Details: {traceback.format_exc()}")
        mdc_files = []
        synthesis_stats = {}
    
    # Step 6: Save findings
    click.echo("\n💾 Saving analysis...")
    analyzer.save_findings(str(analysis_file))
    
    click.echo("\n✅ Analysis complete!")
    
    # Show comprehensive token usage summary
    if analyzer.token_tracker:
        detailed_summary = analyzer.token_tracker.get_detailed_summary()
        click.echo(f"\n{detailed_summary}")
    
    # Show summary
    structure = analyzer.findings["repository"]["structure"]
    click.echo("\n📊 Analysis Summary:")
    click.echo(f"- Found {len(structure['file_types'])} different file types")
    click.echo(f"- Analyzed {len(structure['directories'])} directories")
    click.echo(f"- Generated {len(mdc_files)} rule files")
    
    # Ask about rule generation
    if mdc_files and click.confirm("\n🤔 Would you like to review and save the generated rules?"):
        click.echo("\n📝 Let's review each rule with evidence and statistics.")
        click.echo("For each rule, you can:")
        click.echo("- Accept it (y): Add the rule to your .cursor/rules directory")
        click.echo("- Skip it (n): Don't add this rule")
        click.echo("- Quit (q): Stop reviewing rules\n")
        
        accepted_rules = []
        
        # Get cluster information for context
        git_stats = analyzer._get_git_file_stats()
        candidate_rules = analyzer._convert_to_candidate_rules(all_static_analyses, git_stats)
        clusters = analyzer._cluster_rules(candidate_rules)
        
        for i, mdc_content in enumerate(mdc_files, 1):
            try:
                # Parse the rule to show details
                yaml_end = mdc_content.find('---', 3)
                if yaml_end > 0:
                    front_matter = mdc_content[3:yaml_end].strip()
                    parsed = yaml.safe_load(front_matter)
                    description = parsed.get('description', 'No description')
                    globs = parsed.get('globs', [])
                    
                    # Extract bullets
                    content_after_yaml = mdc_content[yaml_end + 3:].strip()
                    bullets = [line.strip('- ').strip() for line in content_after_yaml.split('\n') if line.strip().startswith('-')]
                    
                    # Find corresponding cluster for evidence
                    cluster_key = None
                    cluster_info = None
                    
                    # Match rule to cluster (approximate matching by description keywords)
                    for key, cluster in clusters.items():
                        if cluster.meta and cluster.meta.score >= 3.0:
                            # Try to match by checking if any cluster rule has similar bullets
                            canonical = analyzer._choose_canonical(cluster)
                            if any(bullet in canonical.bullets for bullet in bullets[:2]):
                                cluster_key = key
                                cluster_info = cluster
                                break
                    
                    click.echo(f"\n{'='*60}")
                    click.echo(f"Rule {i}/{len(mdc_files)}: {description}")
                    click.echo(f"{'='*60}")
                    
                    # Basic rule info
                    click.echo(f"📋 Scope: {', '.join(globs)}")
                    click.echo(f"📝 Rules ({len(bullets)} items):")
                    for bullet in bullets:
                        click.echo(f"    • {bullet}")
                    
                    # Evidence and statistics
                    if cluster_info and cluster_info.meta:
                        click.echo(f"\n📊 Evidence & Statistics:")
                        click.echo(f"    • Confidence Score: {cluster_info.meta.score:.1f}/10")
                        click.echo(f"    • Pattern found in: {cluster_info.meta.support_files} files")
                        click.echo(f"    • Total occurrences: {len(cluster_info.rules)} instances")
                        click.echo(f"    • Git activity: {cluster_info.meta.total_edits} total edits")
                        
                        # Show evidence files with line numbers
                        click.echo(f"\n🔍 Evidence Files:")
                        evidence_files = {}
                        for rule in cluster_info.rules:
                            if rule.file not in evidence_files:
                                evidence_files[rule.file] = []
                            evidence_files[rule.file].extend(rule.evidence_lines)
                        
                        for file_path, lines in list(evidence_files.items())[:5]:  # Show max 5 files
                            line_ranges = sorted(set(lines))
                            if len(line_ranges) > 3:
                                line_display = f"lines {min(line_ranges)}-{max(line_ranges)} ({len(line_ranges)} locations)"
                            else:
                                line_display = f"lines {', '.join(map(str, line_ranges))}"
                            
                            # Show git commit count for this file if available
                            git_info = ""
                            if git_details and 'modification_counts' in git_details:
                                commits = git_details['modification_counts'].get(file_path, 0)
                                if commits > 0:
                                    git_info = f" ({commits} commits)"
                            
                            click.echo(f"    📄 {file_path} - {line_display}{git_info}")
                            
                            # Show a code preview for the first file
                            if file_path == list(evidence_files.keys())[0] and len(line_ranges) > 0:
                                try:
                                    file_full_path = Path(directory) / file_path
                                    if file_full_path.exists():
                                        with open(file_full_path, 'r', encoding='utf-8') as f:
                                            file_lines = f.readlines()
                                            
                                        # Show a snippet around the first evidence line
                                        target_line = min(line_ranges) - 1  # Convert to 0-based
                                        start = max(0, target_line - 1)
                                        end = min(len(file_lines), target_line + 3)
                                        
                                        click.echo(f"        💡 Code preview:")
                                        for i in range(start, end):
                                            line_num = i + 1
                                            line_content = file_lines[i].rstrip()
                                            if line_num in line_ranges:
                                                click.echo(f"        {line_num:3d}► {line_content}")
                                            else:
                                                click.echo(f"        {line_num:3d}  {line_content}")
                                except Exception:
                                    pass  # Skip code preview if file can't be read
                        
                        if len(evidence_files) > 5:
                            click.echo(f"    ... and {len(evidence_files) - 5} more files")
                        
                        # Pattern frequency
                        if cluster_info.meta.support_files > 1:
                            frequency_desc = "common pattern" if cluster_info.meta.support_files >= 3 else "emerging pattern"
                            click.echo(f"\n💡 This appears to be a {frequency_desc} in your codebase.")
                        else:
                            click.echo(f"\n💡 This is a specific pattern found in one file.")
                        
                        # Add recommendation based on evidence strength
                        score = cluster_info.meta.score
                        support_files = cluster_info.meta.support_files
                        total_edits = cluster_info.meta.total_edits
                        
                        if score >= 10 and support_files >= 4:
                            recommendation = "🟢 HIGHLY RECOMMENDED - Strong pattern with wide usage"
                        elif score >= 6 and support_files >= 3:
                            recommendation = "🟡 RECOMMENDED - Good pattern with moderate usage"
                        elif score >= 4 and support_files >= 2:
                            recommendation = "🟠 CONSIDER - Decent pattern, review evidence carefully"
                        elif total_edits >= 20:
                            recommendation = "🔵 WORTH CONSIDERING - High-activity files, may be important"
                        else:
                            recommendation = "⚪ OPTIONAL - Limited evidence, use your judgment"
                        
                        click.echo(f"\n🎯 Recommendation: {recommendation}")
                            
                    else:
                        # Fallback for rules without cluster info
                        click.echo(f"\n📊 Evidence & Statistics:")
                        click.echo(f"    • This rule was generated from analyzed patterns")
                        click.echo(f"    • Confidence: Medium (standalone rule)")
                        click.echo(f"\n🎯 Recommendation: 🟠 CONSIDER - Review carefully")
                    
                else:
                    click.echo(f"\nRule {i}/{len(mdc_files)}: (Unable to parse rule details)")
                    
            except Exception as e:
                click.echo(f"\nRule {i}/{len(mdc_files)}: (Parse error: {e})")
                if verbose:
                    import traceback
                    click.echo(f"Details: {traceback.format_exc()}")
            
            # Get user decision
            choice = click.prompt(
                f"\n🤔 Add this rule to your .cursor/rules directory? (y/n/q)",
                type=click.Choice(['y', 'n', 'q'], case_sensitive=False),
                default='n'
            )
            
            if choice == 'q':
                break
            
            if choice == 'y':
                accepted_rules.append(mdc_content)
        
        # Save accepted rules
        if accepted_rules:
            click.echo(f"\n💾 Organizing {len(accepted_rules)} accepted rules into categories...")
            
            try:
                # Parse accepted rules into StaticAnalysisRule objects for categorization
                rules_for_categorization = []
                for mdc_content in accepted_rules:
                    try:
                        # Parse the rule
                        yaml_end = mdc_content.find('---', 3)
                        if yaml_end > 0:
                            front_matter = mdc_content[3:yaml_end].strip()
                            parsed = yaml.safe_load(front_matter)
                            description = parsed.get('description', 'No description')
                            globs = parsed.get('globs', ['**/*'])
                            
                            # Extract bullets
                            content_after_yaml = mdc_content[yaml_end + 3:].strip()
                            bullets = [line.strip('- ').strip() for line in content_after_yaml.split('\n') if line.strip().startswith('-')]
                            
                            # Create a simple slug from description
                            slug = analyzer._slugify(description)
                            
                            # Import the type we need
                            from baml_client.types import StaticAnalysisRule
                            
                            rule = StaticAnalysisRule(
                                slug=slug,
                                description=description,
                                scope_glob=globs[0] if globs else "**/*",
                                bullets=bullets,
                                evidence_lines=[]  # Not needed for categorization
                            )
                            rules_for_categorization.append(rule)
                    except Exception as e:
                        click.echo(f"⚠️  Failed to parse a rule for categorization: {e}")
                        continue
                
                if rules_for_categorization:
                    # Use LLM to categorize the rules
                    baml_options = analyzer.token_tracker.get_baml_options() if analyzer.token_tracker else {}
                    categories = await analyzer.client.CategorizeAcceptedRules(
                        accepted_rules=rules_for_categorization,
                        baml_options=baml_options
                    )
                    
                    # Track token usage from this call
                    if analyzer.token_tracker:
                        analyzer.token_tracker.track_call_from_collector('rule_categorization', 'claude-sonnet-4-20250514')
                    
                    click.echo(f"\n📂 Suggested categories:")
                    for i, category in enumerate(categories, 1):
                        click.echo(f"  {i}. {category.category_name}.mdc - {category.description} ({len(category.rules)} rules)")
                    
                    if click.confirm(f"\n✅ Create {len(categories)} category files with these groupings?", default=True):
                        created_files = []
                        
                        for category in categories:
                            if not category.rules:
                                continue
                                
                            # Create combined .mdc content for this category
                            front_matter = {
                                'description': category.description,
                                'globs': list(set(rule.scope_glob for rule in category.rules if rule.scope_glob)),
                                'type': 'autoAttached'
                            }
                            
                            # Combine all bullets from rules in this category
                            all_bullets = []
                            for rule in category.rules:
                                all_bullets.extend(rule.bullets)
                            
                            # Remove duplicates while preserving order
                            seen = set()
                            unique_bullets = []
                            for bullet in all_bullets:
                                if bullet not in seen:
                                    seen.add(bullet)
                                    unique_bullets.append(bullet)
                            
                            yaml_content = yaml.dump(front_matter, default_flow_style=False).strip()
                            bullets_content = '\n'.join(f"- {bullet}" for bullet in unique_bullets)
                            
                            category_content = f"""---
{yaml_content}
---

{bullets_content}"""
                            
                            # Save to category file
                            category_file = rules_dir / f"{category.category_name}.mdc"
                            
                            # Handle existing files
                            if category_file.exists():
                                if click.confirm(f"📄 {category.category_name}.mdc already exists. Overwrite?", default=False):
                                    category_file.write_text(category_content, encoding='utf-8')
                                    created_files.append(str(category_file.relative_to(Path(directory))))
                                else:
                                    # Create with a number suffix
                                    counter = 1
                                    while (rules_dir / f"{category.category_name}-{counter}.mdc").exists():
                                        counter += 1
                                    category_file = rules_dir / f"{category.category_name}-{counter}.mdc"
                                    category_file.write_text(category_content, encoding='utf-8')
                                    created_files.append(str(category_file.relative_to(Path(directory))))
                            else:
                                category_file.write_text(category_content, encoding='utf-8')
                                created_files.append(str(category_file.relative_to(Path(directory))))
                        
                        click.echo("\n✅ Category files created successfully!")
                        click.echo(f"📁 Files created in {rules_dir}:")
                        for file_path in created_files:
                            click.echo(f"  • {file_path}")
                    else:
                        # Fall back to individual files with improved names
                        click.echo(f"\n💾 Saving {len(accepted_rules)} rules as individual files...")
                        created_files = analyzer.save_mdc_files(accepted_rules, rules_dir)
                        
                        click.echo("\n✅ Individual rule files created!")
                        click.echo(f"📁 Files created in {rules_dir}:")
                        for file_path in created_files[:5]:  # Show first 5
                            click.echo(f"  • {file_path}")
                        if len(created_files) > 5:
                            click.echo(f"  ... and {len(created_files) - 5} more")
                else:
                    # Fallback if categorization parsing fails
                    click.echo(f"\n💾 Saving {len(accepted_rules)} rules...")
                    created_files = analyzer.save_mdc_files(accepted_rules, rules_dir)
                    
                    click.echo("\n✅ Rules saved!")
                    click.echo(f"📁 Files created in {rules_dir}:")
                    for file_path in created_files[:5]:
                        click.echo(f"  • {file_path}")
                    if len(created_files) > 5:
                        click.echo(f"  ... and {len(created_files) - 5} more")
                        
            except Exception as e:
                click.echo(f"⚠️  Categorization failed: {e}")
                click.echo("📝 Falling back to individual rule files...")
                created_files = analyzer.save_mdc_files(accepted_rules, rules_dir)
                
                click.echo("\n✅ Rules saved as individual files!")
                click.echo(f"📁 Files created in {rules_dir}:")
                for file_path in created_files[:5]:
                    click.echo(f"  • {file_path}")
                if len(created_files) > 5:
                    click.echo(f"  ... and {len(created_files) - 5} more")
        else:
            click.echo("\n👋 No rules were accepted.")
        
    elif mdc_files:
        # Auto-save all rules if not reviewing
        click.echo(f"\n💾 Saving all {len(mdc_files)} rules...")
        created_files = analyzer.save_mdc_files(mdc_files, rules_dir)
        
        click.echo("\n✅ All rules saved!")
        click.echo(f"📁 Files created in {rules_dir}:")
        for file_path in created_files[:5]:  # Show first 5
            click.echo(f"  • {file_path}")
        if len(created_files) > 5:
            click.echo(f"  ... and {len(created_files) - 5} more")
    
    # Clean up old files
    old_rules = Path(directory) / ".cursor" / "rules.mdc"
    if old_rules.exists():
        old_rules.unlink()
        click.echo("\n🗑️  Removed old rules.mdc file")
    
    # Clean up analysis files
    if analysis_file.exists():
        analysis_file.unlink()
    if analysis_dir.exists() and not any(analysis_dir.iterdir()):
        analysis_dir.rmdir()

def main():
    """Entry point for the CLI application."""
    cli()

if __name__ == "__main__":
    main() 