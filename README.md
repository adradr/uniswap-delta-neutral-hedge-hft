# uniswap-delta-neutral-hedge-hft

Uniswap High Frequency Trading w/ Delta Neutral Positions

## Overview

This is a high frequency trading bot that uses Uniswap and a CEX to trade a delta neutral position. The bot will enter a Uniswap position in a crypto & stablecoin pool for a tight range while opening a short position in equivalent amount of the token side. The bot will also rebalance the position if the price of the token moves out of the range.

To rebalance the position, the bot close the Uniswap position and the CEX position and then reopens them at the new price, while collecting fees in the process.

## Requirements

- Python 3.9
- API keys for a CEX (e.g. Binance, FTX, etc.) compatible with ccxt
- EVM compatible private key (e.g. Ethereum, Polygon, etc.)

## Package

### uniswap-hft

#### uniswap_hft.uniswap_math

This module contains the math functions used to calculate the Uniswap token amounts, tick prices

#### uniswap_hft.trading_engine

This module contains the TradingEngine class which is the main class of the bot. It contains the logic to open and close positions, rebalance positions, and calculate the position size.

#### uniswap_hft.slack_interface

This module contains the SlackInterface class which is used to listen for messages from Slack and send messages to Slack to interact with the bot.

# Trading Engine API Documentation

The Trading Engine API provides interfaces for managing and interacting with a trading engine. The following HTTP endpoints are available:

## POST /login

Endpoint for authenticating users. Returns an access token upon successful authentication.

### Request

- Method: `POST`
- Body: JSON object with the following properties:
  - `username` (string): The username.
  - `password` (string): The password.

### Response

- Status: `200` on success, `401` if authentication fails.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `access_token` (string): The access token for authenticated requests (only included on success).
  - `message` (string): A message describing the result of the request.

## POST /refresh

This endpoint is used for refreshing the access token using a valid refresh token.

### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {refresh_token}"`.

### Response

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

## POST /start

Endpoint for starting the trading engine. Requires a valid access token.

### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

### Response

- Status: `200` on success.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.

## POST /stop

Endpoint for stopping the trading engine. Requires a valid access token.

### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

### Response

- Status: `200` on success.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.

## GET /stats

Endpoint for fetching statistics about the current state of the trading engine. Requires a valid access token.

### Request

- Method: `GET`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

### Response

- Status: `200` on success, `404` if the engine is not running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
  - `stats` (object): Statistics about the current state of the trading engine (only included on success).

## POST /update-engine

Endpoint for manually triggering an update of the trading engine. Requires a valid access token.

### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.

### Response

- Status: `200` on success, `404` if the engine is not running.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.

## POST /update-params

Endpoint to update the parameters of the running engine, mainly the `Web3Manager` class instance attributes.

### Request

- Method: `POST`
- Headers: `Authorization` header with the format `"Bearer {access_token}"`.
- Parameters: JSON dictionary containing the parameters to be changes.
  - Example: `{"provider": "https://example.com"}`

### Response

- Status: `200` on success, `401` if no parameters provided
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.


## GET /healthcheck

Endpoint for checking the health status of the API.

### Request

- Method: `GET`

### Response

- Status: `200` on success.
- Body: JSON object with the following properties:
  - `status` (string): The status of the request.
  - `message` (string): A message describing the result of the request.
