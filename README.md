# uniswap-delta-neutral-hedge-hft

Uniswap High Frequency Trading w/ Delta Neutral Positions

## Overview

This is a high frequency trading bot that uses Uniswap and a CEX to trade a delta neutral position. The bot will enter a Uniswap position in a crypto & stablecoin pool for a tight range while opening a short position in equivalent amount of the token side. The bot will also rebalance the position if the price of the token moves out of the range.

To rebalance the position, the bot close the Uniswap position and the CEX position and then reopens them at the new price, while collecting fees in the process.

## Requirements

- Python 3.10
- API keys for a CEX (e.g. Binance, FTX, etc.) compatible with ccxt
- EVM compatible private key (e.g. Ethereum, Polygon, etc.)

# uniswap-hft package

## uniswap_hft.uniswap_math

This module contains the math functions used to calculate the Uniswap token amounts, tick prices

## uniswap_hft.trading_engine

This module contains the TradingEngine class which is the main class of the bot. It contains the logic to open and close positions, rebalance positions, and calculate the position size.
The `trading_engine` is only acting as a wrapper around the `web_manager` to handle operations and prepare a simplified integration for the API.


## uniswap_hft.web_manager

The Web Manager module houses the `Web3Manager` class that is utilized to manage the web3 connection and the Uniswap contract. It is responsible for initializing the connection, opening positions, and maintaining the positions by periodically updating them.

### Class: `Web3Manager`

The `Web3Manager` class initializes the web3 connection and the Uniswap contract. It also has methods to open and update positions in the Uniswap contract.

```python
class Web3Manager:
    def __init__(
        self,
        pool_address: ChecksumAddress,
        pool_fee: int,
        wallet_address: ChecksumAddress,
        wallet_private_key: str,
        range_percentage: int,
        token0_capital: int,
        provider: str,
        debug: bool = False,
    ):
        ...
```

#### Initializer

The class is initialized with the details of the provider, Uniswap contract, and wallet.

**Args:**
* `pool_address` (ChecksumAddress): The address of the pool where liquidity should be provided.
* `pool_fee` (int): The fee of the pool for swapping tokens (you can probably use a hardcoded value).
* `wallet_address` (ChecksumAddress): The address of the wallet where the funds are located.
* `wallet_private_key` (str): The private key of the wallet.
* `range_percentage` (int): How wide the range should be in percentage (e.g., 1 for 1%).
* `token0_capital` (int): How much of the funds should be used to provide liquidity for token0 (e.g., 1000 for 1000 USDC). Note: it will be roughly doubled for the total position size.
* `provider` (str): The provider of the blockchain, e.g., Infura.
* `debug` (bool, optional): Whether to enable debug logging. Defaults to False.

#### Methods

The `Web3Manager` class implements several methods to interact with the Uniswap contract.

**`store_position_history(self)`**

Stores the position history in a JSON file.

**`load_position_history(self)`**

Loads the position history from a JSON file.

**`update_balance(self)`**

Updates the balances of the wallet for token0 and token1.

**`get_current_time_str(self) -> str`**

Returns the current time as a string.

**`parseTxReceiptForTokenId(self, rc: TxReceipt) -> int`**

Parses a transaction receipt for the tokenId.

**`swap_amounts(self) -> Union[TxReceipt, None]`**

Swaps the tokens in the wallet for the token with the least amount.

**`update_position(self)`**

Updates the position of the wallet in the pool.

**`open_position(self) -> TxReceipt`**

Opens a position in Uniswap V3.

**`close_position(self) -> Tuple[TxReceipt, TxReceipt, TxReceipt]`**

Closes a position in the Uniswap V3 pool.

## uniswap_hft.api

The Trading Engine API provides interfaces for managing and interacting with a trading engine. The following HTTP endpoints are available:

### POST /login

Endpoint for authenticating users. Returns an access token and a refresh token upon successful authentication.

#### Request

- Method: `POST`
- Body: JSON object with the following properties:
  - `username` (string): The username.
  - `password` (string): The password.

#### Response

- Status: `200` on success, `401` if authentication fails or if username and password are not provided.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `access_token` (string): The access token for authenticated requests (only included on success).
  - `refresh_token` (string): The refresh token for authenticated requests (only included on success).
  - `message` (string): A message describing the result of the request.

### POST /refresh

This endpoint is used for refreshing the access token using a valid refresh token.

#### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {refresh_token}"`.

#### Response

A successful response will be:

- Status: `200` on success
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `access_token` (string): The new access token for authenticated requests.

If an error occurs, the response will be:

- Status: `401` for invalid or expired refresh token.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.

### GET /start

Endpoint for starting the trading engine. Returns information about the state of the engine. Requires a valid access token.

#### Request

- Method: `GET`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

#### Response

- Status: `200` on success, `404` if the engine is already running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.
  - `stats` (object): Information about the initial state of the engine after starting (only included on success).

### GET /stop

Endpoint for stopping the trading engine. Returns information about the state of the engine. Requires a valid access token.

#### Request

- Method: `GET`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

#### Response

- Status: `200` on success, `404` if the engine is not running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.
  - `stats` (object): Information about the final state of the engine after stopping (only included on success).

### GET /stats

Endpoint for fetching statistics about the current state of the trading engine. Requires a valid access token.

#### Request

- Method: `GET`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

#### Response

- Status:

 `200` on success, `404` if the engine is not running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.
  - `stats` (object): The most recent position history of the trading engine.

### GET /update-engine

Endpoint for manually triggering an update of the trading engine. Returns information about the state of the engine. Requires a valid access token.

#### Request

- Method: `GET`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

#### Response

- Status: `200` on success, `404` if the engine is not running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.
  - `stats` (object): Information about the state of the engine after update (only included on success).

### POST /update-params

Endpoint to update the parameters of the running engine, mainly the `Web3Manager` class instance attributes.

#### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.
- Body: JSON dictionary containing the parameters to be changed. For example: `{"provider": "https://example.com"}`

#### Response

- Status: `200` on success, `401` if no parameters provided
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.

### GET /healthcheck

Endpoint for checking the health status of the API.

#### Request

- Method: `GET`

#### Response

- Status: `200` on success.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `engine` (string): Current state of the engine.


  ## uniswap_hft.telegram_interface

The Telegram Interface module contains the `TelegramAPIHandler` class which is used to interact with the trading bot via Telegram commands. It sends and receives messages to interact with the bot.

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
