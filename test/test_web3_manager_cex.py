from unittest.mock import MagicMock

import pytest

import uniswap_hft.okex_integration.client
from uniswap_hft.web3_manager.web_manager import (DepositFailed,
                                                  InsufficientFunds,
                                                  TransferFailed, Web3Manager,
                                                  WithdrawTimeout)


@pytest.fixture
def web3_manager_cex():
    return Web3Manager(
        pool_address="0x45dda9cb7c25131df268515131f647d726f50608",  #  type: ignore
        pool_fee=500,
        wallet_address="0x0000000000000000000000000000000000000001",  #  type: ignore
        wallet_private_key="0x0000000000000000000000000000000000000002",
        range_percentage=10,
        token0_capital=1000,
        provider="https://polygon-rpc.com/",
        debug=True,
        cex_credentials={
            "main": {
                "api_key": "your_api_key",
                "api_secret": "your_api_secret",
                "passphrase": "your_passphrase",
                "account_name": "your_account_name",
                "chain": "ETH",
                "maximum_spread_bps": 3,
                "block_trading_deadline": 60,
                "is_demo": False,
            },
            "subaccount": {
                "api_key": "your_api_key",
                "api_secret": "your_api_secret",
                "passphrase": "your_passphrase",
                "account_name": "your_account_name",
                "chain": "ETH",
                "maximum_spread_bps": 3,
                "block_trading_deadline": 60,
                "is_demo": False,
            },
        },
    )


def setup_commons(
    web3_manager_cex,
    required_amount0,
    required_amount1,
    required_amount0_decimal,
    required_amount1_decimal,
    existing_amount0,
    existing_amount1,
    existing_amount0_decimal,
    existing_amount1_decimal,
    cex_existing_amount0,
    cex_existing_amount1,
    cex_existing_amount0_decimal,
    cex_existing_amount1_decimal,
    diff_amount0_in_token0,
    diff_amount0_in_token1,
    diff_amount1_in_token0,
    diff_amount1_in_token1,
    required_swap_amount_from_token0_decimal,
    required_swap_amount_from_token1_decimal,
    cex_symbol,
):
    # Mock get_amounts_okx_blocktrading
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "required_amount0": required_amount0,
            "required_amount1": required_amount1,
            "required_amount0_decimal": required_amount0_decimal,
            "required_amount1_decimal": required_amount1_decimal,
            "existing_amount0": existing_amount0,
            "existing_amount1": existing_amount1,
            "existing_amount0_decimal": existing_amount0_decimal,
            "existing_amount1_decimal": existing_amount1_decimal,
            "cex_existing_amount0": cex_existing_amount0,
            "cex_existing_amount1": cex_existing_amount1,
            "cex_existing_amount0_decimal": cex_existing_amount0_decimal,
            "cex_existing_amount1_decimal": cex_existing_amount1_decimal,
            "diff_amount0_in_token0": diff_amount0_in_token0,
            "diff_amount0_in_token1": diff_amount0_in_token1,
            "diff_amount1_in_token0": diff_amount1_in_token0,
            "diff_amount1_in_token1": diff_amount1_in_token1,
            "required_swap_amount_from_token0_decimal": required_swap_amount_from_token0_decimal,
            "required_swap_amount_from_token1_decimal": required_swap_amount_from_token1_decimal,
            "cex_symbol": cex_symbol,
        }
    )


def test_round_amount_to_lotsize(web3_manager_cex):
    web3_manager_cex.cex_client_subaccount.get_instrument = MagicMock(
        return_value=[{"lotSz": "0.000001"}]
    )
    amount = 1.123456789
    assert (
        web3_manager_cex.cex_client_subaccount.round_amount_to_lotsize(
            amount=amount, symbol="ETH-USDC"
        )
        == 1.123456
    )


