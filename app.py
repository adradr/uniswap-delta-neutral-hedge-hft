import os
import argparse
from dotenv import load_dotenv

load_dotenv()

from trading_engine import api, engine

# Create parser
parser = argparse.ArgumentParser(description="Trading engine API")

# Add arguments
parser.add_argument(
    "--jwt-secret-key",
    type=str,
    help="The secret key used to sign the JWT tokens",
    default=os.getenv("JWT_SECRET_KEY"),
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
    "--capital-percentage",
    type=int,
    help="The percentage of capital to use",
    default=os.getenv("CAPITAL_PERCENTAGE"),
)

parser.add_argument(
    "--provider",
    type=str,
    help="Web3 provider url",
    default=os.getenv("PROVIDER"),
)

# Parse arguments
args = parser.parse_args()

# Create trading engine
trading_engine = engine.TradingEngine(
    poolAddress=args.pool_address,
    poolFee=args.pool_fee,
    walletAddress=args.wallet_address,
    walletPrivateKey=args.wallet_private_key,
    range_percentage=args.range_percentage,
    capital_percentage=args.capital_percentage,
    provider=args.provider,
)

# Create trading API
trading_api = api.TradingEngineAPI(
    engine=trading_engine,
    jwt_secret_key=args.jwt_secret_key,
    allowed_users_passwords=args.allowed_users_passwords,
    host=args.host,
    port=args.port,
    debug=args.debug,
)


if __name__ == "__main__":
    trading_api.run()
