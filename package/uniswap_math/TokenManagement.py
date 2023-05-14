"""
- Converts between price <-> tick
- Calculates the prices, ticks for range with defined percentages
- Calculates amount of tokens to provide liquidity in
- Calculates Liquidity
- Calculates swap amounts when opening new LP after exiting previous range
"""

import math
from typing import Tuple


class TokenManager:
    def __init__(self, token0: int, token1: int):
        """Initializes the TokenManager class

        Additional information:
            A tick is defined as:
            p(i) = 1.0001^i, where p(i) is the price at tick i,
            take the loq of each side, so the equation becomes
            log(p[i]) = log(1.0001^i)
            log(p[i]) = i * log(1.0001)
            if log is base 1.0001, then the RHS of the equation above becomes i * 1, =>
            log(p[i]) = i * 1 = i (which is the tick),
            so by taking the base 1.0001 logarithm of the current price, we get the tick at that price

        Args:
            token0 (int): decimals of token0
            token1 (int): decimals of token1
        """
        self.token0 = token0
        self.token1 = token1
        self.Q96: int = 2**96

    def tick_to_sqrt_price_x_96(self, tick: int) -> int:
        """Converts a tick to a sqrt price X96, useable by Uniswap V3

        Args:
            tick (int): _description_

        Returns:
            int: _description_
        """
        return int(1.0001 ** (tick / 2) * self.Q96)

    def sqrt_price_x_96_to_tick(self, price: float) -> int:
        """Converts a sqrt price to a X96 tick price, useable by Uniswap V3

        Args:
            price (float): _description_

        Returns:
            int: _description_
        """
        base = math.sqrt(1.0001)
        p = price / self.Q96
        return math.floor(math.log(p, base))

    def price_to_sqrt_price_x_96(self, price: float) -> int:
        """Converts a price to a sqrt price, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            int: The converted sqrt price value
        """
        return int(math.sqrt((self.token0 / self.token1) / price) * self.Q96)

    def sqrt_price_x_96_to_price(self, sqrt_price_x_96: int) -> float:
        """Converts a sqrt price to a price, useable by Uniswap V3

        Args:
            sqrt_price_x_96 (int): The sqrt price to be converted

        Returns:
            float: The converted price value
        """
        return (1 / ((sqrt_price_x_96 / self.Q96) ** 2)) * (self.token0 / self.token1)

    def tick_to_price(self, tick: int) -> float:
        """Converts a tick to a price, useable by Uniswap V3

        Args:
            tick (int): The tick to be converted

        Returns:
            float: The converted price value
        """
        sqrt_price = self.tick_to_sqrt_price_x_96(tick)
        price = self.sqrt_price_x_96_to_price(sqrt_price)
        return price

    def price_to_tick(self, price: float) -> int:
        """Converts a price to a tick, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            int: The converted tick value
        """
        sqrt_price = self.price_to_sqrt_price_x_96(price)
        tick = self.sqrt_price_x_96_to_tick(sqrt_price)
        return tick

    def get_ranges(
        self, percentage: int, currentPrice: float
    ) -> Tuple[float, float, float, int, int, int]:
        """
        Gives the lower and upper ranges of a soon to be created pool, given a percentage,
        and current price.

        Args:
            percentage (int): How wide should the bin be to provide liqudity in, 0-100
            currentPrice (float): The current price of the token

        Returns:
            Tuple[float, float, float, int, int, int]: a tuple, with lowerRange(price), currentPrice(price), upperRange(price),
        """
        upperRange = currentPrice * (1 + (percentage / 100))
        lowerRange = currentPrice * (1 - (percentage / 100))
        upperTick = self.priceToTick(lowerRange)
        lowerTick = self.priceToTick(upperRange)
        currentTick = self.priceToTick(currentPrice)

        return (lowerRange, currentPrice, upperRange, lowerTick, currentTick, upperTick)

    def get_liquidity(self, token0Amount: int, token1Amount: int) -> int:
        """Returns the total liqudity, based on the amount of each token in the pool.

        Args:
            token0Amount (int): The amount of token0
            token1Amount (int): The amount of token1

        Returns:
            int: The total liqudity, L
        """

        return 0

    def get_minY(self, amountX: int, price: float, percentage: int) -> int:
        """
        Calculates how much of asset y we need to create a new pool, given the current price.
        This function calculates the price ranges from the percentage.

        Args:
            amountX (int):  Amount of token X
            price (float): Current price of token X
            percentage (int): Percentage of the price range (0-100)

        Returns:
            int: Amount of token Y
        """

        # Lower range of the price
        pa = price * (1 - (percentage / 100))

        # Upper range of the price
        pb = price * (1 + (percentage / 100))

        # Calculate the liqudity for the top half of the range
        L_x = amountX * (
            (math.sqrt(price) * math.sqrt(pb)) / (math.sqrt(pb) - math.sqrt(price))
        )

        # Use L_x to calculate amountY
        amountY = L_x * (math.sqrt(price) - math.sqrt(pa))
        return int(amountY)

    def get_minX(self, amountY: int, price: float, percentage: int) -> int:
        """
        Calculates how much of asset x we need to create a new pool, given the current price.
        This function calculates the price ranges from the percentage.

        Args:
            amountY (int): Amount of token Y
            price (float): Current price of token X
            percentage (int): Percentage of the price range (0-100)

        Returns:
            int: Amount of token X
        """

        # Lower range of the price
        pa = price * (1 - (percentage / 100))

        # Upper range of the price
        pb = price * (1 + (percentage / 100))

        # Calculate the liqudity for the top half of the range
        L_y = amountY * (math.sqrt(pb) - math.sqrt(pa))

        # Use L_x to calculate amountY
        amountX = L_y * (math.sqrt(price) - math.sqrt(pa))
        return int(amountX)

    def get_swap_amount(self, amount: int) -> int:
        """
        It is possible to calculate the other amount needed from the price range and the amount of one of the tokens.
        Since one of the tokens will always be a smaller amount, it is best to swap a bit more then half to the other, and create the pool
        that way

        Args:
            amount (int): Amount of token X

        Returns:
            int: Amount of token to swap
        """
        return int(amount * 0.48)


# Do we need this?
# """
# Calculates how much of each token you need to provide to create a pool, given your total liqudity.
# The total liquidity is the amount of funds you have, in total, denominated in the other. For example,
# if you have 3 ETH, and 5000 USDC, and 1 ETH = 1500 USDC, then your total liqudity is 9500 USDC.

# @param liqudity: The total value of your funds
# @returns: Amount of each token you need to create the pool
# """
