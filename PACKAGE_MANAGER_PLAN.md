# Package Manager Distribution Plan

This document outlines how to make `rulectl` available through various package managers.

## Homebrew (macOS/Linux)

### 1. Create Homebrew Tap Repository

Create a new GitHub repository: `homebrew-rulectl` (must start with "homebrew-")

**Repository structure:**
```
homebrew-rulectl/
├── Formula/
│   └── rulectl.rb
└── README.md
```

### 2. Dynamic Formula File

Create `Formula/rulectl.rb` that automatically fetches the latest version:

```ruby
class Rulectl < Formula
  desc "CLI tool for managing and executing rules"
  homepage "https://github.com/actual-software/rulectl"
  
  # Fetch latest version and assets from GitHub API
  def self.latest_release_info
    require 'json'
    require 'net/http'
    require 'uri'
    
    uri = URI('https://api.github.com/repos/actual-software/rulectl/releases/latest')
    response = Net::HTTP.get_response(uri)
    
    if response.code == '200'
      JSON.parse(response.body)
    else
      raise "Failed to fetch release info: #{response.code}"
    end
  end
  
  def self.latest_version
    latest_release_info['tag_name'].sub(/^v/, '')
  end
  
  def self.asset_url(asset_name)
    assets = latest_release_info['assets']
    asset = assets.find { |a| a['name'] == asset_name }
    asset ? asset['browser_download_url'] : nil
  end
  
  def self.calculate_sha256(url)
    require 'digest'
    require 'net/http'
    
    uri = URI(url)
    response = Net::HTTP.get_response(uri)
    
    if response.code == '200'
      Digest::SHA256.hexdigest(response.body)
    else
      raise "Failed to download asset for SHA calculation: #{response.code}"
    end
  end
  
  version latest_version

  on_macos do
    if Hardware::CPU.arm?
      url asset_url("rulectl-macos-arm64")
      sha256 calculate_sha256(asset_url("rulectl-macos-arm64"))
    else
      url asset_url("rulectl-macos-x64")
      sha256 calculate_sha256(asset_url("rulectl-macos-x64"))
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url asset_url("rulectl-linux-arm64")
      sha256 calculate_sha256(asset_url("rulectl-linux-arm64"))
    else
      url asset_url("rulectl-linux-x64")
      sha256 calculate_sha256(asset_url("rulectl-linux-x64"))
    end
  end

  def install
    case OS.kernel_name.downcase
    when "darwin"
      arch_suffix = Hardware::CPU.arm? ? "arm64" : "x64"
      bin.install "rulectl-macos-#{arch_suffix}" => "rulectl"
    when "linux"
      arch_suffix = Hardware::CPU.arm? ? "arm64" : "x64"
      bin.install "rulectl-linux-#{arch_suffix}" => "rulectl"
    end
  end

  test do
    system "#{bin}/rulectl", "--help"
  end
end
```

### 3. Repository Setup

```bash
# Create and setup the tap repository
git clone https://github.com/actual-software/homebrew-rulectl.git
cd homebrew-rulectl
mkdir Formula
# Add the Formula/rulectl.rb file above
git add .
git commit -m "Initial formula for rulectl"
git push
```

### 4. No CI Integration Needed!

With the dynamic formula approach, **no CI updates are required**. The formula automatically:

- Fetches the latest version from GitHub API
- Downloads the correct binary for each platform/architecture
- Calculates SHA256 checksums on-the-fly

**Benefits:**
- Zero maintenance overhead
- Automatically stays in sync with releases
- No need for additional CI jobs or secrets
- No risk of formula getting out of sync

**Trade-offs:**
- Slightly slower installation (downloads happen during `brew install`)
- Requires internet connection during installation
- More complex formula code

**How it works:**
1. User runs `brew install actual-software/rulectl/rulectl`
2. Homebrew calls the formula's class methods
3. Formula fetches latest release info from GitHub API
4. Formula determines correct binary URL for user's platform
5. Formula downloads and verifies the binary
6. Installation proceeds normally

### 5. User Installation

Once set up, users can install with:

```bash
# Add the tap
brew tap actual-software/rulectl

# Install rulectl
brew install rulectl

# Or in one command
brew install actual-software/rulectl/rulectl
```

## APT (Ubuntu/Debian)

### Overview

For APT compatibility, we need to:
1. Create `.deb` packages in CI
2. Host our own APT repository 
3. Provide installation instructions for users

### 1. .deb Package Creation

APT packages are more complex than Homebrew formulas. We'll need to:

- Create package metadata (control files)
- Build `.deb` files containing our binaries
- Host an APT repository (can use GitHub Pages or S3)

### 2. Package Structure

A `.deb` package contains:
```
package/
├── DEBIAN/
│   ├── control          # Package metadata
│   ├── postinst         # Post-install script (optional)
│   └── prerm            # Pre-removal script (optional)
└── usr/
    └── bin/
        └── rulectl      # The binary
```

### 3. Implementation Options

**Option A: Simple GitHub Releases**
- Create `.deb` files in CI
- Upload as release assets
- Users download and install manually with `dpkg -i`

**Option B: Full APT Repository** 
- Create proper APT repository structure
- Host on GitHub Pages or S3
- Users can `apt install` normally

**Option C: Use a service**
- Services like Gemfury or PackageCloud handle hosting
- More complex but more "professional"

### 4. Recommended Approach: Use PackageCloud

For true `apt install rulectl` experience, **use PackageCloud** (~$50/month):

**Why PackageCloud over self-hosting:**
- Proper APT repository requires complex infrastructure
- Need GPG key management and signing
- Repository metadata is finicky to maintain
- Multi-architecture support is challenging
- Security considerations (package verification)

**PackageCloud benefits:**
- Users get clean `apt install rulectl` experience
- Handles .deb creation from your binaries via API
- Manages all repository metadata automatically
- Supports multiple distributions (Ubuntu 20.04, 22.04, Debian 11, 12, etc.)
- Provides installation instructions automatically
- Handles GPG signing and key management

**Alternative: Simple .deb files**
If cost is a concern, start with **Option A** (simple .deb files):
- Create .deb files in CI as release assets
- Users install with `wget + dpkg -i`
- Much easier to implement
- Can upgrade to PackageCloud later when revenue justifies cost

**Implementation with PackageCloud:**
1. Sign up for PackageCloud account
2. Get API token
3. Add CI step to upload binaries to PackageCloud
4. PackageCloud auto-generates .deb packages
5. Users add your repository once:
   ```bash
   curl -s https://packagecloud.io/install/repositories/your-org/rulectl/script.deb.sh | sudo bash
   sudo apt install rulectl
   ```

**Cost-benefit analysis:**
- $50/month = $600/year
- If you have 100+ Ubuntu/Debian users, probably worth it
- If fewer users, stick with GitHub releases + manual .deb downloads

## Next Steps

1. **Homebrew**: Implement tap creation and CI integration
2. **APT**: Decide between simple .deb files vs full repository
3. **Chocolatey**: Plan Windows package manager integration
4. **Testing**: Verify package installation on different platforms

## Timeline

- **Week 1**: Homebrew tap setup and CI integration
- **Week 2**: APT .deb package creation  
- **Week 3**: Chocolatey package (if needed)
- **Week 4**: Documentation and testing