"""
Solipsis Custom Indicators and Maths
"""
import math
import random

import numpy as np
import pandas as pd
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from pandas import DataFrame, Series

"""
Misc. Helper Functions
"""


def same_length(bigger, shorter):
    return np.concatenate(
        (np.full((bigger.shape[0] - shorter.shape[0]), np.nan), shorter)
    )


"""
Maths
"""


def linear_growth(
    start: float, end: float, start_time: int, end_time: int, trade_time: int
) -> float:
    """
    Simple linear growth function. Grows from start to end after end_time minutes (starts after start_time minutes)
    """
    time = max(0, trade_time - start_time)
    rate = (end - start) / (end_time - start_time)

    return min(end, start + (rate * time))


def linear_decay(
    start: float, end: float, start_time: int, end_time: int, trade_time: int
) -> float:
    """
    Simple linear decay function. Decays from start to end after end_time minutes (starts after start_time minutes)
    """
    time = max(0, trade_time - start_time)
    rate = (start - end) / (end_time - start_time)

    return max(end, start - (rate * time))


"""
TA Indicators
"""


def zema(dataframe, period, field='close'):
    """
    Source: https://github.com/freqtrade/technical/blob/master/technical/indicators/overlap_studies.py#L79
    Modified slightly to use ta.EMA instead of technical ema
    """
    df = dataframe.copy()

    df['ema1'] = ta.EMA(df[field], timeperiod=period)
    df['ema2'] = ta.EMA(df['ema1'], timeperiod=period)
    df['d'] = df['ema1'] - df['ema2']
    df['zema'] = df['ema1'] + df['d']

    return df['zema']


def RMI(dataframe, *, length=20, mom=5):
    """
    Source: https://github.com/freqtrade/technical/blob/master/technical/indicators/indicators.py#L912
    """
    df = dataframe.copy()

    df['maxup'] = (df['close'] - df['close'].shift(mom)).clip(lower=0)
    df['maxdown'] = (df['close'].shift(mom) - df['close']).clip(lower=0)

    df.fillna(0, inplace=True)

    df["emaInc"] = ta.EMA(df, price='maxup', timeperiod=length)
    df["emaDec"] = ta.EMA(df, price='maxdown', timeperiod=length)

    df['RMI'] = np.where(
        df['emaDec'] == 0, 0, 100 - 100 / (1 + df["emaInc"] / df["emaDec"])
    )

    return df["RMI"]


def mastreak(dataframe: DataFrame, period: int = 4, field='close') -> Series:
    """
    MA Streak
    Port of: https://www.tradingview.com/script/Yq1z7cIv-MA-Streak-Can-Show-When-a-Run-Is-Getting-Long-in-the-Tooth/
    """
    df = dataframe.copy()

    avgval = zema(df, period, field)

    arr = np.diff(avgval)
    pos = np.clip(arr, 0, 1).astype(bool).cumsum()
    neg = np.clip(arr, -1, 0).astype(bool).cumsum()
    streak = np.where(
        arr >= 0,
        pos - np.maximum.accumulate(np.where(arr <= 0, pos, 0)),
        -neg + np.maximum.accumulate(np.where(arr >= 0, neg, 0)),
    )

    res = same_length(df['close'], streak)

    return res


def pcc(dataframe: DataFrame, period: int = 20, mult: int = 2):
    """
    Percent Change Channel
    PCC is like KC unless it uses percentage changes in price to set channel distance.
    https://www.tradingview.com/script/6wwAWXA1-MA-Streak-Change-Channel/
    """
    df = dataframe.copy()

    df['previous_close'] = df['close'].shift()

    df['close_change'] = (
        (df['close'] - df['previous_close']) / df['previous_close'] * 100
    )
    df['high_change'] = (df['high'] - df['close']) / df['close'] * 100
    df['low_change'] = (df['low'] - df['close']) / df['close'] * 100

    df['delta'] = df['high_change'] - df['low_change']

    mid = zema(df, period, 'close_change')
    rangema = zema(df, period, 'delta')

    upper = mid + rangema * mult
    lower = mid - rangema * mult

    return upper, rangema, lower


