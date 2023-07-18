import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Union

import web3.types
from web3 import Web3
from web3.types import TxReceipt

from .constants import MAX_UINT_128, _netid_to_name
from .util import (_get_eth_simple_cache_middleware, _load_contract,
                   _str_to_addr, nearest_tick)


# Retry decorator
def retry_on_exception(
    retries: int = 3,
    delay: int = 5,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Retry decorator

    Args:
        retries (int, optional): Number of retries. Defaults to 3.
        delay (int, optional): Delay between retries. Defaults to 5.
        exceptions (tuple, optional): Exceptions to catch. Defaults to (Exception,).

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        """Decorator"""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper"""
            for _ in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    print(e)
                    time.sleep(delay)
            return func(*args, **kwargs)

        return wrapper

    return decorator


class Uniswap:
    """Uniswap v3 Python SDK"""

    def __init__(
        self,
        pool_address: str,
        address: str,
        private_key: str,
        provider: str,
        debug: bool = False,
    ) -> None:
        """Initializes the Uniswap SDK

        Args:
            pool_address (str): Address of the pool
            address (str): Address of the wallet
            private_key (str, optional): Private key of the wallet. Defaults to None.
            provider (Web3, optional): Web3 provider. Defaults to None.
            version (int, optional): Uniswap version. Defaults to 3.
            debug (bool, optional): Debug mode. Defaults to False.
        """
        # Validate pool address
        self.pool_address = pool_address
        self.address = address
        self.private_key = private_key
        self.debug = debug
        self.provider = provider

        # Create logger object
        self.logger = logging.getLogger(__name__)

        # Create Web3 object
        self.w3 = Web3(Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60}))
        self.netid = int(self.w3.net.version)
        if self.netid in _netid_to_name:
            self.netname = _netid_to_name[self.netid]
        else:
            raise Exception(f"Unknown netid: {self.netid}")  # pragma: no cover
        self.logger.info(f"Using {self.w3} ('{self.netname}', netid: {self.netid})")
        # Add POA Middleware if network is polygon
        if self.w3.net.version == "137":
            self.w3.middleware_onion.inject(_get_eth_simple_cache_middleware(), layer=0)

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable number
        # The program cannot check for max_approval each time because it decreases
        # with each trade.
        max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(max_approval_hex, 16)
        max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(max_approval_check_hex, 16)

        # Load contracts
        # https://github.com/Uniswap/uniswap-v3-periphery/blob/main/deploys.md
        factory_contract_address = _str_to_addr(
            "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        )
        self.factory_contract = _load_contract(
            self.w3, abi_name="uniswap-v3/factory", address=factory_contract_address
        )
        quoter_addr = _str_to_addr("0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6")
        self.router_address = _str_to_addr("0xE592427A0AEce92De3Edee1F18E0157C05861564")
        self.quoter = _load_contract(
            self.w3, abi_name="uniswap-v3/quoter", address=quoter_addr
        )
        self.router = _load_contract(
            self.w3, abi_name="uniswap-v3/router", address=self.router_address
        )
        self.positionManager_addr = _str_to_addr(
            "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
        )
        self.nonFungiblePositionManager = _load_contract(
            self.w3,
            abi_name="uniswap-v3/nonFungiblePositionManager",
            address=self.positionManager_addr,
        )
        if self.netname == "arbitrum":
            multicall2_addr = _str_to_addr("0x50075F151ABC5B6B448b1272A0a1cFb5CFA25828")
        else:
            multicall2_addr = _str_to_addr("0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696")
        self.multicall2 = _load_contract(
            self.w3, abi_name="uniswap-v3/multicall", address=multicall2_addr
        )

        self.pool = _load_contract(
            self.w3,
            abi_name="uniswap-v3/pool",
            address=pool_address,
        )
        self.token0 = self.pool.functions.token0().call()
        self.token1 = self.pool.functions.token1().call()
        self.token0Contract = _load_contract(
            self.w3, abi_name="uniswap-v3/erc20", address=self.token0
        )
        self.token1Contract = _load_contract(
            self.w3, abi_name="uniswap-v3/erc20", address=self.token1
        )
        self.token0_decimals = self.token0Contract.functions.decimals().call()
        self.token1_decimals = self.token1Contract.functions.decimals().call()
        self.token0_symbol = self.token0Contract.functions.symbol().call()
        self.token1_symbol = self.token1Contract.functions.symbol().call()
        self.Q96 = 2**96

        # Set WETH address
        self.weth_address = None
        if self.token0_symbol == "WETH":
            self.weth_address = self.token0
        elif self.token1_symbol == "WETH":
            self.weth_address = self.token1
        if self.weth_address is not None:
            self.weth = _load_contract(
                self.w3, abi_name="uniswap-v3/weth", address=self.weth_address
            )

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
            self.nonFungiblePositionManager.events.Transfer().processReceipt(rc)
        )
        return logs_transfer[0]["args"]["tokenId"]

    def parseTxReceiptForAmounts(self, rc: web3.types.TxReceipt) -> Dict:
        """Parses a tx receipt for the amounts

        Args:
            rc (web3.types.TxReceipt): web3.types.TxReceipt object instance returned by open_position function

        Returns:
            int: tokenId of Uniswap V3 NFT
        """
        logs_transfer = self.pool.events.Mint().processReceipt(rc)
        return {
            "mint_rc_amount0": logs_transfer[0]["args"]["amount0"],
            "mint_rc_amount1": logs_transfer[0]["args"]["amount1"],
            "mint_rc_amount": logs_transfer[0]["args"]["amount"],
            "mint_rc_tick_lower": logs_transfer[0]["args"]["tickLower"],
            "mint_rc_tick_upper": logs_transfer[0]["args"]["tickUpper"],
        }

    def check_allowance(self):
        """Check allowance for trading on the exchange."""

        # Check allowance for token0
        self.token0_allowance = self.token0Contract.functions.allowance(
            self.address, self.router_address
        ).call()
        if self.token0_allowance < self.max_approval_check_int:
            self.logger.info(
                f"Approving {self.token0} for trading on {self.router_address} (router)"
            )
            self.approve(
                self.token0Contract, self.router_address, self.max_approval_int
            )

        self.token0_allowance = self.token0Contract.functions.allowance(
            self.address, self.nonFungiblePositionManager.address
        ).call()
        if self.token0_allowance < self.max_approval_check_int:
            self.logger.info(
                f"Approving {self.token0} for trading on {self.nonFungiblePositionManager.address} (NFT Manager)"
            )
            self.approve(
                self.token0Contract,
                self.nonFungiblePositionManager.address,
                self.max_approval_int,
            )

        # Check allowance for token1
        self.token1_allowance = self.token1Contract.functions.allowance(
            self.address, self.router_address
        ).call()
        if self.token1_allowance < self.max_approval_check_int:
            self.logger.info(
                f"Approving {self.token1} for trading on {self.router_address} (Router)"
            )
            self.approve(
                self.token1Contract, self.router_address, self.max_approval_int
            )

        self.token1_allowance = self.token1Contract.functions.allowance(
            self.address, self.nonFungiblePositionManager.address
        ).call()
        if self.token1_allowance < self.max_approval_check_int:
            self.logger.info(
                f"Approving {self.token1} for trading on {self.nonFungiblePositionManager.address} (NFT Manager)"
            )
            self.approve(
                self.token1Contract,
                self.nonFungiblePositionManager.address,
                self.max_approval_int,
            )

    def approve(self, token_contract, spender, amount):
        """Approve a spender to spend an amount of a token.

        Args:
            token_contract (web3._utils.datatypes.Contract): The contract of the token.
            spender (str): The spender address.
            amount (int): The amount to approve.
        """
        tx = token_contract.functions.approve(spender, amount).buildTransaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.getTransactionCount(self.address),
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash)

    def _deadline(self) -> int:
        """Get a predefined deadline. 10min by default (same as the Uniswap SDK)."""
        return int(time.time()) + (10 * 60)

    def wrap_eth(self, amount: int):
        """Wrap ETH to WETH.

        Args:
            amount (int): The amount of ETH to wrap.
        """
        if self.weth_address is None:
            raise ValueError("WETH address is not set.")

        tx = self.weth.functions.deposit().buildTransaction(
            {
                "from": self.address,
                "value": amount,
                "nonce": self.w3.eth.getTransactionCount(self.address),
                "gasPrice": self.w3.eth.gasPrice,
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash)

    def unwrap_weth(self, amount: int):
        """Unwrap WETH to ETH.

        Args:
            amount (int): The amount of WETH to unwrap.
        """
        if self.weth_address is None:
            raise ValueError("WETH address is not set.")

        tx = self.weth.functions.withdraw(amount).buildTransaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.getTransactionCount(self.address),
                "gasPrice": self.w3.eth.gasPrice,
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash)

    @retry_on_exception()
    def get_current_price(self) -> float:
        """Gets the current price of the pool

        Returns:
            float: The current price of the pool
        """
        # Get price of uni-v3 pool
        # The current tick of the pool, i.e. according to the last tick transition that was run.
        # This value may not always be equal to SqrtTickMath getTickAtSqrtRatio(sqrtPriceX96) if the price is on a tick boundary.
        # https://docs.uniswap.org/contracts/v3/reference/core/interfaces/pool/IUniswapV3PoolState

        currentPrice = self.pool.functions.slot0().call()[0]
        # Decode the square root price
        sqrt_price = currentPrice / self.Q96

        # square it to get USDC/WETH
        price_usdc_per_weth = sqrt_price**2

        # Invert it to get WETH/USDC
        price_weth_per_usdc = 1 / price_usdc_per_weth

        # Adjust for decimals
        decimal_diff = abs(self.token0_decimals - self.token1_decimals)
        price_weth_per_usdc = price_weth_per_usdc * 10**decimal_diff

        # Map the price to the token0 so always get a USD price
        if self.token0_symbol == "ETH" or self.token0_symbol == "WETH":
            return price_usdc_per_weth * 10**decimal_diff
        elif self.token0_symbol == "USDC":
            return price_weth_per_usdc
        else:
            raise ValueError("Token0 is not ETH or WETH or USDC")

    def get_current_tick(self) -> int:
        """Returns the current tick of the pool"""
        return self.pool.functions.slot0().call()[1]

    def get_token_balances(self):
        """Gets the current token balance of the wallet for token0 and token1"""
        token0_balance = self.token0Contract.functions.balanceOf(self.address).call()
        token1_balance = self.token1Contract.functions.balanceOf(self.address).call()
        return {
            "token0_balance": token0_balance,
            "token1_balance": token1_balance,
            "token0_symbol": self.token0_symbol,
            "token1_symbol": self.token1_symbol,
        }

    def transfer_token(self, token_contract, recipient, amount) -> TxReceipt:
        """Transfer a token to a recipient.

        Args:
            token_contract (web3._utils.datatypes.Contract): The contract of the token.
            recipient (str): The recipient address.
            amount (int): The amount to transfer.
        """
        recipient = Web3.toChecksumAddress(recipient)
        tx = token_contract.functions.transfer(recipient, amount).buildTransaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.getTransactionCount(self.address),
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash)

    def transfer_eth(self, recipient, amount) -> TxReceipt:
        """Transfer ETH to a recipient.

        Args:
            recipient (str): The recipient address.
            amount (int): The amount to transfer.
        """
        recipient = Web3.toChecksumAddress(recipient)
        tx = {
            "from": self.address,
            "to": recipient,
            "value": amount,
            "nonce": self.w3.eth.getTransactionCount(self.address),
            "gasPrice": self.w3.eth.gasPrice,
        }

        # Estimate gas
        tx["gas"] = self.w3.eth.estimateGas(tx)

        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash)

    @retry_on_exception()
    def mint_liquidity(
        self,
        tick_lower: int,
        tick_upper: int,
        amount_0: int,
        amount_1: int,
        recipient: str,
        deadline: Union[int, None] = None,
    ) -> TxReceipt:
        """Mint liquidity in a Uniswap v3 pool

        Returns:
            TxReceipt: Transaction receipt
        """
        fee = self.pool.functions.fee().call()
        assert tick_lower < tick_upper, "Invalid tick range"

        # Set deadline
        if deadline is None:
            deadline = self._deadline()

        # Adjust for tick spacing
        tick_lower = nearest_tick(tick_lower, fee=fee)
        tick_upper = nearest_tick(tick_upper, fee=fee)

        # Create a dict of arguments
        params = {
            "token0": self.token0,
            "token1": self.token1,
            "fee": fee,
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "amount0Desired": amount_0,
            "amount1Desired": amount_1,
            "amount0Min": 0,  # or any other minimum you want to set
            "amount1Min": 0,  # or any other minimum you want to set
            "recipient": recipient,
            "deadline": deadline,
        }

        # Print params line by line
        self.logger.info(f"mint_liquidity params:")
        self.logger.info("\n".join([f"{k}: {v}" for k, v in params.items()]))

        params = (
            self.token0,
            self.token1,
            fee,
            tick_lower,
            tick_upper,
            amount_0,
            amount_1,
            0,  # or any other minimum you want to set
            0,  # or any other minimum you want to set
            recipient,
            deadline,
        )

        # Estimate the gas required for transaction
        gas_estimate = self.nonFungiblePositionManager.functions.mint(
            params
        ).estimateGas({"from": self.address})

        # Increase gas estimate by 10%
        gas_estimate = int(gas_estimate * 1.1)

        # Create the transaction that NonFungiblePositionManager will sign
        nonce = self.w3.eth.getTransactionCount(self.address)
        chain_id = (
            self.w3.eth.chain_id
        )  # using `chain_id` instead of deprecated `chainId`

        transaction = {
            "nonce": nonce,
            "gas": gas_estimate,
            "gasPrice": self.w3.eth.gasPrice,
            "to": self.nonFungiblePositionManager.address,
            "data": self.nonFungiblePositionManager.encodeABI(
                fn_name="mint", args=[params]
            ),
            "chainId": chain_id,
        }

        # Sign the transaction and send it
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @retry_on_exception()
    def decrease_liquidity(self, tokenId: int, deadline: int = 2**64) -> TxReceipt:
        """
        Burns liquidity from the pool by using a tokenId
        """

        # Set deadline
        if deadline is None:
            deadline = self._deadline()

        position = self.nonFungiblePositionManager.functions.positions(tokenId).call()

        # Set up the parameters
        params = {
            "tokenId": tokenId,
            "liquidity": position[7],
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": deadline,
        }

        # Estimate the gas
        gas_estimate = self.nonFungiblePositionManager.functions.decreaseLiquidity(
            params
        ).estimateGas()

        # Increase the gas estimate by 10% to avoid underestimation
        gas_estimate = int(gas_estimate * 1.1)

        # Create the transaction that NonFungiblePositionManager will sign
        nonce = self.w3.eth.getTransactionCount(self.address)
        chain_id = self.w3.eth.chain_id

        transaction = {
            "nonce": nonce,
            "gas": gas_estimate,
            "gasPrice": self.w3.eth.gasPrice,
            "to": self.nonFungiblePositionManager.address,
            "data": self.nonFungiblePositionManager.encodeABI(
                fn_name="decreaseLiquidity", args=[params]
            ),
            "chainId": chain_id,
        }

        # Sign the transaction
        signed_txn = self.w3.eth.account.signTransaction(transaction, self.private_key)

        # Send the transaction
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        # Wait for the transaction to be mined, and get the transaction receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @retry_on_exception()
    def collect_fees(self, tokenId: int):
        """
        Collects fees for the specified tokenId
        """

        # Set up the parameters
        params = {
            "tokenId": tokenId,
            "recipient": self.address,
            "amount0Max": MAX_UINT_128,
            "amount1Max": MAX_UINT_128,
        }

        # Estimate the gas
        gas_estimate = self.nonFungiblePositionManager.functions.collect(
            params
        ).estimateGas()

        # Increase the gas estimate by 10% to avoid underestimation
        gas_estimate = int(gas_estimate * 1.1)

        # Create the transaction that NonFungiblePositionManager will sign
        nonce = self.w3.eth.getTransactionCount(self.address)
        chain_id = self.w3.eth.chain_id

        transaction = {
            "nonce": nonce,
            "gas": gas_estimate,
            "gasPrice": self.w3.eth.gasPrice,
            "to": self.nonFungiblePositionManager.address,
            "data": self.nonFungiblePositionManager.encodeABI(
                fn_name="collect", args=[params]
            ),
            "chainId": chain_id,
        }

        # Sign the transaction
        signed_txn = self.w3.eth.account.signTransaction(transaction, self.private_key)

        # Send the transaction
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        # Wait for the transaction to be mined, and get the transaction receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @retry_on_exception()
    def burn_token(self, tokenId: int):
        """
        Burns liquidity from the pool by using a tokenId
        """
        # Estimate the gas
        gas_estimate = self.nonFungiblePositionManager.functions.burn(
            tokenId
        ).estimateGas()

        # Increase the gas estimate by 10% to avoid underestimation
        gas_estimate = int(gas_estimate * 1.1)

        # Create the transaction that NonFungiblePositionManager will sign
        nonce = self.w3.eth.getTransactionCount(self.address)
        chain_id = self.w3.eth.chain_id

        transaction = {
            "nonce": nonce,
            "gas": gas_estimate,
            "gasPrice": self.w3.eth.gasPrice,
            "to": self.nonFungiblePositionManager.address,
            "data": self.nonFungiblePositionManager.encodeABI(
                fn_name="burn", args=[tokenId]
            ),
            "chainId": chain_id,
        }

        # Sign the transaction
        signed_txn = self.w3.eth.account.signTransaction(transaction, self.private_key)

        # Send the transaction
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        # Wait for the transaction to be mined, and get the transaction receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @retry_on_exception()
    def swap_token_input(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int,
        pool_fee: int = 3000,
        deadline: Union[int, None] = None,
    ):
        """
        Swaps `amount_in` of `token_in` for `token_out` using Uniswap V3
        """

        # Set deadline
        if deadline is None:
            deadline = self._deadline()

        # Set up the parameters
        params = {
            "tokenIn": token_in_address,
            "tokenOut": token_out_address,
            "fee": pool_fee,
            "recipient": self.address,
            "deadline": deadline,
            "amountIn": amount_in,
            "amountOutMinimum": 0,
            "sqrtPriceLimitX96": 0,
        }

        # Create the transaction that the SwapRouter will sign
        nonce = self.w3.eth.getTransactionCount(self.address)
        chain_id = self.w3.eth.chain_id

        transaction = {
            "nonce": nonce,
            "gas": int(8e6),  # gas_estimate,
            "gasPrice": self.w3.eth.gasPrice,
            "to": self.router.address,
            "data": self.router.encodeABI(fn_name="exactInputSingle", args=[params]),
            "chainId": chain_id,
        }

        # Sign the transaction
        signed_txn = self.w3.eth.account.signTransaction(transaction, self.private_key)

        # Send the transaction
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        # Wait for the transaction to be mined, and get the transaction receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
