from eth_typing.evm import ChecksumAddress
from uniswap_math import TokenManagement
from uniswap_v3.uniswap import Uniswap
from web3 import Web3
from web3.types import TxReceipt


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
        capital_percentage: int,
        provider: str,
    ):
        """Initilizes a pool with an associated wallet and a percentage

        Args:
            poolAddress (ChecksumAddress): The address of the pool where liq. should be provided
            poolFee (int): The fee of the pool (probably can use a hardcoded value)
            walletAddress (ChecksumAddress): The address of the wallet where the funds are located at
            walletPrivateKey (str): The private key of the wallet
            range_percentage (int): How wide the range should be in percentage (e.g. 1 for 1%)
            capital_percentage (int): How much of the funds should be used to provide liquidity
            provider (str): The provider of the blockchain, e.g. infura

        """
        # Set variables
        self.poolAddress = poolAddress
        self.poolFee = poolFee
        self.walletAddress = walletAddress
        self.walletPrivateKey = walletPrivateKey
        self.range_percentage = range_percentage
        self.capital_percentage = capital_percentage
        self.provider = provider

        # Initialize variables
        self.position_history = {}
        """
        position_history = [
            {
                "tick_lower": int,
                "tick_upper": int,
                "tokenID": int,
                "swapTx": TxReceipt,
                "openTx": TxReceipt,
                "closeTx": TxReceipt,
        ]
        """

        # Initialize web3
        self.web3 = Web3(
            Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60})
        )

        # Initialize Uniswap object
        self.uniswap = Uniswap(
            address=self.walletAddress,
            pool_address=self.poolAddress,
            private_key=self.walletPrivateKey,
            web3=self.web3,
            version=3,
        )

        self.decimal0 = self.uniswap.token0_decimals
        self.decimal1 = self.uniswap.token1_decimals
        self.token0 = self.uniswap.token0
        self.token1 = self.uniswap.token1
        self.token0Contract = self.uniswap.token0Contract
        self.token1Contract = self.uniswap.token1Contract
        self.pool_contract = self.uniswap.pool

        # Initialize tokenManager
        self.tokenManager = TokenManagement.TokenManager(
            token0=self.decimal0, token1=self.decimal1
        )

        # Get token amount from pool address
        self.update_balance()

    def update_balance(self):
        """Updates the balances of the wallet for token0 and token1"""
        self.token0Balance = self.token0Contract.functions.balanceOf(
            self.walletAddress
        ).call()
        self.token1Balance = self.token1Contract.functions.balanceOf(
            self.walletAddress
        ).call()

    def get_current_price(self) -> float:
        """Gets the current price of the pool

        Returns:
            float: The current price of the pool
        """
        # Get price of uni-v3 pool
        # The current tick of the pool, i.e. according to the last tick transition that was run.
        # This value may not always be equal to SqrtTickMath getTickAtSqrtRatio(sqrtPriceX96) if the price is on a tick boundary.
        # https://docs.uniswap.org/contracts/v3/reference/core/interfaces/pool/IUniswapV3PoolState

        currentPrice = self.pool_contract.functions.slot0().call()[0]
        # Convert price to decimal
        return self.tokenManager.sqrt_price_x_96_to_price(currentPrice)

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

    def swap_amounts(self) -> TxReceipt:
        """Swaps the tokens in the wallet for the token with the least amount

        Raises:
            Exception: If both or none of the token amounts are 0

        Returns:
            TxReceipt: Transaction receipt of the swap
        """
        # Calculate swap amount
        amount0 = self.token0Balance
        amount1 = self.token1Balance
        if amount0 == 0:
            swapAmount = self.tokenManager.get_swap_amount(amount=amount0)
            input_token = self.token0
            output_token = self.token1
        elif amount1 == 0:
            swapAmount = self.tokenManager.get_swap_amount(amount=amount1)
            input_token = self.token1
            output_token = self.token0
        else:
            raise Exception("Both or none of the token amounts are 0")

        # TODO: need to verify if this swap is correct
        # Swap tokens
        hex = self.uniswap.check_approval_and_make_trade(
            input_token=input_token,
            output_token=output_token,
            qty=swapAmount,
            fee=self.poolFee,
            recipient=self.walletAddress,
        )

        # Get TxReceipt from HexBytes and return
        return self.web3.eth.getTransactionReceipt(hex)

    def update_position(self):
        # Get current price and tick
        currentPrice = self.uniswap.get_raw_price(
            token_in=self.token0, token_out=self.token1
        )
        currentTick = self.tokenManager.price_to_tick(currentPrice)

        # Only if tick is higher or lower than range close position
        if (
            currentTick > self.position_history[-1]["upper_tick"]
            or currentTick < self.position_history[-1]["lower_tick"]
        ):
            # Close position
            tx_receipt = self.close_position(self.position_history[-1]["tokenId"])

            # Update balances
            self.update_balance()

            # Swap tokens
            self.swap_amounts()

            # Open position
            tx_receipt = self.open_position(capitalPercentage=self.capital_percentage)

            # Get tokenId
            tokenId = self.parseTxReceiptForTokenId(rc=tx_receipt)

    def open_position(self, capitalPercentage: int = 100) -> TxReceipt:
        """Opens a position in the Uniswap V3 pool

        Args:
            capitalPercentage (int, optional): Percentage of capital to be used for the position. Defaults to 100.

        Returns:
            TxReceipt: Transaction receipt of the open position
        """
        # Get token amounts
        self.update_balance()
        amount0 = self.token0Balance * (capitalPercentage / 100)
        amount1 = self.token1Balance * (capitalPercentage / 100)

        # Get current price
        currentPrice = self.get_current_price()

        # Calculate ticks from currentPrice
        (
            lowerRange,
            currentPrice,
            upperRange,
            lowerTick,
            currentTick,
            upperTick,
        ) = self.tokenManager.get_ranges(
            percentage=self.range_percentage, currentPrice=currentPrice
        )

        # open position at uniswap
        return self.uniswap.check_approval_and_mint_liquidity(
            pool=self.pool_contract,
            amount_0=amount0,
            amount_1=amount1,
            tick_lower=lowerTick,
            tick_upper=upperTick,
        )

    def close_position(self, tokenId: int) -> TxReceipt:
        """Closes a position in the Uniswap V3 pool

        Args:
            tokenId (int): tokenId of the Uniswap V3 NFT

        Returns:
            TxReceipt: Transaction receipt of the close position
        """
        # Close position at uniswap
        return self.uniswap.close_position(tokenId=tokenId, amount0Min=0, amount1Min=0)
