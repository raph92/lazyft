# --- Do not remove these libs ---
import sys
from datetime import datetime, timedelta
from functools import reduce
from pathlib import Path

import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IntParameter,
    DecimalParameter,
    merge_informative_pair,
    CategoricalParameter,
)
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))

# --------------------------------


class BollingerBands(IStrategy):
    # buy_rsi = IntParameter(5, 50, default=30, load=True)
    # sell_rsi = IntParameter(50, 100, default=70, load=True)
    sell_band = CategoricalParameter(
        ['bb_middleband', 'bb_upperband'], default='bb_upperband', load=True
    )
    # region Params
    stoploss = -0.147
    minimal_roi = {'0': 0.188, '21': 0.095, '35': 0.033, '130': 0}


    # endregion

    # Optimal timeframe for the strategy
    # inf_timeframe = '1h'
    timeframe = '1m'
    use_custom_stoploss = False

    custom_fiat = "USD"  # Only relevant if stake is BTC or ETH
    custom_btc_inf = False  # Don't change this.

    # Recommended
    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = True

    def custom_stoploss(
        self,
        pair: str,
        trade: 'Trade',
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        if (
            current_profit < -0.04
            and current_time - timedelta(minutes=35) > trade.open_date_utc
        ):
            return -0.01

        return -0.99

    # def informative_pairs(self):
    #     # add all whitelisted pairs on informative timeframe
    #     pairs = self.dp.current_whitelist()
    #     informative_pairs = [(pair, self.inf_timeframe) for pair in pairs]
    #
    #     # add extra informative pairs if the stake is BTC or ETH
    #     if self.config['stake_currency'] in ('BTC', 'ETH'):
    #         for pair in pairs:
    #             coin, stake = pair.split('/')
    #             coin_fiat = f"{coin}/{self.custom_fiat}"
    #             informative_pairs += [(coin_fiat, self.timeframe)]
    #
    #         stake_fiat = f"{self.config['stake_currency']}/{self.custom_fiat}"
    #         informative_pairs += [(stake_fiat, self.timeframe)]
    #     # if BTC/STAKE is not in whitelist, add it as an informative pair on both timeframes
    #     else:
    #         btc_stake = f"BTC/{self.config['stake_currency']}"
    #         if btc_stake not in pairs:
    #             informative_pairs += [(btc_stake, self.timeframe)]
    #
    #     return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        conditions.append((dataframe['close'] < dataframe['bb_lowerband']))
        conditions.append(dataframe['volume'].gt(0))

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_above(dataframe['close'], dataframe[self.sell_band.value]),
            'sell',
        ] = 1
        return dataframe