def test_deposit_funds_cex_eth(web3_manager_cex):
    web3_manager_cex.cex_client_subaccount.get_deposit_address = MagicMock(
        return_value=[
            {
                "address": "0x9cfb131fbd45d1d913a5d1dd6ac33a1e89a5a0d4",
                "chain": "USDC-Arbitrum One",
            }
        ]
    )
    web3_manager_cex.uniswap.transfer_eth = MagicMock(return_value="0x123456789")
    assert (
        web3_manager_cex.deposit_funds_cex(amount=100, token_symbol="ETH")
        == "0x123456789"
    )


def test_deposit_funds_cex_token(web3_manager_cex):
    web3_manager_cex.cex_client_subaccount.get_deposit_address = MagicMock(
        return_value=[
            {
                "address": "0x9cfb131fbd45d1d913a5d1dd6ac33a1e89a5a0d4",
                "chain": "ETH-Arbitrum One",
            }
        ]
    )
    web3_manager_cex.uniswap.transfer_token = MagicMock(return_value="0x123456789")
    assert (
        web3_manager_cex.deposit_funds_cex(amount=100, token_symbol="USDC")
        == "0x123456789"
    )


def test_wait_for_deposit_okx_blocktrading_timeup(web3_manager_cex):
    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 0,
            "cex_existing_amount0_decimal": 0,
        },
    )
    amounts = {
        "existing_amount0": 0,
        "cex_existing_amount0": 0,
        "cex_existing_amount0_decimal": 0,
    }
    with pytest.raises(DepositFailed):
        web3_manager_cex.wait_for_deposit_okx_blocktrading(
            amounts=amounts,
            watch_key="cex_existing_amount0",
            max_deadline=0.1,
            sleep_time=0.1,
        )


def test_wait_for_deposit_okx_blocktrading_success(web3_manager_cex):
    web3_manager_cex.get_cex_balances = MagicMock(
        side_effect=[
            {
                "cex_existing_amount0": 0,
                "cex_existing_amount0_decimal": 0,
            },
            {
                "cex_existing_amount0": 1,
                "cex_existing_amount0_decimal": 1,
            },
        ]
    )
    amounts = {
        "existing_amount0": 0,
        "cex_existing_amount0": 0,
        "cex_existing_amount0_decimal": 0,
    }

    web3_manager_cex.wait_for_deposit_okx_blocktrading(
        amounts=amounts,
        watch_key="cex_existing_amount0",
        max_deadline=0.2,
        sleep_time=0.1,
    )


def test_transfer_funds_from_sub_to_main_okx_blocktrading_success(web3_manager_cex):
    expected_return_value = {
        "code": "0",
        "data": [
            {
                "amt": "1000",
                "ccy": "USDC",
                "clientId": "",
                "from": "18",
                "to": "6",
                "transId": "31623768",
            }
        ],
        "msg": "",
    }
    web3_manager_cex.cex_client_main.transfer_from_subaccount_to_mainaccount = (
        MagicMock(
            return_value=expected_return_value,
        )
    )

    assert (
        web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading(
            amounts={"cex_existing_amount0": 1},
            amounts_key="cex_existing_amount0",
            currency="USDC",
        )
        == expected_return_value
    )


def test_transfer_funds_from_sub_to_main_okx_blocktrading_failed(web3_manager_cex):
    expected_return_value = {
        "code": "1",
    }

    web3_manager_cex.cex_client_main.transfer_from_subaccount_to_mainaccount = (
        MagicMock(
            return_value=expected_return_value,
        )
    )

    with pytest.raises(TransferFailed):
        web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading(
            amounts={"cex_existing_amount0": 1},
            amounts_key="cex_existing_amount0",
            currency="USDC",
        )


def test_wait_for_withdrawal_okx_blocktrading_timeup(web3_manager_cex):
    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))
    initial_amounts = 0
    with pytest.raises(WithdrawTimeout):
        web3_manager_cex.wait_for_withdrawal_okx_blocktrading(
            wallet_amount=initial_amounts,
            watch_amount="required_amount0_decimal",
            max_deadline=0.1,
            sleep_time=0.2,
        )


def test_wait_for_withdrawal_okx_blocktrading_success(web3_manager_cex):
    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(1, 1))
    initial_amounts = 0

    web3_manager_cex.wait_for_withdrawal_okx_blocktrading(
        wallet_amount=initial_amounts,
        watch_amount="required_amount0_decimal",
        max_deadline=0.2,
        sleep_time=0.1,
    )


