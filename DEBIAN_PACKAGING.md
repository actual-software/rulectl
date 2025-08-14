# Debian Package Support for Rulectl

This document describes the Debian packaging support added to rulectl, enabling installation via `apt` package manager.

## Overview

Rulectl now supports building and distributing `.deb` packages for Debian and Ubuntu systems. This makes installation much easier for users who prefer system package managers over manual binary installation.

## Features

- ✅ **Automated .deb building** in GitHub Actions release workflow
- ✅ **Standalone executable** - no Python runtime dependencies required
- ✅ **Standard Debian packaging** following best practices
- ✅ **Makefile targets** for local development and testing
- ✅ **Proper metadata** including description, dependencies, and maintainer info

## Package Details

- **Package Name**: `rulectl`
- **Architecture**: `amd64` (x86_64)
- **Section**: `devel` (development tools)
- **Dependencies**: Only system libraries (no Python runtime required)
- **Installation Path**: `/usr/bin/rulectl`

## Files Added

### Debian Packaging Configuration (`.github/build/debian/` directory)

- `.github/build/debian/control` - Package metadata and dependencies
- `.github/build/debian/changelog` - Package version history
- `.github/build/debian/compat` - Debhelper compatibility level (13)
- `.github/build/debian/copyright` - License information
- `.github/build/debian/rules` - Build rules and instructions
- `.github/build/debian/install` - File installation mappings

### Build System

- `Makefile` - Build targets for binary and .deb package creation
- `scripts/test-deb-build.sh` - Comprehensive test script

### Documentation

- Updated `README.md` with Debian/Ubuntu installation instructions
- This `DEBIAN_PACKAGING.md` documentation file

## Usage

### For End Users

#### Installation via .deb Package
```bash
# Download the latest .deb package
wget https://github.com/actual-software/rulectl/releases/latest/download/rulectl_*_amd64.deb

# Install the package
sudo dpkg -i rulectl_*_amd64.deb

# Fix dependencies if needed
sudo apt-get install -f
```

#### Uninstallation
```bash
sudo dpkg -r rulectl
```

### For Developers

#### Local Development

```bash
# Show available build targets
make help

# Build binary only
make build-binary

# Test the binary
make test

# Clean build artifacts
make clean

# Check version
make version
```

#### Building .deb Package (Requires Debian/Ubuntu)

```bash
# Install Debian packaging dependencies
make deb-deps

# Build the .deb package
make build-deb

# Install the built package
make install-deb

# Uninstall the package
make uninstall-deb
```

#### Testing

```bash
# Run comprehensive test suite
./scripts/test-deb-build.sh
```

#### Docker-based Building

For developers on macOS/Windows who want to test .deb building:

```bash
docker run --rm -v $(pwd):/workspace -w /workspace ubuntu:22.04 bash -c '
apt-get update && 
apt-get install -y build-essential dpkg-dev debhelper devscripts dh-python python3 python3-pip python3-venv && 
make build-deb'
```

## GitHub Actions Integration

The `.deb` package building is fully integrated into the existing GitHub Actions release workflow:

1. **Triggered by**: Version changes in `version.py` via merged PRs
2. **Build Process**: 
   - Builds the standalone executable using PyInstaller
   - Creates the .deb package using `dpkg-buildpackage`
   - Uploads the package as a release artifact
3. **Release Assets**: The .deb package is automatically attached to GitHub releases

### Workflow Changes

- Added `build-deb-package` job that runs in parallel with binary builds
- Updated release notes to include Debian installation instructions  
- Added .deb package to release assets

## Technical Details

### Package Building Process

1. **Environment Setup**: Install Python 3.11 and Debian packaging tools
2. **Changelog Update**: Generate debian/changelog with current version and GitHub release link
3. **Dependency Installation**: Use `fix_dependencies.py` to install Python deps
4. **BAML Client Generation**: Generate API client code with `baml_init.py`
5. **Binary Building**: Create standalone executable with PyInstaller via `build.py`
6. **Package Creation**: Use `dpkg-buildpackage` to create the .deb package
7. **Artifact Upload**: Upload to GitHub Actions artifacts and releases

### Package Versioning

- **Upstream version**: Matches the project version (e.g., `0.1.3`)
- **Debian revision**: Always `-1` (first build of each upstream version)
- **Final package**: `rulectl_0.1.3-1_amd64.deb`

The debian/changelog is automatically generated and points to GitHub releases for detailed change information, avoiding sync issues between multiple changelog formats.

### Binary Characteristics

- **Size**: ~40MB (includes all Python dependencies)
- **Dependencies**: Only system libraries (libc, etc.)
- **Architecture**: x86_64 (amd64)
- **Compatibility**: Debian 10+, Ubuntu 18.04+

## Roadmap

Future enhancements to consider:

- [ ] **APT Repository**: Set up a custom APT repository for easier installation
- [ ] **ARM64 Support**: Add aarch64/arm64 .deb packages
- [ ] **Multiple Distros**: Support for different Debian/Ubuntu versions
- [ ] **GPG Signing**: Sign packages for enhanced security
- [ ] **Automatic Updates**: Integration with system update mechanisms

## Troubleshooting

### Common Issues

**Q: Installation fails with "dpkg: dependency problems"**
A: Run `sudo apt-get install -f` to fix missing dependencies

**Q: Package not found in releases**
A: Ensure you're downloading from the latest release, and the .deb package was built successfully

**Q: "Package architecture (amd64) does not match system (arm64)"**
A: The current package only supports x86_64. Use the manual installation method for other architectures.

### Development Issues

**Q: `make build-deb` fails with "dpkg-buildpackage: command not found"**
A: Run `make deb-deps` first to install Debian packaging tools

**Q: Build fails on macOS**
A: .deb packages can only be built on Debian/Ubuntu systems. Use Docker or CI for building.

**Q: "Error: .github/build/debian/ directory not found"**
A: Ensure you have all the Debian packaging files in the correct location under `.github/build/debian/`

## Contributing

When contributing to the Debian packaging:

1. Test changes with `./scripts/test-deb-build.sh`
2. Update `.github/build/debian/changelog` for version changes
3. Follow Debian packaging best practices
4. Test installation/uninstallation process
5. Update documentation as needed

## References

- [Debian New Maintainer's Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [Debhelper Documentation](https://manpages.debian.org/testing/debhelper/debhelper.7.en.html)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)