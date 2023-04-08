# uniswap-delta-neutral-hedge-hft
Uniswap High Frequency Trading w/ Delta Neutral Positions

## Overview
This is a high frequency trading bot that uses Uniswap and a CEX to trade a delta neutral position. The bot will enter a Uniswap position in a crypto & stablecoin pool for a tight range while opening a short position in equivalent amount of the token side. The bot will also rebalance the position if the price of the token moves out of the range.

To rebalance the position, the bot close the Uniswap position and the CEX position and then reopens them at the new price, while collecting fees in the process.

## Requirements
- Python 3.9
- API keys for a CEX (e.g. Binance, FTX, etc.) compatible with ccxt
- EVM compatible private key (e.g. Ethereum, Polygon, etc.)

## Package
### uniswap-hft
#### uniswap_hft.uniswap_math

This module contains the math functions used to calculate the Uniswap token amounts, tick prices

#### uniswap_hft.trading_engine

This module contains the TradingEngine class which is the main class of the bot. It contains the logic to open and close positions, rebalance positions, and calculate the position size.

#### uniswap_hft.slack_interface

This module contains the SlackInterface class which is used to listen for messages from Slack and send messages to Slack to interact with the bot.