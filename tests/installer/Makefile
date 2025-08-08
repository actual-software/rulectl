.PHONY: test test-linux clean build run shell

# Default target - run all tests
test: test-linux

# Test Linux installation
test-linux: build-linux run-linux

# Build Docker images
build: build-linux

build-linux:
	@echo "Building Docker image for Linux installer test..."
	docker-compose build test-linux

# Run tests
run: run-linux

run-linux:
	@echo "Running Linux installer test..."
	docker-compose run --rm test-linux

# Open shell for debugging
shell:
	@echo "Opening shell in Linux test container..."
	docker-compose run --rm --entrypoint /bin/bash test-linux

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