def SSLChannels(dataframe, length=10, mode='sma'):
    """
    Source: https://www.tradingview.com/script/xzIoaIJC-SSL-channel/
    Source: https://github.com/freqtrade/technical/blob/master/technical/indicators/indicators.py#L1025
    Usage:
        dataframe['sslDown'], dataframe['sslUp'] = SSLChannels(dataframe, 10)
    """
    if mode not in ('sma'):
        raise ValueError(f"Mode {mode} not supported yet")

    df = dataframe.copy()

    if mode == 'sma':
        df['smaHigh'] = df['high'].rolling(length).mean()
        df['smaLow'] = df['low'].rolling(length).mean()

    df['hlv'] = np.where(
        df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN)
    )
    df['hlv'] = df['hlv'].ffill()

    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])

    return df['sslDown'], df['sslUp']


def SSLChannels_ATR(dataframe, length=7):
    """
    SSL Channels with ATR: https://www.tradingview.com/script/SKHqWzql-SSL-ATR-channel/
    Credit to @JimmyNixx for python
    """
    df = dataframe.copy()

    df['ATR'] = ta.ATR(df, timeperiod=14)
    df['smaHigh'] = df['high'].rolling(length).mean() + df['ATR']
    df['smaLow'] = df['low'].rolling(length).mean() - df['ATR']
    df['hlv'] = np.where(
        df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN)
    )
    df['hlv'] = df['hlv'].ffill()
    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])

    return df['sslDown'], df['sslUp']


def WaveTrend(dataframe, chlen=10, avg=21, smalen=4):
    """
    WaveTrend Ocillator by LazyBear
    https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/
    """
    df = dataframe.copy()

    df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
    df['esa'] = ta.EMA(df['hlc3'], timeperiod=chlen)
    df['d'] = ta.EMA((df['hlc3'] - df['esa']).abs(), timeperiod=chlen)
    df['ci'] = (df['hlc3'] - df['esa']) / (0.015 * df['d'])
    df['tci'] = ta.EMA(df['ci'], timeperiod=avg)

    df['wt1'] = df['tci']
    df['wt2'] = ta.SMA(df['wt1'], timeperiod=smalen)
    df['wt1-wt2'] = df['wt1'] - df['wt2']

    return df['wt1'], df['wt2']


def T3(dataframe, length=5):
    """
    T3 Average by HPotter on Tradingview
    https://www.tradingview.com/script/qzoC9H1I-T3-Average/
    """
    df = dataframe.copy()

    df['xe1'] = ta.EMA(df['close'], timeperiod=length)
    df['xe2'] = ta.EMA(df['xe1'], timeperiod=length)
    df['xe3'] = ta.EMA(df['xe2'], timeperiod=length)
    df['xe4'] = ta.EMA(df['xe3'], timeperiod=length)
    df['xe5'] = ta.EMA(df['xe4'], timeperiod=length)
    df['xe6'] = ta.EMA(df['xe5'], timeperiod=length)
    b = 0.7
    c1 = -b * b * b
    c2 = 3 * b * b + 3 * b * b * b
    c3 = -6 * b * b - 3 * b - 3 * b * b * b
    c4 = 1 + 3 * b + b * b * b + 3 * b * b
    df['T3Average'] = c1 * df['xe6'] + c2 * df['xe5'] + c3 * df['xe4'] + c4 * df['xe3']

    return df['T3Average']


def SROC(dataframe, roclen=21, emalen=13, smooth=21):
    df = dataframe.copy()

    roc = ta.ROC(df, timeperiod=roclen)
    ema = ta.EMA(df, timeperiod=emalen)
    sroc = ta.ROC(ema, timeperiod=smooth)

    return sroc


def rvi(dataframe: DataFrame, periods: int = 14, ema_length=14) -> DataFrame:
    """
    Relative Volatility Index (RVI)
    """
    # calculate std
    df = dataframe.copy()
    df['std'] = qtpylib.rolling_std(df['close'], periods, min_periods=periods)
    df['close_delta'] = dataframe['close'] - dataframe['close'].shift(1)
    df['upper'] = 0.0
    df.loc[df.close_delta > 0, 'upper'] = df['std']
    df['lower'] = 0.0
    df.loc[df.close_delta < 0, 'lower'] = df['std']
    df['upper_ema'] = pta.ema(df['upper'].fillna(0.0), window=ema_length)
    df['lower_ema'] = pta.ema(df['lower'].fillna(0.0), window=ema_length)
    df['rvi'] = df['upper_ema'] / (df['upper_ema'] + df['lower_ema']) * 100
    return df['rvi']


