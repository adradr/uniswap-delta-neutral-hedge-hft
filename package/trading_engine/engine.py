import logging

from eth_typing.evm import ChecksumAddress
from web3_manager import web_manager


class TradingEngine:
    def __init__(
        self,
        poolAddress: ChecksumAddress,
        poolFee: int,
        walletAddress: ChecksumAddress,
        walletPrivateKey: str,
        range_percentage: int,
        capital_percentage: int,
        provider: str,
        debug: bool = False,
    ):
        """Initializes the trading engine

        Args:
            poolAddress (ChecksumAddress): Address of the pool to trade on
            poolFee (int): Fee of the pool in percentage (e.g. 3000 for 0.3%)
            walletAddress (ChecksumAddress): Address of the wallet to use
            walletPrivateKey (str): Private key of the wallet
            range_percentage (int): Range of the position in percentage (e.g. 1 for 1%)
            capital_percentage (int): Percentage of the capital to use (e.g. 10 for 10%)
            provider (str): Provider URL of the blockchain RPC, e.g. infura
            debug (bool, optional): Whether to enable debug logging. Defaults to False.
        """
        self.running = False
        self.logger = logging.getLogger(__name__)  # Retrieve the logger object

        # Set log level based on debug flag
        log_level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(log_level)

        # Initialize web3 manager
        self.web3_manager = web_manager.Web3Manager(
            poolAddress=poolAddress,
            poolFee=poolFee,
            walletAddress=walletAddress,
            walletPrivateKey=walletPrivateKey,
            range_percentage=range_percentage,
            capital_percentage=capital_percentage,
            provider=provider,
        )

    def start(self):
        self.logger.info("Starting trading engine")
        self.running = True
        self.web3_manager.open_position()
        self.logger.info("Started trading engine")
        self.logger.info("Current position: %s", self.web3_manager.position_history[-1])

    def stop(self):
        self.logger.info("Stopping trading engine")
        self.running = False
        self.web3_manager.close_position()
        self.logger.info("Stopped trading engine")
        self.logger.info("Closed position: %s", self.web3_manager.position_history[-1])

    def update(self):
        if self.running:
            self.logger.debug("Updating trading engine")
            self.web3_manager.update_position()
            self.logger.debug("Updated trading engine")
            self.logger.debug(
                "Current position: %s", self.web3_manager.position_history[-1]
            )

    def get_stats(self):
        return {
            "running": self.running,
            "position": self.web3_manager.position_history[-1],
        }
