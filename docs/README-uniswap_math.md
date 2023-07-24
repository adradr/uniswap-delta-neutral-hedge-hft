[Back to Main README](../README.md)

## uniswap_hft.uniswap_math

The above Python code provides a class called `TokenManager` that deals with the calculation and conversion related to tokens, liquidity, prices, and ticks. Here's a breakdown of the functionality:

### `TokenManager` Class

---

- **Class Purpose**: 
    - Provides utility functions to manage tokens' operations, conversions, and calculations.

- **Attributes**:
    - `token0_decimal`: Decimals of token0
    - `token1_decimal`: Decimals of token1
    - `Q96`: Constant for computations (2 raised to the power 96)
    - `lower_range`, `current_price`, `upper_range`, `lower_tick`, `current_tick`, `upper_tick`: Calculated ranges, prices, and ticks based on percentage and current price.
    - `liquidity`: The amount of liquidity for the provided range.

#### Methods:

- **Initialization (`__init__`)**:
    - Initializes the `TokenManager` class and computes essential attributes such as price ranges, ticks, and liquidity.

- **Conversions**:
    - `tick_to_sqrt_price_x_96`: Converts a tick to a sqrt price X96 for Uniswap V3.
    - `sqrt_price_x_96_to_tick`: Converts a sqrt price to a X96 tick price for Uniswap V3.
    - `price_to_sqrt_price_x_96`: Converts a regular price to a sqrt price.
    - `sqrt_price_x_96_to_price`: Converts a sqrt price to a regular price.
    - `tick_to_price`: Converts a tick to a price.
    - `price_to_tick`: Converts a price to a tick.
    - `price_to_sqrtp`: Converts a price to a sqrt price.

- **Range Calculations**:
    - `get_ranges`: Calculates and returns the lower and upper ranges, current price, and their respective ticks based on a given percentage and current price.
    - `range_from_tick`: Returns the lower and upper ticks based on the current tick and a specified percentage range.

- **Liquidity & Amounts**:
    - Static methods `get_liquidity0`, `get_liquidity1`, `get_liquidity`, `get_amount0`, `get_amount1`, and `get_amounts` are used to calculate the liquidity or amounts based on various factors such as sqrt price, amount0, amount1, and decimals.
    - `calculate_liquidity_amounts`: Calculates amounts of token0 and token1 of an LP within a specified price range.
    - `calculate_amounts`: Wrapper function to get amounts of tokens using the class's `get_amounts` static method.

### Note:

In the provided code, there are mentions of _sqrt price X96_ and _tick_. These terms come from Uniswap V3, a decentralized finance (DeFi) protocol. Uniswap V3 uses a new way to represent prices using "ticks" and "sqrt price X96". The provided methods help in converting between these representations and typical price values.

Also, some methods and calculations may seem intricate. These involve the internal mechanics of how Uniswap V3 pools function and how liquidity is calculated and managed within different price ranges.

The `_description_` placeholders in the docstrings can be replaced with appropriate detailed descriptions for each method's arguments and returns.