import argparse
import functools
import json
import logging
import os
import pprint
import time
from typing import Union
import aiohttp
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

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
    def __init__(
        self,
        api_host: str,
        api_port: int,
        api_username: str,
        api_password: str,
        debug_mode: bool,
    ) -> None:
        self.api_url = f"http://{api_host}:{api_port}"
        self.api_username = api_username
        self.api_password = api_password
        self.debug_mode = debug_mode

    @retry()
    async def get_jwt_token(self) -> Union[str, None]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/login",
                json={"username": self.api_username, "password": self.api_password},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["access_token"]
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

        access_token = await self.get_jwt_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            request_func = getattr(session, method.lower())
            async with request_func(
                f"{self.api_url}/{command}",
                headers=headers,
                json=json,
            ) as resp:
                data = await resp.json()
                data = pprint.pformat(data)
                # Format data for Telegram
                data = data.replace("'", "")
                data = data.replace("{", "")
                data = data.replace("}", "")
                # data = data.replace(",", "\n")
                data = data.replace(":", " - ")

        await context.bot.send_message(context._chat_id, data)
        logger.info(f"{command} executed")

    async def start(self, update: Update, context) -> None:
        await self._execute_api_command("start", update, context)

    async def stop(self, update: Update, context) -> None:
        await self._execute_api_command("stop", update, context)

    async def stats(self, update: Update, context) -> None:
        await self._execute_api_command("stats", update, context)

    async def update_engine(self, update: Update, context) -> None:
        await self._execute_api_command("update-engine", update, context)

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


def main():
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
        "--api_host", default=os.getenv("TELEGRAM_ENGINEAPI_HOST"), help="The API HOST"
    )

    parser.add_argument(
        "--api_port", default=os.getenv("TELEGRAM_ENGINEAPI_PORT"), help="The API PORT"
    )

    # Add debug flag
    parser.add_argument(
        "--debug-mode",
        action="store_true",
        help="Start the bot in debug mode (no API calls)",
    )

    args = parser.parse_args()

    if not all([args.username, args.password, args.api_host, args.api_port]):
        logger.error("Not all necessary arguments were provided. Exiting...")
        exit(1)

    engine_app = TelegramAPIHandler(
        args.api_host, args.api_port, args.username, args.password, args.debug_mode
    )
    if args.debug_mode:
        engine_app.debug_mode = True
        logger.info("Bot Starting in Debug Mode")
    else:
        logger.info("Bot Starting in Production Mode")

    print(args.token)

    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", engine_app.start))
    app.add_handler(CommandHandler("stop", engine_app.stop))
    app.add_handler(CommandHandler("stats", engine_app.stats))
    app.add_handler(CommandHandler("update_engine", engine_app.update_engine))
    app.add_handler(CommandHandler("update_params", engine_app.update_params))

    app.run_polling()


if __name__ == "__main__":
    main()
