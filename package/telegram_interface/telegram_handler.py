import argparse
import logging
import requests
import json
import os
import time
import functools
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retry(attempts=5, delay=1):
    def retry_decorator(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except (
                    requests.exceptions.RequestException,
                    KeyError,
                    ValueError,
                ) as e:
                    logger.error(f"Request failed with exception {e}. Retrying...")
                    time.sleep(delay)
            logger.error(f"Failed to execute after {attempts} attempts.")

        return wrapped

    return retry_decorator


class TelegramAPIHandler:
    def __init__(self, api_url, debug_mode):
        self.api_url = api_url
        self.debug_mode = debug_mode

    @retry()
    def get_jwt_token(self, username, password):
        if username or password == "0":
            self.debug_mode = True
            return
        resp = requests.post(
            f"{self.api_url}/login", json={"username": username, "password": password}
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
        else:
            logger.error("Failed to get JWT token")
            logger.info("Entering Debug Mode")
            self.debug_mode = True
            return None

    @retry()
    async def _execute_api_command(self, command, context, method="GET", json=None):
        if self.debug_mode:
            await context.bot.send_message(
                context.from_user.id, f"Executing {command} - DEBUG MODE"
            )
            return

        headers = {"Authorization": f'Bearer {context.user_data["access_token"]}'}
        resp = getattr(requests, method.lower())(
            f"{self.api_url}/{command}",
            headers=headers,
            json=json,
        )
        message = resp.json()["message"]
        await context.bot.send_message(context.from_user.id, message)
        logger.info(f"{command} executed")

    async def start(self, update, context):
        await self._execute_api_command("start", context)

    async def stop(self, update, context):
        await self._execute_api_command("stop", context)

    async def stats(self, update, context):
        await self._execute_api_command("stats", context)

    async def update_engine(self, update, context):
        await self._execute_api_command("update", context)

    async def update_params(self, update, context):
        parts = update.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await context.bot.send_message(
                context.from_user.id, "No parameters provided!"
            )
            return

        command, json_str = parts

        try:
            params_dict = json.loads(json_str)
        except json.JSONDecodeError:
            await context.bot.send_message(
                context.from_user.id, "Invalid JSON provided!"
            )
            return

        if not params_dict:
            await context.bot.send_message(
                context.from_user.id, "No parameters provided!"
            )
            return

        await self._execute_api_command(
            "update_params", context, method="POST", json=params_dict
        )


if __name__ == "__main__":
    dotenv_path = "/path/to/your/.env"
    load_dotenv(dotenv_path) if Path(dotenv_path).exists() else logger.info(
        "No .env file found."
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username", default=os.getenv("USERNAME"), help="The username for the API"
    )
    parser.add_argument(
        "--password", default=os.getenv("PASSWORD"), help="The password for the API"
    )
    parser.add_argument(
        "--token", default=os.getenv("TELEGRAM_API_KEY"), help="The Telegram bot token"
    )
    parser.add_argument("--api_url", default=os.getenv("API_URL"), help="The API URL")
    args = parser.parse_args()

    if not all([args.username, args.password, args.token, args.api_url]):
        logger.error("Not all necessary arguments were provided. Exiting...")
        exit(1)

    engine_app = TelegramAPIHandler(args.api_url, False)
    access_token = engine_app.get_jwt_token(args.username, args.password)
    if not access_token:
        logger.error("Failed to start bot due to authentication failure")
        engine_app.debug_mode = True
        logger.info("Bot Starting in Debug Mode")

    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", engine_app.start))
    app.add_handler(CommandHandler("stop", engine_app.stop))
    app.add_handler(CommandHandler("stats", engine_app.stats))
    app.add_handler(CommandHandler("update_engine", engine_app.update_engine))
    app.add_handler(CommandHandler("update_params", engine_app.update_params))

    app.run_polling()
