import argparse
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "http://<your-api-url>"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to get JWT token
def get_jwt_token(username, password):
    resp = requests.post(
        f"{API_URL}/login", json={"username": username, "password": password}
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    else:
        logger.error("Failed to get JWT token")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = requests.post(
        f"{API_URL}/start",
        headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
    )
    await update.message.reply_text(resp.json()["message"])  # type: ignore
    logger.info("Engine started")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = requests.post(
        f"{API_URL}/stop",
        headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
    )
    await update.message.reply_text(resp.json()["message"])  # type: ignore
    logger.info("Engine stopped")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = requests.get(
        f"{API_URL}/stats",
        headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
    )
    await update.message.reply_text(resp.json()["message"])  # type: ignore
    logger.info("Engine stats retrieved")


async def update_engine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = requests.post(
        f"{API_URL}/update",
        headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
    )
    await update.message.reply_text(resp.json()["message"])  # type: ignore
    logger.info("Engine updated")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="The username for the API")
    parser.add_argument("password", help="The password for the API")
    parser.add_argument("token", help="The Telegram bot token")
    args = parser.parse_args()

    # Get JWT token
    access_token = get_jwt_token(args.username, args.password)
    if not access_token:
        logger.error("Failed to start bot due to authentication failure")
        exit(1)

    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("update", update_engine))

    app.run_polling()
