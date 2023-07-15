import json
import time
import typing
import logging
import datetime
import pysnooper
import web3.types
import eth_typing.evm
import multiprocessing
import uniswap_hft.uniswap_math.TokenManagement
import uniswap_hft.uniswap_v3.uniswap
import uniswap_hft.okex_integration.client
import uniswap_hft.telegram_interface.telegram_handler


class InsufficientFunds(Exception):
    pass


class BlocktradeFailed(Exception):
    pass


class DepositFailed(Exception):
    pass


class TransferFailed(Exception):
    pass


class WithdrawFailed(Exception):
    pass


class WithdrawTimeout(Exception):
    pass


class Web3Manager:
    """Class for managing the web3 connection and the uniswap contract
    1. Init the class with the provider and the uniswap contract
    2. Open a position with the open_position method
    3. Call the update_position method to update the position; it closes the position if the price is not in the range and opens a new one
    """

    def __init__(
        self,
        pool_address: eth_typing.evm.ChecksumAddress,
        pool_fee: int,
        wallet_address: eth_typing.evm.ChecksumAddress,
        wallet_private_key: str,
        range_percentage: int,
        token0_capital: int,
        provider: str,
        burn_on_close: bool = False,
        debug: bool = False,
        position_history_path: str = "position_history.json",
        cex_credentials: typing.Optional[typing.Dict] = None,
        telegram_credentials: typing.Optional[typing.Dict] = None,
    ):
        """Initilizes a pool with an associated wallet and a percentage

        Args:
            pool_address (eth_typing.evm.ChecksumAddress): The address of the pool where liq. should be provided
            pool_fee (int): The fee of the pool for swapping tokens (probably can use a hardcoded value)
            wallet_address (eth_typing.evm.ChecksumAddress): The address of the wallet where the funds are located at
            wallet_private_key (str): The private key of the wallet
            range_percentage (int): How wide the range should be in percentage (e.g. 1 for 1%)
            token0_capital (int): How much of the funds should be used to provide liquidity for token0 (e.g. 1000 for 1000USDC). Note: it will be ~doubled for the total position size
            provider (str): The provider of the blockchain, e.g. infura
            burn_on_close (bool, optional): Whether to burn the liquidity tokens on close. Defaults to False.
            debug (bool, optional): Whether to enable debug logging. Defaults to False.
            position_history_path (str, optional): The path to the position history file. Defaults to "position_history.json".
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

        Raises:
            ValueError: If the range_percentage is not between 0 and 100


        """
        # Set variables
        self.pool_address = pool_address
        self.pool_fee = pool_fee
        self.wallet_address = wallet_address
        self.wallet_private_key = wallet_private_key
        self.range_percentage = range_percentage
        self.token0_capital = token0_capital
        self.provider = provider
        self.burn_on_close = burn_on_close
        self.cex_credentials = cex_credentials
        self.debug = debug
        self.position_history_path = position_history_path

        if cex_credentials is not None:
            self.cex_client_main = uniswap_hft.okex_integration.client.OKXClient(
                api_key=cex_credentials["main"]["api_key"],
                api_secret=cex_credentials["main"]["api_secret"],
                passphrase=cex_credentials["main"]["passphrase"],
                account_name=cex_credentials["main"]["account_name"],
                chain=cex_credentials["main"]["chain"],
                maximum_spread_bps=cex_credentials["main"].get("maximum_spread_bps", 3),
                block_trading_deadline=cex_credentials["main"].get(
                    "block_trading_deadline", 60
                ),
                is_main_account=True,
                debug=debug,
                is_demo=cex_credentials["main"]["is_demo"],
            )

            self.cex_client_subaccount = uniswap_hft.okex_integration.client.OKXClient(
                api_key=cex_credentials["subaccount"]["api_key"],
                api_secret=cex_credentials["subaccount"]["api_secret"],
                passphrase=cex_credentials["subaccount"]["passphrase"],
                account_name=cex_credentials["subaccount"]["account_name"],
                chain=cex_credentials["subaccount"]["chain"],
                maximum_spread_bps=cex_credentials["subaccount"].get(
                    "maximum_spread_bps", 3
                ),
                block_trading_deadline=cex_credentials["subaccount"].get(
                    "block_trading_deadline", 60
                ),
                is_main_account=False,
                debug=debug,
                is_demo=cex_credentials["subaccount"]["is_demo"],
            )

        # Retrieve the logger object
        self.logger = logging.getLogger(__name__)
        log_level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(log_level)

        # Initialize variables
        self.background_process = None
        self.position_history = []
        """
        position_history = [
            {
                "amount0": int,
                "amount1": int,
                "token0_symbol": str,
                "token1_symbol": str,
                "token0_address": str,
                "token1_address": str,
                "tick_lower": int,
                "tick_upper": int,
                "tick_current": int,
                "tick_initial": int,
                "range_lower": float,
                "range_upper": float,
                "price_current": float,
                "price_initial": float,
                "tokenID": int,
                "tx_swap": list,
                "tx_mint": str,
                "tx_decrease": str,
                "tx_collect": str,
                "tx_burn": str,
                "is_open": bool,
                "last_update": datetime,
                "message": str,
            }
        ]
        """

        # Initialize Uniswap object
        self.uniswap = uniswap_hft.uniswap_v3.uniswap.Uniswap(
            pool_address=self.pool_address,
            address=self.wallet_address,
            private_key=self.wallet_private_key,
            provider=self.provider,
        )

        self.decimal0 = self.uniswap.token0_decimals
        self.decimal1 = self.uniswap.token1_decimals
        self.decimal_diff = abs(self.decimal0 - self.decimal1)
        self.decimal_sum = self.decimal0 + self.decimal1
        self.token0 = self.uniswap.token0
        self.token1 = self.uniswap.token1
        self.token0_contract = self.uniswap.token0Contract
        self.token1_contract = self.uniswap.token1Contract
        self.pool_contract = self.uniswap.pool
        self.token0_symbol = self.token0_contract.functions.symbol().call()
        self.token1_symbol = self.token1_contract.functions.symbol().call()
        self.token0_symbol_cex = self.token0_symbol
        self.token1_symbol_cex = self.token1_symbol
        if self.token0_symbol == "WETH":
            self.logger.info("Token0 is WETH, renaming token0_symbol to ETH")
            self.token0_symbol_cex = "ETH"
        if self.token1_symbol == "WETH":
            self.logger.info("Token1 is WETH, renaming token1_symbol to ETH")
            self.token1_symbol_cex = "ETH"

        # Initialize tokenManager
        self.tokenManager = uniswap_hft.uniswap_math.TokenManagement.TokenManager(  #     current_price=self.get_current_price(),
            range_pct=self.range_percentage,
            target_amount=self.token0_capital,
            token0_decimal=min(self.decimal0, self.decimal1),
            token1_decimal=max(self.decimal0, self.decimal1),
            current_price=self.uniswap.get_current_price(),
        )

        # Get token amount from pool address
        self.token0Balance, self.token1Balance = self.update_balance()

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
        self.logger.info(f"Token0 symbol CEX: {self.token0_symbol_cex}")
        self.logger.info(f"Token1 symbol CEX: {self.token1_symbol_cex}")
        self.logger.info(f"Token0 balance: {self.token0Balance}")
        self.logger.info(f"Token1 balance: {self.token1Balance}")

        # Store telegram bot token
        self.telegram_credentials = telegram_credentials
        if self.telegram_credentials is not None:
            self.telegram_bot_token = telegram_credentials["bot_token"]  # type: ignore
            self.telegram_chat_id = telegram_credentials["chat_id"]  # type: ignore
            self.logger.info("Telegram credentials found, testing connection")
            self.send_telegram_message("Uniswap HFT bot started")

        # Try to load position history
        try:
            self.load_position_history()
            self.logger.info("Position history loaded")
        except:
            self.logger.info("Position history not found")

    def send_telegram_message(self, message: str):
        """Send a telegram message"""
        if self.telegram_credentials is not None:
            uniswap_hft.telegram_interface.telegram_handler.send_message(
                bot_token=self.telegram_bot_token,
                chat_id=self.telegram_chat_id,
                text=message,
            )
            self.logger.info(
                f"Telegram message sent to {self.telegram_chat_id}: {message}"
            )

    def store_position_history(self):
        """Store the position history in a json file"""
        with open(self.position_history_path, "w") as f:
            json.dump(self.position_history, f)

    def load_position_history(self):
        """Load the position history from a json file"""
        with open(self.position_history_path, "r") as f:
            self.position_history = json.load(f)

    def get_current_price(self) -> float:
        """Returns the current price of the pool"""
        return self.uniswap.get_current_price()

    def get_current_tick(self) -> int:
        """Returns the current tick of the pool"""
        return self.uniswap.pool.functions.slot0().call()[1]

    def get_current_time_str(self) -> str:
        """Returns the current time as a string"""
        # Save position history
        last_update = time.time()
        last_update_str = datetime.datetime.fromtimestamp(last_update).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return last_update_str

    def parseTxReceiptForTokenId(self, rc: web3.types.TxReceipt) -> int:
        """Parses a tx receipt for the tokenId

        Args:
            rc (web3.types.TxReceipt): web3.types.TxReceipt object instance returned by open_position function

        Returns:
            int: tokenId of Uniswap V3 NFT
        """
        # logs_mint = self.pool_contract.events.Mint().processReceipt(rc)
        # sender = logs_mint[0]["args"]["sender"]

        logs_transfer = (
            self.uniswap.nonFungiblePositionManager.events.Transfer().processReceipt(rc)
        )
        return logs_transfer[0]["args"]["tokenId"]

    def update_balance(self):
        """Updates the balances of the wallet for token0 and token1"""
        token0Balance = self.token0_contract.functions.balanceOf(
            self.wallet_address
        ).call()
        token1Balance = self.token1_contract.functions.balanceOf(
            self.wallet_address
        ).call()

        # If using CEX as source of funds, use ETH balance instead of WETH
        if self.cex_credentials:
            if self.token0_symbol == "WETH":
                token0Balance = self.uniswap.w3.eth.get_balance(self.wallet_address)
            if self.token1_symbol == "WETH":
                token1Balance = self.uniswap.w3.eth.get_balance(self.wallet_address)

        return token0Balance, token1Balance

    def get_existing_required_amounts(self) -> dict:
        # Get existing token amounts
        existing_amount0, existing_amount1 = self.update_balance()

        existing_amount0_decimal = existing_amount0 / 10**self.decimal0
        existing_amount1_decimal = existing_amount1 / 10**self.decimal1

        # Get required token amounts and multiply by 1.01 to account for swap-mint slippage
        required_amount0 = int(self.amount0 * 1.01)
        required_amount1 = int(self.amount1 * 1.01)
        required_amount0_decimal = required_amount0 / 10**self.decimal0
        required_amount1_decimal = required_amount1 / 10**self.decimal1

        return {
            "existing_amount0": existing_amount0,
            "existing_amount0_decimal": existing_amount0_decimal,
            "existing_amount1": existing_amount1,
            "existing_amount1_decimal": existing_amount1_decimal,
            "required_amount0": required_amount0,
            "required_amount0_decimal": required_amount0_decimal,
            "required_amount1": required_amount1,
            "required_amount1_decimal": required_amount1_decimal,
        }

    def deposit_funds_cex(
        self, amount: float, token_symbol: str
    ) -> web3.types.TxReceipt:
        """Method to deposit funds into OKX UniAccount"""
        deposit_address = self.cex_client_subaccount.get_deposit_address(
            currency=token_symbol,
        )
        if len(deposit_address) > 0:
            deposit_address = deposit_address[0]
            self.logger.info(f"Deposit address: {deposit_address}")
            self.logger.info(f"Deposit {token_symbol} amount: {amount}")
        else:
            e_msg = "CEX Deposit address not found"
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise Exception(e_msg)
        # Transfer ETH funds from Metamask to OKX
        if token_symbol == "ETH":
            return self.uniswap.transfer_eth(
                recipient=deposit_address["address"],
                amount=amount,
            )
        # Transfer USDC or WETH funds from Metamask to OKX
        else:
            token_contract = (
                self.uniswap.token0Contract
                if token_symbol == self.uniswap.token0_symbol
                else self.uniswap.token1Contract
            )
            return self.uniswap.transfer_token(
                token_contract=token_contract,
                recipient=deposit_address["address"],
                amount=amount,
            )

    def get_cex_balances(self) -> dict:
        # Find assets in funding balance for self.token0_symbol and self.token1_symbol
        # If not found, continue and check trading balance
        # If found, check if balance is enough
        # If balance is enough, transfer from funding to trading
        # If balance is not enough, check trading balance

        # Example balance response
        # [{'currency': 'USDT', 'balance': 1.0},
        # {'currency': 'USDT', 'balance': 33493.338531196}]

        funding_balance = self.cex_client_subaccount.get_funding_balance()

        cex_existing_amount0 = [
            x for x in funding_balance if x["currency"] == self.token0_symbol_cex
        ]
        cex_existing_amount0 = (
            cex_existing_amount0[0]["balance"] if len(cex_existing_amount0) > 0 else 0
        )
        cex_existing_amount1 = [
            x for x in funding_balance if x["currency"] == self.token1_symbol_cex
        ]
        cex_existing_amount1 = (
            cex_existing_amount1[0]["balance"] if len(cex_existing_amount1) > 0 else 0
        )

        # Transfer amounts from funding to trading if not zero
        if cex_existing_amount0 > 0:
            self.logger.info(
                f"Transfer {cex_existing_amount0} {self.token0_symbol_cex} from funding to trading"
            )
            self.cex_client_subaccount.transfer_within_subaccount(
                from_account="funding",
                to_account="trading",
                currency=self.token0_symbol_cex,
                amount=cex_existing_amount0,
            )

        if cex_existing_amount1 > 0:
            self.logger.info(
                f"Transfer {cex_existing_amount1} {self.token1_symbol_cex} from funding to trading"
            )
            self.cex_client_subaccount.transfer_within_subaccount(
                from_account="funding",
                to_account="trading",
                currency=self.token1_symbol_cex,
                amount=cex_existing_amount1,
            )

        # Check trading balance
        trading_balance = self.cex_client_subaccount.get_trading_balance()

        cex_existing_amount0_decimal = [
            x for x in trading_balance if x["currency"] == self.token0_symbol_cex
        ]
        cex_existing_amount0_decimal = (
            cex_existing_amount0_decimal[0]["balance"]
            if len(cex_existing_amount0_decimal) > 0
            else 0
        )
        cex_existing_amount0 = cex_existing_amount0_decimal * 10**self.decimal0

        cex_existing_amount1_decimal = [
            x for x in trading_balance if x["currency"] == self.token1_symbol_cex
        ]
        cex_existing_amount1_decimal = (
            cex_existing_amount1_decimal[0]["balance"]
            if len(cex_existing_amount1_decimal) > 0
            else 0
        )
        cex_existing_amount1 = cex_existing_amount1_decimal * 10**self.decimal1

        return {
            "cex_existing_amount0": cex_existing_amount0,
            "cex_existing_amount1": cex_existing_amount1,
            "cex_existing_amount0_decimal": cex_existing_amount0_decimal,
            "cex_existing_amount1_decimal": cex_existing_amount1_decimal,
        }

    def get_amounts_okx_blocktrading(self) -> dict:
        current_price = self.get_current_price()
        wallet_amounts = self.get_existing_required_amounts()
        existing_amount0 = wallet_amounts["existing_amount0"]
        existing_amount1 = wallet_amounts["existing_amount1"]
        required_amount0 = wallet_amounts["required_amount0"]
        required_amount1 = wallet_amounts["required_amount1"]

        # Leave ETH in wallet for Tx fees
        if self.token0_symbol == "WETH":
            # Substract 0.1 ETH from existing amount
            existing_amount0 = existing_amount0 - self.uniswap.w3.toWei(0.1, "ether")

        elif self.token1_symbol == "WETH":
            existing_amount1 = existing_amount1 - self.uniswap.w3.toWei(0.1, "ether")

        # TODO: Would be useful to write an amount handler class:
        # Which would know the decimals and return amounts in multiple formats
        # Also could store the different required and existing amounts in the class

        # Calculate required amounts in decimals
        required_amount0_decimal = required_amount0 / 10**self.decimal0
        required_amount1_decimal = required_amount1 / 10**self.decimal1

        # Calculate existing amounts in decimals
        existing_amount0_decimal = existing_amount0 / 10**self.decimal0
        existing_amount1_decimal = existing_amount1 / 10**self.decimal1

        # Add OKX withdrawal fee to required_amount0_decimal
        required_amount0_decimal = required_amount0_decimal + float(
            self.cex_client_subaccount.get_currency(currency=self.token0_symbol_cex)[
                "maxFee"
            ]
        )

        # Add OKX withdrawal fee to required_amount1_decimal
        required_amount1_decimal = required_amount1_decimal + float(
            self.cex_client_subaccount.get_currency(currency=self.token1_symbol_cex)[
                "maxFee"
            ]
        )

        cex_amounts = self.get_cex_balances()
        cex_symbol = f"{self.token0_symbol_cex}-{self.token1_symbol_cex}"
        cex_existing_amount0 = cex_amounts["cex_existing_amount0"]
        cex_existing_amount1 = cex_amounts["cex_existing_amount1"]
        cex_existing_amount0_decimal = cex_amounts["cex_existing_amount0_decimal"]
        cex_existing_amount1_decimal = cex_amounts["cex_existing_amount1_decimal"]

        # Swap amounts in OKX with blocktrading
        diff_amount0_in_token0 = required_amount0_decimal - cex_existing_amount0_decimal
        diff_amount0_in_token1 = (
            required_amount0_decimal - cex_existing_amount0_decimal
        ) * current_price
        diff_amount1_in_token1 = required_amount1_decimal - cex_existing_amount1_decimal
        diff_amount1_in_token0 = (
            required_amount1_decimal - cex_existing_amount1_decimal
        ) / current_price

        # Need to account for spread cost based on maximum spread bps configured
        diff_amount0_in_token0 = diff_amount0_in_token0 * (
            1 + self.cex_client_subaccount.maximum_spread_bps / 100 / 100
        )
        diff_amount0_in_token1 = diff_amount0_in_token1 * (
            1 + self.cex_client_subaccount.maximum_spread_bps / 100 / 100
        )
        diff_amount1_in_token0 = diff_amount1_in_token0 * (
            1 + self.cex_client_subaccount.maximum_spread_bps / 100 / 100
        )
        diff_amount1_in_token1 = diff_amount1_in_token1 * (
            1 + self.cex_client_subaccount.maximum_spread_bps / 100 / 100
        )

        # Need to account for lotsize rounding
        diff_amount0_in_token0 = self.cex_client_subaccount.round_amount_to_lotsize(
            amount=diff_amount0_in_token0, symbol=cex_symbol
        )
        diff_amount1_in_token0 = self.cex_client_subaccount.round_amount_to_lotsize(
            amount=diff_amount1_in_token0, symbol=cex_symbol
        )
        diff_amount0_in_token1 = self.cex_client_subaccount.round_amount_to_lotsize(
            amount=diff_amount0_in_token1, symbol=cex_symbol
        )
        diff_amount1_in_token1 = self.cex_client_subaccount.round_amount_to_lotsize(
            amount=diff_amount1_in_token1, symbol=cex_symbol
        )

        # Cast values to absolute
        diff_amount0_in_token0 = abs(diff_amount0_in_token0)
        diff_amount1_in_token0 = abs(diff_amount1_in_token0)
        diff_amount0_in_token1 = abs(diff_amount0_in_token1)
        diff_amount1_in_token1 = abs(diff_amount1_in_token1)

        # Calculate required amounts for swap
        required_swap_amount_from_token0_decimal = (
            required_amount0_decimal + diff_amount1_in_token0
        )
        required_swap_amount_from_token1_decimal = (
            required_amount1_decimal + diff_amount0_in_token1
        )

        return {
            "required_amount0": required_amount0,
            "required_amount1": required_amount1,
            "required_amount0_decimal": required_amount0_decimal,
            "required_amount1_decimal": required_amount1_decimal,
            "existing_amount0": existing_amount0,
            "existing_amount1": existing_amount1,
            "existing_amount0_decimal": existing_amount0_decimal,
            "existing_amount1_decimal": existing_amount1_decimal,
            "cex_existing_amount0": cex_existing_amount0,
            "cex_existing_amount1": cex_existing_amount1,
            "cex_existing_amount0_decimal": cex_existing_amount0_decimal,
            "cex_existing_amount1_decimal": cex_existing_amount1_decimal,
            "diff_amount0_in_token0": diff_amount0_in_token0,
            "diff_amount0_in_token1": diff_amount0_in_token1,
            "diff_amount1_in_token0": diff_amount1_in_token0,
            "diff_amount1_in_token1": diff_amount1_in_token1,
            "required_swap_amount_from_token0_decimal": required_swap_amount_from_token0_decimal,
            "required_swap_amount_from_token1_decimal": required_swap_amount_from_token1_decimal,
            "cex_symbol": cex_symbol,
        }

    def log_amounts_okx_blocktrading(self, amounts: dict) -> None:
        # Log current price and token amounts
        self.logger.info(
            f"[WALLET] Existing amount for {self.token0_symbol}: {amounts['existing_amount0_decimal']}"
        )
        self.logger.info(
            f"[CEX] Existing amount for {self.token0_symbol}: {amounts['cex_existing_amount0_decimal']}"
        )
        self.logger.info(
            f"[WALLET] Existing amount for {self.token1_symbol}: {amounts['existing_amount1_decimal']}"
        )
        self.logger.info(
            f"[CEX] Existing amount for {self.token1_symbol}: {amounts['cex_existing_amount1_decimal']}"
        )
        self.logger.info(
            f"Required amount for {self.token0_symbol}: {amounts['required_amount0_decimal']}"
        )
        self.logger.info(
            f"Required amount for {self.token1_symbol}: {amounts['required_amount1_decimal']}"
        )

    def wait_for_deposit_okx_blocktrading(
        self,
        amounts: dict,
        watch_key: typing.Literal["cex_existing_amount0", "cex_existing_amount1"],
        max_deadline: int = 300,
        sleep_time: int = 5,
    ) -> None:
        # Check if deposit is done
        deadline = time.time() + max_deadline
        while True:
            cex_amounts = self.get_cex_balances()
            # Check if deposit is done
            if amounts[watch_key] != cex_amounts[watch_key]:
                break
            elif time.time() > deadline:
                e_msg = f"Deposit failed: deadline exceeded ({watch_key})"
                self.send_telegram_message(message=e_msg)
                raise DepositFailed(e_msg)
            else:
                self.logger.info("Waiting for deposit to arrive")
                time.sleep(sleep_time)

    def deposit_amounts_if_needed_okx_blocktrading(
        self,
        amounts: dict,
        deposit_amounts_key: typing.Literal["existing_amount0", "existing_amount1"],
        cex_watch_amounts_key: typing.Literal[
            "cex_existing_amount0", "cex_existing_amount1"
        ],
        token_symbol: str,
        max_deadline: int = 300,
    ) -> str:
        deposit_tx_respone = self.deposit_funds_cex(
            amount=amounts[deposit_amounts_key],
            token_symbol=token_symbol,
        )
        # Store deposit tx hash
        deposit_tx_hash = deposit_tx_respone.transactionHash.hex()  # type: ignore
        self.logger.info(f"Deposit tx hash: {deposit_tx_hash}")

        # Check if deposit is done
        self.wait_for_deposit_okx_blocktrading(
            amounts=amounts,
            watch_key=cex_watch_amounts_key,
            max_deadline=max_deadline,
        )

        return deposit_tx_hash

    def transfer_funds_from_sub_to_main_okx_blocktrading(
        self, amounts, amounts_key, currency
    ) -> dict:
        # Transfer funds to main account
        transfer_response = (
            self.cex_client_main.transfer_from_subaccount_to_mainaccount(
                from_account="trading",
                to_account="funding",
                subaccount_name=self.cex_client_subaccount.account_name,
                currency=currency,
                amount=amounts[amounts_key],
            )
        )
        if transfer_response["code"] != "0":
            e_msg = f"CEX Transfer failed (Subaccount to Main): {transfer_response}"
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise TransferFailed(e_msg)
        self.logger.info(
            f"Transfer funds to main account, {amounts_key}: {transfer_response}"
        )
        return transfer_response

    def wait_for_withdrawal_okx_blocktrading(
        self,
        wallet_amount: float,
        watch_amount: typing.Literal[
            "required_amount0_decimal", "required_amount1_decimal"
        ],
        max_deadline: int = 300,
        sleep_time: int = 5,
    ) -> None:
        # Check if deposit is done
        deadline = time.time() + max_deadline
        while True:
            amount0, amount1 = self.update_balance()
            if watch_amount == "required_amount0_decimal":
                amount = amount0
            elif watch_amount == "required_amount1_decimal":
                amount = amount1
            # Check if deposit is done
            if wallet_amount != amount:
                break
            elif time.time() > deadline:
                e_msg = f"Withdrawal failed: deadline exceeded ({watch_amount})"
                self.send_telegram_message(message=e_msg)
                raise WithdrawTimeout(e_msg)
            else:
                self.logger.info("Waiting for withdrawal to arrive")
                time.sleep(sleep_time)

    def withdraw_amounts_okx_blocktrading(
        self,
        wallet_amount: float,
        amounts: dict,
        amounts_key: typing.Literal[
            "required_amount0_decimal", "required_amount1_decimal"
        ],
        currency: str,
        max_deadline: int = 300,
    ) -> dict:
        # Withdraw funds from OKX to Metamask token0
        withdraw_response = self.cex_client_main.withdraw_from_mainaccount(
            currency=currency,
            amount=amounts[amounts_key],
            destination_address=self.wallet_address,
        )
        if withdraw_response["code"] != "0":
            e_msg = f"Withdraw failed from OKX ({amounts_key}): {withdraw_response}"
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise WithdrawFailed(e_msg)
        self.logger.info(
            f"Withdraw {amounts[amounts_key]} {currency} from OKX to Metamask: {withdraw_response}"
        )
        self.wait_for_withdrawal_okx_blocktrading(
            wallet_amount=wallet_amount,
            watch_amount=amounts_key,
            max_deadline=max_deadline,
        )

        return withdraw_response

    def make_block_trade(self, symbol, direction, amount):
        return self.cex_client_subaccount.make_single_leg_block_trade(
            symbol=symbol,
            side=direction,
            amount=amount,
            act_anonymous=True,
            allow_partial_fill=False,
            deadline=self.cex_client_main.block_trading_deadline,
            maximum_spread_bps=self.cex_client_subaccount.maximum_spread_bps,
        )

    def swap_stable(self, token_swap):
        stable_amount = token_swap["data"][0]["legs"][0]["sz"]
        stable_amount *= token_swap["data"][0]["legs"][0]["px"]
        return self.make_block_trade("USDT-USDC", "buy", stable_amount)

    def handle_no_quote_exception(self, e_msg, amounts, amounts_key):
        e_msg = f"Blocktrade got no quotes({amounts_key}): {e_msg}. Retrying...Routing to USDC, instead of USDT or USDT instead of USDT"
        self.logger.error(e_msg)
        self.send_telegram_message(message=e_msg)

        if amounts["cex_symbol"] == "ETH-USDT":
            symbol = "ETH-USDC"
        elif amounts["cex_symbol"] == "ETH-USDC":
            symbol = "ETH-USDT"
        else:
            raise Exception(f"Unknown symbol: {amounts['cex_symbol']}")

        # Make block trades with USDC or USDT and swap to the other stablecoin
        return_dict = {}
        return_dict["token_swap"] = self.make_block_trade(
            symbol, "buy", amounts[amounts_key]
        )
        return_dict["stable_swap"] = self.swap_stable(return_dict["token_swap"])

        return return_dict

    def block_trade_okx_blocktrading(
        self,
        amounts: dict,
        direction: str,
        amounts_key: str,
    ) -> dict:
        try:
            block_trade_response = self.make_block_trade(
                amounts["cex_symbol"], direction, amounts[amounts_key]
            )
            self.logger.info(block_trade_response)
            return {"token_swap": block_trade_response}

        except uniswap_hft.okex_integration.client.BlockTradingNoQuote as e_msg:
            return self.handle_no_quote_exception(str(e_msg), amounts, amounts_key)

        except (
            uniswap_hft.okex_integration.client.BlockTradingTimeOut,
            uniswap_hft.okex_integration.client.BlockTradingError,
        ) as e_msg:
            e_msg = f"Blocktrade failed({amounts_key}): {e_msg}"
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise BlocktradeFailed(
                e_msg
            )  # TODO: minimum notional error exception handling

    def swap_amounts_okx_blocktrading(self) -> typing.List:
        """
        Flow of funds

        1. Deposit funds into OKX UniAccount if needed
        2. Calculate token amounts for position
        3. Swap amounts in OKX with blocktrading
            - make_single_leg_block_trade on OKX in UniAccount (ETH -> USDT or USDT -> ETH)
            - transfer funds from UniAccount to Main Account
            - withdraw funds from OKX to Metamask
        4. Uniswap position open
        5. Hedge position on OKX in UniAccount
        6. Update position on Uniswap and close position
        7. Deposit funds from Metamask to OKX
            - ETH
            - USDT
        """
        return_values = []
        # Get existing and required token amounts
        amounts = self.get_amounts_okx_blocktrading()
        self.log_amounts_okx_blocktrading(amounts=amounts)

        # Get deposit addresses and deposit funds if needed
        if amounts["existing_amount0"] > 0:
            return_values.append(
                self.deposit_amounts_if_needed_okx_blocktrading(
                    amounts=amounts,
                    deposit_amounts_key="existing_amount0",
                    cex_watch_amounts_key="cex_existing_amount0",
                    token_symbol=self.token0_symbol_cex,
                )
            )

        if amounts["existing_amount1"] > 0:
            return_values.append(
                self.deposit_amounts_if_needed_okx_blocktrading(
                    amounts=amounts,
                    deposit_amounts_key="existing_amount1",
                    cex_watch_amounts_key="cex_existing_amount1",
                    token_symbol=self.token1_symbol_cex,
                )
            )

        # TODO: Remove unnecessary comments
        # cex_amounts = self.get_cex_balances()
        # amounts["cex_existing_amount0"] = cex_amounts["cex_existing_amount0"]
        # amounts["cex_existing_amount1"] = cex_amounts["cex_existing_amount1"]
        # amounts["cex_existing_amount0_decimal"] = cex_amounts[
        #     "cex_existing_amount0_decimal"
        # ]
        # amounts["cex_existing_amount1_decimal"] = cex_amounts[
        #     "cex_existing_amount1_decimal"
        # ]
        # Update CEX amounts after deposit
        amounts = self.get_amounts_okx_blocktrading()
        self.log_amounts_okx_blocktrading(amounts=amounts)

        # Decide if swap is needed
        if (
            amounts["cex_existing_amount0_decimal"]
            >= amounts["required_amount0_decimal"]
            and amounts["cex_existing_amount1_decimal"]
            >= amounts["required_amount1_decimal"]
        ):
            self.logger.info(
                "No swap needed, existing amounts are sufficient, withdraw funds from OKX to Metamask"
            )
        # Swap USDC for ETH (Blocktrade)
        elif (
            amounts["cex_existing_amount0_decimal"]
            >= amounts["required_swap_amount_from_token0_decimal"]
        ):
            self.logger.info(
                f"Blocktrade {amounts['diff_amount1_in_token0']} {self.token0_symbol_cex} for {amounts['diff_amount1_in_token1']} {self.token1_symbol_cex}"
            )
            return_values.append(
                self.block_trade_okx_blocktrading(
                    amounts=amounts,
                    direction="buy",
                    amounts_key="diff_amount1_in_token0",
                )
            )

        # Swap ETH for USDC (Blocktrade)
        elif (
            amounts["cex_existing_amount1_decimal"]
            >= amounts["required_swap_amount_from_token1_decimal"]
        ):
            self.logger.info(
                f"Blocktrade {amounts['diff_amount0_in_token1']} {self.token1_symbol_cex} for {amounts['diff_amount0_in_token0']} {self.token0_symbol_cex}"
            )
            return_values.append(
                self.block_trade_okx_blocktrading(
                    amounts=amounts,
                    direction="sell",
                    amounts_key="diff_amount0_in_token0",
                )
            )

        else:
            e_msg = f"Not enough funds for position, please deposit funds to OKX Subaccount ({self.cex_client_subaccount.account_name}) or wallet ({self.wallet_address})."
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise InsufficientFunds(e_msg)

        # Transfer funds to main account
        return_values.append(
            self.transfer_funds_from_sub_to_main_okx_blocktrading(
                amounts=amounts,
                amounts_key="required_amount0_decimal",
                currency=self.token0_symbol_cex,
            )
        )
        return_values.append(
            self.transfer_funds_from_sub_to_main_okx_blocktrading(
                amounts=amounts,
                amounts_key="required_amount1_decimal",
                currency=self.token1_symbol_cex,
            )
        )

        # Fetch pre-withdraw balances and withdraw funds to Metamask
        wallet_amount0, wallet_amount1 = self.update_balance()

        try:
            return_values.append(
                self.withdraw_amounts_okx_blocktrading(
                    wallet_amount=wallet_amount0,
                    amounts=amounts,
                    amounts_key="required_amount0_decimal",
                    currency=self.token0_symbol_cex,
                )
            )

            return_values.append(
                self.withdraw_amounts_okx_blocktrading(
                    wallet_amount=wallet_amount1,
                    amounts=amounts,
                    amounts_key="required_amount1_decimal",
                    currency=self.token1_symbol_cex,
                )
            )

        except WithdrawTimeout as e:
            self.logger.error(
                "Withdraw timeout, initiating restart of position opening"
            )
            # Start the background process for checking funds arrival
            wallet_amount = (
                wallet_amount0
                if "required_amount0_decimal" in e.args[0]
                else wallet_amount1
            )
            watch_amount = (
                "required_amount0_decimal"
                if "required_amount0_decimal" in e.args[0]
                else "required_amount1_decimal"
            )
            self.background_process = multiprocessing.Process(
                target=self.handle_wait_for_withdrawal_okx_blocktrading_exception,
                args=(
                    wallet_amount,
                    watch_amount,
                    7200,
                    60,
                ),
            )
            self.background_process.start()
            return_values.append(e.args[0])

        return return_values

    def handle_wait_for_withdrawal_okx_blocktrading_exception(
        self,
        wallet_amount: float,
        watch_amount: typing.Literal[
            "required_amount0_decimal", "required_amount1_decimal"
        ],
        max_deadline: int,
        sleep_time: int,
    ) -> None:
        """Waits for the withdrawal to be completed and restart the position opening"""

        # Wait for withdrawal to be completed
        msg = f"Waiting for withdrawal of {watch_amount} to be completed after initial timeout of {max_deadline} seconds."
        self.logger.info(msg)
        self.send_telegram_message(message=msg)
        self.wait_for_withdrawal_okx_blocktrading(
            wallet_amount=wallet_amount,
            watch_amount=watch_amount,
            max_deadline=max_deadline,
            sleep_time=sleep_time,
        )

        # Restart position opening
        msg = "Withdrawal completed, restarting position opening"
        self.logger.info(msg)
        self.send_telegram_message(message=msg)
        self.open_position()

    @pysnooper.snoop()
    def swap_amounts_uniswap(self) -> typing.Union[web3.types.TxReceipt, None]:
        """Swaps the tokens in the wallet for the token with the least amount

        Raises:
            Exception: If both or none of the token amounts are 0

        Returns:
            web3.types.TxReceipt: Transaction receipt of the swap
        """
        # Get existing and required token amounts
        current_price = self.get_current_price()
        wallet_amounts = self.get_existing_required_amounts()
        existing_amount0 = wallet_amounts["existing_amount0"]
        existing_amount1 = wallet_amounts["existing_amount1"]
        required_amount0 = wallet_amounts["required_amount0"]
        required_amount1 = wallet_amounts["required_amount1"]

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
            self.send_telegram_message(message=e_msg)
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
                self.send_telegram_message(message=e_msg)
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
                self.send_telegram_message(message=e_msg)
                raise InsufficientFunds(e_msg)

        else:
            e_msg = "Unexpected error"
            self.logger.error(e_msg)
            self.send_telegram_message(message=e_msg)
            raise Exception(e_msg)

        # Swap tokens
        hex = self.uniswap.swap_token_input(
            token_in_address=input_token,
            token_out_address=output_token,
            amount_in=swapAmount,
            pool_fee=self.pool_fee,
        )

        # Get web3.types.TxReceipt from HexBytes and return
        return self.uniswap.w3.eth.getTransactionReceipt(hex)

    def swap_amounts(
        self,
    ) -> typing.Union[typing.Dict, typing.List, web3.types.TxReceipt, None]:
        """
        Determines the appropriate swap method based on the presence of cex_credentials.
        Executes the swap and returns the result.

        Returns:
            Union[dict, web3.types.TxReceipt, None]: Result of the swap operation
        """
        if self.cex_credentials:
            return self.swap_amounts_okx_blocktrading()
        else:
            return self.swap_amounts_uniswap()

    def update_position(self):
        """Updates the position of the wallet in the pool
        1. Get current price and tick
        2. Only if tick is higher or lower than range close position
            a. Close position
            b. Open position

        """
        # Check if position is open
        if not self.position_history[-1]["open"]:
            self.logger.info("No open position")
            return

        # Get current price and tick
        current_price = self.get_current_price()
        current_tick = self.get_current_tick()

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

    def open_position(self) -> None:
        """Open a position at Uniswap V3
        1. Updates the balances of the wallet for token0 and token1
        2. Swaps the tokens in the wallet for the token with the least amount
        3. Opens a position at Uniswap V3
        4. Saves the position in the position_history list

        Returns:
            web3.types.TxReceipt: Transaction receipt of the open position
        """
        # Get current price
        current_price = self.get_current_price()
        current_tick = self.get_current_tick()
        (tick_low, tick_high) = self.tokenManager.range_from_tick(
            currentTick=current_tick,
            percentage=self.range_percentage,
        )
        range_low = self.tokenManager.tick_to_price(tick=tick_low)
        range_low = 1 / range_low * 10**self.decimal_sum
        range_high = self.tokenManager.tick_to_price(tick=tick_high)
        range_high = 1 / range_high * 10**self.decimal_sum

        # Print range info
        self.logger.info(
            f"Current price: {current_price} | Range: {range_low} - {range_high}"
        )

        # Calculate required amounts
        self.amount0, self.amount1 = self.tokenManager.calculate_amounts(
            current_price=current_price,
        )
        self.amount0 = int(self.amount0 * 10**self.decimal0)
        self.amount1 = int(self.amount1 * 10**self.decimal1)

        # Get token amounts
        self.token0Balance, self.token1Balance = self.update_balance()

        history = {
            "amount0": self.amount0,
            "amount1": self.amount1,
            "token0_symbol": self.token0_symbol,
            "token1_symbol": self.token1_symbol,
            "token0_address": self.token0,
            "token1_address": self.token1,
            "tick_lower": tick_low,
            "tick_upper": tick_high,
            "tick_current": current_tick,
            "tick_initial": current_tick,
            "range_lower": range_low,
            "range_upper": range_high,
            "price_current": current_price,
            "price_initial": current_price,
            "last_update": self.get_current_time_str(),
        }

        # TODO: Approve tokens
        # self.uniswap.approve()

        # Swap tokens
        swap_rc = self.swap_amounts()
        # If swap_rc is a list and Withdrawal failed: deadline exceeded is in the list
        if (
            isinstance(swap_rc, list)
            and "Withdrawal failed: deadline exceeded" in swap_rc
        ):
            # Save position in position_history
            history.update(
                {
                    "tokenID": None,
                    "tx_mint": None,
                    "tx_swap": None,
                    "tx_decrease": None,
                    "tx_collect": None,
                    "tx_burn": None,
                    "is_open": False,
                    "message": "Withdrawal failed: deadline exceeded",
                }
            )
            self.position_history.append(history)
            self.store_position_history()
            return

        # Wrap the token WETH to ETH if using CEX
        if self.cex_credentials:
            if self.token0_symbol == "WETH" or self.token1_symbol == "ETH":
                amount = self.amount0
            elif self.token1_symbol == "WETH" or self.token0_symbol == "ETH":
                amount = self.amount1
            else:
                e_msg = "Unexpected error in wrappping ETH"
                self.send_telegram_message(message=e_msg)
                raise Exception(e_msg)
            self.uniswap.wrap_eth(amount=amount)

        # open position at uniswap
        rc_mint = self.uniswap.mint_liquidity(
            tick_lower=tick_low,
            tick_upper=tick_high,
            amount_0=self.amount0,
            amount_1=self.amount1,
            recipient=self.wallet_address,
        )

        # Get the transaction hash from the receipt objects
        swap_tx_hash = (
            swap_rc.transactionHash.hex() if swap_rc is web3.types.TxReceipt else swap_rc  # type: ignore
        )
        mint_tx_hash = rc_mint.transactionHash.hex()  # type: ignore

        # Get tokenId
        tokenId = self.parseTxReceiptForTokenId(rc=rc_mint)

        # Save position in position_history
        history.update(
            {
                "tokenID": tokenId,
                "tx_mint": mint_tx_hash,
                "tx_swap": swap_tx_hash,
                "tx_decrease": None,
                "tx_collect": None,
                "tx_burn": None,
                "is_open": True,
                "last_update": self.get_current_time_str(),
                "message": "success",
            }
        )

        # Save position history
        self.position_history.append(history)
        self.store_position_history()

        # Notify telegram of new position
        self.send_telegram_message(
            message=f"New position opened\n"
            f"TokenId: {tokenId}\n"
            f"Tokens: {self.token0_symbol}/{self.token1_symbol}\n"
            f"Amount0: {self.amount0/10**self.decimal0} {self.token0_symbol}\n"
            f"Amount1: {self.amount1/10**self.decimal1} {self.token1_symbol}\n"
            f"Price: {current_price}\n"
            f"Range: {range_low} - {range_high}\n"
            f"https://app.uniswap.org/#/pool/{tokenId}"
        )

        # Check if there is a backgroud process running and terminate and join it
        if self.background_process:
            self.background_process.terminate()
            self.background_process.join()

    def close_position(
        self,
    ) -> None:
        """Closes a position in the Uniswap V3 pool
        1. Closes the position at Uniswap V3
        2. Saves the position in the position_history list

        Returns:
            web3.types.TxReceipt: Transaction receipt of the close position
        """
        # Close position at uniswap
        token_id = self.position_history[-1]["tokenID"]

        # Get transaction receipts
        receipt_remove_liquidity = self.uniswap.decrease_liquidity(tokenId=token_id)
        receipt_collect_fees = self.uniswap.collect_fees(tokenId=token_id)

        # Get the transaction hash from the receipt objects
        remove_liquidity_tx_hash = receipt_remove_liquidity.transactionHash.hex()  # type: ignore
        collect_fees_tx_hash = receipt_collect_fees.transactionHash.hex()  # type: ignore

        # Unwrap the token WETH to ETH if using CEX
        if self.cex_credentials:
            weth_amount = self.uniswap.get_token_balances()
            weth_amount = weth_amount[
                "token0_balance" if self.token0_symbol == "WETH" else "token1_balance"
            ]
            self.uniswap.unwrap_weth(amount=weth_amount)

        # Make return tuple
        return_tuple = (receipt_remove_liquidity, receipt_collect_fees, None)

        # Burn the token only if burn_on_close is True
        if self.burn_on_close:
            receipt_burn = self.uniswap.burn_token(tokenId=token_id)
            burn_tx_hash = receipt_burn.transactionHash.hex()  # type: ignore
            self.position_history[-1]["tx_burn"] = burn_tx_hash
            return_tuple = (
                receipt_remove_liquidity,
                receipt_collect_fees,
                receipt_burn,
            )

        # Save position history
        self.position_history[-1]["tx_decrease"] = remove_liquidity_tx_hash
        self.position_history[-1]["tx_collect"] = collect_fees_tx_hash
        self.position_history[-1]["last_update"] = self.get_current_time_str()
        self.position_history[-1]["is_open"] = False

        # Save position history
        self.store_position_history()
