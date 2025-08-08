.PHONY: test test-linux test-macos clean build run shell shell-macos

# Default target - run all tests
test: test-linux test-macos

# Test Linux installation
test-linux: build-linux run-linux

# Test macOS installation (simulated)
test-macos: build-macos run-macos

# Build Docker images
build: build-linux build-macos

build-linux:
	@echo "Building Docker image for Linux installer test..."
	docker-compose build test-linux

build-macos:
	@echo "Building Docker image for macOS installer test..."
	docker-compose build test-macos

# Run tests
run: run-linux run-macos

run-linux:
	@echo "Running Linux installer test..."
	docker-compose run --rm test-linux

run-macos:
	@echo "Running macOS installer test (simulated)..."
	docker-compose run --rm test-macos

# Open shells for debugging
shell:
	@echo "Opening shell in Linux test container..."
	docker-compose run --rm --entrypoint /bin/bash test-linux

shell-macos:
	@echo "Opening shell in macOS test container..."
	docker-compose run --rm --entrypoint /bin/bash test-macos

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down --volumes --remove-orphans
	docker system prune -f

# View logs
logs:
	docker-compose logs -f

# Rebuild and test everything
rebuild: clean build run