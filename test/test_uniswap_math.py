import math

from uniswap_math import TokenManagement

# Initialize the TokenManager with token0 decimals 6 and token1 decimals 18
token_manager = TokenManagement.TokenManager(6, 18)


def test_initialization():
    assert token_manager.token0_decimal == 6
    assert token_manager.token1_decimal == 18
    assert token_manager.Q96 == 2**96


def test_tick_to_sqrt_price_x_96():
    tick = 80000
    assert (
        token_manager.tick_to_sqrt_price_x_96(tick) == 4324846105750217080405799993344
    )


def test_sqrt_price_x_96_to_tick():
    price = math.sqrt(1000) * token_manager.Q96
    assert token_manager.sqrt_price_x_96_to_tick(price) == 69081


def test_price_to_sqrt_price_x_96():
    price = 1
    assert token_manager.price_to_sqrt_price_x_96(price) == 4.574240095500993e28


def test_sqrt_price_x_96_to_price():
    sqrt_price_x_96 = int(math.sqrt(1000) * token_manager.Q96)
    assert (
        token_manager.sqrt_price_x_96_to_price(sqrt_price_x_96) == 0.0003333333333333333
    )


def test_tick_to_price():
    tick = -80069
    assert token_manager.tick_to_price(tick) == 1000.1321227639803


def test_price_to_tick():
    price = 1000.1321227639803
    assert token_manager.price_to_tick(price) == -80070


def test_calculate_amounts():
    current_price = 5000
    range_low = 4545
    range_high = 5500
    total_amount_token0 = 5000
    assert token_manager.calculate_amounts(
        current_price, range_low, range_high, total_amount_token0
    ) == (5000000000, 998976618347425408)


def test_get_ranges():
    assert token_manager.get_ranges(10, 1000) == (
        909.090909090909,
        1000,
        1100.0,
        -81021,
        -80068,
        -79115,
    )
