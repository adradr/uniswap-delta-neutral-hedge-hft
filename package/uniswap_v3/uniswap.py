import time
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from web3 import Web3
from web3.types import TxReceipt

from .util import (
    _addr_to_str,
    _get_eth_simple_cache_middleware,
    _load_contract,
    _load_contract_erc20,
    _str_to_addr,
    _validate_address,
    chunks,
    encode_sqrt_ratioX96,
    is_same_address,
    nearest_tick,
)
from .constants import (
    ETH_ADDRESS,
    MAX_TICK,
    MAX_UINT_128,
    MIN_TICK,
    WETH9_ADDRESS,
    _netid_to_name,
    _tick_bitmap_range,
    _tick_spacing,
)


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
        self.Q96 = 2**96

    def _deadline(self) -> int:
        """Get a predefined deadline. 10min by default (same as the Uniswap SDK)."""
        return int(time.time()) + 10 * 60

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
        return price_weth_per_usdc

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

        # Estimate the gas required for transaction
        gas_estimate = self.nonFungiblePositionManager.functions.mint(
            params
        ).estimateGas({"from": self.address})

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

    def burn_token(self, tokenId: int):
        """
        Burns liquidity from the pool by using a tokenId
        """
        # Estimate the gas
        gas_estimate = self.nonFungiblePositionManager.functions.burn(
            tokenId
        ).estimateGas()

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
