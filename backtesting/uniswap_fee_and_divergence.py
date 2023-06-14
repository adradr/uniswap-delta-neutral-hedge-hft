import time
import ccxt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from uniswap_hft.uniswap_math import TokenManagement


class DataFetcher:
    def __init__(
        self,
        from_date: str,
        to_date: str,
        symbol="ETH/USDT",
        max_limit=500,
        max_retries=5,
        exchange=ccxt.binance(),
    ):
        self.exchange = exchange
        self.from_date = from_date
        self.to_date = to_date
        self.from_date = self.exchange.parse8601(f"{from_date}T00:00:00Z")
        self.from_date_initial = self.from_date
        self.to_date = self.exchange.parse8601(f"{to_date}T00:00:00Z")
        self.symbol = symbol
        self.max_limit = max_limit
        self.max_retries = max_retries
        self.df = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        self.df.set_index("timestamp", inplace=True)

    def fetch_data(self):
        while self.from_date < self.to_date:  #  type: ignore
            try:
                data = self.exchange.fetch_ohlcv(
                    self.symbol,
                    timeframe="1h",
                    since=self.from_date,
                    limit=self.max_limit,
                )
                if len(data) > 0:
                    temp_df = pd.DataFrame(
                        data,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )
                    temp_df["timestamp"] = pd.to_datetime(
                        temp_df["timestamp"], unit="ms"
                    )
                    temp_df.set_index("timestamp", inplace=True)
                    self.df = pd.concat([self.df, temp_df])
                    self.from_date = self.df.index[-1].value // 10**6  #  type: ignore
                    print(f"Fetched data until:", self.df.index[-1])
                else:
                    break
            except (
                ccxt.ExchangeError,
                ccxt.AuthenticationError,
                ccxt.ExchangeNotAvailable,
                ccxt.RequestTimeout,
            ) as error:
                print(
                    "Got an error",
                    str(error),
                    ", retrying in",
                    self.max_retries,
                    "seconds...",
                )
                time.sleep(self.max_retries)


class HedgeManager:
    def __init__(
        self, initial_price: float, amount: float, exchange_fee: float
    ) -> None:
        self.initial_price = initial_price
        self.amount = amount
        self.exchange_fee = exchange_fee
        self.current_price = initial_price
        self.initial_usd_value = amount * initial_price
        self.current_usd_value = self.initial_usd_value
        self.pnl = 0
        self.fee_cost = self.initial_usd_value * self.exchange_fee

    def update_hedge(self, price: float) -> None:
        self.current_price = price
        self.current_usd_value = self.amount * price
        self.pnl = self.initial_usd_value - self.current_usd_value

    def close_hedge(self, price: float) -> None:
        self.update_hedge(price=price)
        self.fee_cost += self.current_usd_value * self.exchange_fee


