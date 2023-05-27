import argparse
import logging
import requests
import json
import os
import time
import functools
from dotenv import load_dotenv
from typing import Any, NamedTuple, Union
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
    def __init__(self, api_url: str, debug_mode: bool) -> None:
        self.api_url = api_url
        self.debug_mode = debug_mode

    @retry()
    def get_jwt_token(self, username: str, password: str) -> Union[str, None]:
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
    async def _execute_api_command(
        self,
        command: str,
        update: Update,
        context,
        method: str = "GET",
        json: dict = {},
    ) -> None:
        if self.debug_mode:
            await update.message.reply_text(  #  type: ignore
                f"Executing {command} - DEBUG MODE"
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

    async def start(self, update: Update, context) -> None:
        await self._execute_api_command("start", update, context)

    async def stop(self, update: Update, context) -> None:
        await self._execute_api_command("stop", update, context)

    async def stats(self, update: Update, context) -> None:
        await self._execute_api_command("stats", update, context)

    async def update_engine(self, update: Update, context) -> None:
        await self._execute_api_command("update", update, context)

    async def update_params(self, update: Update, context) -> None:
        parts = update.message.text.split(maxsplit=1)  # type: ignore
        if len(parts) < 2:
            await update.message.reply_text("No parameters provided!")  # type: ignore
            return

        command, json_str = parts

        try:
            params_dict = json.loads(json_str)
        except json.JSONDecodeError:
            await update.message.reply_text("Invalid JSON provided!")  # type: ignore
            return

        if not params_dict:
            await update.message.reply_text("No parameters provided!")  # type: ignore
            return

        await self._execute_api_command(
            "update_params", update, context, method="POST", json=params_dict
        )


if __name__ == "__main__":
    # Load environment variables and parse arguments
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        default=os.getenv("TELEGRAM_ENGINEAPI_USERNAME"),
        help="The username for the API",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("TELEGRAM_ENGINEAPI_PASSWORD"),
        help="The password for the API",
    )
    parser.add_argument(
        "--token", default=os.getenv("TELEGRAM_API_KEY"), help="The Telegram bot token"
    )
    parser.add_argument(
        "--api_url", default=os.getenv("TELEGRAM_ENGINEAPI_URL"), help="The API URL"
    )

    # Add debug flag
    parser.add_argument(
        "--debug-mode",
        action="store_true",
        help="Start the bot in debug mode (no API calls)",
    )

    args = parser.parse_args()

    if not all([args.username, args.password, args.api_url]):
        logger.error("Not all necessary arguments were provided. Exiting...")
        exit(1)

    engine_app = TelegramAPIHandler(args.api_url, False)
    if args.debug_mode:
        engine_app.debug_mode = True
        logger.info("Bot Starting in Debug Mode")
    else:
        access_token = engine_app.get_jwt_token(args.username, args.password)

    print(args.token)

    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", engine_app.start))
    app.add_handler(CommandHandler("stop", engine_app.stop))
    app.add_handler(CommandHandler("stats", engine_app.stats))
    app.add_handler(CommandHandler("update_engine", engine_app.update_engine))
    app.add_handler(CommandHandler("update_params", engine_app.update_params))

    app.run_polling()
