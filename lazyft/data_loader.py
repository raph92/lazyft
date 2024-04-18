from typing import Union, Optional

import pandas as pd
from diskcache import Cache
from freqtrade.configuration import TimeRange
from freqtrade.data.history import load_pair_history
from freqtrade.strategy import merge_informative_pair

from lazyft import logger, paths
from lazyft.config import Config
from lazyft import downloader
from lazyft.paths import PAIR_DATA_DIR
from lazyft.strategy import load_strategy

cache = Cache(paths.CACHE_DIR)


def load_pair_data(
    pair: str,
    timeframe: str,
    config: Config,
    timerange=None,
    startup_candles=0,
    download: bool = True
) -> pd.DataFrame:
    """
    Loads the pair from the exchange and returns a pandas dataframe

    :param pair: The pair to load
    :param timeframe: The timeframe to load
    :param config: The config object
    :param timerange: The timerange to load data for
    :param startup_candles: The number of candles to load before the timerange
    :param download: Whether to download data from the exchange
    :return: A DataFrame with the OHLCV data.
    """

    cache_key = f"{pair}_{timeframe}_{config.exchange}_{timerange}"
    
    # Check if data is already cached
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Using cached data for {pair} {timeframe} {config.exchange} {timerange}")
        return cached_data

    def fetch_data(pair, timeframe, exchange, timerange):
        if timerange and download:
            downloader.download_pair(
                pair.upper(), intervals=[timeframe], timerange=timerange, config=config
            )
        return load_pair_history(
            datadir=PAIR_DATA_DIR.joinpath(exchange),
            timeframe=timeframe,
            pair=pair.upper(),
            data_format="json",
            timerange=TimeRange.parse_timerange(timerange) if timerange else None,
            startup_candles=startup_candles,
        )

    data = fetch_data(pair, timeframe, config.exchange, timerange)
    if not data.empty:
        cache.set(cache_key, data, expire=60 * 30, tag="data_loader.load_pair_data")
        logger.info(f"Cached data for {pair} {timeframe} {config.exchange} {timerange}")
    else:
        assert not data.empty, f"Data for {pair} {timeframe} {config.exchange} {timerange} is empty"
    logger.info(
        f"Loaded {len(data)} rows for {pair} @ timeframe {timeframe}, data starts at "
        f'{data.iloc[0]["date"]}'
    )
    return data


def load_and_populate_pair_data(
    strategy_name: str, pair: str, timeframe: str, config: Config, timerange=None
) -> pd.DataFrame:
    """
    Loads pair data, populates indicators, and returns the dataframe

    :param strategy_name: The name of the strategy to load
    :param pair: The pair to load data for
    :param timeframe: The timeframe to load data for
    :param config: The config object
    :param timerange: A TimeRange object
    :return: A dataframe with the populated data
    """
    data = load_pair_data(pair, timeframe, config, timerange=timerange)
    from lazyft import BASIC_CONFIG

    strategy = load_strategy(strategy_name, BASIC_CONFIG)
    populated = strategy.advise_all_indicators({pair: data})
    return populated[pair]


def load_pair_data_for_each_timeframe(
    pair: str, 
    timerange: str, 
    timeframes: list[str], 
    config: Config, 
    column=None, 
    download: bool = True  # New parameter to control downloading
) -> Union[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Loads the data for a given pair, for each timeframe in the given list of timeframes, for the given
    timerange. If a column is specified, the data is returned as a DataFrame with the appropriate
    "{column}_{timeframe}" column for each dataframe.

    :param pair: The pair you want to load data for
    :param timerange: the range of time to load data for
    :param timeframes: list of timeframes to load data for
    :param config: the config object
    :param column: the column to load data for.
    :param download: Whether to download data from the exchange
    :return: A list of dataframes
    """
    merged = load_pair_data(pair, timeframes[0], config, timerange=timerange, download=download)
    for tf in timeframes[1:]:
        merged = merge_informative_pair(
            merged, load_pair_data(pair, tf, config, timerange=timerange, download=download), timeframes[0], tf
        )
    logger.info(merged.describe())
    if column:
        # get all columns in merged that contain the column
        columns = [col for col in merged.columns if column in col]
        df_with_columns = merged[columns]
        return df_with_columns
    return merged


def get_all_pair_data(
    config: Config,
    pairlist: Optional[list[str]] = None,
    days=None,
    timerange: Optional[str] = None,
    timeframe: str = "1h",
    download: bool = True,
):
    """
    Get all pair data from the provided pair list or config whitelist for a given amount of days or a timerange.

    :param config: A config file object
    :param days: How many days worth of data to download
    :param timerange: Optional timerange parameter
    :param timeframe: The timeframe for which to download and load the data
    :param download: Whether to download the data
    :return: A dictionary with pair as key and its data as value
    """
    pair_data = {}
    pairs = pairlist if pairlist is not None else config.whitelist

    # Use the provided pairlist or fallback to config.whitelist if pairlist is None

    for pair in pairs:
        # Load the data into a DataFrame
        data = load_pair_data(pair, timeframe, config, timerange, download=download)
        pair_data[pair] = data
    return pair_data


if __name__ == "__main__":
    print(load_pair_data_for_each_timeframe("BTC/USDT", "20220101-", ["1h", "2h", "4h", "8h"]))
