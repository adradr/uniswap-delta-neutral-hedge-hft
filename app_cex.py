import argparse
import logging
import os

from dotenv import load_dotenv

from uniswap_hft.trading_engine import api, engine


def str_to_bool(s):
    if s == "True":
        return True
    elif s == "False":
        return False
    else:
        raise ValueError("Received non-boolean value: {}".format(s))


# Create a temporary parser to only parse the --env-file argument
temp_parser = argparse.ArgumentParser(add_help=False)
temp_parser.add_argument(
    "--env-file",
    type=str,
    help="Path to the .env file",
    default="rand.env",
)
args, _ = temp_parser.parse_known_args()

# Load the environment variables
load_dotenv(dotenv_path=args.env_file)

# Create parser
parser = argparse.ArgumentParser(description="Trading engine API")
parser.add_argument(
    "--env-file",
    type=str,
    help="Path to the .env file",
    default=".env",
)

# Add more arguments
parser.add_argument(
    "--jwt-secret-key",
    type=str,
    help="The secret key used to sign the JWT tokens",
    default=os.getenv("JWT_SECRET_KEY"),
)
parser.add_argument(
    "--jwt-access-token-expires",
    type=int,
    help="The expiration time in minutes for access tokens",
    default=os.getenv("JWT_ACCESS_TOKEN_EXPIRES"),
)
parser.add_argument(
    "--allowed-users-passwords",
    type=str,
    nargs="+",
    help="A list of allowed users and passwords",
    default=os.getenv("ALLOWED_USERS_PASSWORDS"),
)
parser.add_argument(
    "--host",
    type=str,
    help="The host to run the API on",
    default=os.getenv("HOST"),
)
parser.add_argument(
    "--port",
    type=int,
    help="The port to run the API on",
    default=os.getenv("PORT"),
)
parser.add_argument(
    "--debug",
    type=str_to_bool,
    help="Whether to run the API in debug mode",
    default=str_to_bool(os.getenv("DEBUG")),
)

parser.add_argument(
    "--pool-address",
    type=str,
    help="The address of the pool",
    default=os.getenv("POOL_ADDRESS"),
)

parser.add_argument(
    "--pool-fee",
    type=int,
    help="The fee of the pool",
    default=os.getenv("POOL_FEE"),
)

parser.add_argument(
    "--wallet-address",
    type=str,
    help="The address of the wallet",
    default=os.getenv("WALLET_ADDRESS"),
)

parser.add_argument(
    "--wallet-private-key",
    type=str,
    help="The private key of the wallet",
    default=os.getenv("WALLET_PRIVATE_KEY"),
)

parser.add_argument(
    "--range-percentage",
    type=int,
    help="The range percentage",
    default=os.getenv("RANGE_PERCENTAGE"),
)

parser.add_argument(
    "--usd-capital",
    type=int,
    help="How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size",
    default=os.getenv("USD_CAPITAL"),
)

parser.add_argument(
    "--provider",
    type=str,
    help="Web3 provider url",
    default=os.getenv("PROVIDER"),
)

parser.add_argument(
    "--burn-on-close",
    type=str_to_bool,
    help="Whether to burn the remaining tokens on close",
    default=str_to_bool(os.getenv("BURN_ON_CLOSE")),
)

parser.add_argument(
    "--telegram-token",
    type=str,
    help="Telegram token",
    default=os.getenv("TELEGRAM_API_KEY"),
)

parser.add_argument(
    "--telegram-chat-id",
    type=str,
    help="Telegram chat id",
    default=os.getenv("TELEGRAM_CHAT_ID"),
)

parser.add_argument(
    "--position-history-path",
    type=str,
    help="Path to the position history file, defaults to position_history.json",
    default=os.getenv("POSITION_HISTORY_PATH", "position_history.json"),
)

# Get credentials from environment variables based on the dicts above
parser.add_argument(
    "--cex-mainaccount-api-key",
    type=str,
    help="The API key for the main account",
    default=os.getenv("CEX_MAINACCOUNT_API_KEY"),
)

parser.add_argument(
    "--cex-mainaccount-api-secret",
    type=str,
    help="The API secret for the main account",
    default=os.getenv("CEX_MAINACCOUNT_API_SECRET"),
)

parser.add_argument(
    "--cex-mainaccount-passphrase",
    type=str,
    help="The passphrase for the main account",
    default=os.getenv("CEX_MAINACCOUNT_PASSPHRASE"),
)

parser.add_argument(
    "--cex-subaccount-api-key",
    type=str,
    help="The API key for the main account",
    default=os.getenv("CEX_SUBACCOUNT_API_KEY"),
)

parser.add_argument(
    "--cex-subaccount-api-secret",
    type=str,
    help="The API secret for the main account",
    default=os.getenv("CEX_SUBACCOUNT_API_SECRET"),
)