def test_swap_amounts_okx_blocktrading_failure_not_enough_funds(web3_manager_cex):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "existing_amount0": 0,
            "existing_amount1": 0,
            "required_amount0_decimal": 1,
            "required_amount1_decimal": 1,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1_decimal": 0,
            "required_swap_amount_from_token0_decimal": 1,
            "required_swap_amount_from_token1_decimal": 1,
        }
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 0,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1": 0,
            "cex_existing_amount1_decimal": 0,
        }
    )

    with pytest.raises(InsufficientFunds):
        web3_manager_cex.swap_amounts_okx_blocktrading()


def test_swap_amounts_okx_blocktrading_success_no_swap_needed_enough_in_wallet(
    web3_manager_cex,
):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        side_effect=[
            {
                "existing_amount0": 1,
                "existing_amount1": 1,
                "required_amount0_decimal": 1,
                "required_amount1_decimal": 1,
                "cex_existing_amount0_decimal": 0,
                "cex_existing_amount1_decimal": 0,
            },
            {
                "existing_amount0": 0,
                "existing_amount1": 0,
                "required_amount0_decimal": 1,
                "required_amount1_decimal": 1,
                "cex_existing_amount0_decimal": 1,
                "cex_existing_amount1_decimal": 1,
            },
            {
                "existing_amount0": 0,
                "existing_amount1": 0,
                "required_amount0_decimal": 1,
                "required_amount1_decimal": 1,
                "cex_existing_amount0_decimal": 1,
                "cex_existing_amount1_decimal": 1,
            },
        ]
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.deposit_amounts_if_needed_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "deposit"},
    )

    web3_manager_cex.check_required_and_existing_amounts = MagicMock(
        return_value=("required_amount0_decimal", "required_amount1_decimal")
    )

    web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "transfer"}
    )

    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))

    web3_manager_cex.withdraw_amounts_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "withdraw"}
    )

    assert web3_manager_cex.swap_amounts_okx_blocktrading() == [
        {"code": "0", "type": "deposit"},
        {"code": "0", "type": "deposit"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "withdraw"},
        {"code": "0", "type": "withdraw"},
    ]


def test_swap_amounts_okx_blocktrading_success_no_swap_needed_enough_in_cex(
    web3_manager_cex,
):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "existing_amount0": 0,
            "existing_amount1": 0,
            "required_amount0_decimal": 1,
            "required_amount1_decimal": 1,
            "cex_existing_amount0_decimal": 1,
            "cex_existing_amount1_decimal": 1,
        }
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 1,
            "cex_existing_amount0_decimal": 1,
            "cex_existing_amount1": 1,
            "cex_existing_amount1_decimal": 1,
        }
    )

    web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "transfer"}
    )

    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))

    web3_manager_cex.withdraw_amounts_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "withdraw"}
    )

    assert web3_manager_cex.swap_amounts_okx_blocktrading() == [
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "withdraw"},
        {"code": "0", "type": "withdraw"},
    ]


def test_swap_amounts_okx_blocktrading_success_swap_token0_to_token1(web3_manager_cex):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "existing_amount0": 0,
            "existing_amount1": 0,
            "required_amount0_decimal": 1,
            "required_amount1_decimal": 1,
            "cex_existing_amount0_decimal": 2,
            "cex_existing_amount1_decimal": 0,
            "required_swap_amount_from_token0_decimal": 2,
            "diff_amount1_in_token0": -1,
            "diff_amount1_in_token1": 1,
            # "current_price": 1,
        }
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 2,
            "cex_existing_amount0_decimal": 2,
            "cex_existing_amount1": 0,
            "cex_existing_amount1_decimal": 0,
        }
    )

    web3_manager_cex.block_trade_okx_blocktrading = MagicMock(
        return_value={"token_swap": {"code": "0", "type": "block_trade"}}
    )

    web3_manager_cex.check_required_and_existing_amounts = MagicMock(
        return_value=("required_amount0_decimal", "required_amount1_decimal")
    )

    web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "transfer"}
    )

    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))

    web3_manager_cex.withdraw_amounts_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "withdraw"}
    )

    assert web3_manager_cex.swap_amounts_okx_blocktrading() == [
        {"token_swap": {"code": "0", "type": "block_trade"}},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "withdraw"},
        {"code": "0", "type": "withdraw"},
    ]


