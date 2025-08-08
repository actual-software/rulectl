.PHONY: test clean build run shell

# Default target
test: clean build run

# Build the Docker image
build:
	@echo "Building Docker image for Linux installer test..."
	docker-compose build

# Run the test
run:
	@echo "Running installer test in Docker container..."
	docker-compose run --rm test-linux

# Open a shell in the container for debugging
shell:
	@echo "Opening shell in test container..."
	docker-compose run --rm --entrypoint /bin/bash test-linux

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down --volumes --remove-orphans
	docker system prune -f

# View logs
logs:
	docker-compose logs -f

# Rebuild and test
rebuild: clean build run