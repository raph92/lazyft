"""
https://kaabar-sofien.medium.com/the-catapult-indicator-innovative-trading-techniques-8910ac962c57
"""
# --- Do not remove these libs ---
import sys
from datetime import datetime, timedelta
from functools import reduce
from numbers import Number
from pathlib import Path
from pprint import pprint
from typing import Optional, Union, Tuple

import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import pandas as pd
import pandas_ta
import talib.abstract as ta
from finta import TA
from freqtrade.constants import ListPairsWithTimeframes
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IntParameter,
    DecimalParameter,
    merge_informative_pair,
    CategoricalParameter,
)
from freqtrade.strategy.interface import IStrategy
from numpy import number
from pandas import DataFrame
from pandas_ta import ema
import logging
from indicator_opt import IndicatorOptHelper, indicators, Comparison, InvalidSeriesError

sys.path.append(str(Path(__file__).parent))


logger = logging.getLogger(__name__)


class IndicatorMix(IStrategy):
    # region Parameters
    iopt = IndicatorOptHelper.get()
    buy_comparisons, sell_comparisons = iopt.create_local_parameters(
        locals(), num_buy=3, num_sell=2
    )
    # endregion
    # region Params
    minimal_roi = {"0": 0.10, "20": 0.05, "64": 0.03, "168": 0}
    stoploss = -0.25
    buy_params = {
        "buy_comparison_series_1": "EMA_100",
        "buy_comparison_series_2": "T3Average_1h",
        "buy_comparison_series_3": "EMA",
        "buy_operator_1": "<",
        "buy_operator_2": ">=",
        "buy_operator_3": "<=",
        "buy_series_1": "ewo",
        "buy_series_2": "bb_middleband_1h",
        "buy_series_3": "T3Average",
    }
    # endregion
    timeframe = '5m'
    use_custom_stoploss = False

    # Recommended
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = True
    startup_candle_count = 200

    def informative_pairs(self) -> ListPairsWithTimeframes:
        pairs = self.dp.current_whitelist()
        # get each timeframe from inf_timeframes
        return [
            (pair, timeframe)
            for pair in pairs
            for timeframe in self.iopt.inf_timeframes
        ]

    def populate_informative_indicators(self, dataframe: DataFrame, metadata):
        inf_dfs = {}
        for timeframe in self.iopt.inf_timeframes:
            inf_dfs[timeframe] = self.dp.get_pair_dataframe(
                pair=metadata['pair'], timeframe=timeframe
            )
        for indicator in indicators.values():
            if not indicator.timeframe:
                continue
            inf_dfs[indicator.timeframe] = indicator.populate(
                inf_dfs[indicator.timeframe]
            )
        for tf, df in inf_dfs.items():
            dataframe = merge_informative_pair(dataframe, df, self.timeframe, tf)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for indicator in indicators.values():
            if indicator.timeframe:
                continue
            dataframe = indicator.populate(dataframe)
        dataframe = self.populate_informative_indicators(dataframe, metadata)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self.iopt.create_conditions(
            dataframe,
            self.buy_comparisons,
            self,
            'buy',
        )
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self.iopt.create_conditions(
            dataframe,
            self.sell_comparisons,
            self,
            'sell',
        )
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'sell'] = 1
        return dataframe
