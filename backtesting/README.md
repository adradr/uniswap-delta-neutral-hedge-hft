## Uniswap V3 Strategy Backtest Results

### Executive Summary

This internal document presents the result of our backtest on a Uniswap V3 strategy for the ETH/USDC pool with the aim to assess the impact of different configurations on performance, specifically focusing on the range and whether a hedging strategy was implemented.

### Assumption for backtesting

During this experiment due to the lack of data, it has been difficult to quite exactly scale up potiential fee revenue earned by unit of volume in the pool. Due to the lack of liquidity density data for each datapoint, we had to make an assumption in order to linearly scale this fee variable:

- We are not significant liquidity providers in the pool based on `own_capital_usd / TVL` ratio.

- Therefore related to the first point, even with narrow ranges we are not owning significant amount of the range

If both of these assumptions are taken as true, we can linearly scale our rewards from a position we held open for 10 days of $100 face value, which earned $2.01 in that time period. If these assumptions are false in real life than the fee earner per volume unit would scale much more like a log function with diminishing returns as we are making the range narrower and owning more and more of the liquidity range.

### Findings 

Our findings indicate that both range percentage and hedging are vital factors influencing the strategy's performance. The key results of our backtest are summarized below:

- The configuration that achieved the highest ROI (157.67%) had a range percentage of 0.25 and utilized hedging. This configuration also had the lowest drawdown (45.7%), indicating a relatively lower risk compared to other configurations.

- Overall, configurations with hedging resulted in a better ROI than those without. For example, when a range of 0.25% was used, the hedged strategy achieved a significantly higher ROI (157.67%) compared to the unhedged strategy (95.31%). This suggests that hedging could effectively offset some of the losses due to the divergence, leading to better overall performance.

- Our analysis also shows that a larger range doesn't necessarily equate to better performance. The configuration with the highest range (10%) had one of the lowest ROIs, whether hedged (-24.40%) or unhedged (-43.29%). This could be due to the fact that larger ranges may result in lower concentrated liquidity multipler, thus generating fewer fees.

- Conversely, a smaller range, specifically 0.25%, achieved the best results in both hedged and unhedged scenarios. This suggests that a more frequent trading approach could be advantageous, given the fee structure of Uniswap V3.

- As expected, hedging helped decrease the directional risk. For each range, hedged strategies consistently exhibited a lower drawdown than their unhedged counterparts. This clearly indicates the risk-mitigation benefit of hedging.

Based on these findings, we suggest further exploration of the following additional strategies to increase return and decrease directional risks:

1. Adjusting the range more dynamically: Instead of sticking to a single static range for the entire duration, the strategy could adjust its range based on market conditions. For example, it could use a larger range in more volatile conditions and a smaller one in less volatile conditions.

2. Incorporating predictive models: Machine learning models could be utilized to predict the future price of ETH and adjust the range or the hedging strategy accordingly.

3. Implementing stop-loss rules: To further control risk, the strategy could close the position and hedge it once the loss reaches a certain threshold.

We hope these insights are helpful in refining our Uniswap V3 strategy. We recommend conducting additional backtests incorporating the strategies suggested above for further optimization.

### Notes:
- Range percentages are meant to be doubles, as they indicate what percentage from current price we are positioning our upper and lower range.

### Latest version of the nalysis notebook can be found here:
- [HTML](uniswap_fee_and_divergence_results_analysis.html)
- [IPynb](uniswap_fee_and_divergence_results_analysis.ipynb)

### Summary of the results:
|               |   Number of positions |   Total Fees Generated |   Losses Due to Divergence |   Total PNL with Fees |        ROI |       DD |   ID |
|:--------------|----------------------:|-----------------------:|---------------------------:|----------------------:|-----------:|---------:|-----:|
| (10.0, True)  |                    63 |        76132.5         |                  -24.5659  |              1048.32  | -24.3968   | 0.604139 |    0 |
| (10.0, False) |                    63 |        76132.5         |                  -36.5008  |            -43285.5   | -43.2855   | 0.60383  |    1 |
| (9.0, True)   |                    66 |        84591.7         |                   14.8901  |              9694.16  | -16.3129   | 0.580023 |    2 |
| (9.0, False)  |                    66 |        84591.7         |                   -7.0298  |            -36165.8   | -36.1658   | 0.605812 |    3 |
| (8.0, True)   |                    92 |        95165.6         |                  -26.1271  |              5298.6   | -20.6051   | 0.623922 |    4 |
| (8.0, False)  |                    92 |        95165.6         |                  -38.529   |            -40540.4   | -40.5404   | 0.654174 |    5 |
| (7.0, True)   |                   105 |       108761           |                  -32.5742  |              8627.29  | -15.9384   | 0.636237 |    6 |
| (7.0, False)  |                   105 |       108761           |                  -39.5969  |            -37328.4   | -37.3284   | 0.661893 |    7 |
| (6.0, True)   |                   131 |       126887           |                  -24.7179  |             15276.5   |  -8.25819  | 0.635138 |    8 |
| (6.0, False)  |                   131 |       126887           |                  -32.4272  |            -31702.7   | -31.7027   | 0.677762 |    9 |
| (5.0, True)   |                   187 |       152265           |                  -14.1105  |             14447.6   | -10.557    | 0.634995 |   10 |
| (5.0, False)  |                   187 |       152265           |                  -22.4445  |            -35212.9   | -35.2129   | 0.676395 |   11 |
| (4.0, True)   |                   270 |       190331           |                  -15.9135  |             20886.6   |  -4.4084   | 0.65801  |   12 |
| (4.0, False)  |                   270 |       190331           |                  -22.0234  |            -30425.8   | -30.4258   | 0.724144 |   13 |
| (3.0, True)   |                   397 |       253775           |                   -9.34331 |             28719.7   |   0.909471 | 0.634923 |   14 |
| (3.0, False)  |                   397 |       253775           |                  -15.8214  |            -28648.4   | -28.6484   | 0.699935 |   15 |
| (2.0, True)   |                   694 |       380662           |                   -4.40667 |             45732.5   |  14.8291   | 0.625625 |   16 |
| (2.0, False)  |                   694 |       380662           |                  -10.8815  |            -18693.2   | -18.6932   | 0.71162  |   17 |
| (1.0, True)   |                  1658 |       761325           |                   -9.44503 |             89710.9   |  41.8408   | 0.575305 |   18 |
| (1.0, False)  |                  1658 |       761325           |                  -14.5361  |               678.959 |   0.678959 | 0.700314 |   19 |
| (0.75, True)  |                  2281 |            1.0151e+06  |                  -10.3274  |            113218     |  51.2344   | 0.540954 |   20 |
| (0.75, False) |                  2281 |            1.0151e+06  |                  -15.5559  |              7401.58  |   7.40158  | 0.677577 |   21 |
| (0.5, True)   |                  3349 |            1.52265e+06 |                  -11.0608  |            175150     |  80.3034   | 0.488346 |   22 |
| (0.5, False)  |                  3349 |            1.52265e+06 |                  -16.7696  |             30933.6   |  30.9336   | 0.608637 |   23 |
| (0.25, True)  |                  5427 |            3.0453e+06  |                  -12.9676  |            367941     | 157.673    | 0.456666 |   24 |
| (0.25, False) |                  5427 |            3.0453e+06  |                  -19.3061  |             95305.7   |  95.3057   | 0.526607 |   25 |