def EWO(dataframe, ema_length=5, ema2_length=35):
    df = dataframe.copy()
    ema1 = ta.EMA(df, timeperiod=ema_length)
    ema2 = ta.EMA(df, timeperiod=ema2_length)
    emadif = (ema1 - ema2) / df["low"] * 100
    return emadif


def bollinger_bands(dataframe: DataFrame, timeperiod=20, stds=2):
    # Bollinger bands
    df = dataframe.copy()
    bollinger = qtpylib.bollinger_bands(
        qtpylib.typical_price(df), window=timeperiod, stds=stds
    )
    df['bb_lowerband'] = bollinger['lower']
    df['bb_middleband'] = bollinger['mid']
    df['bb_upperband'] = bollinger['upper']
    return df


def atr_ma(dataframe: DataFrame):
    """Get moving average of average true range"""
    df = dataframe.copy()
    if 'atr' not in df:
        df['atr'] = ta.ATR(df)
    df['atr_ma'] = ta.MA(df['atr'])
    return df


def stoch_sma(dataframe: DataFrame, window=80, sma_window=10):
    """"""
    stoch = qtpylib.stoch(dataframe, window)
    return qtpylib.sma((stoch['slow_k'] + stoch['slow_d']) / 2, sma_window)


def heiken_ashi(dataframe, smooth_inputs=False, smooth_outputs=False, length=10):
    df = dataframe[['open', 'close', 'high', 'low']].copy().fillna(0)
    if smooth_inputs:
        df['open_s'] = ta.EMA(df['open'], timeframe=length)
        df['high_s'] = ta.EMA(df['high'], timeframe=length)
        df['low_s'] = ta.EMA(df['low'], timeframe=length)
        df['close_s'] = ta.EMA(df['close'], timeframe=length)

        open_ha = (df['open_s'].shift(1) + df['close_s'].shift(1)) / 2
        high_ha = df.loc[:, ['high_s', 'open_s', 'close_s']].max(axis=1)
        low_ha = df.loc[:, ['low_s', 'open_s', 'close_s']].min(axis=1)
        close_ha = (df['open_s'] + df['high_s'] + df['low_s'] + df['close_s']) / 4
    else:
        open_ha = (df['open'].shift(1) + df['close'].shift(1)) / 2
        high_ha = df.loc[:, ['high', 'open', 'close']].max(axis=1)
        low_ha = df.loc[:, ['low', 'open', 'close']].min(axis=1)
        close_ha = (df['open'] + df['high'] + df['low'] + df['close']) / 4

    open_ha = open_ha.fillna(0)
    high_ha = high_ha.fillna(0)
    low_ha = low_ha.fillna(0)
    close_ha = close_ha.fillna(0)

    if smooth_outputs:
        open_sha = ta.EMA(open_ha, timeframe=length)
        high_sha = ta.EMA(high_ha, timeframe=length)
        low_sha = ta.EMA(low_ha, timeframe=length)
        close_sha = ta.EMA(close_ha, timeframe=length)
        # return as ohlc dataframe
        return DataFrame(
            {'open': open_sha, 'high': high_sha, 'low': low_sha, 'close': close_sha}
        )
    else:
        # return as ohlc dataframe
        return DataFrame(
            {'open': open_ha, 'high': high_ha, 'low': low_ha, 'close': close_ha}
        )


