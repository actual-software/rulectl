# GitHub Actions Release Workflow Implementation Plan

## Project Overview
Create an automated GitHub Actions workflow that builds and releases standalone executables for the Rules Engine CLI tool across 6 different platform/architecture combinations when the version is incremented in `setup.py`.

## Current State Analysis

### Build System
- **Build Tool**: PyInstaller (v5.13.0+)
- **Entry Point**: `rules_engine/cli.py`
- **Binary Name**: `rules-engine` (`.exe` on Windows)
- **Python Version**: 3.8+ required

### Key Dependencies
- **Core**: click, colorama, pathspec, pyyaml, python-dotenv
- **BAML**: baml-py (>=0.202.1), requires pre-generation before build
- **Type Support**: typing_extensions, pydantic

### Special Requirements
1. **BAML Generation**: Must run `baml-cli generate` before building
2. **BAML Files**: Located in `baml_src/` directory, must be bundled
3. **Config Files**: Must include `config/` directory
4. **Environment Variables**: 
   - `BAML_LOG=OFF` during build
   - `RULES_ENGINE_BUILD=1` to indicate build mode

## Target Platforms (6 Binaries)

| Platform | Architecture | Runner | Binary Name |
|----------|-------------|---------|------------|
| Windows | x86_64 | windows-latest | rules-engine-windows-x64.exe |
| Windows | ARM64 | windows-latest (with emulation) | rules-engine-windows-arm64.exe |
| macOS | x86_64 | macos-13 | rules-engine-macos-x64 |
| macOS | ARM64 | macos-14 | rules-engine-macos-arm64 |
| Linux | x86_64 | ubuntu-latest | rules-engine-linux-x64 |
| Linux | ARM64 | ubuntu-latest (with QEMU) | rules-engine-linux-arm64 |

## Workflow Architecture

### 1. Trigger Conditions
- **Event**: Push to `main` branch (after PR merge)
- **Condition**: Version line changed in `setup.py`
- **Version Format**: `version="X.Y.Z"` (semantic versioning)
- **Validation**: Only trigger on version increases

### 2. Job Structure

```yaml
jobs:
  detect-version-change:
    # Checks if version increased
    # Outputs: version_changed, new_version, old_version
    
  build-binaries:
    # Matrix build for 6 platforms
    # Depends on: detect-version-change
    # Condition: if version_changed == true
    
  create-release:
    # Creates GitHub Release with artifacts
    # Depends on: build-binaries
    # Attaches all 6 binaries
```

### 3. Version Detection Logic
```python
# Pseudocode for version comparison
old_version = extract_version_from_previous_commit()
new_version = extract_version_from_current_commit()

if semantic_version(new_version) > semantic_version(old_version):
    trigger_build = true
```

### 4. Build Process Per Platform

1. **Setup Environment**
   - Checkout code with full history
   - Setup Python 3.11
   - Create virtual environment

2. **Install Dependencies**
   - Upgrade pip
   - Install typing_extensions and pydantic first (conflict resolution)
   - Install all requirements.txt

3. **Prepare BAML**
   - Set environment variables
   - Run `python baml_init.py` to generate BAML client
   - Verify generation succeeded

4. **Build Executable**
   - Run `python build.py`
   - PyInstaller creates single-file executable
   - Binary output to `dist/` directory

5. **Platform-Specific Handling**
   - **Windows**: Add `.exe` extension
   - **macOS**: Set bundle identifier, skip code signing
   - **Linux**: Set executable permissions (chmod +x)
   - **ARM**: Use QEMU emulation or dedicated runners

6. **Upload Artifact**
   - Rename binary with platform suffix
   - Upload using actions/upload-artifact@v4

### 5. Release Creation

1. **Download All Artifacts**
   - Retrieve all 6 platform binaries
   - Verify all builds succeeded

2. **Create GitHub Release**
   - Tag: `v{version}` (e.g., v0.1.1)
   - Title: `Rules Engine v{version}`
   - Generate release notes from commits
   - Mark as draft initially

3. **Attach Binaries**
   - Upload all 6 binaries as release assets
   - Use descriptive names for each platform

4. **Finalize Release**
   - Publish release (remove draft status)
   - No automated package registry publishing

## Implementation Files

### Required Files
1. `.github/workflows/release.yml` - Main workflow definition
2. `suppress_warnings.py` - Runtime hook for PyInstaller (check if exists)

### Workflow File Structure
```yaml
name: Build and Release

on:
  push:
    branches: [main]
    paths:
      - 'setup.py'

jobs:
  # ... (detailed implementation to follow)
```

## Key Considerations

### Security
- Use GitHub's built-in GITHUB_TOKEN for authentication
- No hardcoded credentials
- Artifacts are temporarily stored, cleaned after 90 days

### Error Handling
- Each job should fail fast on errors
- Use continue-on-error: false (default)
- Clear error messages in logs

### Performance
- Use matrix strategy for parallel builds
- Cache Python dependencies where possible
- Minimize checkout depth where appropriate

### Testing
- Each binary should be smoke-tested before release
- Run `--help` command to verify basic functionality
- Check file size sanity (not empty, not too large)

## ARM Build Strategy

### Options for ARM Support

1. **QEMU Emulation** (Recommended for Linux ARM)
   - Use docker/setup-qemu-action
   - Slower but reliable
   - No additional runner costs

2. **Self-Hosted Runners** (For production)
   - Native ARM runners for better performance
   - Requires infrastructure setup

3. **Cross-Compilation** (Alternative)
   - Build on x64 targeting ARM
   - May have compatibility issues

## Next Steps

1. ✅ Analyze existing build system
2. ✅ Document implementation plan
3. ⏳ Wait for other PR to be merged and pull main
4. 🔄 Implement `.github/workflows/release.yml`
5. 🔄 Test workflow with version increment
6. 🔄 Validate all 6 binaries work correctly
7. 🔄 Final review and adjustments

## Notes

- No automatic publishing to PyPI or other registries
- Binaries are self-contained (no Python required on target)
- BAML files are bundled within the executable
- Version must follow semantic versioning (X.Y.Z format)
- Workflow only triggers on version increases, not decreases

## Example Version Change Detection

```bash
# Get version from previous commit
git show HEAD~1:setup.py | grep 'version=' | sed 's/.*version="\(.*\)".*/\1/'

# Get version from current commit  
grep 'version=' setup.py | sed 's/.*version="\(.*\)".*/\1/'

# Compare versions using Python
python -c "from packaging import version; print(version.parse('0.1.1') > version.parse('0.1.0'))"
```

## Estimated Timeline

- Version detection job: ~30 seconds
- Each platform build: 3-5 minutes
- Total parallel build time: ~5 minutes
- Release creation: ~1 minute
- **Total workflow time: ~6-7 minutes**

---

*This document represents the complete implementation plan as of the current state. Resume implementation after pulling latest changes from main.*