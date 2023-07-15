import decimal
import logging
import time
import typing

import okx.Account
import okx.BlockTrading
import okx.Funding
import okx.MarketData
import okx.PublicData
import okx.SubAccount


class BlockTradingTimeOut(Exception):
    pass


class BlockTradingError(Exception):
    pass


class BlockTradingNoQuote(Exception):
    pass


# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def only_main_account(func):
    def wrapper(self, *args, **kwargs):
        if self.is_main_account:
            return func(self, *args, **kwargs)
        else:
            raise ValueError(
                "This operation can only be performed from the main account."
            )

    return wrapper


def only_sub_account(func):
    def wrapper(self, *args, **kwargs):
        if not self.is_main_account:
            return func(self, *args, **kwargs)
        else:
            raise ValueError("This operation can only be performed from a sub-account.")

    return wrapper


class OKXClient:
    """
    OKXClient is a wrapper class for the OKX API Wrapper.

    It provides a simple interface for the OKX API Wrapper, which helps to simplyfy the use inside the UniSwap HFT project.
    Main functionalities:
    - Subaccount management (get subaccounts, get balances, transfer between subaccounts)
    - Funding management (get balances, transfer between accounts)
    - Block trading management (get counterparties, create RFQs, execute RFQs)
    - Account management (withdraw, deposit, get balances)

    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        account_name: str,
        chain: typing.Literal[
            "MATIC-Polygon",
            "ETH-ERC20",
            "ETH-Arbitrum One",
            "USDT-Polygon",
            "USDT-ERC20",
            "USDC-ERC20",
            "USDC-Polygon",
            "USDC-Arbitrum One",
        ],
        is_main_account: bool = False,
        maximum_spread_bps: int = 3,
        block_trading_deadline: int = 60,
        is_demo: bool = False,
        debug: bool = False,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.account_name = account_name
        self.chain = chain
        self.is_main_account = is_main_account
        self.maximum_spread_bps = maximum_spread_bps
        self.block_trading_deadline = block_trading_deadline
        self.is_demo = is_demo
        self.okx_flag = "1" if self.is_demo else "0"
        self.debug = debug

        self.subaccount_manager = okx.SubAccount.SubAccountAPI(
            api_key=self.api_key,
            api_secret_key=self.api_secret,
            passphrase=self.passphrase,
            debug=self.debug,
            flag=self.okx_flag,
        )
        self.account_manager = okx.Account.AccountAPI(
            api_key=self.api_key,
            api_secret_key=self.api_secret,
            passphrase=self.passphrase,
            debug=self.debug,
            flag=self.okx_flag,
        )
        self.block_trading_manager = okx.BlockTrading.BlockTradingAPI(
            api_key=self.api_key,
            api_secret_key=self.api_secret,
            passphrase=self.passphrase,
            debug=self.debug,
            flag=self.okx_flag,
        )
        self.funding_manager = okx.Funding.FundingAPI(
            api_key=self.api_key,
            api_secret_key=self.api_secret,
            passphrase=self.passphrase,
            debug=self.debug,
            flag=self.okx_flag,
        )

        self.public_manager = okx.PublicData.PublicAPI(
            api_key=self.api_key,
            api_secret_key=self.api_secret,
            passphrase=self.passphrase,
            debug=self.debug,
            flag=self.okx_flag,
        )

    @only_main_account
    def get_subaccounts(self) -> list:
        return [
            subaccount["subAcct"]
            for subaccount in self.subaccount_manager.get_subaccount_list()["data"]
        ]

    @only_main_account
    def get_subaccount_balances(self, subaccount_id: str) -> list:
        return [
            {
                "currency": asset["ccy"],
                "balance": float(asset["bal"]),
            }
            for asset in self.subaccount_manager.get_funding_balance(
                subAcct=subaccount_id
            )["data"]
        ]

    def get_funding_balance(self):
        return [
            {
                "currency": asset["ccy"],
                "balance": float(asset["availBal"]),
            }
            for asset in self.funding_manager.get_balances()["data"]
        ]

    def get_trading_balance(self):
        return [
            {
                "currency": asset["ccy"],
                "balance": float(asset["availBal"]),
            }
            for asset in self.account_manager.get_account_balance()["data"][0][
                "details"
            ]
        ]

    def get_currency(self, currency: str):
        ccy = self.funding_manager.get_currencies(ccy=currency)["data"]
        # Split first "-" only, ccy is in format "ETH-ERC20" or "USDC-Avalanche C-Chain"
        return [x for x in ccy if x["chain"] == f"{currency}-{self.chain}"][0]

    def get_instrument(
        self,
        instrument: str,
        insturment_type: typing.Literal["SPOT", "MARGIN", "SWAP", "FUTURES"] = "SPOT",
    ):
        instruments = self.public_manager.get_instruments(instType=insturment_type)[
            "data"
        ]
        return [x for x in instruments if x["instId"] == instrument]

    def round_amount(self, input_amount: float, min_rounded_amount: float) -> float:
        input_amount_dec = decimal.Decimal(str(input_amount))
        min_rounded_amount_dec = decimal.Decimal(str(min_rounded_amount))

        rounded_amount_dec = (input_amount_dec / min_rounded_amount_dec).quantize(
            1, rounding=decimal.ROUND_05UP
        ) * min_rounded_amount_dec
        return float(rounded_amount_dec)

    def round_amount_to_lotsize(self, amount: float, symbol: str):
        instrument_info = self.get_instrument(instrument=symbol)
        if instrument_info[0]["lotSz"]:
            lot_size = instrument_info[0]["lotSz"]
            return self.round_amount(input_amount=amount, min_rounded_amount=lot_size)
        else:
            raise Exception(
                "Instrument does not have a lot size: ", symbol, instrument_info
            )

    @only_sub_account
    def transfer_within_subaccount(
        self,
        from_account: typing.Literal["funding", "trading"],
        to_account: typing.Literal["funding", "trading"],
        currency: str,
        amount: float,
        loan_transfer: bool = False,
    ) -> dict:
        """Transfer funds within a subaccount
        Only API keys with Trade privilege can call this endpoint.
        This endpoint supports the transfer of funds between your funding account and trading account, and from the master account to sub-accounts.
        Sub-account can transfer out to master account by default. Need to call "Set Permission Of Transfer Out" to grant privilege first if you want sub-account transferring to another sub-account (sub-accounts need to belong to same master account.)

        Args:
            from_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): type of account to transfer from
            to_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): type of account to transfer to
            currency (str): symbol of currency to transfer
            amount (float): amount to transfer
            loan_transfer (bool, optional): whether to transfer as a loan. Defaults to False.

        Returns:
            dict: response from OKX API
        """
        # Casting OKX values for ease of use
        if from_account == "funding":
            from_account_str = 6
        elif from_account == "trading":
            from_account_str = 18
        if to_account == "funding":
            to_account_str = 6
        elif to_account == "trading":
            to_account_str = 18
        loan_transfer_str = "true" if loan_transfer else "false"

        return self.funding_manager.funds_transfer(
            ccy=currency,
            amt=amount,
            to=to_account_str,
            from_=from_account_str,
            loanTrans=loan_transfer_str,
            # https://www.okx.com/docs-v5/en/#rest-api-funding-funds-transfer
            type="0",  # 0: transfer within account
        )

    @only_main_account
    def transfer_from_subaccount_to_subaccount(
        self,
        from_subaccount_name: str,
        to_subaccount_name: str,
        from_account: typing.Literal["funding", "trading"],
        to_account: typing.Literal["funding", "trading"],
        currency: str,
        amount: float,
        loan_transfer: bool = False,
        omit_risk_check: bool = False,
    ) -> dict:
        """Transfer funds between subaccounts using the master account

        Args:
            from_subaccount_name (str): name of subaccount to transfer from
            to_subaccount_name (str): name of subaccount to transfer to
            from_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            to_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            currency (str): symbol of currency to transfer
            amount (float): amount to transfer
            loan_transfer (bool, optional): to transfer loan. Defaults to False.
            omit_risk_check (bool, optional): skip risk check. Defaults to False.

        Returns:
            dict: response from OKX API
        """
        # Casting OKX values for ease of use
        if from_account == "funding":
            from_account_str = 6
        elif from_account == "trading":
            from_account_str = 18
        if to_account == "funding":
            to_account_str = 6
        elif to_account == "trading":
            to_account_str = 18
        loan_transfer_str = "true" if loan_transfer else "false"
        omit_risk_check_str = "true" if omit_risk_check else "false"

        return self.subaccount_manager.subAccount_transfer(
            ccy=currency,
            amt=amount,
            fromSubAccount=from_subaccount_name,
            toSubAccount=to_subaccount_name,
            to=to_account_str,
            froms=from_account_str,
            loanTrans=loan_transfer_str,
            omitPosRisk=omit_risk_check_str,
        )

    @only_main_account
    def transfer_from_subaccount_to_mainaccount(
        self,
        from_account: typing.Literal["funding", "trading"],
        to_account: typing.Literal["funding", "trading"],
        subaccount_name: str,
        currency: str,
        amount: float,
        loan_transfer: bool = False,
    ) -> dict:
        """Transfer funds from subaccount to master account

        Args:
            from_subaccount_name (str): name of subaccount to transfer from
            to_subaccount_name (str): name of subaccount to transfer to
            from_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            to_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            currency (str): symbol of currency to transfer
            amount (float): amount to transfer
            loan_transfer (bool, optional): to transfer loan. Defaults to False.
            omit_risk_check (bool, optional): skip risk check. Defaults to False.

        Returns:
            dict: response from OKX API
        """
        # Casting OKX values for ease of use
        if from_account == "funding":
            from_account_str = 6
        elif from_account == "trading":
            from_account_str = 18
        if to_account == "funding":
            to_account_str = 6
        elif to_account == "trading":
            to_account_str = 18
        loan_transfer_str = "true" if loan_transfer else "false"

        return self.funding_manager.funds_transfer(
            ccy=currency,
            amt=amount,
            to=to_account_str,
            from_=from_account_str,
            type="2",  # 3: sub-account to master account (Only applicable to APIKey from sub-account)
            # https://www.okx.com/docs-v5/en/#rest-api-funding-funds-transfer
            subAcct=subaccount_name,
            loanTrans=loan_transfer_str,
        )

    @only_main_account
    def transfer_from_mainaccount_to_subaccount(
        self,
        from_account: typing.Literal["funding", "trading"],
        to_account: typing.Literal["funding", "trading"],
        subaccount_name: str,
        currency: str,
        amount: float,
        loan_transfer: bool = False,
    ) -> dict:
        """Transfer funds from subaccount to master account

        Args:
            from_subaccount_name (str): name of subaccount to transfer from
            to_subaccount_name (str): name of subaccount to transfer to
            from_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            to_account (typing.Literal[&quot;funding&quot;, &quot;trading&quot;]): account type to transfer
            currency (str): symbol of currency to transfer
            amount (float): amount to transfer
            loan_transfer (bool, optional): to transfer loan. Defaults to False.
            omit_risk_check (bool, optional): skip risk check. Defaults to False.

        Returns:
            dict: response from OKX API
        """
        # Casting OKX values for ease of use
        if from_account == "funding":
            from_account_str = 6
        elif from_account == "trading":
            from_account_str = 18
        if to_account == "funding":
            to_account_str = 6
        elif to_account == "trading":
            to_account_str = 18
        loan_transfer_str = "true" if loan_transfer else "false"

        return self.funding_manager.funds_transfer(
            ccy=currency,
            amt=amount,
            to=to_account_str,
            from_=from_account_str,
            type="1",  # 3: sub-account to master account (Only applicable to APIKey from sub-account)
            # https://www.okx.com/docs-v5/en/#rest-api-funding-funds-transfer
            subAcct=subaccount_name,
            loanTrans=loan_transfer_str,
        )

    def get_deposit_address(
        self,
        currency: str,
    ) -> list:
        """Returns deposit addresses for a given currency and optionally chain

        Args:
            currency (str): symbol of currency to get deposit addresses for
            chain (typing.Optional[str], optional): Chain to get deposit addresses for. Defaults to None.

        Returns:
            dict: response from OKX API
        """
        # Get all deposit addresses
        deposit_addresses = self.funding_manager.get_deposit_address(
            ccy=currency,
        )
        deposit_addresses = deposit_addresses["data"]
        # Filter those that match the chain and selected is True
        return [
            {
                "address": address["addr"],
                "chain": address["chain"],
            }
            for address in deposit_addresses
            if address["selected"] == True
            and (address["chain"] == f"{currency}-{self.chain}")
        ]

    @only_main_account
    def withdraw_from_mainaccount(
        self,
        currency: str,
        amount: float,
        destination_address: str,
    ) -> dict:
        max_fee = float(self.get_currency(currency)["maxFee"])
        amount = amount - max_fee
        return self.funding_manager.withdrawal(
            ccy=currency,
            amt=amount,
            dest=4,  # on-chain https://www.okx.com/docs-v5/en/#rest-api-funding-withdrawal
            toAddr=destination_address,
            fee=max_fee,
            chain=f"{currency}-{self.chain}",
        )

    @only_sub_account
    def make_single_leg_block_trade(
        self,
        symbol: str,
        amount: float,
        side: typing.Literal["buy", "sell"],
        maximum_spread_bps: int,
        allow_partial_fill: bool = False,
        act_anonymous: bool = False,
        deadline: int = 120,
        tgtCcy: str = "base_ccy",
    ) -> dict:
        allow_partial_fill_str = "true" if allow_partial_fill else "false"
        act_anonymous_str = "true" if act_anonymous else "false"

        # Get the counterparties
        self.counterparties = self.block_trading_manager.counterparties()["data"]
        counterparties = [c["traderCode"] for c in self.counterparties]

        # Create legs
        legs = [
            {
                "instId": symbol,
                # "tdMode":"cross",
                # "ccy": "USDT",
                "sz": amount,
                "side": side,
                "tgtCcy": tgtCcy,  # ccy of the size
            }
        ]

        # Create the RFQ
        rqf_response = self.block_trading_manager.create_rfq(
            counterparties=counterparties,
            anonymous=act_anonymous_str,
            allowPartialExecution=allow_partial_fill_str,
            legs=legs,
        )

        # Get the quote for the RFQ
        if rqf_response["code"] != "0":
            raise BlockTradingError(rqf_response)

        logger.info(f"Created RFQ with ID {rqf_response['data'][0]['rfqId']}")
        rfq_id = rqf_response["data"][0]["rfqId"]
        logger.info(f"Created RFQ with ID {rfq_id}")
        logger.info(f"Waiting for quotes to come in...")
        logger.info(f"Maximum spread: {maximum_spread_bps} bps")
        logger.info(f"Avaialable spreads: ")

        # Start the timer
        start_time = time.time()

        while True:
            quote_response = self.block_trading_manager.get_quotes(rfqId=rfq_id)
            quotes = quote_response["data"]
            sell_side = [q for q in quotes if q["quoteSide"] == "sell"]
            buy_side = [q for q in quotes if q["quoteSide"] == "buy"]

            # Filter out expired quotes, take only active quotes
            sell_side = [q for q in sell_side if q["state"] == "active"]
            buy_side = [q for q in buy_side if q["state"] == "active"]

            # Unpack single legs into a single key
            for q in sell_side:
                q["legs"] = q["legs"][0]
            for q in buy_side:
                q["legs"] = q["legs"][0]

            # Check if we have any quotes
            if len(sell_side) == 0 or len(buy_side) == 0:
                if time.time() - start_time > 60:
                    e_msg = "No quotes received in 60 seconds"
                    logger.info(e_msg)
                    raise BlockTradingNoQuote(e_msg)

            # Calculate the spreads
            spread_bps_list = []
            for sell_quote in sell_side:
                for buy_quote in buy_side:
                    sell_quote_px = float(sell_quote["legs"]["px"])
                    quote_id = (
                        buy_quote["quoteId"]
                        if side == "sell"
                        else sell_quote["quoteId"]
                    )
                    buy_quote_px = float(buy_quote["legs"]["px"])
                    spread_bps = ((sell_quote_px / buy_quote_px) - 1) * 10000
                    spread_bps = round(spread_bps, 2)
                    spread_bps_list.append(
                        (buy_quote_px, spread_bps, sell_quote_px, quote_id)
                    )

            # Print best available spread
            if len(spread_bps_list) > 0:
                best_spread = sorted(spread_bps_list, key=lambda x: x[1])[0]
                logger.info(
                    f"Best spread: {best_spread[1]} bps, buy at {best_spread[0]}, sell at {best_spread[2]}"
                )
            else:
                logger.info(f"No spreads available, waiting...")

            # Filter and sort the spreads
            filtered_spreads = sorted(
                [
                    s
                    for s in spread_bps_list
                    if -maximum_spread_bps <= s[1] <= maximum_spread_bps
                ],
                key=lambda x: x[1],
            )

            # Sleep if no spreads are available or deadline reached
            if len(filtered_spreads) == 0 and time.time() - start_time < deadline:
                time.sleep(1)
                continue
            elif time.time() - start_time > deadline:
                # TODO: Kill the RFQ
                msg = "Deadline reached, no acceptable spread available, returning"
                logger.info(msg)
                raise BlockTradingTimeOut(msg)

            # Take the best spread
            else:
                # Log the best spread
                logger.info(f"{filtered_spreads[0]}")
                # Save the quote ID
                best_spread = filtered_spreads[0]
                quote_id = best_spread[3]

                return self.block_trading_manager.execute_quote(
                    rfqId=rfq_id, quoteId=quote_id, legs=legs
                )


# [
#     {
#         "quoteId": "3ISPA7O",
#         "clQuoteId": "",
#         "rfqId": "3ISPA78",
#         "clRfqId": "",
#         "validUntil": "1687272627121",
#         "state": "active",
#         "reason": "",
#         "traderCode": "WAGMI",
#         "quoteSide": "sell",
#         "legs": [
#             {
#                 "instId": "ETH-USDT",
#                 "side": "buy",
#                 "sz": "1",
#                 "tgtCcy": "base_ccy",
#                 "posSide": "",
#                 "tdMode": "",
#                 "px": "1720.64",
#                 "ccy": "",
#             }
#         ],
#         "tag": "",
#         "cTime": "1687272567121",
#         "uTime": "1687272567000",
#     },
#     {
#         "quoteId": "3ISPA7G",
#         "clQuoteId": "",
#         "rfqId": "3ISPA78",
#         "clRfqId": "",
#         "validUntil": "1687272627100",
#         "state": "active",
#         "reason": "",
#         "traderCode": "WAGMI",
#         "quoteSide": "buy",
#         "legs": [
#             {
#                 "instId": "ETH-USDT",
#                 "side": "buy",
#                 "sz": "1",
#                 "tgtCcy": "base_ccy",
#                 "posSide": "",
#                 "tdMode": "",
#                 "px": "1720.14",
#                 "ccy": "",
#             }
#         ],
#         "tag": "",
#         "cTime": "1687272567100",
#         "uTime": "1687272567000",
#     },
# ]
