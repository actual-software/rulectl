.PHONY: help build-binary build-deb clean test install deb-deps

# Get version from version.py
VERSION := $(shell python3 -c "exec(open('version.py').read()); print(VERSION)")

help: ## Show this help message
	@echo "Rulectl Build System"
	@echo "==================="
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build-binary: ## Build the standalone executable
	@echo "Building rulectl binary..."
	BAML_LOG=OFF RULECTL_BUILD=1 python3 build.py

build-deb: deb-deps ## Build Debian package
	@echo "Building Debian package for rulectl $(VERSION)..."
	@if [ ! -d "debian" ]; then \
		echo "Error: debian/ directory not found. Please ensure Debian packaging files exist."; \
		exit 1; \
	fi
	dpkg-buildpackage -us -uc -b
	@echo "✅ Debian package built successfully!"
	@echo "Package files:"
	@ls -la ../*.deb 2>/dev/null || echo "No .deb files found in parent directory"

build-deb-source: deb-deps ## Build Debian source package
	@echo "Building Debian source package for rulectl $(VERSION)..."
	dpkg-buildpackage -us -uc -S
	@echo "✅ Debian source package built successfully!"

deb-deps: ## Install Debian packaging dependencies
	@echo "Installing Debian packaging dependencies..."
	@if ! command -v dpkg-buildpackage >/dev/null 2>&1; then \
		echo "Installing dpkg-dev..."; \
		sudo apt-get update && sudo apt-get install -y dpkg-dev; \
	fi
	@if ! command -v debuild >/dev/null 2>&1; then \
		echo "Installing devscripts..."; \
		sudo apt-get install -y devscripts; \
	fi
	@if ! dpkg -l | grep -q debhelper; then \
		echo "Installing debhelper..."; \
		sudo apt-get install -y debhelper; \
	fi
	@if ! dpkg -l | grep -q dh-python; then \
		echo "Installing dh-python..."; \
		sudo apt-get install -y dh-python; \
	fi
	@echo "✅ All Debian packaging dependencies installed"

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf venv/
	rm -rf build_venv/
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */**/__pycache__/
	rm -f ../*.deb
	rm -f ../*.dsc
	rm -f ../*.changes
	rm -f ../*.tar.xz
	rm -f ../*.buildinfo
	@echo "✅ Clean complete"

test: build-binary ## Test the built binary
	@echo "Testing rulectl binary..."
	@if [ ! -f "dist/rulectl" ]; then \
		echo "Error: Binary not found. Run 'make build-binary' first."; \
		exit 1; \
	fi
	chmod +x dist/rulectl
	./dist/rulectl --help
	./dist/rulectl config --help
	@echo "✅ Binary tests passed!"

install: build-binary ## Install rulectl to ~/.local/bin
	@echo "Installing rulectl to ~/.local/bin..."
	mkdir -p ~/.local/bin
	cp dist/rulectl ~/.local/bin/
	chmod +x ~/.local/bin/rulectl
	@echo "✅ rulectl installed to ~/.local/bin/rulectl"
	@echo ""
	@echo "Make sure ~/.local/bin is in your PATH:"
	@echo "  echo 'export PATH=\"\$$HOME/.local/bin:\$$PATH\"' >> ~/.bashrc"
	@echo "  source ~/.bashrc"

install-deb: ## Install the built .deb package
	@echo "Installing Debian package..."
	@DEB_FILE=$$(ls ../*.deb 2>/dev/null | head -1); \
	if [ -z "$$DEB_FILE" ]; then \
		echo "Error: No .deb package found. Run 'make build-deb' first."; \
		exit 1; \
	fi; \
	echo "Installing $$DEB_FILE..."; \
	sudo dpkg -i "$$DEB_FILE" || (echo "Attempting to fix dependencies..." && sudo apt-get install -f)
	@echo "✅ Debian package installed successfully!"

uninstall-deb: ## Uninstall the Debian package
	@echo "Uninstalling rulectl Debian package..."
	sudo dpkg -r rulectl
	@echo "✅ rulectl package uninstalled"

version: ## Show current version
	@echo "Current version: $(VERSION)"

.DEFAULT_GOAL := help