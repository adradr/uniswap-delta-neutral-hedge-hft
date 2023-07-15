.DEFAULT_GOAL := help
# Variables
DOCKER_COMPOSE_FILE = docker-compose.yml
COMPOSE_COMMAND = docker-compose -f $(DOCKER_COMPOSE_FILE)
DOCKER_BUILDX = docker buildx build --platform linux/amd64,linux/arm64 --push
DOCKERFILE_PATH = .
DOCKER_REPO = acrtradingdeskdev.azurecr.io/trading-engine/uniswap-hft
PYTHON_INTERPRETER = python
TELEGRAM_HANDLER = uniswap_hft.telegram_interface.telegram_handler
GIT_COMMIT = $(shell git rev-parse --short HEAD)
# Default values
ENV_FILE ?= .env
TAG ?= $(GIT_COMMIT)

# Targets
.PHONY: build up test telegram help

build:
	$(DOCKER_BUILDX) -t $(DOCKER_REPO):$(GIT_COMMIT) -t $(DOCKER_REPO):latest -f Dockerfile $(DOCKERFILE_PATH)

up:
	TAG=$(TAG) $(COMPOSE_COMMAND) --env-file $(ENV_FILE) up

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

help:
	@echo "Available targets:"
	@echo "  build         Build the Docker image using docker-compose."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "  up            Run the Docker containers defined in the docker-compose.yml file."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "  test          Run the tests using pytest."
	@echo "  telegram      Run the Telegram solution separately with the specified command."
	@echo "                ENV_FILE=<env-file> Specify the environment file to use."
	@echo "  help          Display this help message."
