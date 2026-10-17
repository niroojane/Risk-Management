"""Rolling optimization backtest: core strategy + tactical overlays.

Port of the Crypto App notebook's 'Get Results' (`get_result`): the strategy is
re-optimized on each rebalancing period, overlays are blended in with their
weight limits, and the resulting Fund / Core / Overlay schedules are simulated
on the full price history.
"""
import warnings
from concurrent.futures import ThreadPoolExecutor
from os import cpu_count
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .rebalancing import rebalanced_dynamic_quantities, rebalanced_portfolio
from .risk_metrics import (
    RiskAnalysis,
    beta_constraint,
    build_constraint,
    compute_per_asset_betas,
    information_ratio_constraint,
    tracking_error_constraint,
    vol_constraint,
)

RELATIVE_OBJECTIVES = {'tracking_error', 'information_ratio'}
ANCHOR_OFFSETS = {
    'Monthly': pd.offsets.BMonthEnd(),
    'Quarterly': pd.offsets.BQuarterEnd(),
    'Yearly': pd.offsets.BYearEnd(),
}


def anchor_dates(prices: pd.DataFrame, returns: pd.DataFrame, frequency: str) -> List[pd.Timestamp]:
    """Rebalancing anchors: the trading day nearest to each business period end, plus the last date."""
    offset = ANCHOR_OFFSETS.get(frequency, pd.offsets.BMonthEnd())
    candidates = pd.DatetimeIndex(sorted(set(prices.index + offset)))
    if candidates.empty:
        candidates = pd.DatetimeIndex([returns.index[-1]])
    idx = np.asarray(returns.index.get_indexer(candidates, method='nearest'))
    selected = returns.index[idx[idx >= 0]].tolist()
    return sorted(set(selected + [returns.index[-1]]))


def window_constraints(
    subset: pd.DataFrame,
    weight_constraints: list,
    risk_constraints: Dict[str, Tuple[str, float]],
    bench_weights: Optional[pd.Series],
    bench_returns: Optional[pd.Series],
) -> list:
    """Weight constraints + the risk constraints estimated on this window"""
    constraints = list(weight_constraints)
    if 'volatility' in risk_constraints:
        sign, limit = risk_constraints['volatility']
        constraints += vol_constraint(subset.cov(), sign, limit)
    if bench_returns is not None and 'beta' in risk_constraints:
        sign, limit = risk_constraints['beta']
        constraints += beta_constraint(compute_per_asset_betas(subset, bench_returns), sign, limit)
    if bench_weights is not None and 'tracking_error' in risk_constraints:
        sign, limit = risk_constraints['tracking_error']
        constraints += tracking_error_constraint(subset.cov(), bench_weights, sign, limit)
    if bench_weights is not None and 'information_ratio' in risk_constraints:
        sign, limit = risk_constraints['information_ratio']
        constraints += information_ratio_constraint(subset, bench_weights, sign, limit)
    return constraints


