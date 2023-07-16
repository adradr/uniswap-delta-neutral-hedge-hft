.DEFAULT_GOAL := help
# Variables
DOCKER_COMPOSE_FILE = docker-compose.yml
COMPOSE_COMMAND = docker compose -f $(DOCKER_COMPOSE_FILE) --env-file $(ENV_FILE)
DOCKER_BUILDX = docker buildx build --platform linux/amd64,linux/arm64 --push
DOCKERFILE_PATH = .
DOCKER_REPO = acrtradingdeskdev.azurecr.io/trading-engine/uniswap-hft
PYTHON_INTERPRETER = python
TELEGRAM_HANDLER = uniswap_hft.telegram_interface.telegram_handler
GIT_COMMIT = $(shell git rev-parse --short HEAD)
# Default values
DETACHED ?= false
ENV_FILE ?= .env
TAG ?= $(GIT_COMMIT)

# Targets
.PHONY: build up test telegram restart down logs

build:
	$(DOCKER_BUILDX) -t $(DOCKER_REPO):$(GIT_COMMIT) -t $(DOCKER_REPO):latest -f Dockerfile $(DOCKERFILE_PATH)

up:
	@if [ "$(DETACHED)" = "true" ]; then \
		TAG=$(TAG) $(COMPOSE_COMMAND) up -d; \
	else \
		TAG=$(TAG) $(COMPOSE_COMMAND) up; \
	fi

test:
	$(PYTHON_INTERPRETER) -m pytest

telegram:
	$(PYTHON_INTERPRETER) -c "\
	import dotenv;\
	import os;\
	import subprocess;\
	dotenv.load_dotenv('$(ENV_FILE)');\
	print(os.environ);\
	subprocess.run(['$(PYTHON_INTERPRETER)', '-m', '$(TELEGRAM_HANDLER)'])"

restart:
	$(COMPOSE_COMMAND) restart

down:
	$(COMPOSE_COMMAND) down

logs:
	$(COMPOSE_COMMAND) logs -f

help:
	@echo "Available targets:"
	@echo "  build         Build the Docker image using docker-compose."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "                TAG=<tag> Specify the tag to use for the Docker image."
	@echo "  up            Run the Docker containers defined in the docker-compose.yml file."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "                TAG=<tag> Specify the tag to use for the Docker image."
	@echo "  test          Run the tests using pytest."
	@echo "  telegram      Run the Telegram solution separately with the specified command."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "  restart       Restart the Docker containers."
	@echo "  down          Stop and remove the Docker containers."
	@echo "  logs          Show the logs of the Docker containers with the follow option."
	@echo "  help          Display this help message."