# def super_trend(df, multiplier, timeperiod=10):
#     """
#     From https://github.com/kennedyCzar/FORECASTING-1.0
#     :Arguments:
#       df:
#         dataframe
#       :ATR:
#         Average True range
#       :multiplier:
#         factor to multiply with ATR for upper and lower band
#       :n:
#         period
#
#     :Return type:
#       Supertrend
#     """
#     df = df.copy(deep=True)
#     ATR = ta.ATR(df, timeperiod=timeperiod)
#     df['Upper_band_start'] = (df.high + df.low) / 2 + (multiplier * ATR)
#     df['Lower_band_start'] = (df.high + df.low) / 2 - (multiplier * ATR)
#     df = df.fillna(0)
#     df['SuperTrend'] = np.nan
#     # Upper_band
#     df['Upper_band'] = df['Upper_band_start']
#     df['Lower_band'] = df['Lower_band_start']
#     # Upper_band
#     for ii in range(timeperiod, df.shape[0]):
#         if df['close'][ii - 1] <= df['Upper_band'][ii - 1]:
#             df['Upper_band'][ii] = min(
#                 df['Upper_band_start'][ii], df['Upper_band'][ii - 1]
#             )
#         else:
#             df['Upper_band'][ii] = df['Upper_band_start'][ii]
#
#             # Lower_band
#     for ij in range(timeperiod, df.shape[0]):
#         if df['close'][ij - 1] >= df['Lower_band'][ij - 1]:
#             df['Lower_band'][ij] = max(
#                 df['Lower_band_start'][ij], df['Lower_band'][ij - 1]
#             )
#         else:
#             df['Lower_band'][ij] = df['Lower_band_start'][ij]
#
#             # SuperTrend
#     for ik in range(1, len(df['SuperTrend'])):
#         if df['close'][timeperiod - 1] <= df['Upper_band'][timeperiod - 1]:
#             df['SuperTrend'][timeperiod - 1] = df['Upper_band'][timeperiod - 1]
#         elif df['close'][timeperiod - 1] > df['Upper_band'][ik]:
#             df = df.fillna(0)
#             df['SuperTrend'][timeperiod - 1] = df['Lower_band'][timeperiod - 1]
#     for sp in range(timeperiod, df.shape[0]):
#         if (
#             df['SuperTrend'][sp - 1] == df['Upper_band'][sp - 1]
#             and df['close'][sp] <= df['Upper_band'][sp]
#         ):
#             df['SuperTrend'][sp] = df['Upper_band'][sp]
#         elif (
#             df['SuperTrend'][sp - 1] == df['Upper_band'][sp - 1]
#             and df['close'][sp] >= df['Upper_band'][sp]
#         ):
#             df['SuperTrend'][sp] = df['Lower_band'][sp]
#         elif (
#             df['SuperTrend'][sp - 1] == df['Lower_band'][sp - 1]
#             and df['close'][sp] >= df['Lower_band'][sp]
#         ):
#             df['SuperTrend'][sp] = df['Lower_band'][sp]
#         elif (
#             df['SuperTrend'][sp - 1] == df['Lower_band'][sp - 1]
#             and df['close'][sp] <= df['Lower_band'][sp]
#         ):
#             df['SuperTrend'][sp] = df['Upper_band'][sp]
#     # return supertrend only
#     return df['SuperTrend']


