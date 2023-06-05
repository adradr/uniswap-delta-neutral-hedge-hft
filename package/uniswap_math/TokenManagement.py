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
    def __init__(self, token0_decimal: int, token1_decimal: int):
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
            token0_decimal (int): decimals of token0
            token1_decimal (int): decimals of token1
        """
        self.token0_decimal = token0_decimal
        self.token1_decimal = token1_decimal
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
        return abs(math.floor(math.log(p,base)))

    def price_to_sqrt_price_x_96(self, price: float) -> float:
        """Converts a price to a sqrt price, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            int: The converted sqrt price value
        """
        return math.sqrt((10 ** (self.token0_decimal - self.token1_decimal)) * price) * self.Q96

    def sqrt_price_x_96_to_price(self, sqrt_price_x_96: int) -> float:
        """Converts a sqrt price to a price, useable by Uniswap V3

        Args:
            sqrt_price_x_96 (int): The sqrt price to be converted

        Returns:
            float: The converted price value
        """
        return (1 / ((sqrt_price_x_96 / self.Q96) ** 2)) * (
            self.token0_decimal / self.token1_decimal
        )

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
    
    def range_from_tick(currentTick: int, percentage: int) -> Tuple:
        """Returns a Tuple, with the lower and upper ticks

        Args:
            currentTick(int): The tick corresponding to the current price, obtained from 
                              the Uniswap V3 pool contract
            
            percentage(int): The percentage of the range

        Returns:
            Tuple(int, int): The lower and upper tick of the range
        """
        perc = (percentage / 100) / 2
        deltaTick = int(math.log((1.00 + perc), 1.0001))
        upperTick = currentTick + deltaTick
        lowerTick = currentTick - deltaTick
        return (lowerTick, upperTick)

    def liquidity0(self, amount: int, pa: int, pb: int) -> float:
        """
        Calculates the liquidity value for token0.

        Args:
            amount (float): The amount of tokens.
            pa (float): The price of token A.
            pb (float): The price of token B.

        Returns:
            float: The liquidity value for token0.
        """
        if pa > pb:
            pa, pb = pb, pa
        return (amount * (pa * pb) / self.Q96) / (pb - pa)

    def liquidity1(self, amount: int, pa: int, pb: int) -> float:
        """
        Calculates the liquidity value for token1.

        Args:
            amount (float): The amount of tokens.
            pa (float): The price of token A.
            pb (float): The price of token B.

        Returns:
            float: The liquidity value for token1.
        """
        if pa > pb:
            pa, pb = pb, pa
        return amount * self.Q96 / (pb - pa)

    def calc_amount0(self, liq: int, pa: int, pb: int) -> int:
        """
        Calculates the amount of token0.

        Args:
            liq (float): The liquidity value.
            pa (float): The price of token A.
            pb (float): The price of token B.

        Returns:
            int: The amount of token0.
        """
        if pa > pb:
            pa, pb = pb, pa
        return int(liq * self.Q96 * (pb - pa) / pa / pb)

    def calc_amount1(self, liq: int, pa: int, pb: int) -> int:
        """
        Calculates the amount of token1.

        Args:
            liq (float): The liquidity value.
            pa (float): The price of token A.
            pb (float): The price of token B.

        Returns:
            int: The amount of token1.
        """
        if pa > pb:
            pa, pb = pb, pa
        return int(liq * (pb - pa) / self.Q96)

    def price_to_sqrtp(self, price: float) -> int:
        """Converts a price to a sqrt price, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            float: The converted sqrt price value
        """
        return int(math.sqrt(price) * self.Q96)

    def calculate_amounts(
        self,
        current_price: float,
        range_low: float,
        range_high: float,
        total_token0_amount: float,
    ) -> Tuple[int, int]:
        """Calculates the amounts of token0 and token1.
        Requires to use prices in eth format e.g.: 1800 for $1800

        Args:
            current_price (int): Current price for the pool
            range_low (int): Price range low
            range_high (int): Price range high
            total_token0_amount (int): Total amount of token0

        Returns:
            Tuple[int, int]: Amounts of token1 and token0 in wei
        """
        # calculate sqrt price
        sqrtp_low = self.price_to_sqrtp(range_low)
        sqrtp_cur = self.price_to_sqrtp(current_price)
        sqrtp_upp = self.price_to_sqrtp(range_high)

        # calculate liquidity
        eth = 10**self.token1_decimal
        amount_eth = 1 * eth
        amount_usdc = total_token0_amount * eth

        liq0 = self.liquidity0(amount_eth, sqrtp_cur, sqrtp_upp)
        liq1 = self.liquidity1(amount_usdc, sqrtp_cur, sqrtp_low)
        liq = int(min(liq0, liq1))

        # calculate amount0 and amount1
        amount0 = self.calc_amount0(liq, sqrtp_upp, sqrtp_cur)
        amount1 = self.calc_amount1(liq, sqrtp_low, sqrtp_cur)

        return amount1, amount0

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
        lowerRange = currentPrice / (1 + (percentage / 100))
        upperTick = self.price_to_tick(lowerRange)
        lowerTick = self.price_to_tick(upperRange)
        currentTick = self.price_to_tick(currentPrice)

        return (lowerRange, currentPrice, upperRange, lowerTick, currentTick, upperTick)