def test_swap_amounts_okx_blocktrading_success_swap_token1_to_token0(web3_manager_cex):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "existing_amount0": 0,
            "existing_amount1": 0,
            "required_amount0_decimal": 1,
            "required_amount1_decimal": 1,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1_decimal": 2,
            "required_swap_amount_from_token0_decimal": 0,
            "required_swap_amount_from_token1_decimal": 2,
            "diff_amount1_in_token0": 1,
            "diff_amount1_in_token1": -1,
            # "current_price": 1,
        }
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 0,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1": 2,
            "cex_existing_amount1_decimal": 2,
        }
    )

    web3_manager_cex.block_trade_okx_blocktrading = MagicMock(
        return_value={"token_swap": {"code": "0", "type": "block_trade"}}
    )

    web3_manager_cex.check_required_and_existing_amounts = MagicMock(
        return_value=("required_amount0_decimal", "required_amount1_decimal")
    )

    web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "transfer"}
    )

    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))

    web3_manager_cex.withdraw_amounts_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "withdraw"}
    )

    assert web3_manager_cex.swap_amounts_okx_blocktrading() == [
        {"token_swap": {"code": "0", "type": "block_trade"}},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "withdraw"},
        {"code": "0", "type": "withdraw"},
    ]


def test_swap_amounts_okx_blocktrading_success_swap_token1_to_token0_no_marketmaker(
    web3_manager_cex,
):
    web3_manager_cex.get_amounts_okx_blocktrading = MagicMock(
        return_value={
            "existing_amount0": 0,
            "existing_amount1": 0,
            "required_amount0_decimal": 1,
            "required_amount1_decimal": 1,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1_decimal": 2,
            "required_swap_amount_from_token0_decimal": 0,
            "required_swap_amount_from_token1_decimal": 2,
            "diff_amount1_in_token0": 1,
            "diff_amount1_in_token1": -1,
            "current_price": 1,
            "cex_symbol": "ETH/USDC",
        }
    )

    web3_manager_cex.log_amounts_okx_blocktrading = MagicMock()

    web3_manager_cex.get_cex_balances = MagicMock(
        return_value={
            "cex_existing_amount0": 0,
            "cex_existing_amount0_decimal": 0,
            "cex_existing_amount1": 2,
            "cex_existing_amount1_decimal": 2,
        }
    )

    # Make web3_manager_cex.make_block_trade return with an exception
    web3_manager_cex.make_block_trade = MagicMock(
        side_effect=[uniswap_hft.okex_integration.client.BlockTradingNoQuote()]
    )

    web3_manager_cex.handle_no_quote_exception = MagicMock(
        return_value={
            "token_swap": {"code": "0", "type": "block_trade"},
            "stable_swap": {"code": "0", "type": "block_trade"},
        }
    )

    web3_manager_cex.check_required_and_existing_amounts = MagicMock(
        return_value=("required_amount0_decimal", "required_amount1_decimal")
    )

    web3_manager_cex.transfer_funds_from_sub_to_main_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "transfer"}
    )

    web3_manager_cex.update_wallet_balance = MagicMock(return_value=(0, 0))

    web3_manager_cex.withdraw_amounts_okx_blocktrading = MagicMock(
        return_value={"code": "0", "type": "withdraw"}
    )

    assert web3_manager_cex.swap_amounts_okx_blocktrading() == [
        {
            "token_swap": {"code": "0", "type": "block_trade"},
            "stable_swap": {"code": "0", "type": "block_trade"},
        },
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "transfer"},
        {"code": "0", "type": "withdraw"},
        {"code": "0", "type": "withdraw"},
    ]
