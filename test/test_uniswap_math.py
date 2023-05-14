
import pytest
from uniswap_math import TokenManagement

ticks = [200240, 200698, 201030]
prices = [2014.29, 1923.93, 1861.11]


@pytest.fixture
def token_manager():
    return TokenManagement.TokenManager(10**18, 10**6)


def test_price_to_tick(token_manager):
    for idx, price in enumerate(prices):
        tick = token_manager.price_to_tick(price)
        assert tick == ticks[idx]


def test_tick_to_price(token_manager):
    for idx, tick in enumerate(ticks):
        price = token_manager.tick_to_price(tick)
        print(price)
        assert price, 2 == prices[idx]
