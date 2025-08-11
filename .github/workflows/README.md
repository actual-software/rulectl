# GitHub Actions Release Workflow

## Overview

This workflow automatically builds and releases Rulectl binaries for 6 different platform/architecture combinations when the version is incremented in `version.py`.

## Supported Platforms

| Platform | Architecture | Runner | Binary Name |
|----------|-------------|---------|------------|
| Windows | x64 | windows-latest | rulectl-windows-x64.exe |
| Windows | ARM64 | windows-latest (emulated) | rulectl-windows-arm64.exe |
| macOS | x64 (Intel) | macos-13 | rulectl-macos-x64 |
| macOS | ARM64 (Apple Silicon) | macos-14 | rulectl-macos-arm64 |
| Linux | x64 | ubuntu-latest | rulectl-linux-x64 |
| Linux | ARM64 | ubuntu-24.04-arm | rulectl-linux-arm64 |

## How It Works

### 1. Trigger
The workflow triggers when:
- A push is made to the `main` branch
- The `version.py` file is modified
- The version number has **increased** (not decreased or unchanged)

### 2. Version Detection
- Extracts version from current and previous commit
- Uses semantic versioning comparison
- Only proceeds if version increased (e.g., 0.1.0 → 0.1.1)

### 3. Build Process
For each platform:
1. Sets up Python 3.11 environment
2. Creates virtual environment
3. Installs dependencies (with conflict resolution)
4. Generates BAML client code
5. Builds standalone executable with PyInstaller
6. Tests binary with `--help` command
7. Uploads as artifact

### 4. Release Creation
- Downloads all 6 binaries
- Creates draft GitHub Release
- Attaches all binaries with platform-specific names
- Generates release notes from commit history

## Usage

### Creating a Release

1. **Update version** in `version.py`:
   ```python
   VERSION = "0.1.1"  # Increment from previous version
   ```

2. **Commit and push** to main:
   ```bash
   git add version.py
   git commit -m "Bump version to 0.1.1"
   git push origin main
   ```

3. **Monitor workflow** at Actions tab in GitHub

4. **Publish release**:
   - Go to Releases page
   - Review the draft release
   - Click "Publish release" when ready

### Version Format
- Must follow semantic versioning: `X.Y.Z`
- Examples: `0.1.0`, `1.0.0`, `2.3.14`
- Pre-release versions not supported

## Important Notes

### ARM64 Support
- **Linux ARM64**: Uses native GitHub-hosted runner (free for public repos)
- **Windows ARM64**: Currently uses emulation (native runners coming soon)
- **macOS ARM64**: Uses native Apple Silicon runner (macos-14)

### Runner Versions (2025)
- `ubuntu-latest`: Ubuntu 24.04
- `windows-latest`: Windows Server 2022 (migrating to 2025)
- `macos-13`: Intel-based macOS
- `macos-14`: Apple Silicon macOS
- `ubuntu-24.04-arm`: Native ARM64 Linux

### Build Environment
Required environment variables set automatically:
- `BAML_LOG=OFF`: Disables BAML logging during build
- `RULES_ENGINE_BUILD=1`: Indicates build mode

### Binary Naming Convention
```
rulectl-{platform}-{architecture}.{extension}
```
Examples:
- `rulectl-windows-x64.exe`
- `rulectl-macos-arm64`
- `rulectl-linux-x64`

## Troubleshooting

### Build Failures

1. **BAML Generation Failed**
   - Check `baml_init.py` exists
   - Verify BAML files in `baml_src/`
   - Ensure baml-py is in requirements.txt

2. **PyInstaller Build Failed**
   - Check `build.py` configuration
   - Verify all hidden imports are specified
   - Check suppress_warnings.py exists

3. **Version Not Triggering Build**
   - Ensure version actually increased
   - Check version format matches regex: `VERSION="X.Y.Z"`
   - Verify push is to main branch

### Testing Locally

Simulate the build process locally:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Generate BAML
export BAML_LOG=OFF
export RULES_ENGINE_BUILD=1
python baml_init.py

# Build executable
python build.py

# Test binary
dist/rulectl --help
```

## Maintenance

### Updating Python Version
Edit `.github/workflows/release.yml`:
```yaml
python-version: '3.11'  # Change from 3.11
```

### Adding New Platform
Add new entry to build matrix:
```yaml
- os: new-os
  arch: new-arch
  runner: runner-name
  binary_name: binary
  artifact_name: rulectl-new-platform
```

### Changing Release Behavior
- To auto-publish (not recommended): Remove `draft: true`
- To mark as pre-release: Set `prerelease: true`
- To change tag format: Modify `tag_name` pattern

## Security Considerations

- Uses GitHub's built-in `GITHUB_TOKEN`
- No external credentials required
- Artifacts auto-expire after 1 day
- Draft releases require manual publishing

## Performance

- Total workflow time: ~6-7 minutes
- Parallel builds for all platforms
- No caching (ensures clean builds)
- Minimal artifact retention (1 day)

## Related Files

- `.github/workflows/release.yml`: Main workflow file
- `version.py`: Version source (single source of truth)
- `setup.py`: Uses version from version.py
- `build.py`: PyInstaller configuration
- `baml_init.py`: BAML generation script
- `suppress_warnings.py`: Runtime warning suppression