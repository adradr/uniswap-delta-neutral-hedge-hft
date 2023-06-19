import datetime
import json
import logging
import time
from typing import Tuple, Union

from eth_typing.evm import ChecksumAddress
from web3.types import TxReceipt

from uniswap_hft.uniswap_math import TokenManagement
from uniswap_hft.uniswap_v3.uniswap import Uniswap


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
        pool_address: ChecksumAddress,
        pool_fee: int,
        wallet_address: ChecksumAddress,
        wallet_private_key: str,
        range_percentage: int,
        token0_capital: int,
        provider: str,
        debug: bool = False,
    ):
        """Initilizes a pool with an associated wallet and a percentage

        Args:
            pool_address (ChecksumAddress): The address of the pool where liq. should be provided
            pool_fee (int): The fee of the pool for swapping tokens (probably can use a hardcoded value)
            wallet_address (ChecksumAddress): The address of the wallet where the funds are located at
            wallet_private_key (str): The private key of the wallet
            range_percentage (int): How wide the range should be in percentage (e.g. 1 for 1%)
            token0_capital (int): How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size
            provider (str): The provider of the blockchain, e.g. infura
            debug (bool, optional): Whether to enable debug logging. Defaults to False.

        """
        # Set variables
        self.pool_address = pool_address
        self.pool_fee = pool_fee
        self.wallet_address = wallet_address
        self.wallet_private_key = wallet_private_key
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
                "tick_current": int,
                "tick_initial": int,
                "range_lower": float,
                "range_upper": float,
                "price_current": float,
                "price_initial": float,
                "tokenID": int,
                "tx_swap": str,
                "tx_mint": str,
                "tx_decrease": str,
                "tx_collect": str,
                "tx_burn": str,
                "is_open": bool,
                "last_update": datetime,
            }
        ]
        """

        # Initialize Uniswap object
        self.uniswap = Uniswap(
            pool_address=self.pool_address,
            address=self.wallet_address,
            private_key=self.wallet_private_key,
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
            current_price=self.uniswap.get_current_price(),
            range_pct=self.range_percentage,
            target_amount=self.token0_capital,
            token0_decimal=self.decimal0,
            token1_decimal=self.decimal1,
        )

        # Get token amount from pool address
        self.update_balance()

        # Log pool info line by line
        self.logger.info("Pool info:")
        self.logger.info(f"Pool address: {self.pool_address}")
        self.logger.info(f"Swap pool fee: {self.pool_fee}")
        self.logger.info(f"Wallet address: {self.wallet_address}")
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

        # Try to load position history
        try:
            self.load_position_history()
            self.logger.info("Position history loaded")
        except:
            self.logger.info("Position history not found")

    def store_position_history(self):
        """Store the position history in a json file"""
        with open("position_history.json", "w") as f:
            json.dump(self.position_history, f)

    def load_position_history(self):
        """Load the position history from a json file"""
        with open("position_history.json", "r") as f:
            self.position_history = json.load(f)

    def update_balance(self):
        """Updates the balances of the wallet for token0 and token1"""
        self.token0Balance = self.token0_contract.functions.balanceOf(
            self.wallet_address
        ).call()
        self.token1Balance = self.token1_contract.functions.balanceOf(
            self.wallet_address
        ).call()

    def get_current_time_str(self) -> str:
        """Returns the current time as a string"""
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
        existing_amount0 = self.token0Balance  # USDC
        existing_amount1 = self.token1Balance  # ETH
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
        current_price_decimal = self.uniswap.get_current_price()
        current_price = current_price_decimal * 10**self.tokenManager.token0_decimal

        # Log current price and token amounts
        self.logger.info(f"Current price: {current_price_decimal}")
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

        # SWAP TOKEN1 FOR TOKEN0
        # Token0 amount is less than required
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

            """
            1000 USDC / 1 ETH
            1000 * 10**6 / 1 * 10**18

            1000 * 10**6 / 10**18 * 1 = 0,000000001 ETH / 1 * 10**6 USDC
            1000 * 10**6 = 1 000 000 000 USDC / 1 * 10**18 ETH
            """

        # SWAP TOKEN0 FOR TOKEN1
        # Token1 amount is less than required
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
            pool_fee=self.pool_fee,
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
        current_price = self.uniswap.get_current_price()
        current_tick = self.tokenManager.price_to_tick(current_price)

        # Read current tick from Uniswap V3 contract

        # Save current tick and price
        self.position_history[-1]["tick_current"] = current_tick
        self.position_history[-1]["price_current"] = current_price
        self.position_history[-1]["last_update"] = self.get_current_time_str()

        # Save position history
        self.store_position_history()

        # Only if tick is higher or lower than range close position
        if (
            current_tick > self.position_history[-1]["tick_upper"]
            or current_tick < self.position_history[-1]["tick_lower"]
        ):
            # Log close position
            self.logger.info("Price is outside of range. Closing position")

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
            percentage=self.range_percentage, current_price=current_price
        )

        # Calculate required amounts
        self.amount1, self.amount0 = self.tokenManager.calculate_amounts(
            current_price=current_price,
        )
        self.amount0 = int(self.amount0 * 10**self.tokenManager.token0_decimal)
        self.amount1 = int(self.amount1 * 10**self.tokenManager.token1_decimal)

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
            recipient=self.wallet_address,
        )

        # Get the transaction hash from the receipt objects
        swap_tx_hash = swap_rc["transactionHash"].hex() if swap_rc else None
        mint_tx_hash = rc_mint["transactionHash"].hex()

        # Get tokenId
        tokenId = self.parseTxReceiptForTokenId(rc=rc_mint)

        # Save position in position_history
        self.position_history.append(
            {
                "tick_lower": tick_low,
                "tick_upper": tick_high,
                "tick_current": current_tick,
                "tick_initial": current_tick,
                "range_lower": range_low,
                "range_upper": range_high,
                "price_current": current_price,
                "price_initial": current_price,
                "tokenID": tokenId,
                "tx_mint": mint_tx_hash,
                "tx_swap": swap_tx_hash,
                "tx_decrease": None,
                "tx_collect": None,
                "tx_burn": None,
                "is_open": True,
                "last_update": self.get_current_time_str(),
            }
        )

        # Save position history
        self.store_position_history()

        return rc_mint

    def close_position(self) -> Tuple[TxReceipt, TxReceipt, TxReceipt]:
        """Closes a position in the Uniswap V3 pool
        1. Closes the position at Uniswap V3
        2. Saves the position in the position_history list

        Returns:
            TxReceipt: Transaction receipt of the close position
        """
        # Close position at uniswap
        token_id = self.position_history[-1]["tokenID"]

        # Get transaction receipts
        receipt_remove_liquidity = self.uniswap.decrease_liquidity(tokenId=token_id)
        receipt_collect_fees = self.uniswap.collect_fees(tokenId=token_id)
        receipt_burn = self.uniswap.burn_token(tokenId=token_id)

        # Get the transaction hash from the receipt objects
        remove_liquidity_tx_hash = receipt_remove_liquidity["transactionHash"].hex()
        collect_fees_tx_hash = receipt_collect_fees["transactionHash"].hex()
        burn_tx_hash = receipt_burn["transactionHash"].hex()

        # Save position history
        self.position_history[-1]["tx_decrease"] = remove_liquidity_tx_hash
        self.position_history[-1]["tx_collect"] = collect_fees_tx_hash
        self.position_history[-1]["tx_burn"] = burn_tx_hash
        self.position_history[-1]["last_update"] = self.get_current_time_str()
        self.position_history[-1]["is_open"] = False

        # Save position history
        self.store_position_history()

        return (
            receipt_remove_liquidity,
            receipt_collect_fees,
            receipt_burn,
        )
