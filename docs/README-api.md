[Back to Main README](../README.md)

## uniswap_hft.api

The Trading Engine API provides interfaces for managing and interacting with a trading engine. The following documentation details all the different endpoints and requests that can be made to the API with their corresponding responses.

---

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
