[Back to Main README](../README.md)

# Makefile Documentation

The Makefile in the project provides convenient shortcuts for building, running, testing the project, and other Docker-related operations, as well as running the Telegram solution separately. Below are the available targets and their usage:

---

## Targets

### build

Builds the Docker image using `docker buildx`. You can specify the environment file using the `ENV_FILE` variable and the tag for the Docker image using the `TAG` variable.

```bash
make build [ENV_FILE=<env-file>] [TAG=<tag>]
```

### up

Runs the Docker containers defined in the `docker-compose.yml` file. You can run them in detached mode by setting the `DETACHED` variable to `true`.

```bash
make up [ENV_FILE=<env-file>] [TAG=<tag>] [DETACHED=<true|false>]
```

### pull

Pulls the Docker images defined in the `docker-compose.yml` file.

```bash
make pull [ENV_FILE=<env-file>] [TAG=<tag>]
```

### restart

Restarts the Docker containers.

```bash
make restart
```

### down

Stops and removes the Docker containers.

```bash
make down
```

### logs

Displays the logs of the Docker containers with the follow option.

```bash
make logs
```

### test

Runs the tests using `pytest`.

```bash
make test
```

### telegram

Runs the Telegram solution separately with the specified command. You can specify the environment file to use by setting the `ENV_FILE` variable.

```bash
make telegram [ENV_FILE=<env-file>]
```

### help

Displays the help message, showing the available targets and their usage.

```bash
make help
```

Note: By default, when running `make` without any target specified, it will print out the help message.

## Usage

To use the Makefile targets, open a terminal and navigate to the project directory. Then, run the desired target using the `make` command followed by the target name.

For example, to build the Docker image with a specific tag and environment file, run:

```bash
make build TAG=v1.2.0 ENV_FILE=./custom.env
```

To run the Docker containers in detached mode with a specific tag, use:

```bash
make up DETACHED=true TAG=v1.2.0
```

To see the available targets and their usage, simply run:

```bash
make help
```