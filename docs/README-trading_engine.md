[Back to Main README](../README.md)

## uniswap_hft.trading_engine

The `TradingEngine` class is an advanced trading bot designed to operate on the Uniswap protocol with high-frequency trading (HFT) strategies. It interfaces with the Ethereum blockchain, as well as the OKEX exchange (and optionally a Telegram bot) to manage, update, and retrieve trading stats in real time.

---

### Class: `TradingEngine`

**Initialization**:
```python
trading_engine = TradingEngine(
    pool_address,
    pool_fee,
    wallet_address,
    wallet_private_key,
    range_percentage,
    usd_capital,
    provider,
    burn_on_close=False,
    debug=False,
    position_history_path="position_history.json",
    cex_credentials=None,
    telegram_credentials=None
)
```

#### Attributes:

- `running`: A boolean indicating whether the trading engine is running.
- `logger`: Logging object for the class.
- `web3_manager`: An instance of the Web3Manager, which interacts with the Ethereum blockchain.

#### Methods:

1. **`start()`**:
   - Starts the trading engine.
   - Opens a position on the Uniswap pool.
   - Returns the most recent position from the position history.

2. **`stop()`**:
   - Stops the trading engine.
   - Closes the position on the Uniswap pool.
   - Returns the most recent position from the position history.

3. **`update_engine()`**:
   - Updates the trading engine's position if it's running.
   - Returns the most recent position from the position history or an empty dictionary if not running.

4. **`update_params(params: dict)`**:
   - Updates trading engine parameters based on provided values in the `params` dictionary.
   - Available parameters include: `range_percentage`, `usd_capital`, `pool_fee`, `pool_address`, `wallet_address`, `wallet_private_key`, and `provider`.

5. **`get_stats()`**:
   - Retrieves the current status of the trading engine.
   - Returns a dictionary with the engine's running status and the latest position from the position history.

---

### Key Parameters:

- **`pool_address`** (`eth_typing.evm.ChecksumAddress`): Address of the Uniswap pool to trade on.

- **`pool_fee`** (`int`): Fee of the pool in percentage (e.g., 3000 for 0.3%).

- **`wallet_address`** (`eth_typing.evm.ChecksumAddress`): Ethereum wallet address used for trading.

- **`wallet_private_key`** (`str`): Private key of the Ethereum wallet.

- **`range_percentage`** (`int`): Trading range for the position in percentage (e.g., 1 for 1%).

- **`usd_capital`** (`int`): Amount in USDC to be used for liquidity provision.

- **`provider`** (`str`): Provider URL for the Ethereum blockchain (e.g., Infura).

- **`burn_on_close`** (`bool`): If True, the position will be burned when closing.

- **`debug`** (`bool`): Enables detailed logging if set to True.

- **`position_history_path`** (`str`): File path to save and retrieve the history of positions.

- **`cex_credentials`** (`dict`): Credentials for the OKEX exchange. Includes credentials for both main and subaccount.

- **`telegram_credentials`** (`dict`): Credentials for Telegram bot notifications (includes bot token and chat ID).

---

### Dependencies:

- `logging`: To maintain logs.
- `typing`: To define complex types and data structures.
- `eth_typing.evm`: To define Ethereum-related types.
- `uniswap_hft.web3_manager.web_manager`: To interact with the Ethereum blockchain.

**Note**: The `TradingEngine` integrates with Ethereum, Uniswap, OKEX, and optionally a Telegram bot. Ensure the required libraries and dependencies are installed and that the Ethereum node or provider is accessible. Ensure you follow best practices for handling private keys and sensitive credentials.