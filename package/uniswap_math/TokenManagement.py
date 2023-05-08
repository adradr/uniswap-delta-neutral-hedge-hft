"""
- Converts between price <-> tick
- Calculates the prices, ticks for range with defined percentages
- Calculates amount of tokens to provide liquidity in
- Calculates Liquidity
- Calculates swap amounts when opening new LP after exiting previous range

"""

import math


class TokenManager:
    def __init__(self, token0, token1):
        self.token0 = token0
        self.token1 = token1
        self.Q96 = 2**96

    """
    Convert a price to a tick, useable by Uniswap V3

    A tick is defined as:
    p(i) = 1.0001^i, where p(i) is the price at tick i,
    take the loq of each side, so the equation becomes
    log(p[i]) = log(1.0001^i)
    log(p[i]) = i * log(1.0001)
    if log is base 1.0001, then the RHS of the equation above becomes i * 1, =>
    log(p[i]) = i * 1 = i (which is the tick),
    so by taking the base 1.0001 logarithm of the current price, we get the tick at that price

    @param price: The price to be converted 
    @returns: The converted tick
    """

    def tick_to_sqrt_price_x_96(self, tick):
        return int(1.0001 ** (tick / 2) * self.Q96)

    def sqrt_price_x_96_to_tick(self, price):
        base = math.sqrt(1.0001)
        p = price / self.Q96
        return math.floor(math.log(p, base))

    def price_to_sqrt_price_x_96(self, price):
        return math.sqrt((self.token0 / self.token1) / price) * Q96

    def sqrt_price_x_96_to_price(self, sqrt_price_x_96):
        return (1 / ((sqrt_price_x_96 / self.Q96) ** 2)) * (self.token0 / self.token1)

    def tickToPrice(self, tick):
        sqrt_price = self.tick_to_sqrt_price_x_96(tick)
        price = self.sqrt_price_x_96_to_price(sqrt_price)
        return price

    def priceToTick(self, price):
        sqrt_price = self.price_to_sqrt_price_x_96(price)
        tick = self.sqrt_price_x_96_to_tick(sqrt_price)
        return tick

    """
    Gives the lower and upper ranges of a soon to be created pool, given a percentage,
    and current price.
    @param percentage: How wide should the bin be to provide liqudity in, 0-100
    @param currentPrice: The current price of the token
    @returns: a tuple, with lowerRange(price), currentPrice(price), upperRange(price), 
    and the corresponding ticks, in that order
    """

    def getRanges(self, percentage, currentPrice):
        upperRange = currentPrice * (1 + (percentage / 100))
        lowerRange = currentPrice * (1 - (percentage / 100))
        upperTick = self.priceToTick(lowerRange)
        lowerTick = self.priceToTick(upperRange)
        currentTick = self.priceToTick(currentPrice)

        return (lowerRange, currentPrice, upperRange, lowerTick, currentTick, upperTick)

    """
    Returns the total liqudity, based on the amount of each token in the pool.
    @param token0Amount: The amount of token0
    @param token1Amount: The amount of token1
    @returns: The total liqudity, L
    """

    def getLiquidity(token0Amount, token1Amount):
        return 0

    """
    Calculates how much of each token you need to provide to create a pool, given your total liqudity.
    The total liquidity is the amount of funds you have, in total, denominated in the other. For example,
    if you have 3 ETH, and 5000 USDC, and 1 ETH = 1500 USDC, then your total liqudity is 9500 USDC.

    @param liqudity: The total value of your funds
    @returns: Amount of each token you need to create the pool
    """

    """
    Calculates how much of asset y we need to create a new pool, given the current price.
    This function calculates the price ranges from the percentage.
    """

    def getMinY(amountX, price, percentage):
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
        return amountY

    """
    Calculates how much of asset x we need to create a new pool, given the current price.
    This function calculates the price ranges from the percentage.
    """

    def getMinX(amountY, price, percentage):
        # Lower range of the price
        pa = price * (1 - (percentage / 100))

        # Upper range of the price
        pb = price * (1 + (percentage / 100))

        # Calculate the liqudity for the top half of the range
        L_y = amountY * (math.sqrt(pb) - math.sqrt(pa))

        # Use L_x to calculate amountY
        amountY = L_y * (math.sqrt(price) - math.sqrt(pa))
        return amountY

    """
    It is possible to calculate the other amount needed from the price range and the amount of one of the tokens.
    Since one of the tokens will always be a smaller amount, it is best to swap a bit more then half to the other, and create the pool 
    that way
    """

    def getSwapAmount(amount):
        return amount * 0.48
