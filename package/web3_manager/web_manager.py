import datetime
import logging
import time
from typing import Tuple, Union

from eth_typing.evm import ChecksumAddress
from uniswap_math import TokenManagement
from uniswap_v3.uniswap import Uniswap
from web3.types import TxReceipt


class InsufficientFunds(Exception):
    pass


class Web3Manager:
    """Class for managing the web3 connection and the uniswap contract
    1. Init the class with the provider and the uniswap contract
    2. Open a position with the open_position method
    3. Call the update_position method to update the position; it closes the position if the price is not in the range and opens a new one
    """

    def __init__(
        self,
        poolAddress: ChecksumAddress,
        poolFee: int,
        walletAddress: ChecksumAddress,
        walletPrivateKey: str,
        range_percentage: int,
        token0_capital: int,
        provider: str,
        debug: bool = False,
    ):
        """Initilizes a pool with an associated wallet and a percentage

        Args:
            poolAddress (ChecksumAddress): The address of the pool where liq. should be provided
            poolFee (int): The fee of the pool for swapping tokens (probably can use a hardcoded value)
            walletAddress (ChecksumAddress): The address of the wallet where the funds are located at
            walletPrivateKey (str): The private key of the wallet
            range_percentage (int): How wide the range should be in percentage (e.g. 1 for 1%)
            token0_capital (int): How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size
            provider (str): The provider of the blockchain, e.g. infura
            debug (bool, optional): Whether to enable debug logging. Defaults to False.

        """
        # Set variables
        self.poolAddress = poolAddress
        self.poolFee = poolFee
        self.walletAddress = walletAddress
        self.walletPrivateKey = walletPrivateKey
        self.range_percentage = range_percentage
        self.token0_capital = token0_capital
        self.provider = provider

        self.logger = logging.getLogger(__name__)  # Retrieve the logger object

        # Set log level based on debug flag
        log_level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(log_level)

        # Initialize variables
        self.position_history = []
        """
        position_history = [
            {
                "tick_lower": int,
                "tick_upper": int,
                "current_tick": int,
                "initial_tick": int,
                "lower_range": float,
                "upper_range": float,
                "current_price": float,
                "intial_price": float,
                "tokenID": int,
                "swapTxRc": TxReceipt,
                "openTxRc": TxReceipt,
                "removeTxRc": TxReceipt,
                "collectTxRc": TxReceipt,
                "burnTxRc": TxReceipt,
                "last_update": datetime,
            }
        ]
        """

        # Initialize Uniswap object
        self.uniswap = Uniswap(
            pool_address=self.poolAddress,
            address=self.walletAddress,
            private_key=self.walletPrivateKey,
            provider=self.provider,
        )

        self.decimal0 = self.uniswap.token0_decimals
        self.decimal1 = self.uniswap.token1_decimals
        self.token0 = self.uniswap.token0
        self.token1 = self.uniswap.token1
        self.token0_contract = self.uniswap.token0Contract
        self.token1_contract = self.uniswap.token1Contract
        self.pool_contract = self.uniswap.pool
        self.token0_symbol = self.token0_contract.functions.symbol().call()
        self.token1_symbol = self.token1_contract.functions.symbol().call()

        # Initialize tokenManager
        self.tokenManager = TokenManagement.TokenManager(
            token0_decimal=self.decimal0, token1_decimal=self.decimal1
        )

        # Get token amount from pool address
        self.update_balance()

        # Log pool info line by line
        self.logger.info("Pool info:")
        self.logger.info(f"Pool address: {self.poolAddress}")
        self.logger.info(f"Swap pool fee: {self.poolFee}")
        self.logger.info(f"Wallet address: {self.walletAddress}")
        self.logger.info(f"Range percentage: {self.range_percentage}")
        self.logger.info(f"Token0 capital: {self.token0_capital}")
        self.logger.info(f"Provider: {self.provider}")
        self.logger.info(f"Decimal0: {self.decimal0}")
        self.logger.info(f"Decimal1: {self.decimal1}")
        self.logger.info(f"Token0: {self.token0}")
        self.logger.info(f"Token1: {self.token1}")
        self.logger.info(f"Token0 symbol: {self.token0_symbol}")
        self.logger.info(f"Token1 symbol: {self.token1_symbol}")
        self.logger.info(f"Token0 balance: {self.token0Balance}")
        self.logger.info(f"Token1 balance: {self.token1Balance}")

    def update_balance(self):
        """Updates the balances of the wallet for token0 and token1"""
        self.token0Balance = self.token0_contract.functions.balanceOf(
            self.walletAddress
        ).call()
        self.token1Balance = self.token1_contract.functions.balanceOf(
            self.walletAddress
        ).call()

    def get_current_time_str(self) -> str:
        # Save position history
        last_update = time.time()
        last_update_str = datetime.datetime.fromtimestamp(last_update).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return last_update_str

    def parseTxReceiptForTokenId(self, rc: TxReceipt) -> int:
        """Parses a tx receipt for the tokenId

        Args:
            rc (TxReceipt): TxReceipt object instance returned by open_position function

        Returns:
            int: tokenId of Uniswap V3 NFT
        """
        # logs_mint = self.pool_contract.events.Mint().processReceipt(rc)
        # sender = logs_mint[0]["args"]["sender"]

        logs_transfer = (
            self.uniswap.nonFungiblePositionManager.events.Transfer().processReceipt(rc)
        )
        return logs_transfer[0]["args"]["tokenId"]

    def swap_amounts(self) -> Union[TxReceipt, None]:
        """Swaps the tokens in the wallet for the token with the least amount

        Raises:
            Exception: If both or none of the token amounts are 0

        Returns:
            TxReceipt: Transaction receipt of the swap
        """
        # Get existing token amounts
        existing_amount0 = self.token0Balance
        existing_amount1 = self.token1Balance
        existing_amount0_decimal = (
            existing_amount0 / 10**self.tokenManager.token0_decimal
        )
        existing_amount1_decimal = (
            existing_amount1 / 10**self.tokenManager.token1_decimal
        )

        # Get required token amounts and multiply by 1.01 to account for swap-mint slippage
        required_amount0 = self.amount0 * 1.01
        required_amount1 = self.amount1 * 1.01
        required_amount0_decimal = (
            required_amount0 / 10**self.tokenManager.token0_decimal
        )
        required_amount1_decimal = (
            required_amount1 / 10**self.tokenManager.token1_decimal
        )

        # Get current price
        current_price = self.uniswap.get_current_price()

        # Log current price and token amounts
        self.logger.info(f"Current price: {current_price}")
        self.logger.info(
            f"Existing/Required amount for {self.token0_symbol}: "
            f"{existing_amount0_decimal } / {required_amount0_decimal}"
        )
        self.logger.info(
            f"Existing/Required amount for {self.token1_symbol}: "
            f"{existing_amount1_decimal} / {required_amount1_decimal}"
        )

        # Both token amounts are equal or more than required
        # NO SWAP
        if (
            existing_amount0 >= required_amount0
            and existing_amount1 >= required_amount1
        ):
            self.logger.info("No swap required")
            return None

        # Both token amounts are less than required
        # RAISE ERROR
        elif (
            existing_amount0 < required_amount0 and existing_amount1 < required_amount1
        ):
            e_msg = "Both token amounts are less than required"
            self.logger.error(e_msg)
            raise InsufficientFunds(e_msg)

        # Token0 amount is less than required
        # SWAP TOKEN0 FOR TOKEN1
        elif existing_amount0 < required_amount0:
            # Check if token1 amount is enough for swap and required_amount1
            if existing_amount1 >= required_amount1 + (
                existing_amount1 / current_price
            ):
                # Get swap amounts token1 for token0
                swapAmount = required_amount0 - existing_amount0
                input_token = self.token1
                output_token = self.token0
            else:
                e_msg = "Token1 amount is not enough for swap and required_amount1"
                self.logger.error(e_msg)
                raise InsufficientFunds(e_msg)

        # Token1 amount is less than required
        # SWAP TOKEN1 FOR TOKEN0
        elif existing_amount1 < required_amount1:
            # Check if token0 amount is enough for swap and required_amount0
            if existing_amount0 >= required_amount0 + (
                existing_amount0 / current_price
            ):
                # Get swap amounts token0 for token1
                swapAmount = required_amount1 - existing_amount1
                input_token = self.token0
                output_token = self.token1
            else:
                e_msg = "Token0 amount is not enough for swap and required_amount0"
                self.logger.error(e_msg)
                raise InsufficientFunds(e_msg)

        else:
            self.logger.error("Unexpected error")
            raise Exception("Unexpected error")

        # Swap tokens
        hex = self.uniswap.swap_token_input(
            token_in_address=input_token,
            token_out_address=output_token,
            amount_in=swapAmount,
            pool_fee=self.poolFee,
        )

        # Get TxReceipt from HexBytes and return
        return self.uniswap.w3.eth.getTransactionReceipt(hex)

    def update_position(self):
        """Updates the position of the wallet in the pool
        1. Get current price and tick
        2. Only if tick is higher or lower than range close position
            a. Close position
            b. Open position

        """
        # Get current price and tick
        currentPrice = self.uniswap.get_current_price()
        currentTick = self.tokenManager.price_to_tick(currentPrice)

        # Save current tick and price
        self.position_history[-1]["current_tick"] = currentTick
        self.position_history[-1]["current_price"] = currentPrice
        self.position_history[-1]["last_update"] = self.get_current_time_str()

        # Only if tick is higher or lower than range close position
        if (
            currentTick > self.position_history[-1]["upper_tick"]
            or currentTick < self.position_history[-1]["lower_tick"]
        ):
            # Close position
            self.close_position()

            # Open position
            self.open_position()

    def open_position(self) -> TxReceipt:
        """Open a position at Uniswap V3
        1. Updates the balances of the wallet for token0 and token1
        2. Swaps the tokens in the wallet for the token with the least amount
        3. Opens a position at Uniswap V3
        4. Saves the position in the position_history list

        Args:
            capitalPercentage (int, optional): Percentage of capital to be used for the position. Defaults to 100.

        Returns:
            TxReceipt: Transaction receipt of the open position
        """
        # Get current price
        current_price = self.uniswap.get_current_price()

        # Calculate ticks from currentPrice
        (
            range_low,
            current_price,
            range_high,
            tick_low,
            current_tick,
            tick_high,
        ) = self.tokenManager.get_ranges(
            percentage=self.range_percentage, currentPrice=current_price
        )

        # Calculate amounts
        self.amount0, self.amount1 = self.tokenManager.calculate_amounts(
            current_price=current_price,
            range_low=range_low,
            range_high=range_high,
            total_token0_amount=self.token0_capital,
        )

        # Get token amounts
        self.update_balance()

        # Swap tokens
        swap_rc = self.swap_amounts()

        # open position at uniswap
        rc_mint = self.uniswap.mint_liquidity(
            tick_lower=tick_low,
            tick_upper=tick_high,
            amount_0=self.amount0,
            amount_1=self.amount1,
            recipient=self.walletAddress,
        )

        # Get tokenId
        tokenId = self.parseTxReceiptForTokenId(rc=rc_mint)

        # Save position in position_history
        self.position_history.append(
            {
                "tick_lower": tick_low,
                "tick_upper": tick_high,
                "current_tick": current_tick,
                "initial_tick": current_tick,
                "lower_range": range_low,
                "upper_range": range_high,
                "current_price": current_price,
                "intial_price": current_price,
                "tokenID": tokenId,
                "openTxRc": rc_mint,
                "swapTxRc": swap_rc,
                "removeTxRc": None,
                "collectTxRc": None,
                "burnTxRc": None,
                "last_update": self.get_current_time_str(),
            }
        )

        return rc_mint

    def close_position(self) -> Tuple[TxReceipt, TxReceipt, TxReceipt]:
        """Closes a position in the Uniswap V3 pool
        1. Closes the position at Uniswap V3
        2. Saves the position in the position_history list

        Args:
            tokenId (int): tokenId of the Uniswap V3 NFT

        Returns:
            TxReceipt: Transaction receipt of the close position
        """
        # Close position at uniswap
        token_id = self.position_history[-1]["tokenID"]

        # Get transaction receipts
        receipt_remove_liquidity = self.uniswap.decrease_liquidity(tokenId=token_id)
        receipt_collect_fees = self.uniswap.collect_fees(tokenId=token_id)
        receipt_burn = self.uniswap.burn_token(tokenId=token_id)

        # Save position history
        self.position_history[-1]["removeTxRc"] = receipt_remove_liquidity
        self.position_history[-1]["collectTxRc"] = receipt_collect_fees
        self.position_history[-1]["burnTxRc"] = receipt_burn
        self.position_history[-1]["last_update"] = self.get_current_time_str()

        return (
            receipt_remove_liquidity,
            receipt_collect_fees,
            receipt_burn,
        )
