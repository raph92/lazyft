# LazyFT

LazyFT is convenient [FreqTrade](https://github.com/freqtrade/freqtrade) wrapper that makes developing and testing strategies a lot easier for me. My hope is that it will do the same for you.

The features include but are not limited to:

- **Automatic data downloading** - LFT will always know when you need to download data, so no more worrying about that.
- **Backtest and Hyperopt Repository** - LFT keeps track of every hyperopt and backtest you save so that you can easily reference them later.
- **Hyperopt IDs** - LFT will automatically remove and add the appropriate parameters based on the IDs you pass to a backtest.
- **Space Handler** - LFT supports creating custom spaces for strategies that extends the kind of optimizations you can do.
- **Automatic strategy versioning** - LFT will automatically save a copy of the your strategy after a hyperopt that you can easily retrieve even after you've made changes to your strategy.
- Easily access pairlist and other config settings from previous runs.
- Get notifications when your hyperopt is completed.
- and more!

## Getting Stated

### Installation

#### Install in existing FreqTrade environment

`pip install https://github.com/raph92/lazyft/archive/refs/heads/runner.zip`

#### Quick start in new environment

```bash
git clone https://github.com/raph92/lazyft.git
cd lazyft
pip install -e .
lft init
```

### Directory

#### Config Files

LFT expects FreqTrade config files to be in the **./configs** folder. It will ask to automatically create **./config** on it's first run. It will also attempt to detect and automatically move all config files to the **./configs** folder.

#### User Data

LFT also expects a **./user_data** folder in the base directory.

## Backtest

```python
from lazyft.command_parameters import BacktestParameters


bp = BacktestParameters(
    config_path='config.json',
    days=90,
    download_data=True,
    max_open_trades=3,
    interval='1h',
    starting_balance=100,
    stake_amount='unlimited',
)
backtest_runner = bp.run('Strategy')
```

Now LFT will check to see if any pair data is missing and then proceed to run the backtest.

### Important Things to Know About Backtests

#### Parameters

The **days** parameter will automatically be split into 2/3rds for the hyperopt and 1/3rd for backtesting.
To bypass this you can use the **timerange** parameter like you normally would in freqtrade: `timerange='20220101-20220131'` or `timerange='20220101-'`.

The **config_path** can be a string or a [Config](https://github.com/raph92/lazyft/blob/runner/lazyft/config.py#L18) object. It will automatically search the **configs/** directory for the specified config file.

The [BacktestRunner](https://github.com/raph92/lazyft/blob/runner/lazyft/backtest/runner.py#L95) class will have a [BacktestReport](https://github.com/raph92/lazyft/blob/runner/lazyft/models/backtest.py#L75) attribute that will be saved after a successful run. This can be accessed by **backtest_runner.report**.

You can save a run by calling **backtest_runner.save()** and the run will be logged to the database **lazyft.db** in your working directory. The reports can then by accessed in aggregate using the [RepoExplorer](https://github.com/raph92/lazyft/blob/runner/lazyft/reports.py#L45). You can directly access all backtest through [get_backtest_repo().get(<report_id>)](https://github.com/raph92/lazyft/blob/runner/lazyft/reports.py#L454).

```python
get_backtest_repo().df()
```

|  id | strategy | hyperopt_id | date              | exchange | m_o_t | stake     | balance | n_pairlist | avg_profit_pct | avg_duration | wins | losses |  sortino |  drawdown | total_profit_pct | total_profit | trades | days | tag               |
| --: | :------- | ----------: | :---------------- | :------- | ----: | :-------- | ------: | ---------: | -------------: | :----------- | ---: | -----: | -------: | --------: | ---------------: | -----------: | -----: | ---: | :---------------- |
|   4 | Strategy |             | 06/01/22 15:32:28 | binance  |     3 | unlimited |     100 |         29 |        0.12113 | 11:52:00     |    2 |     13 | 0.545416 | 0.0251296 |           0.0053 |         0.53 |     16 |   29 | 20220503-20220601 |

### Hyperopt

The [hyperopt API](https://github.com/raph92/lazyft/blob/runner/lazyft/command_parameters.py#L205) works the same way the Backtest does except that it has extra parameters.

```python
h_params = HyperoptParameters(
    epochs=20,
    config_path='config.json',
    days=30,
    spaces="buy sell",
    loss='CalmarHyperOptLoss',
    interval='1h',
    min_trades=100,
    starting_balance=100,
    max_open_trades=3,
    stake_amount=100,
    jobs=-2,
    download_data=True,
)

h_params.run('Strategy', background=True)
report = h_params.save()

```

Passing the **background** parameter to `h_params.run()` will allow the hyperopt to run in a separate thread. This is useful when running in jupyter notebooks.

Similar to the backtest, you can access the [hyperopt report](https://github.com/raph92/lazyft/blob/runner/lazyft/models/hyperopt.py#L81) via `h_params.report`.

#### Epochs

You can access a specific epoch within the hyperopt as follows:
`h_runner.report.show_epoch(<n>)`, **n** being the epoch number to show.

You can also quickly create a new report from the specific epoch: `report.new_report_from_epoch(n)`

Again, you can access previous hyperopts through the repo:

```python
get_hyperopt_repo().df()
```

|   id | strategy   | date              | exchange   |   m_o_t | stake     |   balance |   n_pairlist |   avg_profit_pct | avg_duration   |   wins |   losses |   drawdown |   total_profit_pct |   total_profit |   trades |   days | tag                       |
|-----:|:-----------|:------------------|:-----------|--------:|:----------|----------:|-------------:|-----------------:|:---------------|-------:|---------:|-----------:|-------------------:|---------------:|---------:|-------:|:--------------------------|
|    1 | InverseV2  | 06/01/22 15:31:47 | binance    |       3 | unlimited |       100 |           29 |         0.704275 | 11:14:00       |      7 |       21 |  0.0351595 |          0.0711687 |           7.12 |       31 |     51 | 20220303-20220502,default |
