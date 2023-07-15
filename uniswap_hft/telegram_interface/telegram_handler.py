import os
import json
import time
import pprint
import typing
import dotenv
import aiohttp
import logging
import requests
import argparse
import functools
import telegram
import telegram.ext

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_message(bot_token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        # Handle error
        pass


def admin_check(func):
    @functools.wraps(func)
    async def wrapped(
        self,
        update: telegram.Update,
        context: telegram.ext.CallbackContext,
        *args,
        **kwargs,
    ):
        chat_id = context._chat_id
        admins = await context.bot.get_chat_administrators(chat_id)

        admin_usernames = [admin.user.username for admin in admins]
        logger.info(f"Admin usernames: {admin_usernames}")
        logger.info(f"Required usernames: {self.required_usernames}")

        if not any(username in admin_usernames for username in self.required_usernames):
            # None of the required usernames are in the admin list, bot leaves the chat
            logger.info("No admin found, leaving chat...")
            await update.message.reply_text("Permission denied, leaving chat...")  # type: ignore
            await context.bot.leave_chat(chat_id)
        else:
            return await func(self, update, context, *args, **kwargs)

    return wrapped


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
        required_usernames: list,
        debug_mode: bool,
    ) -> None:
        self.api_url = f"http://{api_host}:{api_port}"
        self.api_username = api_username
        self.api_password = api_password
        self.required_usernames = required_usernames
        self.debug_mode = debug_mode

    @retry()
    async def get_jwt_token(self) -> typing.Union[str, None]:
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
        update: telegram.Update,
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

    async def get_chat_id(self, update: telegram.Update, context) -> None:
        await update.message.reply_text(  # type: ignore
            # f"Chat ID: {update.message.chat_id}"
            f"Chat ID: {context._chat_id}"
        )

    @admin_check
    async def start(self, update: telegram.Update, context) -> None:
        await self._execute_api_command("start", update, context)

    @admin_check
    async def stop(self, update: telegram.Update, context) -> None:
        await self._execute_api_command("stop", update, context)

    @admin_check
    async def stats(self, update: telegram.Update, context) -> None:
        await self._execute_api_command("stats", update, context)

    @admin_check
    async def update_engine(self, update: telegram.Update, context) -> None:
        await self._execute_api_command("update-engine", update, context)

    @admin_check
    async def update_params(self, update: telegram.Update, context) -> None:
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
    dotenv.load_dotenv()
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

    parser.add_argument(
        "--required_usernames",
        default=os.getenv("TELEGRAM_REQUIRED_USERNAMES"),
        help="A comma separated list of usernames that are allowed to use the bot, e.g.: username1,username2",
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

    # Parse required usernames into a list
    args.required_usernames = args.required_usernames.split(",")

    engine_app = TelegramAPIHandler(
        api_host=args.api_host,
        api_port=args.api_port,
        api_username=args.username,
        api_password=args.password,
        required_usernames=args.required_usernames,
        debug_mode=args.debug_mode,
    )
    if args.debug_mode:
        engine_app.debug_mode = True
        logger.info("Bot Starting in Debug Mode")
    else:
        logger.info("Bot Starting in Production Mode")

    print(args.token)

    app = telegram.ext.ApplicationBuilder().token(args.token).build()
    app.add_handler(telegram.ext.CommandHandler("start", engine_app.start))
    app.add_handler(telegram.ext.CommandHandler("stop", engine_app.stop))
    app.add_handler(telegram.ext.CommandHandler("stats", engine_app.stats))
    app.add_handler(
        telegram.ext.CommandHandler("update_engine", engine_app.update_engine)
    )
    app.add_handler(
        telegram.ext.CommandHandler("update_params", engine_app.update_params)
    )
    app.add_handler(telegram.ext.CommandHandler("get_chat_id", engine_app.get_chat_id))

    app.run_polling()


if __name__ == "__main__":
    main()