parser.add_argument(
    "--cex-subaccount-passphrase",
    type=str,
    help="The passphrase for the main account",
    default=os.getenv("CEX_SUBACCOUNT_PASSPHRASE"),
)

parser.add_argument(
    "--cex-subaccount-account-name",
    type=str,
    help="The account name for the main account",
    default=os.getenv("CEX_SUBACCOUNT_NAME"),
)

parser.add_argument(
    "--cex-chain",
    type=str,
    help="The chain for the main account",
    default=os.getenv("CEX_CHAIN"),
)

parser.add_argument(
    "--cex-maximum-spread-bps",
    type=float,
    help="The maximum spread in bps for the main account",
    default=os.getenv("CEX_MAXIMUM_SPREAD_BPS"),
)

parser.add_argument(
    "--cex-block-trading-deadline",
    type=int,
    help="The block trading deadline for the main account",
    default=os.getenv("CEX_BLOCK_TRADING_DEADLINE"),
)

parser.add_argument(
    "--cex-is-demo",
    type=str_to_bool,
    help="Whether the to use a demo account, needs demo credentials",
    default=str_to_bool(os.getenv("CEX_IS_DEMO")),
)

# Parse arguments
args = parser.parse_args()
print(args)

# cex_credentials (Dict[str, Dict[str, str]]): The credentials for the OKEX API. Needs a dict with "main" and "subaccount" keys, containing a dictionaries  Defaults to None.
#     e.g.:
#     {
#         "main": {
#             "api_key": "your_api_key",
#             "api_secret": "your_api_secret",
#             "passphrase": "your_passphrase",
#             "account_name": "your_account_name",
#             "chain": "ETH",
#             "maximum_spread_bps": 3, [optional, default: 3]
#             "block_trading_deadline": 60, [optional, default: 60]
#             "is_demo": False, [optional, default: False]
#         },
#         "subaccount": {
#             "api_key": "your_api_key",
#             "api_secret": "your_api_secret",
#             "passphrase": "your_passphrase",
#             "account_name": "your_account_name",
#             "chain": "ETH",
#             "maximum_spread_bps": 3, [optional, default: 3]
#             "block_trading_deadline": 60, [optional, default: 60]
#             "is_demo": False, [optional, default: False]
#         },
#     }


# Create cex_credentials dict
args.cex_credentials = {
    "main": {
        "api_key": args.cex_mainaccount_api_key,
        "api_secret": args.cex_mainaccount_api_secret,
        "passphrase": args.cex_mainaccount_passphrase,
        "account_name": "Main Account",
        "chain": args.cex_chain,
        "maximum_spread_bps": args.cex_maximum_spread_bps,
        "block_trading_deadline": args.cex_block_trading_deadline,
        "is_demo": args.cex_is_demo,
    },
    "subaccount": {
        "api_key": args.cex_subaccount_api_key,
        "api_secret": args.cex_subaccount_api_secret,
        "passphrase": args.cex_subaccount_passphrase,
        "account_name": args.cex_subaccount_account_name,
        "chain": args.cex_chain,
        "maximum_spread_bps": args.cex_maximum_spread_bps,
        "block_trading_deadline": args.cex_block_trading_deadline,
        "is_demo": args.cex_is_demo,
    },
}

# Create telegram_credentials dict
if args.telegram_token and args.telegram_chat_id:
    args.telegram_credentials = {
        "bot_token": args.telegram_token,
        "chat_id": args.telegram_chat_id,
    }


# Cast user and password pairs to tuples
if args.allowed_users_passwords:
    users_passwords = []
    pairs = args.allowed_users_passwords.split(";")
    for pair in pairs:
        user, password = pair.split(":")
        users_passwords.append((user, password))
        args.allowed_users_passwords = users_passwords

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)


# Create trading engine
trading_engine = engine.TradingEngine(
    pool_address=args.pool_address,
    pool_fee=args.pool_fee,
    wallet_address=args.wallet_address,
    wallet_private_key=args.wallet_private_key,
    range_percentage=args.range_percentage,
    usd_capital=args.usd_capital,
    provider=args.provider,
    burn_on_close=args.burn_on_close,
    cex_credentials=args.cex_credentials,
    # telegram_credentials=args.telegram_credentials,
    position_history_path=args.position_history_path,
)

# Create trading API
trading_api = api.TradingEngineAPI(
    engine=trading_engine,
    jwt_secret_key=args.jwt_secret_key,
    jwt_access_token_expires=args.jwt_access_token_expires,
    allowed_users_passwords=args.allowed_users_passwords,
    host=args.host,
    port=args.port,
    debug=args.debug,
)

if __name__ == "__main__":
    trading_api.run()