def chop_zone(dataframe, length=30):
    """
    PineScript to Python conversion.
    """
    color_dict = {
        'dark_red': 'dark_red',
        'red': 'red',
        'orange': 'orange',
        'light_orange': 'light_orange',
        'yellow': 'yellow',
        'turquoise': 'turquoise',
        'dark_green': 'dark_green',
        'pale_green': 'pale_green',
        'lime': 'lime',
    }
    # source = close
    df: pd.DataFrame = dataframe.copy(deep=True)
    source = dataframe['close']
    # avg = hlc3
    avg = pta.hlc3(dataframe['high'], dataframe['low'], dataframe['close'])
    # print('avg', avg.head())
    # highestHigh
    df['highestHigh'] = df['high'].rolling(length).max()
    # lowestLow = ta.lowest(periods)
    df['lowestLow'] = df['low'].rolling(length).min()
    # print('lowestLow', df['lowestLow'].tail())
    # print('highestHigh', df['highestHigh'].tail())
    # span = 25 / (highestHigh - lowestLow) * lowestLow
    df['span'] = 25 / (df['highestHigh'] - df['lowestLow']) * df['lowestLow']
    # ema34 = ta.ema(source, 34)
    df['ema34'] = ta.EMA(source, 34)
    # print('span', df['span'].tail())
    # print('ema34', df['ema34'].tail())
    # y2_ema34 = (ema34[1] - ema34) / avg * span
    df['y2_ema34'] = (df['ema34'].shift(1) - df['ema34']) / avg * df['span']
    # print('y2_ema34', df['y2_ema34'].tail())
    # c_ema34 = math.sqrt((x2_ema34 - x1_ema34)*(x2_ema34 - x1_ema34) + (y2_ema34 - y1_ema34)*(y2_ema34 - y1_ema34))
    df['c_ema34'] = np.sqrt(1 + (df['y2_ema34'] ** 2))
    # print('c_ema34', df['c_ema34'].tail())
    # emaAngle_1 = math.round(180 * math.acos((x2_ema34 - x1_ema34)/c_ema34) / pi)
    df['emaAngle_1'] = np.round(180 * np.arccos(1 / df['c_ema34']) / np.pi)
    # emaAngle = if y2_ema34 is greater than 0, make it negative.
    df['emaAngle'] = np.where(df['y2_ema34'] > 0, -df['emaAngle_1'], df['emaAngle_1'])
    # print('emaAngle', df['emaAngle'].tail())
    # chopZoneColor = emaAngle >= 5 ? colorTurquoise :
    # emaAngle < 5 and emaAngle >= 3.57 ? colorDarkGreen :
    # emaAngle < 3.57 and emaAngle >= 2.14 ? colorPaleGreen :
    # emaAngle < 2.14 and emaAngle >= .71 ? colorLime :
    # emaAngle <= -1 * 5 ? colorDarkRed :
    # emaAngle > -1 * 5 and emaAngle <= -1 * 3.57 ? colorRed :
    # emaAngle > -1 * 3.57 and emaAngle <= -1 * 2.14 ? colorOrange :
    # emaAngle > -1 * 2.14 and emaAngle <= -1 * .71 ? colorLightOrange : colorYellow
    df.loc[(df['emaAngle'] >= 5), 'color'] = color_dict['turquoise']
    df.loc[(df['emaAngle'] < 5) & (df['emaAngle'] >= 3.57), 'color'] = color_dict[
        'dark_green'
    ]
    df.loc[(df['emaAngle'] < 3.57) & (df['emaAngle'] >= 2.14), 'color'] = color_dict[
        'pale_green'
    ]
    df.loc[(df['emaAngle'] < 2.14) & (df['emaAngle'] >= 0.71), 'color'] = color_dict[
        'lime'
    ]
    df.loc[
        (df['emaAngle'] > -1 * 5) & (df['emaAngle'] <= -1 * 3.57), 'color'
    ] = color_dict['red']
    df.loc[
        (df['emaAngle'] > -1 * 3.57) & (df['emaAngle'] <= -1 * 2.14), 'color'
    ] = color_dict['orange']
    df.loc[
        (df['emaAngle'] > -1 * 2.14) & (df['emaAngle'] <= -1 * 0.71), 'color'
    ] = color_dict['light_orange']
    df.loc[df['emaAngle'] < -1 * 0.71, 'color'] = color_dict['yellow']
    df.loc[df['emaAngle'] <= -1 * 5, 'color'] = color_dict['dark_red']
    return df['color']


def supertrend(dataframe: DataFrame, multiplier, period):
    dataframe = dataframe.copy()
    supertrend = pta.supertrend(
        dataframe['high'],
        dataframe['low'],
        dataframe['close'],
        length=20,
        multiplier=3,
    )
    dataframe['supertrend_crossover'] = (
        supertrend.iloc[:, 1].rolling(3).mean().round(3) == -0.333
    )
    return dataframe['supertrend_crossover'].astype(int)


if __name__ == '__main__':
    # fill dataframe with fake ohlc data from zero to 100
    df = DataFrame(
        {
            'open': list(random.randint(0, 100) for _ in range(1000)),
            'high': list(random.randint(0, 100) for _ in range(1000)),
            'low': list(random.randint(0, 100) for _ in range(1000)),
            'close': list(random.randint(0, 100) for _ in range(1000)),
        }
    )

    s = supertrend(df, 3, 20)
    print(s[s != 0])
