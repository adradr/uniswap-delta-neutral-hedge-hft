import pytest
from web3.types import TxReceipt
from unittest.mock import patch, MagicMock
from uniswap_hft.web3_manager.web_manager import InsufficientFunds, Web3Manager


@pytest.fixture
def web3_manager_dex():
    return Web3Manager(
        pool_address="0x45dda9cb7c25131df268515131f647d726f50608",
        pool_fee=500,
        wallet_address="0x0000000000000000000000000000000000000001",
        wallet_private_key="0x0000000000000000000000000000000000000002",
        range_percentage=10,
        token0_capital=1000,
        provider="https://polygon-rpc.com/",
        debug=True,
    )


def test_swap_amounts_no_swap_needed(web3_manager_dex):
    with patch.object(web3_manager_dex, "update_balance"), patch.object(
        web3_manager_dex, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager_dex.token0Balance = 10**6 * 1000 * 1.01
        web3_manager_dex.token1Balance = 10**18 * 500 * 1.01
        web3_manager_dex.amount0 = 10**6 * 1000
        web3_manager_dex.amount1 = 10**18 * 500
        web3_manager_dex.tokenManager.token0_decimal = 6
        web3_manager_dex.tokenManager.token1_decimal = 18
        web3_manager_dex.update_balance = MagicMock(
            return_value=(
                web3_manager_dex.token0Balance,
                web3_manager_dex.token1Balance,
            )
        )
        web3_manager_dex.uniswap.get_current_price.return_value = 1000

        result = web3_manager_dex.swap_amounts()

        assert result is None
        web3_manager_dex.uniswap.get_current_price.assert_called_once()
        web3_manager_dex.uniswap.swap_token_input.assert_not_called()


def test_swap_amounts_token0_to_token1(web3_manager_dex):
    with patch.object(web3_manager_dex, "update_balance"), patch.object(
        web3_manager_dex, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager_dex.update_balance = MagicMock(
            return_value=(10**6 * 2000, 10**18 * 0)
        )
        web3_manager_dex.amount0 = 10**6 * 1000  # target amount with token decimals 6
        web3_manager_dex.amount1 = 10**18 * 1  # target amount with token decimals 18
        web3_manager_dex.tokenManager.token0_decimal = 6
        web3_manager_dex.tokenManager.token1_decimal = 18
        web3_manager_dex.uniswap.get_current_price.return_value = 1000
        web3_manager_dex.uniswap.swap_token_input.return_value = "0x00"
        web3_manager_dex.uniswap.w3.eth.getTransactionReceipt.return_value = TxReceipt(
            {"status": 1}
        )

        result = web3_manager_dex.swap_amounts()

        assert isinstance(result, dict)
        assert "status" in result
        web3_manager_dex.uniswap.get_current_price.assert_called_once()
        web3_manager_dex.uniswap.swap_token_input.assert_called_once()


def test_swap_amounts_token1_to_token0(web3_manager_dex):
    with patch.object(web3_manager_dex, "update_balance"), patch.object(
        web3_manager_dex, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager_dex.update_balance = MagicMock(
            return_value=(10**6 * 0, 10**18 * 2)
        )
        web3_manager_dex.amount0 = 10**6 * 1000  # target amount with token decimals 6
        web3_manager_dex.amount1 = 10**18 * 1  # target amount with token decimals 18
        web3_manager_dex.tokenManager.token0_decimal = 6
        web3_manager_dex.tokenManager.token1_decimal = 18
        web3_manager_dex.uniswap.get_current_price.return_value = 1000
        web3_manager_dex.uniswap.swap_token_input.return_value = "0x00"
        web3_manager_dex.uniswap.w3.eth.getTransactionReceipt.return_value = TxReceipt(
            {"status": 1}
        )

        result = web3_manager_dex.swap_amounts()

        assert isinstance(result, dict)
        assert "status" in result
        web3_manager_dex.uniswap.get_current_price.assert_called_once()
        web3_manager_dex.uniswap.swap_token_input.assert_called_once()


def test_swap_amounts_insufficient_funds(web3_manager_dex):
    with patch.object(web3_manager_dex, "update_balance"), patch.object(
        web3_manager_dex, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager_dex.update_balance = MagicMock(
            return_value=(
                web3_manager_dex.token0Balance,
                web3_manager_dex.token1Balance,
            )
        )
        web3_manager_dex.token0Balance = (
            10**6 * 500
        )  # token decimals 6 with 500 balance
        web3_manager_dex.token1Balance = (
            10**18 * 0
        )  # token decimals 18 with 500 balance
        web3_manager_dex.amount0 = (
            10**6 * 1000
        )  # required amount with token decimals 6
        web3_manager_dex.amount1 = (
            10**18 * 1
        )  # required amount with token decimals 18
        web3_manager_dex.tokenManager.token0_decimal = 6
        web3_manager_dex.tokenManager.token1_decimal = 18
        web3_manager_dex.uniswap.get_current_price.return_value = 1000

        with pytest.raises(InsufficientFunds):
            web3_manager_dex.swap_amounts()
