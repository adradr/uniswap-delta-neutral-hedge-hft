import logging
import typing

import eth_typing.evm

import uniswap_hft.web3_manager.web_manager


class TradingEngine:
    def __init__(
        self,
        pool_address: eth_typing.evm.ChecksumAddress,
        pool_fee: int,
        wallet_address: eth_typing.evm.ChecksumAddress,
        wallet_private_key: str,
        range_percentage: int,
        usd_capital: int,
        provider: str,
        burn_on_close: bool = False,
        debug: bool = False,
        position_history_path: str = "position_history.json",
        cex_credentials: typing.Optional[
            typing.Dict[str, typing.Dict[str, typing.Union[float, int, bool]]]
        ] = None,
        telegram_credentials: typing.Optional[typing.Dict] = None,
    ):
        """Initializes the trading engine

        Args:
            pool_address (eth_typing.evm.ChecksumAddress): Address of the pool to trade on
            pool_fee (int): Fee of the pool in percentage (e.g. 3000 for 0.3%)
            wallet_address (eth_typing.evm.ChecksumAddress): Address of the wallet to use
            wallet_private_key (str): Private key of the wallet
            range_percentage (int): Range of the position in percentage (e.g. 1 for 1%)
            usd_capital (int): How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size
            provider (str): Provider URL of the blockchain RPC, e.g. infura
            burn_on_close (bool, optional): Whether to burn the position on close. Defaults to False.
            debug (bool, optional): Whether to enable debug logging. Defaults to False.
            position_history_path (str, optional): Path to the position history file. Defaults to "position_history.json".
            cex_credentials (Dict[str, Dict[str, str]]): The credentials for the OKEX API. Needs a dict with "main" and "subaccount" keys, containing a dictionaries  Defaults to None.
                e.g.:
                {
                    "main": {
                        "api_key": "your_api_key",
                        "api_secret": "your_api_secret",
                        "passphrase": "your_passphrase",
                        "account_name": "your_account_name",
                        "chain": "ETH",
                        "maximum_spread_bps": 3, [optional, default: 3]
                        "block_trading_deadline": 60, [optional, default: 60]
                        "is_demo": False, [optional, default: False]
                    },
                    "subaccount": {
                        "api_key": "your_api_key",
                        "api_secret": "your_api_secret",
                        "passphrase": "your_passphrase",
                        "account_name": "your_account_name",
                        "chain": "ETH",
                        "maximum_spread_bps": 3, [optional, default: 3]
                        "block_trading_deadline": 60, [optional, default: 60]
                        "is_demo": False, [optional, default: False]

                    },
                }
            telegram_credentials (Dict[str, str]): The credentials for the telegram bot. Needs a dict with "token" and "chat_id" keys, containing the token and the chat_id. Defaults to None.
                e.g.:
                {
                    "bot_token": "your_token",
                    "chat_id": "your_chat_id",
                }
        """
        self.running = False
        self.logger = logging.getLogger(__name__)  # Retrieve the logger object

        # Set log level based on debug flag
        log_level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(log_level)

        # Initialize web3 manager
        self.web3_manager = uniswap_hft.web3_manager.web_manager.Web3Manager(
            pool_address=pool_address,
            pool_fee=pool_fee,
            wallet_address=wallet_address,
            wallet_private_key=wallet_private_key,
            range_percentage=range_percentage,
            usd_capital=usd_capital,
            provider=provider,
            burn_on_close=burn_on_close,
            position_history_path=position_history_path,
            cex_credentials=cex_credentials,
            telegram_credentials=telegram_credentials,
        )

        # Set running flag to true if position_history is_open is true
        if len(self.web3_manager.position_history) > 0:
            if self.web3_manager.position_history[-1]["is_open"]:
                self.running = True
                self.logger.info("Trading engine is running")

    def start(self) -> dict:
        self.logger.info("Starting trading engine")
        self.web3_manager.open_position()
        self.logger.info("Started trading engine")
        self.logger.info("Current position: %s", self.web3_manager.position_history[-1])
        self.running = True
        return self.web3_manager.position_history[-1]

    def stop(self) -> dict:
        self.logger.info("Stopping trading engine")
        self.web3_manager.close_position()
        self.logger.info("Stopped trading engine")
        self.logger.info("Closed position: %s", self.web3_manager.position_history[-1])
        self.running = False
        return self.web3_manager.position_history[-1]

    def update_engine(self) -> dict:
        if self.running:
            self.logger.debug("Updating trading engine")
            self.web3_manager.update_position()
            self.logger.debug("Updated trading engine")
            self.logger.debug(
                "Current position: %s", self.web3_manager.position_history[-1]
            )
            return self.web3_manager.position_history[-1]
        return {}

    def update_params(self, params: dict):
        self.logger.info("Updating trading engine")

        for k, v in params.items():
            if k == "range_percentage":
                self.web3_manager.range_percentage = v
            elif k == "usd_capital":
                self.web3_manager.usd_capital = v
            elif k == "pool_fee":
                self.web3_manager.pool_fee = v
            elif k == "pool_address":
                self.web3_manager.pool_address = v
            elif k == "wallet_address":
                self.web3_manager.wallet_address = v
            elif k == "wallet_private_key":
                self.web3_manager.wallet_private_key = v
            elif k == "provider":
                self.web3_manager.provider = v
            else:
                self.logger.warning("Unknown parameter %s", k)

        self.logger.info("Updated trading engine")

    def get_stats(self):
        return {
            "running": self.running,
            "position": self.web3_manager.position_history[-1],
        }
