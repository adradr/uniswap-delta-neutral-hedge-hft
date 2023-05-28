import argparse
import logging
import os

from dotenv import load_dotenv
from uniswap_hft.trading_engine import api, engine

# Create parser
load_dotenv()
parser = argparse.ArgumentParser(description="Trading engine API")

# Add arguments
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
    type=bool,
    help="Whether to run the API in debug mode",
    default=os.getenv("DEBUG"),
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
    "--token0-capital",
    type=int,
    help="How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size",
    default=os.getenv("TOKEN0_CAPITAL"),
)

parser.add_argument(
    "--provider",
    type=str,
    help="Web3 provider url",
    default=os.getenv("PROVIDER"),
)

# Parse arguments
args = parser.parse_args()

# Cast user and password pairs to tuples
if args.allowed_users_passwords is not None:
    args.allowed_users_passwords = [
        tuple(pair.split(",")) for pair in args.allowed_users_passwords.split()
    ]

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
    token0_capital=args.token0_capital,
    provider=args.provider,
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
