import logging
import pytest
from ..package.uniswap_math.TokenManagement import TokenManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ticks = [200240, 200700, 201031]
prices = [2014.29, 1923.74, 1861.10]


def test_manager():
    return TokenManager(10**18, 10**6)


def test_price_to_tick(ticks, prices):
    for idx, price in enumerate(prices):
        assert TokenManager.priceToTick(price) == ticks[idx]


def test_tick_to_price(ticks, prices):
    for idx, tick in enumerate(ticks):
        assert TokenManager.tickToPrice(tick) == prices[idx]
