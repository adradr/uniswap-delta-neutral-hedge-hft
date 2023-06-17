import os
import time
import requests
import argparse
import logging
import dotenv
import apscheduler.schedulers.background
import apscheduler.jobstores.sqlalchemy
import apscheduler.executors.pool
from typing import Optional

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Argument Parser
parser = argparse.ArgumentParser(description="Trading Engine Update Scheduler")
parser.add_argument(
    "--username",
    type=str,
    default=os.getenv("SCHEDULER_ENGINEAPI_USERNAME"),
    help="Username for API authentication",
)
parser.add_argument(
    "--password",
    type=str,
    default=os.getenv("SCHEDULER_ENGINEAPI_PASSWORD"),
    help="Password for API authentication",
)
parser.add_argument(
    "--interval",
    type=int,
    default=os.getenv("SCHEDULER_INTERVAL"),
    help="Scheduler interval in seconds",
)
parser.add_argument(
    "--api-host",
    type=str,
    default=os.getenv("SCHEDULER_ENGINEAPI_HOST"),
    help="Login endpoint",
)
parser.add_argument(
    "--api-port",
    type=str,
    default=os.getenv("SCHEDULER_ENGINEAPI_PORT"),
    help="Login endpoint",
)

args = parser.parse_args()

HTTP_PREFIX = "http://"
LOGIN_ENDPOINT = f"{HTTP_PREFIX}{args.api_host}:{args.api_port}/login"
UPDATE_ENDPOINT = f"{HTTP_PREFIX}{args.api_host}:{args.api_port}/update-engine"
STATS_ENDPOINT = f"{HTTP_PREFIX}{args.api_host}:{args.api_port}/stats"


def get_auth_token(username: str, password: str) -> Optional[str]:
    """Log in and return the authentication token, or None if login failed."""
    response = requests.post(
        LOGIN_ENDPOINT, json={"username": username, "password": password}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        logging.error("Failed to authenticate: %s", response.text)
        return None


def update_engine(token: str) -> None:
    """Update the trading engine."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(UPDATE_ENDPOINT, headers=headers)
    if response.status_code == 200:
        logging.info("Successfully updated the trading engine")
    else:
        logging.error("Failed to update the trading engine: %s", response.text)


def get_stats(token: str) -> None:
    """Update the trading engine."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(STATS_ENDPOINT, headers=headers)
    if response.status_code == 200:
        logging.info("Successfully retrieved the trading engine stats")
        logging.info(response.json())
    else:
        logging.error("Failed to update the trading engine: %s", response.text)


def scheduler_job_update_engine():
    """Scheduler job function."""
    token = get_auth_token(args.username, args.password)
    if token:
        update_engine(token)


def scheduler_job_get_stats():
    """Scheduler job function."""
    token = get_auth_token(args.username, args.password)
    if token:
        get_stats(token)


def main():
    # Configure the scheduler
    jobstores = {
        "default": apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore(
            url="sqlite:///jobs.sqlite"
        ),
    }
    executors = {"default": apscheduler.executors.pool.ThreadPoolExecutor(20)}
    job_defaults = {"coalesce": False, "max_instances": 3}
    scheduler = apscheduler.schedulers.background.BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
    )
    scheduler.add_job(scheduler_job_update_engine, "interval", seconds=args.interval)
    scheduler.add_job(scheduler_job_get_stats, "interval", seconds=args.interval)
    scheduler.start()
    logging.info("Scheduler started with an interval of %d seconds", args.interval)

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()


if __name__ == "__main__":
    main()
