Evidence from rulectl/git_utils.py (1,643 lines) and rulectl/analyzer.py demonstrates deep Git integration implemented by Ethan (2025-09-02, commit b4a0531a). The GitAnalyzer class provides git blame analysis (get_file_statistics), branch detection (_find_main_branch), commit history tracking (get_recent_activity), and gitignore-based file filtering. This pattern enables provenance tracking by attributing code patterns to specific authors, dates, and commits, which is essential for understanding architectural decision origins.

## Policies
- Use subprocess module with git commands for all Git repository operations in Python applications
- Validate Git repository existence before performing any git operations using subprocess.run(['git', 'rev-parse', '--git-dir'])
- Integrate gitignore patterns for file filtering using pathspec module with 'gitwildmatch' pattern type
- Implement git blame analysis to track file provenance including author, date, and commit metadata
- Detect repository main branch dynamically by checking for 'main', 'master', or current branch
- Use Path.resolve() for absolute path resolution when working with Git repository paths
- Extract git metadata (commit hash, author, email, date) for all analyzed files to support provenance tracking

## Instructions
- Create GitAnalyzer class with __init__ accepting repo_path and validating Git repository
- Use subprocess.run() with git commands, capturing stdout with text=True and check=True
- Implement _validate_git_repo() method calling 'git rev-parse --git-dir' to verify repository
- Parse git blame output to extract line-by-line author and commit information
- Load and parse .gitignore file using pathspec.PathSpec.from_lines('gitwildmatch', patterns)
- Implement get_file_statistics() to return commit count and author data per file
- Use collections.defaultdict and collections.Counter for aggregating Git statistics