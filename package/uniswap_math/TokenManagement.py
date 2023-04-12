"""
- Converts between price <-> tick
- Calculates the prices, ticks for range with defined percentages
- Calculates amount of tokens to provide liquidity in
- Calculates Liquidity
- Calculates swap amounts when opening new LP after exiting previous range

"""

import math

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


def priceToTick(price):
    return math.floor(math.log(price, 1.0001))


def adjustedPricesToTicks(price0, price1, decimal):
    p0, p1 = (1 / price0), (1 / price1)
    p0_adj = p0 * math.pow(10, decimal)
    p1_adj = p1 * math.pow(10, decimal)
    print(p0_adj)
    print(p1_adj)
    tick0 = 2 * (math.log(1.0001, math.sqrt(p0_adj)))
    tick1 = 2 * (math.log(1.0001, math.sqrt(p1_adj)))
    return (tick0, tick1)


"""
Convert a tick, used by Uniswap V3 to a price

A tick is defined as:
p(i) = 1.0001^i, where p(i) is the price at tick i,
so the get the price at a tick, we need to raise 1.0001 to the power of i

@param tick: The tick to be converted 
@returns: The converted price
"""


def tickToPrice(tick):
    return math.floor(math.pow(1.0001, tick))


def adjustedPricesFromTick(tick0, tick1, decimal0, decimal1):
    p0 = math.pow(math.pow(1.0001, (tick0 / 2)), 2)
    p1 = math.pow(math.pow(1.0001, (tick1 / 2)), 2)

    p0_adj = p0 * math.pow(10, (decimal0 - decimal1))
    p1_adj = p1 * math.pow(10, (decimal0 - decimal1))

    return ((1 / p0_adj), (1 / p1_adj))


"""
Gives the lower and upper ranges of a soon to be created pool, given a percentage,
and current price.
@param percentage: How wide should the bin be to provide liqudity in, 0-100
@param currentPrice: The current price of the token
@returns: a tuple, with lowerRange(price), currentPrice(price), upperRange(price), 
and the corresponding ticks, in that order
"""


def getRanges(percentage, currentPrice):
    upperRange = currentPrice * (1 + (percentage / 100))
    lowerRange = currentPrice * (1 - (percentage / 100))
    upperTick = priceToTick(upperRange)
    lowerTick = priceToTick(lowerRange)
    currentTick = priceToTick(currentPrice)

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


def getTokenAmount(liquidity):
    return 0


'''
Calculates how much of asset y we need to create a new pool, given the current price.
This function calculates the price ranges from the percentage.
'''
def getSwapAmount(amountX, price, percentage):
    #Lower range of the price
    pa = price * (1 - (percentage / 100))
    print(pa)
    #Upper range of the price
    pb = price * (1 + (percentage / 100))
    print(pb)
    #Calculate the liqudity for the top half of the range
    L_x = amountX * ((math.sqrt(price) * math.sqrt(pb)) / (math.sqrt(pb) - math.sqrt(price)))

    #Use L_x to calculate amountY
    amountY = L_x = (math.sqrt(price) - math.sqrt(pa))
    return amountY



print(adjustedPricesToTicks(2014.29, 1923.74, 12))
print(getSwapAmount(2, 2000, 25))