def run_backtest(
    prices: pd.DataFrame,
    objective: str,
    frequency: str = 'Monthly',
    overlays: Sequence[Tuple[str, float]] = (),
    weight_constraints: Sequence[Tuple[str, str, float]] = (),
    risk_constraints: Optional[Dict[str, Tuple[str, float]]] = None,
    bench_weights: Optional[pd.Series] = None,
    benchmark: Tuple[str, str] = ('Bitcoin', 'BTCUSDT'),
    model_row: int = -2,
    calendar_annualization: bool = False,
) -> dict:
    """Rolling optimization of `objective` blended with `overlays` [(objective, weight)].

    Returns the Fund (final), Core and Overlay weight schedules, the Model
    allocation (`model_row`: -2 = last complete period as the Crypto App,
    -1 = last row as the Multi Asset App), their simulated values and the
    metrics table shown by the notebook. `benchmark` = (series name, ticker).
    """
    risk_constraints = risk_constraints or {}
    returns = prices.pct_change(fill_method=None)
    columns = prices.columns

    wanted = {objective} | {name for name, _ in overlays}
    if bench_weights is None and wanted & RELATIVE_OBJECTIVES:
        raise ValueError("Min Tracking Error / Max Information Ratio need a benchmark allocation")
    if bench_weights is not None:
        bench_weights = bench_weights.reindex(columns).fillna(0.0)

    overlay_total = sum(limit for _, limit in overlays)
    if overlay_total > 1 + 1e-9:
        raise ValueError("Overlay weights exceed 100%")
    core_weight = max(1 - overlay_total, 0.0)

    rows = [list(c) for c in weight_constraints]
    weight_cons = build_constraint(prices, np.array(rows, dtype=object)) if rows else []

    # Benchmark's realized returns over the full history, computed once for the beta constraints
    bench_returns = None
    if bench_weights is not None and risk_constraints:
        bench_returns = rebalanced_portfolio(prices, bench_weights, frequency=frequency).sum(axis=1).pct_change()

    dates = anchor_dates(prices, returns, frequency)
    if len(dates) < 2:
        raise ValueError("Not enough anchor dates to perform a rolling optimization")

    failures: List[str] = []

    def worker(subset, strategy):
        if subset.empty or len(subset) < 2:
            return None
        constraints = window_constraints(subset, weight_cons, risk_constraints, bench_weights, bench_returns)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            weights = RiskAnalysis(subset).optimize(
                objective=strategy,
                constraints=constraints or False,
                bench_weights=bench_weights if strategy in RELATIVE_OBJECTIVES else None,
            )
        if caught:
            failures.append(strategy)
        return subset.index[-1], np.round(weights, 6), strategy

    tasks = [(returns.loc[dates[i]:dates[i + 1]], strategy)
             for strategy in [objective] + [name for name, _ in overlays]
             for i in range(len(dates) - 1)]
    results: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        for out in executor.map(lambda task: worker(*task), tasks):
            if out is not None:
                date, weights, strategy = out
                results.setdefault(strategy, {})[date] = weights

    if objective not in results:
        raise ValueError("The optimization failed on every period")

    periods = len(dates) - 1
    messages = [
        f"{strategy}: the optimizer did not converge on {failures.count(strategy)} of {periods} periods "
        f"-- those weights may not satisfy every constraint."
        for strategy in dict.fromkeys(failures)
    ]

    def schedule(strategy):
        return pd.DataFrame(results[strategy], index=columns).T.sort_index()

    core = schedule(objective)
    overlay = pd.DataFrame(0.0, index=core.index, columns=columns)
    for name, limit in overlays:
        overlay = overlay.add(schedule(name) * limit, fill_value=0)
    final = core * core_weight + overlay

    first_row = pd.DataFrame([np.full(len(columns), 1 / len(columns))], index=[dates[0]], columns=columns)
    denominator = (1 - core_weight) if core_weight < 1 else 1
    final = pd.concat([first_row, final])
    core = pd.concat([first_row, core])
    overlay = pd.concat([first_row, overlay / denominator])

    schedules = {'Fund': final, 'Core': core, 'Overlay': overlay if overlays else None}
    values = pd.DataFrame({
        name: (rebalanced_dynamic_quantities(prices, matrix) * prices).sum(axis=1)
        for name, matrix in schedules.items() if matrix is not None
    })
    benchmark_name, benchmark_ticker = benchmark
    if benchmark_ticker in prices.columns:
        values[benchmark_name] = prices[benchmark_ticker]

    metrics = (calendar_backtest_metrics(values, benchmark_name) if calendar_annualization
               else backtest_metrics(values, returns, benchmark_name))
    return {
        'schedules': schedules,
        'model': final.iloc[model_row] if len(final) >= abs(model_row) else final.iloc[-1],
        'metrics': metrics,
        'warnings': messages,
    }


def calendar_backtest_metrics(values: pd.DataFrame, benchmark: str = 'Benchmark') -> pd.DataFrame:
    """Multi Asset App version: return, annualized return over calendar years,
    volatility, Sharpe ratio, drawdown and tracking errors"""
    performance = values.pct_change(fill_method=None)
    cumulative = (1 + performance.fillna(0)).cumprod() * 100
    drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax()

    n_years = max((values.index[-1] - values.index[0]).days / 365.25, 1e-9)
    total_return = values.apply(lambda s: s.dropna().iloc[-1] / s.dropna().iloc[0] - 1)

    metrics = pd.DataFrame(index=values.columns)
    metrics['Returns'] = total_return
    metrics['Annualized Return'] = (1 + total_return) ** (1 / n_years) - 1
    metrics['Volatility'] = performance.std() * np.sqrt(252)
    metrics['Sharpe Ratio'] = metrics['Annualized Return'] / metrics['Volatility']
    metrics['Drawdown'] = drawdown.min()
    metrics['Date Drawdown'] = drawdown.idxmin().dt.date
    if benchmark in performance.columns:
        excess = performance.drop(columns=benchmark).sub(performance[benchmark], axis=0)
        metrics[f'Tracking Error to {benchmark}'] = excess.std() * np.sqrt(252)
    excess_core = performance.drop(columns='Core').sub(performance['Core'], axis=0)
    metrics['Tracking Error to Core'] = excess_core.std() * np.sqrt(252)
    return metrics.fillna(0).T


def backtest_metrics(values: pd.DataFrame, returns: pd.DataFrame, benchmark: str = 'Bitcoin') -> pd.DataFrame:
    """Return, volatility, Sharpe ratio, drawdown and tracking errors of the backtest series"""
    performance = values.pct_change(fill_method=None)
    cumulative = (1 + performance).cumprod() * 100
    drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax()

    metrics = pd.DataFrame()
    metrics['Returns'] = values.iloc[-2] / values.iloc[0] - 1
    metrics['Volatility'] = performance.std() * np.sqrt(252)
    annualized = (1 + metrics['Returns']) ** (1 / len(set(returns.index.year))) - 1
    metrics['Sharpe Ratio'] = annualized / metrics['Volatility']
    metrics['Drawdown'] = drawdown.min()
    metrics['Date Drawdown'] = drawdown.idxmin().dt.date
    for bench in (benchmark, 'Core'):
        if bench in performance.columns:
            excess = performance.loc[:, performance.columns != bench].sub(performance[bench], axis=0)
            metrics[f'Tracking Error to {bench}'] = excess.std() * np.sqrt(252)
    return metrics.fillna(0).T
