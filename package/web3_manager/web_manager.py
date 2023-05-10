from uniswap_math import TokenManagement
from web3 import Web3, EthereumTesterProvider
from uniswap import Uniswap

class webManager:
    '''
    Initilizes a pool with an associated wallet and a percentage
    params:
    poolAddress - The address of the pool where liq. should be provided
    abi - ABI of the pool (probably can use a hardcoded value)
    wallettAddress - The address of the wallet where the funds are located at
    percentage - How wide the range should be where liq. is provided
    tokenABI - ABI of an ERC20 token, only need the decimals, balanceOf()
    autoSwap - If set to True, when the position is closed, it will automatically swap the tokens, so the pool can be reopened
    autoOpen - If set to True, it will automatically open a new position, if there are enough funds to do so
    '''
    def __init__(self, poolAddress, abi, walletAddress, percentage, tokenABI, autoSwap=False, autoOpen=False):
        self.poolAddress = poolAddress
        self.abi = abi
        self.contract = Web3.eth.contract(address=self.poolAddress, abi=self.abi)
        self.walletAddress = walletAddress
        self.percentage = percentage
        self.autoSwap = autoSwap
        self.autoOpen = autoOpen
        self.ranges = []

        #Get Tokens from pool address
        self.token0 = self.contract.functions.token0().call()
        self.token1 = self.contract.functions.token1().call()
        self.token0Contract = Web3.eth.contract(address=self.token0, abi=tokenABI)
        self.token1Contract = Web3.eth.contract(address=self.token1, abi=tokenABI)

        #Get decimals
        self.decimal0 = self.token0Contract.functions.decimals().call()
        self.decimal1 = self.token1Contract.functions.decimals().call()

        #Get token amount from pool address
        self.token0Balance = self.token0Contract.functions.balanceOf(self.walletAddress).transact()
        self.token1Balance = self.token1Contract.functions.balanceOf(self.walletAddress).transact()

        #Initialize tokenManager
        self.tokManager = TokenManagement(self.decimal0, self.decimal1)

    def openPosition(self, currentPrice, valuePercentage=100):
        #Get token amounts
        amount0 = self.token0Balance * (valuePercentage / 100)
        amount1 = self.token1Balance * (valuePercentage / 100)

        #Calculate ticks from currentPrice
        allRanges = self.tokManager(self.percentage, currentPrice)
        self.ranges.append(allRanges[3])
        self.ranges.append(allRanges[5])

        #open position at uniswap
        tx_receipt = Uniswap.mint_liquidity(self.poolAddress, amount0, amount1, allRanges[3], allRanges[5], int(18446744073709551616))
        return tx_receipt

    def closePosition(self, currentPrice, tokenId, forceClose=True):
        #convert currentPrice to tick
        currentTick = self.tokManager.priceToTick(currentPrice)

        if forceClose == False:
            #if tick is higher or lower, close the position
            if currentTick > self.ranges[1] or currentTick < self.ranges[0]:
                tx_receipt = Uniswap.close_position(tokenId, 0, 0)
        else:
            tx_receipt = Uniswap.close_position(tokenId, 0, 0)

        if self.autoSwap == True:
            amount0 = self.token0Contract.functions.balanceOf(self.walletAddress).call()
            amount1 = self.token1Contract.functions.balanceOf(self.walletAddress).call()
            if amount0 == 0:
                swapAmount = self.tokManager.getSwapAmount(amount0)
            elif amount1 == 0:
                swapAmount = self.tokManager.getSwapAmount(amount1)

        if self.autoOpen == True:
            self.openPosition(currentPrice)
            