class PositionManager:
    def __init__(
        self,
        id: int,
        range_pct: float,
        initial_usd_capital: int,
        price: float,
        fee_per_volume: float,
        exchange_fee: float,
        is_hedged: bool,
        timestamp,
    ):
        """Position manager for Uniswap position and hedge

        Args:
            id (int): index of the position
            range_pct (float): percentage of the range to use in one direction towards the ranges
            initial_usd_capital (int): initial capital in USD to be used for the Uniswap position
            price (float): current USD price of the token
            fee_per_volume (float): how much fee does UniSwap charge per units of volume
            exchange_fee (float): fee percentage charged by the exchange e.g 0.1% = 0.001
            hedge_range_pct (float): what point of the range should be hedged of token0 e.g 100% = lower range amount
            timestamp (_type_): timestamp of the position creation
        """
        self.range_pct = range_pct
        self.id = id
        self.open_price = None
        self.close_price = None
        self.open_timestamp = None
        self.close_timestamp = None
        self.is_open = False
        self.fee = 0
        self.cumm_fee = 0
        self.divergence = 0
        self.divergence_uniswap = 0
        self.divergence_hedge = 0
        self.pnl_uniswap = 0
        self.pnl_hedge = 0
        self.pnl_total_with_fees = 0
        self.amount_token0 = 0
        self.amount_token1 = 0
        self.current_usd_value_uniswap = 0
        self.current_usd_value_hedge = 0
        self.initial_usd_capital = initial_usd_capital
        self.fee_per_volume = fee_per_volume
        self.exchange_fee = exchange_fee
        self.is_hedged = is_hedged
        self.net_usd_capital = 0

        # Calculate initial capital amounts
        if is_hedged:
            self.initial_usd_capital_uniswap = initial_usd_capital / 3 * 2
            self.initial_usd_capital_hedge = initial_usd_capital / 3 * 1
        else:
            self.initial_usd_capital_uniswap = initial_usd_capital
            self.initial_usd_capital_hedge = 0

        # Create Uniswap position
        self.token_manager = TokenManagement.TokenManager(
            current_price=price,
            range_pct=range_pct,
            target_amount=self.initial_usd_capital_uniswap,
            token0_decimal=6,
            token1_decimal=18,
        )
        self.amount_token1, self.amount_token0 = self.token_manager.calculate_amounts(
            current_price=price,
        )
        self.open_position(price=price, timestamp=timestamp)
        self.open_hedge(price=price, exchange_fee=exchange_fee)

    def open_hedge(self, price, exchange_fee):
        amount_token = self.amount_token1 if self.is_hedged else 0
        self.hedge_manager = HedgeManager(
            initial_price=price,
            amount=amount_token,
            exchange_fee=exchange_fee,
        )
        self.initial_usd_capital_hedge = self.hedge_manager.initial_usd_value

    def open_position(self, price, timestamp):
        # Calculate amounts for the new position
        self.open_price = price
        self.open_timestamp = timestamp
        self.is_open = True
        self.initial_usd_capital_uniswap = self.amount_token0 + (
            self.amount_token1 * price
        )

    def update_position(self, price, volume, timestamp):
        # Update token amounts
        self.amount_token1, self.amount_token0 = self.token_manager.calculate_amounts(
            current_price=price,
        )

        # Update current USD values
        self.hedge_manager.update_hedge(price=price)

        # Calculate fee, divergence and update hedge
        self.calculate_fee(volume=volume)
        self.calculate_current_usd_values(price=price)
        self.calculate_divergence()
        self.calculate_pnl()

        # Close and reopen position if price is out of range
        if (
            price < self.token_manager.lower_range
            or price > self.token_manager.upper_range
        ):
            self.hedge_manager.close_hedge(price=price)
            self.close_position(price=price, timestamp=timestamp)

    def close_position(self, price, timestamp):
        self.close_price = price
        self.close_timestamp = timestamp
        self.is_open = False
        self.hedge_manager.close_hedge(price=price)
        self.calculate_current_usd_values(price=price)

    def calculate_pnl(self):
        self.pnl_uniswap = (
            self.current_usd_value_uniswap - self.initial_usd_capital_uniswap
        )
        self.pnl_hedge = self.hedge_manager.pnl
        self.pnl_total = self.pnl_uniswap + self.pnl_hedge
        self.pnl_total_with_fees = (
            self.pnl_total + self.cumm_fee - self.hedge_manager.fee_cost
        )

    def calculate_current_usd_values(self, price):
        self.current_usd_value_hedge = self.hedge_manager.current_usd_value
        self.current_usd_value_uniswap = self.amount_token0 + (
            self.amount_token1 * price
        )
        self.net_usd_capital = (
            self.current_usd_value_uniswap
            + self.current_usd_value_hedge
            + self.cumm_fee
            - self.hedge_manager.fee_cost
        )

    def calculate_fee(self, volume):
        self.cumm_fee += volume * self.fee_per_volume
        self.fee = volume * self.fee_per_volume

    def calculate_divergence(self):
        self.divergence_uniswap = (
            self.current_usd_value_uniswap / self.initial_usd_capital_uniswap
        ) - 1
        self.divergence_hedge = (
            ((self.current_usd_value_hedge / self.initial_usd_capital_hedge) - 1)
            if self.is_hedged
            else 0
        )
        self.divergence = (
            (self.current_usd_value_uniswap + self.current_usd_value_hedge)
            / self.initial_usd_capital
        ) - 1


