[Back to Main README](../README.md)

## uniswap_hft.telegram_interface

The Telegram Interface module contains the `TelegramAPIHandler` class which is used to interact with the trading bot via Telegram commands. It sends and receives messages to interact with the bot.

---
---
### Class: `TelegramAPIHandler`

#### Initialization

The class is initialized with the following parameters:

- `api_url` (str): The URL of the trading bot's API.
- `debug_mode` (bool): A boolean value that determines whether the bot is in debug mode.

The `debug_mode` if set to True bypasses actual API calls and returns debug messages.

### Methods

#### `get_jwt_token(self, username: str, password: str) -> Union[str, None]`

This method is used to authenticate the user and get a JWT token. This method returns the JWT token if the authentication is successful, and None if it fails.

#### `_execute_api_command(self, command: str, update: Update, context, method: str = "GET", json: dict = {}) -> None`

This method is used to execute API commands. It requires the command to be executed, a Telegram update object, and the context. Optional parameters include the HTTP method (default is GET) and a JSON dictionary to be included in the request.

#### `start(self, update: Update, context) -> None`

This method starts the trading bot.

#### `stop(self, update: Update, context) -> None`

This method stops the trading bot.

#### `stats(self, update: Update, context) -> None`

This method returns the current statistics of the trading bot.

#### `update_engine(self, update: Update, context) -> None`

This method manually triggers an update of the trading bot.

#### `update_params(self, update: Update, context) -> None`

This method is used to update the parameters of the running engine.

### Command Handlers

Command handlers are added to listen for certain commands from the Telegram chat:

- `start`: Starts the trading bot.
- `stop`: Stops the trading bot.
- `stats`: Fetches the current statistics of the trading bot.
- `update_engine`: Manually triggers an update of the trading bot.
- `update_params`: Updates the parameters of the running engine.

Please note that all the commands when given in the chat need to be preceded by `/`. For example: `/start` to start the trading bot.
