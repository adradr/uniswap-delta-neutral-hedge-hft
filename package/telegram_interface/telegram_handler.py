import argparse
import logging
import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "http://<your-api-url>"
DEBUG_MODE = False

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to get JWT token
def get_jwt_token(username, password):
    if username or password == "0":
        DEBUG_MODE = True
        return
    resp = requests.post(
        f"{API_URL}/login", json={"username": username, "password": password}
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    else:
        logger.error("Failed to get JWT token")
        logger.info("Entering Debug Mode")
        DEBUG_MODE = True
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        update.message.reply_text("Engine Started - DEBUG MODE")
    else:
        resp = requests.post(
            f"{API_URL}/start",
            headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
        )
        await update.message.reply_text(resp.json()["message"])  # type: ignore
        logger.info("Engine started")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        update.message.reply_text("Engine Stopped - DEBUG MODE")
    else:
        resp = requests.post(
            f"{API_URL}/stop",
            headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
        )
        await update.message.reply_text(resp.json()["message"])  # type: ignore
        logger.info("Engine stopped")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        update.message.reply_text("Engine stats requested - DEBUG MODE")
        #TODO: Add mock engine stats, maybe import webmanager
    else:
        resp = requests.get(
            f"{API_URL}/stats",
            headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
        )
        await update.message.reply_text(resp.json()["message"])  # type: ignore
        #TODO: Send stats, if not packed correctly
        logger.info("Engine stats retrieved")


async def update_engine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        update.message.reply_text("Engine Updated! - DEBUG MODE")
    else:
        resp = requests.post(
            f"{API_URL}/update",
            headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
        )
        await update.message.reply_text(resp.json()["message"])  # type: ignore
        logger.info("Engine updated")

async def update_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #Get the parameters from the command text
    command, json_str = update.message.text.split(maxsplit=1)
    
    # Convert the JSON string into a dict
    params_dict = json.loads(json_str)
    
    if not params_dict:
        await update.message.reply_text("No parameters provided!")
        return

    if DEBUG_MODE == True:
        update.message.reply_text(f"Parameters Received: {params_dict} \n - DEBUG MODE")
    else:
        # Use the parameters in the API request
        resp = requests.post(
            f"{API_URL}/update_params",
            headers={"Authorization": f'Bearer {context.user_data["access_token"]}'},  # type: ignore
            json=params_dict  #TODO CHECK IF ENGINE CAN USE JSON DATA
        )
        await update.message.reply_text(f"Parameters Updated: {params_dict}")
        logger.info("Parameters updated")



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
        DEBUG_MODE = True
        logger.info("Bot Starting in Debug Mode")

    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("update_engine", update_engine))
    app.add_handler(CommandHandler("update_params", update_params))

    app.run_polling()