class DataBacktester:
    def __init__(
        self,
        data,
        capital_usd,
        range_pct,
        fee_per_volume,
        exchange_fee,
        is_hedged,
    ):
        self.data = data
        self.capital_usd = capital_usd
        self.range_pct = range_pct
        self.fee_per_volume = fee_per_volume
        self.exchange_fee = exchange_fee
        self.is_hedged = is_hedged
        self.final_capital = 0
        self.roi = 0
        self.max_dd = 0
        self.number_of_days = 0
        self.number_of_positions = 0
        self.total_fees = 0

        self.positions = []
        self.backtest_df = pd.DataFrame()

    def data_generator(self):
        for index, row in self.data.iterrows():
            yield row, index

    def run(self):
        data_gen = self.data_generator()
        for idx, (ohlcv, timestamp) in enumerate(data_gen):
            # Create new position on the first index
            if idx == 0:
                self.current_position = PositionManager(
                    id=idx,
                    range_pct=self.range_pct,
                    initial_usd_capital=self.capital_usd,
                    price=ohlcv["close"],
                    timestamp=timestamp,
                    fee_per_volume=self.fee_per_volume,
                    exchange_fee=self.exchange_fee,
                    is_hedged=self.is_hedged,
                )

            # Update current position
            self.current_position.update_position(
                price=ohlcv["close"], volume=ohlcv["volume"], timestamp=timestamp
            )

            # Append data to backtest dataframe
            self.backtest_df = pd.concat(
                [
                    self.backtest_df,
                    pd.DataFrame(
                        data={
                            "timestamp": timestamp,
                            "open": ohlcv["open"],
                            "high": ohlcv["high"],
                            "low": ohlcv["low"],
                            "close": ohlcv["close"],
                            "volume": ohlcv["volume"],
                            "id": self.current_position.id,
                            "fee": self.current_position.fee,
                            "fee_cumm": self.current_position.cumm_fee,
                            "divergence": self.current_position.divergence,
                            "pnl_uniswap": self.current_position.pnl_uniswap,
                            "pnl_hedge": self.current_position.pnl_hedge,
                            "pnl_total": self.current_position.pnl_total,
                            "pnl_total_with_fees": self.current_position.pnl_total_with_fees,
                            "current_usd_value_uniswap": self.current_position.current_usd_value_uniswap,
                            "current_usd_value_hedge": self.current_position.current_usd_value_hedge,
                            "net_usd_capital": self.current_position.net_usd_capital,
                            "amount_token0": self.current_position.amount_token0,
                            "amount_token1": self.current_position.amount_token1,
                            "upper_range": self.current_position.token_manager.upper_range,
                            "lower_range": self.current_position.token_manager.lower_range,
                            "open_timestamp": self.current_position.open_timestamp,
                        },
                        index=[0],
                    ),
                ]
            )

            # Append position to list if it's closed
            if not self.current_position.is_open:
                self.positions.append(self.current_position)

                # Create new position
                new_id = self.positions[-1].id + 1
                capital_usd = self.positions[-1].net_usd_capital
                if capital_usd < 0:
                    print("Capital is negative, exiting...")
                    break

                # Create new position
                self.current_position = PositionManager(
                    id=new_id,
                    range_pct=self.range_pct,
                    initial_usd_capital=capital_usd,
                    price=ohlcv["close"],
                    timestamp=timestamp,
                    fee_per_volume=self.fee_per_volume,
                    exchange_fee=self.exchange_fee,
                    is_hedged=self.is_hedged,
                )

        # Set index
        self.backtest_df.set_index("timestamp", inplace=True)
        self.final_capital = self.backtest_df.net_usd_capital.iloc[-1]
        self.roi = DataBacktester.calculate_roi(
            final_capital=self.final_capital, initial_capital=self.capital_usd
        )
        self.max_dd = DataBacktester.max_drawdown(self.backtest_df.net_usd_capital)
        self.total_fees = self.backtest_df.fee.sum()
        self.number_of_positions = len(self.positions)
        self.number_of_days = (
            len(self.backtest_df) / 24
            if self.data.index.inferred_freq == "H"
            else len(self.backtest_df)
            if self.data.index.inferred_freq == "D"
            else None
        )

        return self

    @staticmethod
    def calculate_roi(final_capital, initial_capital):
        return (final_capital / initial_capital * 100) - 100

    @staticmethod
    def max_drawdown(portfolio_values):
        hwm = np.maximum.accumulate(portfolio_values)
        drawdown = (hwm - portfolio_values) / hwm
        max_dd = np.max(drawdown)
        return max_dd

    def plot_position(self, id: int):
        id_df = self.backtest_df[self.backtest_df.id == id]
        ax = id_df.plot(y=["pnl_uniswap", "pnl_hedge"], figsize=(15, 5), grid=True)
        plt.title("PnL of Uniswap and Hedge Positions")
        plt.show()

        fig, ax1 = plt.subplots(figsize=(15, 5))

        # Plot pnl_total and fee on the primary y-axis
        ax1.plot(id_df.index, id_df["pnl_total"], alpha=0.3, color="g", label="PnL")
        ax1.plot(id_df.index, id_df["fee"], alpha=0.3, color="b", label="Fee")
        ax1.set_ylabel("Total PnL and Fees")
        ax1.grid(True)
        ax1.legend()
        # Create a secondary y-axis that shares the same x-axis
        ax2 = ax1.twinx()

        # Plot volume on the secondary y-axis with a line plot
        ax2.plot(id_df.index, id_df["volume"], alpha=0.7, color="r", label="Volume")
        ax2.set_ylabel("Volume")
        ax2.legend()

        # Create the legends for both y-axes
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")
        # Set the title of the plot
        plt.title(
            "Uniswap and Hedge Positions\nPnL is the sum of pnl_uniswap and pnl_hedge\nFee is the cumulative fee earned\nVolume is the USD volume of the pool"
        )

        # Show the plot
        plt.show()

    def plot_backtest(self):
        ax = self.backtest_df.plot(
            y="volume", secondary_y=True, alpha=0.7, figsize=(15, 5), grid=True
        )
        self.backtest_df.plot(y="close", ax=ax, alpha=1)
        plt.title("Volume and Close Price")
        plt.show()

        # Divergence
        (self.backtest_df.divergence * 100).plot(grid=True, figsize=(15, 5))
        plt.title("Divergence at position closes")
        plt.show()

        (self.backtest_df.groupby("id").last().divergence * 100).plot.hist(
            bins=100, figsize=(15, 5), grid=True
        )
        # Add text box with describe output
        describe_output = (
            self.backtest_df.groupby("id").last().divergence * 100
        ).describe()
        text_box = "\n".join(
            [
                f"{statistic}: {value:.3f}"
                for statistic, value in describe_output.items()
            ]
        )

        plt.text(
            0.05,
            0.95,
            text_box,
            transform=plt.gca().transAxes,
            fontsize=10,
            verticalalignment="top",
        )

        plt.title("Distribution of Divergence at position closes")
        plt.show()

        # Current USD Value
        ax = self.backtest_df.plot(
            y=["current_usd_value_uniswap", "current_usd_value_hedge"],
            alpha=0.8,
            figsize=(15, 5),
            grid=False,
        )
        self.backtest_df.plot(y="close", ax=ax, alpha=0.7, secondary_y=True, grid=True)
        plt.title("Current USD Value of Uniswap and Hedge Positions")
        plt.show()

        # PnL
        self.backtest_df.groupby("id").last()["pnl_total_with_fees"].plot(
            figsize=(15, 5), kind="hist", bins=100, grid=True
        )
        # Add text box with describe output
        describe_output = (
            self.backtest_df.groupby("id").last()["pnl_total_with_fees"]
        ).describe()
        text_box = "\n".join(
            [
                f"{statistic}: {value:.3f}"
                for statistic, value in describe_output.items()
            ]
        )
        plt.text(
            0.05,
            0.95,
            text_box,
            transform=plt.gca().transAxes,
            fontsize=10,
            verticalalignment="top",
        )
        plt.title("Final PnL distribution of positions")
        plt.show()

        ax = self.backtest_df.plot(
            y="pnl_total_with_fees",
            alpha=0.8,
            figsize=(15, 5),
            grid=True,
        )
        self.backtest_df.plot(
            y="close",
            ax=ax,
            alpha=0.7,
            secondary_y=True,
            grid=False,
            label="close price",
        )
        plt.title(
            "PnL of Uniswap and Hedge Positions\npnl_total_with_fees = pnl_uniswap + pnl_hedge + uniswap fees - hedge fees"
        )
        plt.show()

        # Fees
        self.backtest_df.fee.cumsum().plot(grid=True, figsize=(15, 5))
        plt.title("Cumulative Fee Paid")
        plt.show()

        # Net Capital
        ax = self.backtest_df.plot(
            y="net_usd_capital",
            alpha=0.8,
            figsize=(15, 5),
            grid=True,
        )
        self.backtest_df.plot(
            y="close",
            ax=ax,
            alpha=0.7,
            secondary_y=True,
            grid=False,
            label="ETH/USDT close price",
        )
        plt.title(
            "Net USD Value of Uniswap and Hedge Positions\nnet_usd_capital = current_usd_value_uniswap + current_usd_value_hedge + uni_fee - hedge_fee"
        )
        plt.show()
