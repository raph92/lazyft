import pathlib

BASE_DIR = pathlib.Path.cwd().resolve()
LOG_DIR = BASE_DIR.joinpath('logs')
LOG_DIR.mkdir(exist_ok=True)
CONFIG_DIR = BASE_DIR.joinpath('configs')
USER_DATA_DIR = BASE_DIR.joinpath('user_data')
STRATEGY_DIR = USER_DATA_DIR.joinpath('strategies')
LAST_HYPEROPT_RESULTS_FILE = USER_DATA_DIR.joinpath('hyperopt_results', '.last_result.json')
ENSEMBLE_FILE = STRATEGY_DIR.joinpath('ensemble.json')
HYPEROPT_LOG_PATH = LOG_DIR.joinpath('hyperopt_logs/')
HYPEROPT_LOG_PATH.mkdir(exist_ok=True)
BACKTEST_LOG_PATH = LOG_DIR.joinpath('backtest_logs/')
BACKTEST_LOG_PATH.mkdir(exist_ok=True)
PAIR_DATA_DIR = USER_DATA_DIR.joinpath('data')
