import argparse
import logging
import requests
import json
import os
import time
from dotenv import load_dotenv
from pathlib import Path
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
        await update.message.reply_text("Engine Started - DEBUG MODE")
    else:
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not API_URL:
                    raise ValueError("No API URL provided")
                try:
                    token = context.user_data["access_token"]
                except KeyError:
                    raise ValueError("No access token provided")
                resp = requests.get(
                    f"{API_URL}/start",
                    headers={"Authorization": f'Bearer {token}'},  # type: ignore
                )
                try:
                    message = resp.json()["message"]
                except KeyError:
                    raise ValueError("No message key in the response")
                except ValueError:
                    raise ValueError("Response is not JSON")
                await update.message.reply_text(message)  # type: ignore
                logger.info("Engine started")
                break  # If the request is successful, break out of the loop
            except (requests.exceptions.RequestException, ValueError) as e:
                # If a request exception or ValueError occurs, print it and retry after a delay
                logger.error(f"Request failed with exception {e}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
        else:
            # If we've exhausted the maximum number of attempts, send a failure message
            await update.message.reply_text("Failed to start engine after several attempts.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        await update.message.reply_text("Engine Stopped - DEBUG MODE")
    else:
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not API_URL:
                    raise ValueError("No API URL provided")
                try:
                    token = context.user_data["access_token"]
                except KeyError:
                    raise ValueError("No access token provided")
                resp = requests.get(
                    f"{API_URL}/stop",
                    headers={"Authorization": f'Bearer {token}'},  # type: ignore
                )
                try:
                    message = resp.json()["message"]
                except KeyError:
                    raise ValueError("No message key in the response")
                except ValueError:
                    raise ValueError("Response is not JSON")
                await update.message.reply_text(message)  # type: ignore
                logger.info("Engine stopped")
                break  # If the request is successful, break out of the loop
            except (requests.exceptions.RequestException, ValueError) as e:
                # If a request exception or ValueError occurs, print it and retry after a delay
                logger.error(f"Request failed with exception {e}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
        else:
            # If we've exhausted the maximum number of attempts, send a failure message
            await update.message.reply_text("Failed to stop engine after several attempts.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        await update.message.reply_text("Engine stats requested - DEBUG MODE")
        #TODO: Add mock engine stats, maybe import webmanager
    else:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if not API_URL:
                    raise ValueError("No API URL provided")
                try:
                    token = context.user_data["access_token"]
                except KeyError:
                    raise ValueError("No access token provided")
                resp = requests.get(
                    f"{API_URL}/stats",
                    headers={"Authorization": f'Bearer {token}'},  # type: ignore
                )
                try:
                    message = resp.json()["message"]
                except KeyError:
                    raise ValueError("No message key in the response")
                except ValueError:
                    raise ValueError("Response is not JSON")
                await update.message.reply_text(message)  # type: ignore
                logger.info("Engine stats retrieved")
                break  # If the request is successful, break out of the loop
            except (requests.exceptions.RequestException, ValueError) as e:
                # If a request exception or ValueError occurs, print it and retry after a delay
                logger.error(f"Request failed with exception {e}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
        else:
            # If we've exhausted the maximum number of attempts, send a failure message
            await update.message.reply_text("Failed to retrieve engine stats after several attempts.")


async def update_engine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if DEBUG_MODE == True:
        await update.message.reply_text("Engine Updated! - DEBUG MODE")
    else:
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not API_URL:
                    raise ValueError("No API URL provided")
                try:
                    token = context.user_data["access_token"]
                except KeyError:
                    raise ValueError("No access token provided")
                resp = requests.get(
                    f"{API_URL}/update",
                    headers={"Authorization": f'Bearer {token}'},  # type: ignore
                )
                try:
                    message = resp.json()["message"]
                except KeyError:
                    raise ValueError("No message key in the response")
                except ValueError:
                    raise ValueError("Response is not JSON")
                await update.message.reply_text(message)  # type: ignore
                logger.info("Engine updated")
                break  # If the request is successful, break out of the loop
            except (requests.exceptions.RequestException, ValueError) as e:

                # If a request exception or ValueError occurs, print it and retry after a delay
                logger.info(f"Request failed with exception {e}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
        else:
            # If we've exhausted the maximum number of attempts, send a failure message
            await update.message.reply_text("Failed to update engine after several attempts.")
            logger.error("Failed to update engine due to errors")


async def update_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the parameters from the command text
    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("No parameters provided!")
        return

    command, json_str = parts

    # Convert the JSON string into a dict
    try:
        params_dict = json.loads(json_str)
    except json.JSONDecodeError:
        await update.message.reply_text("Invalid JSON provided!")
        return

    if not params_dict:
        await update.message.reply_text("No parameters provided!")
        return

    if DEBUG_MODE == True:
        await update.message.reply_text(f"Parameters Received: {params_dict} \n - DEBUG MODE")
    else:
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not API_URL:
                    raise ValueError("No API URL provided")
                try:
                    token = context.user_data["access_token"]
                except KeyError:
                    raise ValueError("No access token provided")
                resp = requests.post(
                    f"{API_URL}/update_params",
                    headers={"Authorization": f'Bearer {token}'},  # type: ignore
                    json=params_dict
                )
                try:
                    message = resp.json()["message"]
                except KeyError:
                    raise ValueError("No message key in the response")
                except ValueError:
                    raise ValueError("Response is not JSON")
                await update.message.reply_text(f"Parameters Updated: {params_dict}")
                logger.info("Parameters updated")
                break  # If the request is successful, break out of the loop
            except (requests.exceptions.RequestException, ValueError) as e:
                # If a request exception or ValueError occurs, print it and retry after a delay
                logger.error(f"Request failed with exception {e}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
        else:
            # If we've exhausted the maximum number of attempts, send a failure message
            await update.message.reply_text("Failed to update parameters after several attempts.")


if __name__ == "__main__":

    # Set the path to your .env file
    dotenv_path = '/path/to/your/.env'

    # Check if a .env file exists in the current directory
    if Path('.env').exists():
        load_dotenv()
    elif Path(dotenv_path).exists():
        load_dotenv(dotenv_path)
    else:
        logger.info("No .env file found.")

    # Create the argument parser
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument("--username", help="The username for the API")
    parser.add_argument("--password", help="The password for the API")
    parser.add_argument("--token", help="The Telegram bot token")
    parser.add_argument("--api_url", help="The API URL")

    # Parse the arguments
    args = parser.parse_args()

    # If no arguments were provided, use the values from the .env file or exit if they are not set
    args.username = args.username or os.getenv('USERNAME')
    args.password = args.password or os.getenv('PASSWORD')
    args.token = args.token or os.getenv('TELEGRAM_API_KEY')
    args.api_url = args.api_url or os.getenv('API_URL')
    API_URL = args.api_url

    if not all([args.username, args.password, args.token, args.api_url]):
        logger.error("Not all necessary arguments were provided. Exiting...")
        exit(1)
        
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