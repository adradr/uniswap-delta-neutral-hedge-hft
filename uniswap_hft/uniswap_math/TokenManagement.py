"""
- Converts between price <-> tick
- Calculates the prices, ticks for range with defined percentages
- Calculates amount of tokens to provide liquidity in
- Calculates Liquidity
- Calculates swap amounts when opening new LP after exiting previous range
"""

import math
import typing
from typing import Tuple

import numpy


class TokenManager:
    def __init__(
        self,
        current_price: float,
        range_pct: float,
        target_amount: float,
        token0_decimal: int,
        token1_decimal: int,
    ):
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

        # Calculate ranges
        (
            self.lower_range,
            self.current_price,
            self.upper_range,
            self.lower_tick,
            self.current_tick,
            self.upper_tick,
        ) = self.get_ranges(
            percentage=range_pct,
            current_price=current_price,
        )

        # Calculate liquidity
        amount0, amount1 = self.calculate_liquidity_amounts(
            range_low_price=self.lower_range,
            range_high_price=self.upper_range,
            current_price=current_price,
            target_amount=target_amount,
        )

        self.liquidity = self.get_liquidity(
            asqrt=current_price,
            asqrtA=self.lower_range,
            asqrtB=self.upper_range,
            amount0=amount0,
            amount1=amount1,
            decimal0=self.token0_decimal,
            decimal1=self.token1_decimal,
        )

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
        return int(abs(math.log(p, base)))

    def price_to_sqrt_price_x_96(self, price: float) -> float:
        """Converts a price to a sqrt price, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            int: The converted sqrt price value
        """
        return (
            math.sqrt((10 ** (self.token0_decimal - self.token1_decimal)) * price)
            * self.Q96
        )

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
        tick_basis_constant = 1.0001
        decimal_diff = self.token0_decimal - self.token1_decimal
        return 1 / ((tick_basis_constant**tick) * (10**decimal_diff))

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

    def price_to_sqrtp(self, price: float) -> int:
        """Converts a price to a sqrt price, useable by Uniswap V3

        Args:
            price (float): The price to be converted

        Returns:
            float: The converted sqrt price value
        """
        return int(math.sqrt(price) * self.Q96)

    def get_ranges(
        self, percentage: float, current_price: float
    ) -> typing.Tuple[float, float, float, int, int, int]:
        """
        Gives the lower and upper ranges of a soon to be created pool, given a percentage,
        and current price.

        Args:
            percentage (int): How wide should the bin be to provide liqudity in, 0-100
            current_price (float): The current price of the token

        Returns:
            typing.Tuple[float, float, float, int, int, int]: a tuple, containing the lower range,
            current price, upper range, lower tick, current tick, upper tick
        """
        upper_range = current_price * (1 + (percentage / 100))
        lower_range = current_price / (1 + (percentage / 100))
        upper_tick = self.price_to_tick(lower_range)
        lower_tick = self.price_to_tick(upper_range)
        current_tick = self.price_to_tick(current_price)

        return (
            lower_range,
            current_price,
            upper_range,
            lower_tick,
            current_tick,
            upper_tick,
        )

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

    # Use 'get_liquidity' function to calculate liquidity as a function of amounts and price range
    @staticmethod
    def get_liquidity0(sqrtA, sqrtB, amount0, decimals):
        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        liquidity = amount0 / (
            (2**96 * (sqrtB - sqrtA) / sqrtB / sqrtA) / 10**decimals
        )
        return liquidity

    @staticmethod
    def get_liquidity1(sqrtA, sqrtB, amount1, decimals):
        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        liquidity = amount1 / ((sqrtB - sqrtA) / 2**96 / 10**decimals)
        return liquidity

    @staticmethod
    def get_liquidity(asqrt, asqrtA, asqrtB, amount0, amount1, decimal0, decimal1):
        sqrt = (numpy.sqrt(asqrt * 10 ** (decimal1 - decimal0))) * (2**96)
        sqrtA = numpy.sqrt(asqrtA * 10 ** (decimal1 - decimal0)) * (2**96)
        sqrtB = numpy.sqrt(asqrtB * 10 ** (decimal1 - decimal0)) * (2**96)

        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        if sqrt <= sqrtA:
            liquidity0 = TokenManager.get_liquidity0(sqrtA, sqrtB, amount0, decimal0)
            return liquidity0
        elif sqrt < sqrtB and sqrt > sqrtA:
            liquidity0 = TokenManager.get_liquidity0(sqrt, sqrtB, amount0, decimal0)
            liquidity1 = TokenManager.get_liquidity1(sqrtA, sqrt, amount1, decimal1)
            liquidity = liquidity0 if liquidity0 < liquidity1 else liquidity1
            return liquidity

        else:
            liquidity1 = TokenManager.get_liquidity1(sqrtA, sqrtB, amount1, decimal1)
            return liquidity1

    @staticmethod
    def get_amount0(sqrtA, sqrtB, liquidity, decimals):
        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        amount0 = (
            liquidity * 2**96 * (sqrtB - sqrtA) / sqrtB / sqrtA
        ) / 10**decimals

        return amount0

    @staticmethod
    def get_amount1(sqrtA, sqrtB, liquidity, decimals):
        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        amount1 = liquidity * (sqrtB - sqrtA) / 2**96 / 10**decimals

        return amount1

    @staticmethod
    def get_amounts(asqrt, asqrtA, asqrtB, liquidity, decimal0, decimal1):
        sqrt = (numpy.sqrt(asqrt * 10 ** (decimal1 - decimal0))) * (2**96)
        sqrtA = numpy.sqrt(asqrtA * 10 ** (decimal1 - decimal0)) * (2**96)
        sqrtB = numpy.sqrt(asqrtB * 10 ** (decimal1 - decimal0)) * (2**96)

        if sqrtA > sqrtB:
            (sqrtA, sqrtB) = (sqrtB, sqrtA)

        if sqrt <= sqrtA:
            amount0 = TokenManager.get_amount0(sqrtA, sqrtB, liquidity, decimal0)
            return amount0, 0

        elif sqrt < sqrtB and sqrt > sqrtA:
            amount0 = TokenManager.get_amount0(sqrt, sqrtB, liquidity, decimal0)

            amount1 = TokenManager.get_amount1(sqrtA, sqrt, liquidity, decimal1)

            return amount0, amount1

        else:
            amount1 = TokenManager.get_amount1(sqrtA, sqrtB, liquidity, decimal1)
            return 0, amount1

    def calculate_liquidity_amounts(
        self,
        range_low_price: float,
        range_high_price: float,
        current_price: float,
        target_amount: float,
    ) -> typing.Tuple[float, float]:
        """Calculates amounts of token0 and token1 of an LP with range [range_low_price, range_high_price] at a given price

        Args:
            range_low_price (float): Range minimum
            range_high_price (float): Range maximum
            current_price (float): Current price
            target_amount (int): Target amount of investment

        Returns:
            typing.Tuple[float, float]: Returns the amounts of token0, token1
        """
        SMIN = numpy.sqrt(
            range_low_price * 10 ** (self.token1_decimal - self.token0_decimal)
        )
        SMAX = numpy.sqrt(
            range_high_price * 10 ** (self.token1_decimal - self.token0_decimal)
        )

        sqrt0 = numpy.sqrt(
            current_price * 10 ** (self.token1_decimal - self.token0_decimal)
        )

        if SMIN < sqrt0 < SMAX:
            deltaL = target_amount / (
                (sqrt0 - SMIN)
                + ((1 / sqrt0) - (1 / SMAX))
                * (current_price * 10 ** (self.token1_decimal - self.token0_decimal))
            )
            amount1 = deltaL * (sqrt0 - SMIN)
            amount0 = (
                deltaL
                * ((1 / sqrt0) - (1 / SMAX))
                * 10 ** (self.token1_decimal - self.token0_decimal)
            )
        elif sqrt0 < SMIN:
            deltaL = target_amount / ((1 / SMIN - 1 / SMAX) * current_price)
            amount1 = 0
            amount0 = deltaL * (1 / SMIN - 1 / SMAX)
        else:
            deltaL = target_amount / (SMAX - SMIN)
            amount1 = deltaL * (SMAX - SMIN)
            amount0 = 0

        return amount0, amount1

    def calculate_amounts(
        self,
        current_price: float,
    ) -> typing.Tuple[float, float]:
        return TokenManager.get_amounts(
            asqrt=current_price,
            asqrtA=self.lower_range,
            asqrtB=self.upper_range,
            liquidity=self.liquidity,
            decimal0=self.token0_decimal,
            decimal1=self.token1_decimal,
        )
