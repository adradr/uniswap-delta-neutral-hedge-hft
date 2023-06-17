import os
import pytest
import dotenv
from unittest.mock import MagicMock, patch
from web3.types import TxReceipt
from uniswap_hft.web3_manager.web_manager import Web3Manager, InsufficientFunds

dotenv.load_dotenv()

RANGE_PCT = 10
TOKEN0_CAPITAL = 1000


@pytest.fixture
def web3_manager():
    return Web3Manager(
        pool_address=os.environ.get("POOL_ADDRESS"),  # type: ignore
        pool_fee=os.environ.get("POOL_FEE"),  # type: ignore
        wallet_address=os.environ.get("WALLET_ADDRESS"),  # type: ignore
        wallet_private_key=os.environ.get("WALLET_PRIVATE_KEY"),  # type: ignore
        range_percentage=RANGE_PCT,
        token0_capital=TOKEN0_CAPITAL,
        provider=os.environ.get("PROVIDER"),  # type: ignore
        debug=True,
    )


def test_swap_amounts_token0_to_token1(web3_manager):
    with patch.object(web3_manager, "update_balance"), patch.object(
        web3_manager, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager.token0Balance = (
            10**6 * 2000
        )  # token decimals 6 with 2000 balance
        web3_manager.token1Balance = 10**18 * 0  # token decimals 18 with 500 balance
        web3_manager.amount0 = 10**6 * 1000  # target amount with token decimals 6
        web3_manager.amount1 = 10**18 * 1  # target amount with token decimals 18
        web3_manager.tokenManager.token0_decimal = 6
        web3_manager.tokenManager.token1_decimal = 18
        web3_manager.uniswap.get_current_price.return_value = 1000
        web3_manager.uniswap.swap_token_input.return_value = "0x00"
        web3_manager.uniswap.w3.eth.getTransactionReceipt.return_value = TxReceipt(
            {"status": 1}
        )

        result = web3_manager.swap_amounts()

        assert isinstance(result, dict)
        assert "status" in result
        web3_manager.uniswap.get_current_price.assert_called_once()
        web3_manager.uniswap.swap_token_input.assert_called_once()


def test_swap_amounts_token1_to_token0(web3_manager):
    with patch.object(web3_manager, "update_balance"), patch.object(
        web3_manager, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager.token0Balance = 10**6 * 0
        web3_manager.token1Balance = 10**18 * 2
        web3_manager.amount0 = 10**6 * 1000  # target amount with token decimals 6
        web3_manager.amount1 = 10**18 * 1  # target amount with token decimals 18
        web3_manager.tokenManager.token0_decimal = 6
        web3_manager.tokenManager.token1_decimal = 18
        web3_manager.uniswap.get_current_price.return_value = 1000
        web3_manager.uniswap.swap_token_input.return_value = "0x00"
        web3_manager.uniswap.w3.eth.getTransactionReceipt.return_value = TxReceipt(
            {"status": 1}
        )

        result = web3_manager.swap_amounts()

        assert isinstance(result, dict)
        assert "status" in result
        web3_manager.uniswap.get_current_price.assert_called_once()
        web3_manager.uniswap.swap_token_input.assert_called_once()


def test_swap_amounts_insufficient_funds(web3_manager):
    with patch.object(web3_manager, "update_balance"), patch.object(
        web3_manager, "uniswap"
    ), patch("logging.getLogger"):
        web3_manager.token0Balance = 10**6 * 500  # token decimals 6 with 500 balance
        web3_manager.token1Balance = 10**18 * 0  # token decimals 18 with 500 balance
        web3_manager.amount0 = 10**6 * 1000  # required amount with token decimals 6
        web3_manager.amount1 = 10**18 * 1  # required amount with token decimals 18
        web3_manager.tokenManager.token0_decimal = 6
        web3_manager.tokenManager.token1_decimal = 18
        web3_manager.uniswap.get_current_price.return_value = 1000

        with pytest.raises(InsufficientFunds):
            web3_manager.swap_amounts()
