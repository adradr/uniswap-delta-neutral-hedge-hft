from setuptools import setup

setup(
    name="uniswap-hft",
    version="0.1",
    description="Uniswap trading library, which allows to create a delta neutral hedge for a given token pair.",
    url="https://github.com/adradr/uniswap-delta-neutral-hedge-hft",
    author="Adrian Lenard, Patrik Belteky",
    author_email="adrian.lenard@me.com, patrik.belteky@gmail.com",
    packages=[
        "uniswap_math",
        "uniswap_v3",
        "web3_manager",
        "trading_engine",
        "telegram_interface",
    ],
    package_data={
        "web3_manager": [
            "assets/*",
        ],
        "uniswap_v3": [
            "assets/*",
            "assets/uniswap-v1/*",
            "assets/uniswap-v2/*",
            "assets/uniswap-v3/*",
        ],
    },
    install_requires=[
        "pytest",
        "pandas",
        "numpy",
        "jsonpickle",
        "python-dotenv",
        "argparse",
        "flask",
        "flask_jwt_extended",
        "cherrypy",
        "apscheduler",
        "psutil",
        "ccxt",
        "web3==5.30.0",
        "uniswap-python",
        "python-telegram-bot",
    ],
)
