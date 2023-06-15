import math

from uniswap_hft.uniswap_math import TokenManagement

RANGE_PCT = 10
CURRENT_PRICE = 1000
TARGET_CAPITAL_USD = 1000
TOKEN0_DECIMAL = 6
TOKEN1_DECIMAL = 18

# Initialize the TokenManager with token0 decimals 6 and token1 decimals 18
token_manager = TokenManagement.TokenManager(
    current_price=CURRENT_PRICE,
    range_pct=RANGE_PCT,
    target_amount=TARGET_CAPITAL_USD,
    token0_decimal=TOKEN0_DECIMAL,
    token1_decimal=TOKEN1_DECIMAL,
)


def test_initialization():
    assert token_manager.token0_decimal == TOKEN0_DECIMAL
    assert token_manager.token1_decimal == TOKEN1_DECIMAL
    assert token_manager.Q96 == 2**96
    assert token_manager.current_price == CURRENT_PRICE
    (
        lower_range,
        current_price,
        upper_range,
        lower_tick,
        current_tick,
        upper_tick,
    ) = token_manager.get_ranges(RANGE_PCT, CURRENT_PRICE)
    assert token_manager.lower_range == lower_range
    assert token_manager.current_price == current_price
    assert token_manager.upper_range == upper_range
    assert token_manager.lower_tick == lower_tick
    assert token_manager.current_tick == current_tick
    assert token_manager.upper_tick == upper_tick


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
    assert token_manager.price_to_sqrt_price_x_96(price) == 7.922816251426433e22


def test_sqrt_price_x_96_to_price():
    sqrt_price_x_96 = int(math.sqrt(1000) * token_manager.Q96)
    assert (
        token_manager.sqrt_price_x_96_to_price(sqrt_price_x_96) == 0.0003333333333333333
    )


def test_tick_to_price():
    tick = 207242
    assert token_manager.tick_to_price(tick) == 1000.1019830731274


def test_price_to_tick():
    price = 1000
    assert token_manager.price_to_tick(price) == 207243


def test_calculate_amounts_range_high():
    current_price = 1100
    assert token_manager.calculate_amounts(current_price) == (
        0,
        1024.4044240850747,
    )


def test_calculate_amounts_range_low():
    current_price = 909.09
    assert token_manager.calculate_amounts(current_price) == (
        1.0244044240850747,
        0,
    )


def test_get_ranges():
    assert token_manager.get_ranges(10, 1000) == (
        909.090909090909,
        1000,
        1100.0,
        206290,
        207243,
        208196,
    )
