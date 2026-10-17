"""Portfolio construction and risk analytics.

Ported from the legacy `src/RiskMetrics.py` module (Risk Management project).
The computations are unchanged; only notebook-specific side effects were
removed (prints replaced by logging, unused imports dropped).
"""
import logging
import warnings

import numpy as np
import pandas as pd
import scipy.optimize as sco
from joblib import Parallel, delayed
from scipy.optimize import minimize
from scipy.special import xlogy
from scipy.stats import chi2, norm
from statsmodels.stats.correlation_tools import cov_nearest

logger = logging.getLogger(__name__)


# =============================================================================
# General functions
# =============================================================================

def compute_rolling_per_asset_betas(returns_window, benchmark_return_series, window):
    """Rolling per-asset beta (slope of each asset's return vs. a benchmark
    return series), computed as rolling covariance / rolling variance.

    Same definition as `compute_per_asset_betas` (cov(asset, bench) /
    var(bench)), vectorized across the whole history in one pass.
    """
    common_index = returns_window.index.intersection(benchmark_return_series.index)
    returns_aligned = returns_window.loc[common_index]
    benchmark_aligned = benchmark_return_series.loc[common_index]

    rolling_cov = returns_aligned.rolling(window).cov(benchmark_aligned)
    rolling_var = benchmark_aligned.rolling(window).var()
    return rolling_cov.div(rolling_var, axis=0)


def compute_per_asset_betas(returns_window, benchmark_return_series):
    """Simple-regression beta of each asset in `returns_window` vs. a benchmark.

    `benchmark_return_series` should already be a return series, not raw
    prices/levels. Returns a numpy array of length `returns_window.shape[1]`,
    one beta per asset column, in the same column order as `returns_window`.

    beta_i = cov(asset_i, bench) / var(bench), each asset over the dates where
    both it and the benchmark have a return. 0 where it can't be estimated.
    """
    if returns_window.shape[1] == 0 or returns_window.shape[0] < 2:
        return np.zeros(returns_window.shape[1])

    if isinstance(benchmark_return_series, pd.DataFrame):
        # e.g. Portfolio.portfolio(weights): a one-column frame of returns
        benchmark_return_series = benchmark_return_series.iloc[:, 0]
    y = pd.Series(benchmark_return_series).reindex(returns_window.index)
    beta = np.zeros(returns_window.shape[1])
    for i, (_, x) in enumerate(returns_window.items()):
        both = x.notna() & y.notna()
        if both.sum() < 2:
            continue
        var_y = y[both].var()
        if var_y > 0:
            beta[i] = x[both].cov(y[both]) / var_y
    return beta


def performance_contribution(weighted_returns):
    """Cumulative contribution of each asset to the portfolio return."""
    portfolio_return = weighted_returns.sum(axis=1)

    # Wealth index
    wealth = portfolio_return.copy()
    wealth.iloc[0] = 0
    wealth = (1 + wealth).cumprod()

    return (
        weighted_returns
        .mul(wealth.shift(1), axis=0)
        .fillna(0)
        .cumsum()
    )


def drawdown_contribution(weighted_returns):
    """Contribution of each asset to the running drawdown (Frongello linking)."""
    portfolio_return = weighted_returns.sum(axis=1)

    # Wealth index and high-water mark
    wealth = (1 + portfolio_return).cumprod()
    peak = wealth.cummax()

    # Identify drawdown regimes
    regime = peak.ne(peak.shift()).cumsum()

    contribution_to_drawdown = pd.DataFrame(
        0.0,
        index=weighted_returns.index,
        columns=weighted_returns.columns
    )

    for _, idx in weighted_returns.groupby(regime).groups.items():
        r = weighted_returns.loc[idx]
        rp = portfolio_return.loc[idx]

        # Frongello linking factor: product of (1 + rp) AFTER date t
        cum_factor = (1 + rp).cumprod()
        total_factor = cum_factor.iloc[-1]
        factor = total_factor / cum_factor
        factor = factor.shift(-1, fill_value=1.0)

        contribution_to_drawdown.loc[idx] = r.mul(factor, axis=0).cumsum()

    return contribution_to_drawdown.ffill()


def get_var_contribution(func_name, args, returns, weights_series,
                         window=252, var_centile=0.05, n_jobs=-1):
    """Rolling simulated VaR / CVaR (portfolio and per-asset) using the
    `RiskAnalysis` simulation `func_name` on each `window`."""

    def process_window(i):
        try:
            subset = returns.iloc[i:i + window]
            weights = weights_series.loc[subset.index[-1]]

            portfolio = RiskAnalysis(subset.loc[:, weights.index])
            func = getattr(portfolio, func_name)

            if func_name == 'monte_carlo':
                distrib = pd.DataFrame(func(*args)[1], columns=portfolio.returns.columns)
            else:
                distrib = pd.DataFrame(func(*args), columns=portfolio.returns.columns)

            distrib = distrib.mul(weights, axis=1)
            distrib['Portfolio'] = distrib.sum(axis=1)
            var = distrib.sort_values(by='Portfolio').iloc[int(distrib.shape[0] * var_centile)]
            cvar = distrib.loc[distrib['Portfolio'] < var['Portfolio']].mean()

        except Exception:
            logger.exception("VaR contribution failed at window %s", i)
            raise
        return subset.index[-1], var, cvar

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)  # +1: the last window ends on the latest date
    )

    dico_results_var = {date: var for date, var, _ in results}
    dico_results_cvar = {date: cvar for date, _, cvar in results}

    var_dataframe = pd.DataFrame.from_dict(dico_results_var, orient='index').sort_index()
    cvar_dataframe = pd.DataFrame.from_dict(dico_results_cvar, orient='index').sort_index()

    return var_dataframe, cvar_dataframe


def get_ex_ante_vol(weights_series, returns, window=252, n_jobs=-1):
    """Rolling ex-ante annualized volatility for time-varying weights."""

    def process_window(i):
        subset = returns.iloc[i:i + window]
        weights = weights_series.loc[subset.index[-1]]
        weights = weights[weights != 0]

        portfolio_class = RiskAnalysis(subset.loc[:, weights.index])
        return subset.index[-1], portfolio_class.variance(weights)

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)
    )

    return pd.DataFrame.from_dict(dict(results), orient='index').sort_index()


def get_ex_ante_vol_contribution_in_pct(weights_series, returns, window=252, n_jobs=-1):
    """Rolling per-asset contribution to ex-ante volatility, in %."""

    def process_window(i):
        subset = returns.iloc[i:i + window]
        weights = weights_series.loc[subset.index[-1]]
        weights = weights[weights != 0]
        portfolio_class = RiskAnalysis(subset.loc[:, weights.index])
        return subset.index[-1], portfolio_class.var_contrib_pct(weights)['Vol Contribution in %']

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)
    )

    dataframe = pd.DataFrame.from_dict(dict(results), orient='index').sort_index()
    dataframe['Total Vol in %'] = dataframe.sum(axis=1)

    return dataframe


def get_ex_ante_vol_contribution(weights_series, returns, window=252, n_jobs=-1):
    """Rolling per-asset contribution to ex-ante volatility."""

    def process_window(i):
        subset = returns.iloc[i:i + window]
        weights = weights_series.loc[subset.index[-1]]
        weights = weights[weights != 0]
        portfolio_class = RiskAnalysis(subset.loc[:, weights.index])
        return subset.index[-1], portfolio_class.var_contrib(weights)[0]['Vol Contribution']

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)
    )

    dataframe = pd.DataFrame.from_dict(dict(results), orient='index').sort_index()
    dataframe['Total Vol'] = dataframe.sum(axis=1)

    return dataframe


def get_correlation_contribution(weights_series, returns, window=252, n_jobs=-1):
    """Rolling per-asset correlation part of the ex-ante volatility."""

    def process_window(i):
        subset = returns.iloc[i:i + window]
        weights = weights_series.loc[subset.index[-1]]
        weights = weights[weights != 0]
        portfolio_class = RiskAnalysis(subset.loc[:, weights.index])
        return subset.index[-1], portfolio_class.var_contrib(weights)[0]['Correlation']

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)
    )

    dataframe = pd.DataFrame.from_dict(dict(results), orient='index').sort_index()
    dataframe['Total Correlation'] = dataframe.sum(axis=1)

    return dataframe


def get_idiosyncratic_contribution(weights_series, returns, window=252, n_jobs=-1):
    """Rolling per-asset idiosyncratic part of the ex-ante volatility."""

    def process_window(i):
        subset = returns.iloc[i:i + window]
        weights = weights_series.loc[subset.index[-1]]
        weights = weights[weights != 0]
        portfolio_class = RiskAnalysis(subset.loc[:, weights.index])
        return subset.index[-1], portfolio_class.var_contrib(weights)[0]['Idiosyncratic Risk']

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0] - window + 1)
    )

    dataframe = pd.DataFrame.from_dict(dict(results), orient='index').sort_index()
    dataframe['Total Idiosyncratic Vol'] = dataframe.sum(axis=1)

    return dataframe


def first_pca_over_time(returns, window=252, n_jobs=-1):
    """Share of variance explained by the first principal component, rolling."""

    def process_window(i):
        temp = returns.iloc[i:i + window]

        # skip incomplete window
        if temp.shape[0] < window:
            return None

        index = temp.index[-1]
        eig_val, _ = np.linalg.eigh(temp.cov())
        eig_val = eig_val[::-1]
        variance_explained = eig_val / eig_val.sum()

        return index, variance_explained[0]

    results = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(process_window)(i)
        for i in range(returns.shape[0])
    )

    results = [r for r in results if r is not None]
    return pd.DataFrame.from_dict(dict(results), orient='index').sort_index()


def halton_sequences(number, base=2):
    """Halton sequence element `number` in `base`."""
    inv_base = 1 / base
    i = number
    halton = 0

    while i > 0:
        digit = i % base
        halton = halton + digit * inv_base
        i = (i - digit) / base
        inv_base = inv_base / base

    return halton


def generate_halton(iterations, dimensions=1, base=2):
    """Halton sequences in `base`, shuffled per dimension."""
    rng = np.random.default_rng()
    haltons = [halton_sequences(i, base=base) for i in range(iterations)]
    matrix = [haltons for _ in range(dimensions)]
    return rng.permuted(matrix, axis=1)


def is_pos_def(x):
    # eigvalsh on the symmetric part: real eigenvalues, no complex noise from eigvals
    x = np.asarray(x, dtype=float)
    return np.all(np.linalg.eigvalsh((x + x.T) / 2) > 0)


def _nearest_pd(x):
    """cov_nearest returns a PSD matrix whose smallest eigenvalue can be ~0,
    which np.linalg.cholesky rejects; nudge the diagonal until it factors."""
    x = cov_nearest(np.asarray(x, dtype=float))
    jitter = 1e-10 * max(np.mean(np.diag(x)), 1e-12)
    for _ in range(10):
        try:
            np.linalg.cholesky(x)
            return x
        except np.linalg.LinAlgError:
            x = x + np.eye(len(x)) * jitter
            jitter *= 10
    return x


def performance(perf, weights):
    """Daily performance of a portfolio."""
    return np.dot(perf, weights)


def rolling_var(returns, weights, window=30, Q=1):
    """Rolling VaR on a `window`-day window (historical, parametric and
    multivariate models) at the Q-th percentile.

    Each VaR is estimated on the window ENDING THE DAY BEFORE (.shift(1)) and
    compared with that day's return -- otherwise the tested return is inside
    its own estimate.
    """
    value_at_risk = pd.DataFrame()

    mean = returns.rolling(window).mean().dropna()
    cov = returns.rolling(window).cov().dropna()

    index = sorted(tuple(set(cov.index.get_level_values(0))))

    var = {}
    for date in index:
        multivariate_var = performance(
            np.random.multivariate_normal(mean.loc[date], cov.loc[date], 10000), weights
        )
        var[date] = np.percentile(multivariate_var, Q)

    var = pd.Series(var)

    portfolio = Portfolio(returns).portfolio(weights)['Portfolio']

    value_at_risk['Historical'] = portfolio.rolling(window=window).apply(lambda x: np.percentile(x, Q)).shift(1)
    value_at_risk['Parametric'] = (portfolio.rolling(window=window).std() * norm(loc=0, scale=1).ppf(Q / 100)).shift(1)
    value_at_risk['Multivariate'] = var.reindex(portfolio.index).shift(1)
    value_at_risk['Portfolio'] = portfolio

    return value_at_risk.dropna()


def kupiec_test(rolling_var, Q=5):
    """Kupiec proportion-of-failures backtest of each VaR model column."""
    number_obs = rolling_var.shape[0]
    confidence = Q / 100

    stats = {
        'Proportion of failure': [],
        'Kupiec Stat': [],
        'P-value': [],
        'Model': [],
    }

    for col in rolling_var.columns:
        if col == 'Portfolio':
            continue

        number_violation = np.sum(np.where(rolling_var[col] > rolling_var['Portfolio'], 1, 0))
        number_non_violation = number_obs - number_violation
        proportion_violation = number_violation / number_obs
        proportion_non_violation = 1 - proportion_violation

        # log-likelihood ratio in log form: the product of powers underflows to 0
        # for long histories (log(0) = -inf); xlogy handles 0 violations (0*log 0 = 0)
        kupiec = 2 * (xlogy(number_non_violation, proportion_non_violation)
                      + xlogy(number_violation, proportion_violation)
                      - number_non_violation * np.log(1 - confidence)
                      - number_violation * np.log(confidence))

        p_value = 1 - chi2.cdf(kupiec, 1)

        stats['Kupiec Stat'].append(kupiec)
        stats['P-value'].append(p_value)
        stats['Proportion of failure'].append(proportion_violation)
        stats['Model'].append(col)

    stats = pd.DataFrame(stats.values(), index=stats.keys(), columns=stats['Model'])
    return stats.drop(stats.index[3])


# =============================================================================
# Optimization constraints (SLSQP dictionaries)
# =============================================================================

SIGN_MAP = {'=': 'eq', '≥': 'ineq', '≤': 'ineq'}


def create_constraint(sign, limit, position):
    """Bound on the weight of the asset at `position`."""
    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: limit - weights[position]}]
    return [{'type': SIGN_MAP[sign], 'fun': lambda weights: weights[position] - limit}]


def diversification_constraint(sign, limit):
    """Bound applied to every weight."""
    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: limit - weights}]
    return [{'type': SIGN_MAP[sign], 'fun': lambda weights: weights - limit}]


def beta_constraint(beta, sign, limit):
    """Bound on the portfolio beta (weights · per-asset betas)."""
    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: limit - np.dot(weights, beta)}]
    return [{'type': SIGN_MAP[sign], 'fun': lambda weights: np.dot(weights, beta) - limit}]


def vol_constraint(cov_matrix, sign, limit):
    """Bound on the annualized volatility (cov_matrix is daily)."""

    def vol(weights):
        return np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(252)

    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: limit - vol(weights)}]
    return [{'type': SIGN_MAP[sign], 'fun': lambda weights: vol(weights) - limit}]


def tracking_error_constraint(cov_matrix, bench_weights, sign, limit):
    """Annualized tracking-error constraint vs. a benchmark weight vector.

    cov_matrix    : daily covariance of the universe (DataFrame or array)
    bench_weights : benchmark weights over the SAME universe (Series is
                    reindexed on cov_matrix's columns, missing assets -> 0)
    limit         : annualized TE, in decimals (0.05 = 5%)

    Works on TE² instead of TE (no sqrt -> no infinite gradient when the
    weights hit the benchmark, no NaN on a slightly non-PSD covariance),
    normalized by limit² so the constraint is well scaled for SLSQP, and
    passes the analytic Jacobian.
    """
    if isinstance(bench_weights, pd.Series) and isinstance(cov_matrix, pd.DataFrame):
        bench_weights = bench_weights.reindex(cov_matrix.columns).fillna(0.0)

    cov = np.asarray(cov_matrix, dtype=float)
    cov = (cov + cov.T) / 2 * 252
    bench = np.asarray(bench_weights, dtype=float).ravel()

    if bench.shape[0] != cov.shape[0]:
        raise ValueError(f"bench_weights has {bench.shape[0]} assets, cov_matrix has {cov.shape[0]}")

    limit = float(limit)
    if limit < 0:
        raise ValueError("Tracking error limit must be ≥ 0")

    # TE ≥ 0 always holds. For TE ≤ 0 / TE = 0, an exact w = bench equality
    # would clash with the budget constraint (more equalities than weights)
    # and TE² = 0 has a zero gradient, so use a tiny tolerance instead.
    if limit == 0:
        if sign == '≥':
            return []
        limit = 1e-4

    target = limit ** 2

    def te_ratio(weights):
        active = np.asarray(weights) - bench
        return active @ cov @ active / target

    def te_ratio_grad(weights):
        active = np.asarray(weights) - bench
        return 2 * cov @ active / target

    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: 1 - te_ratio(weights),
                 'jac': lambda weights: -te_ratio_grad(weights)}]
    return [{'type': SIGN_MAP[sign], 'fun': lambda weights: te_ratio(weights) - 1,
             'jac': te_ratio_grad}]


def information_ratio_constraint(returns, bench_weights, sign, limit, ann=252):
    """Ex-ante information-ratio constraint vs. a benchmark weight vector.

        IR(w) = active return / tracking error
              = (w - b)·μ·ann / sqrt((w - b)ᵀ Σ (w - b) · ann)

    Imposed without the division: IR ≥ L  <=>  active_return - L·TE ≥ 0,
    which keeps it defined and smooth at w = b. TE is smoothed by a tiny ε so
    its gradient stays finite at w = b. The analytic Jacobian is passed.
    """
    if isinstance(bench_weights, pd.Series):
        bench_weights = bench_weights.reindex(returns.columns).fillna(0.0)
    bench = np.asarray(bench_weights, dtype=float).ravel()
    # same estimates as Portfolio.optimize: NaN returns count as 0
    mu = returns.fillna(0).mean().to_numpy() * ann
    cov = returns.cov().to_numpy() * ann
    cov = (cov + cov.T) / 2

    if bench.shape[0] != mu.shape[0]:
        raise ValueError(f"bench_weights has {bench.shape[0]} assets, returns has {mu.shape[0]}")

    limit = float(limit)
    eps = 1e-12

    def te(weights):
        active = np.asarray(weights) - bench
        return np.sqrt(active @ cov @ active + eps)

    def excess(weights):
        # active return - limit * TE  (>= 0  <=>  IR >= limit)
        return (np.asarray(weights) - bench) @ mu - limit * te(weights)

    def excess_grad(weights):
        active = np.asarray(weights) - bench
        return mu - limit * (cov @ active) / te(weights)

    if sign == '≤':
        return [{'type': SIGN_MAP[sign], 'fun': lambda weights: -excess(weights),
                 'jac': lambda weights: -excess_grad(weights)}]
    return [{'type': SIGN_MAP[sign], 'fun': excess, 'jac': excess_grad}]


def build_constraint(prices, constraint_matrix):
    """SLSQP constraints from rows of (ticker | 'All', sign, limit)."""
    constraints = []

    drop_down_list_asset = list(prices.columns) + ['All']

    for row in range(constraint_matrix.shape[0]):
        temp = constraint_matrix[row, :]
        ticker = temp[0]

        if ticker not in drop_down_list_asset:
            continue

        sign = temp[1]
        limit = float(temp[2])

        if ticker == 'All':
            constraint = diversification_constraint(sign, limit)
        else:
            position = np.where(prices.columns == ticker)[0][0]
            constraint = create_constraint(sign, limit, position)

        constraints.extend(constraint)

    return constraints


def set_symmetric(A, limit):
    """Symmetrize A with the max of each pair, zeroing values ≥ limit."""
    A = A.copy()
    n = A.shape[0]

    for i in range(n):
        for j in range(i + 1, n):
            value = max(A[i, j], A[j, i])
            A[i, j] = A[j, i] = value if value < limit else 0

    return A


# =============================================================================
# Portfolio construction
# =============================================================================

class Portfolio:
    """Portfolio metrics and optimization with various constraints."""

    def __init__(self, returns):
        self.returns = returns

    def inventory(self, weights):
        dico_ptf = dict(zip(self.returns.columns, weights))
        inventory = pd.DataFrame(dico_ptf.values(), index=dico_ptf.keys(), columns=['Weights'])
        return inventory.loc[(inventory != 0).any(axis=1)].sort_values(by='Weights', ascending=False)

    def portfolio(self, weights):
        portfolio = pd.DataFrame()
        portfolio['Portfolio'] = np.sum(weights * self.returns, axis=1)
        return portfolio

    def evolution(self, weights):
        return (1 + self.portfolio(weights)).cumprod() * 100

    def performance(self, weights):
        return np.sum(self.returns * weights, axis=1).mean() * 252

    def variance(self, weights):
        """Annualized volatility (kept as `variance` for compatibility)."""
        return np.sqrt(np.dot(weights.T, np.dot(self.returns.cov(), weights))) * np.sqrt(252)

    def sharpe_ratio(self, weights):
        return self.performance(weights) / self.variance(weights)

    def optimize(self, objective='minimum_variance', constraints=False, bench_weights=None):
        """Long-only, fully-invested weights maximizing / minimizing `objective`:
        minimum_variance, sharpe_ratio, risk_parity, maximum_diversification,
        eigenportfolio, and -- relative to `bench_weights` (benchmark weights
        over the same assets; a Series is matched by ticker, missing -> 0):
          tracking_error     minimum ex-ante tracking error
          information_ratio  maximum ex-ante information ratio
        """
        # Estimated once per optimization -- the objectives below are called
        # hundreds of times by SLSQP. mu matches self.performance()
        # (np.sum over assets treats a NaN return as 0).
        cov = self.returns.cov().values * 252
        mu = self.returns.fillna(0).mean().values * 252
        asset_vol = np.sqrt(np.diag(cov))

        def sum_equal_one(weight):
            return np.sum(weight) - 1

        def variance(weights):
            return weights @ cov @ weights

        def volatility(weights):
            return np.sqrt(variance(weights))

        def sharpe_ratio(weights):
            return - (weights @ mu) / volatility(weights)

        def risk_contrib(weights):
            return weights * (cov @ weights) / volatility(weights)

        def risk_parity(weights):
            RC = risk_contrib(weights)
            total_risk = RC.sum()
            target = total_risk / len(weights)
            return np.sum(((RC - target) / total_risk) ** 2)

        def diversification_ratio(weights):
            port_vol = np.sqrt(weights @ cov @ weights)
            return -(weights @ asset_vol) / port_vol

        def rayleigh_quotient(weights):
            return -np.dot(weights.T, np.dot(cov, weights)) / np.dot(weights.T, weights)

        objectives = {
            'minimum_variance': volatility,
            'sharpe_ratio': sharpe_ratio,
            'risk_parity': risk_parity,
            'maximum_diversification': diversification_ratio,
            'eigenportfolio': rayleigh_quotient,
        }

        n_assets = len(self.returns.columns)
        weight = np.array([1 / n_assets] * n_assets)

        bench = None
        if bench_weights is not None:
            if isinstance(bench_weights, pd.Series):
                bench_weights = bench_weights.reindex(self.returns.columns).fillna(0.0)
            bench = np.asarray(bench_weights, dtype=float).ravel()
            if bench.shape[0] != n_assets:
                raise ValueError(f"bench_weights has {bench.shape[0]} assets, returns has {n_assets}")

        def tracking_variance(weights):
            # TE² (no sqrt: smooth at w = bench); scaled so SLSQP sees O(1) values
            active = weights - bench
            return active @ cov @ active * 100

        def tracking_variance_grad(weights):
            return 2 * cov @ (weights - bench) * 100

        te_eps = 1e-8  # keeps the IR defined at w = bench (TE = 0)

        def information_ratio(weights):
            active = weights - bench
            return - (active @ mu) / np.sqrt(active @ cov @ active + te_eps)

        def information_ratio_grad(weights):
            active = weights - bench
            te = np.sqrt(active @ cov @ active + te_eps)
            return - (mu / te - (active @ mu) * (cov @ active) / te ** 3)

        objectives['tracking_error'] = tracking_variance
        objectives['information_ratio'] = information_ratio
        jacobians = {'tracking_error': tracking_variance_grad, 'information_ratio': information_ratio_grad}
        if objective not in objectives:
            raise ValueError(f"Objective function undefined: {objective!r} (expected one of {sorted(objectives)})")
        if objective in jacobians and bench is None:
            raise ValueError(f"optimize('{objective}') needs bench_weights (the benchmark's weights).")

        if objective == 'information_ratio' and np.allclose(weight, bench, atol=1e-6):
            # the IR is flat (0/0) at the benchmark: start a step towards the best-returning asset
            tilt = np.zeros(n_assets)
            tilt[np.argmax(mu)] = 1.0
            weight = 0.9 * bench + 0.1 * tilt

        bounds = tuple((0, 1) for _ in range(n_assets))

        if not constraints:
            constraints = [{'type': 'eq', 'fun': sum_equal_one}]
        else:
            constraints = [{'type': 'eq', 'fun': sum_equal_one}] + constraints

        optimum_weights = sco.minimize(objectives[objective], weight, method='SLSQP', bounds=bounds,
                                       constraints=constraints, jac=jacobians.get(objective))

        if not optimum_weights.success:
            # SLSQP still returns its last iterate: usable, but the constraints may not hold.
            warnings.warn(f"optimize('{objective}') did not converge -- the weights may not satisfy "
                          f"every constraint.", RuntimeWarning, stacklevel=2)

        # Always return valid long-only, fully-invested weights: a failed SLSQP
        # iterate can break the budget too. On success this only removes ~1e-12 rounding.
        weights = np.clip(np.nan_to_num(optimum_weights.x), 0, None)
        if weights.sum() <= 0:
            return np.full(n_assets, 1 / n_assets)
        return weights / weights.sum()

    def efficient_frontier(self, constraints=False, points=100):
        num_assets = self.returns.shape[1]
        bounds = [(0, 1) for _ in range(num_assets)]

        def portfolio_return(weights):
            return weights @ self.returns.mean() * 252

        def sum_equal_one(weight):
            return np.sum(weight) - 1

        def portfolio_risk(weights):
            return np.sqrt(weights @ self.returns.cov() @ weights) * np.sqrt(252)

        if not constraints:
            constraints = [{'type': 'eq', 'fun': sum_equal_one}]
        else:
            constraints = [{'type': 'eq', 'fun': sum_equal_one}] + constraints

        res_min = minimize(portfolio_risk, np.ones(num_assets) / num_assets,
                           bounds=bounds, constraints=constraints)
        res_max = minimize(lambda w: -portfolio_return(w), np.ones(num_assets) / num_assets,
                           bounds=bounds, constraints=constraints)

        if not res_min.success or not res_max.success:
            raise ValueError("Constraints make optimization infeasible")

        mus = np.linspace(portfolio_return(res_min.x), portfolio_return(res_max.x), points)

        frontier_weights = []
        frontier_returns = []
        frontier_risks = []
        frontier_sharpe_ratio = []

        for mu in mus:
            target_return_constraint = {'type': 'eq', 'fun': lambda weights, mu=mu: portfolio_return(weights) - mu}
            result = minimize(
                portfolio_risk,
                x0=frontier_weights[-1] if frontier_weights else np.ones(num_assets) / num_assets,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints + [target_return_constraint]
            )
            if result.success:
                weights = result.x
                frontier_weights.append(weights)
                frontier_returns.append(portfolio_return(weights))
                frontier_risks.append(portfolio_risk(weights))
                frontier_sharpe_ratio.append(portfolio_return(weights) / portfolio_risk(weights))

        return frontier_weights, frontier_returns, frontier_risks, frontier_sharpe_ratio

    def black_Litterman(self, P, Q, weights, risk_aversion, tau=0.025):
        implied_returns = risk_aversion * self.returns.cov().dot(weights).squeeze()
        omega = np.diag(np.diag(P.dot(tau * self.returns.cov()).dot(P.T)))
        sigma_scaled = self.returns.cov() * tau
        # Π + τΣPᵀ (PτΣPᵀ + Ω)⁻¹ (Q − PΠ)  -- Ω belongs inside the inverse
        BL_returns = implied_returns + sigma_scaled.dot(P.T).dot(
            np.linalg.inv(P.dot(sigma_scaled).dot(P.T) + omega)).dot(Q - P.dot(implied_returns))
        inv_cov = np.linalg.inv(self.returns.cov())
        BL_weights = inv_cov.dot(BL_returns)
        BL_weights = BL_weights / BL_weights.sum()

        return BL_weights, BL_returns


# =============================================================================
# Risk analysis
# =============================================================================

class RiskAnalysis(Portfolio):
    """Market risk / VaR of a portfolio and which assets contribute to it."""

    def __init__(self, returns):
        self.returns = returns
        super().__init__(returns=returns)

    def historical_var(self, weights, last_days=False, Q=5):
        """Historical VaR / CVaR on the past `last_days` days at the Q-th percentile."""
        performance = super().portfolio(weights)

        if last_days:
            performance = performance[-last_days:]

        var = np.percentile(performance, Q)
        cvar = performance[performance < var].mean().values[0]

        return var, cvar

    def parametric_var(self, weights, Q=0.95, stress_factor=1):
        """Parametric (normal) VaR / CVaR at confidence Q."""
        # Expected shortfall of a normal, closed form: σ·φ(z)/(1-Q)
        variance = super().variance(weights) * stress_factor
        daily_vol = variance / np.sqrt(252)
        VaR = daily_vol * norm.ppf(1 - Q)
        CVaR = -daily_vol * norm.pdf(norm.ppf(1 - Q)) / (1 - Q)

        return VaR, CVaR

    def stressed_moments(self, stress_factor=1.0):
        """(stressed daily std, stressed correlation) used by every simulation.

        stress_factor:
          scalar          -> every volatility × stress_factor
          vector / list   -> volatility of asset i × stress_factor[i]
          N×N matrix      -> DIAGONAL = volatility multipliers, OFF-DIAGONAL =
                             correlation shocks added to the historical
                             correlation (then clipped to [-1, 1] and made
                             positive definite)
        """
        std = self.returns.std()
        corr = self.returns.corr().to_numpy()
        stress = np.asarray(stress_factor, dtype=float)

        if stress.ndim == 0:
            stressed_std = std * float(stress)
        elif stress.ndim == 1:
            stressed_std = std * stress
        elif stress.ndim == 2:
            stressed_std = std * np.diag(stress)
            shock = np.tril(stress, -1)  # below the diagonal only
            corr = corr + shock + shock.T
        else:
            raise ValueError("Invalid stress_factor shape")

        corr = np.clip(corr, -1, 1)
        np.fill_diagonal(corr, 1.0)
        if not is_pos_def(corr):
            corr = _nearest_pd(corr)
        return stressed_std, corr

    def multivariate_distribution(self, iterations=10000, stress_factor=1.0, mean_shock=1.0):
        stressed_std, corr = self.stressed_moments(stress_factor)
        std = stressed_std.to_numpy()
        stressed_cov = corr * np.outer(std, std)

        mean = self.returns.mean() * mean_shock
        return np.random.multivariate_normal(mean, stressed_cov, iterations)

    def gaussian_copula(self, iterations=10000, stress_factor=1.0, mean_shock=1.0):
        randoms = np.random.normal(size=(iterations, self.returns.shape[1])).T

        stressed_std, corr_matrix = self.stressed_moments(stress_factor)

        cholesky = np.linalg.cholesky(corr_matrix)
        simulation = pd.DataFrame(np.matmul(cholesky, randoms).T)
        simulation.columns = self.returns.columns

        return simulation * stressed_std + self.returns.mean() * mean_shock

    def t_copula(self, iterations=10000, stress_factor=1.0, mean_shock=1.0, df=5):
        """Multivariate Student-t with `df` degrees of freedom (fat tails).
        Rescaled by sqrt((df-2)/df) so each asset keeps its (stressed)
        volatility -- only the tails get fatter."""
        if df <= 2:
            raise ValueError("df must be > 2 (the variance of a Student-t is infinite otherwise)")
        chi_squared = np.random.chisquare(df=df, size=iterations)

        randoms = np.random.normal(size=(iterations, self.returns.shape[1])).T

        stressed_std, corr_matrix = self.stressed_moments(stress_factor)

        cholesky = np.linalg.cholesky(corr_matrix)

        simulation = np.matmul(cholesky, randoms) / np.sqrt(chi_squared / df) * np.sqrt((df - 2) / df)
        simulation = pd.DataFrame(simulation.T)
        simulation.columns = self.returns.columns

        return simulation * stressed_std + self.returns.mean() * mean_shock

    def gumbel_copula(self, iterations=10000, theta=2, stress_vec=1.0, mean_return_shock=1.0):
        n_assets = self.returns.shape[1]

        # Step 1: sample positive stable variable
        V = np.random.uniform(0, np.pi, iterations)
        W = np.random.exponential(size=iterations)

        alpha = 1 / theta

        S = (
            np.sin(alpha * V) / (np.sin(V) ** alpha)
            * (np.sin((1 - alpha) * V) / W) ** (1 - alpha)
        )

        # Step 2: generate dependent uniforms
        E = np.random.exponential(size=(iterations, n_assets))
        U = np.exp(-(E / S[:, None]) ** alpha)

        # Step 3: convert uniforms into stressed returns
        means = self.returns.mean() * mean_return_shock
        stds = self.returns.std() * stress_vec

        return norm.ppf(U, loc=means, scale=stds)

    def monte_carlo(self, spot, horizon=20 / 252, iterations=10000, stress_factor=1.0, mean_return_shock=1.0):
        num_asset = len(self.returns.columns)

        randoms = np.random.normal(size=(iterations, num_asset)).T

        # same stress conventions as the other simulations
        stressed_std, corr_matrix = self.stressed_moments(stress_factor)

        vol = stressed_std.to_numpy() * np.sqrt(252)  # annualized standard deviations
        shocked_means = self.returns.mean() * 252 * mean_return_shock

        cholesky = np.linalg.cholesky(corr_matrix)

        drift = np.exp((shocked_means - 0.5 * vol ** 2) * horizon)
        factors = spot * drift

        factors_vec = factors.to_numpy().reshape(len(factors), -1)

        simulation = pd.DataFrame(np.matmul(cholesky, randoms).T)
        simulation.columns = self.returns.columns

        monte_carlo = factors_vec.T * np.exp(simulation.dot(np.diag(vol)) * np.sqrt(horizon))
        monte_carlo = pd.DataFrame(monte_carlo)
        monte_carlo.columns = self.returns.columns
        perf_monte_carlo = np.log(monte_carlo / spot)

        return monte_carlo, perf_monte_carlo

    def pca(self, num_components=2):
        """Eigenvalues / eigenvectors of the covariance matrix and the
        eigenportfolios (eigenvectors normalized to sum to 1)."""
        cov_matrix = self.returns.cov()

        eig_val, eig_vec = np.linalg.eig(cov_matrix)
        sorted_eig_val = eig_val.argsort()[::-1]
        eig_val = eig_val[sorted_eig_val]
        eig_vec = eig_vec[:, sorted_eig_val]
        eig_val = eig_val[:num_components]
        eig_vec = eig_vec[:, 0:num_components]

        PC = {}
        for i in range(eig_vec.shape[1]):
            PC["PC" + str(i + 1)] = eig_vec[:, i] / eig_vec[:, i].sum()

        portfolio_components = pd.DataFrame(PC.values(), index=PC.keys(), columns=self.returns.columns).T

        return eig_val, eig_vec, portfolio_components

    def var_contrib(self, weights):
        """Per-asset decomposition of the annualized volatility into
        idiosyncratic and correlation parts, plus the weighted covariance."""
        cov = self.returns.cov()

        W = np.outer(weights, weights)
        vol_contrib = W * cov * 252

        portfolio_var = vol_contrib.sum()
        portfolio_vol = np.sqrt(portfolio_var.sum())
        idiosyncratic_vol = np.diag(np.diag(vol_contrib))

        weighted_covar = pd.DataFrame(vol_contrib, index=self.returns.columns, columns=self.returns.columns)
        weighted_covar = weighted_covar.divide(portfolio_vol)

        corr_mat = pd.DataFrame(vol_contrib - idiosyncratic_vol, index=self.returns.columns, columns=self.returns.columns)
        idio_mat = pd.DataFrame(idiosyncratic_vol, index=self.returns.columns, columns=self.returns.columns)

        contrib = pd.concat([idio_mat.sum() + corr_mat.sum(), idio_mat.sum(), corr_mat.sum()], axis=1)
        contrib = contrib.divide(portfolio_vol)
        contrib.columns = ['Vol Contribution', 'Idiosyncratic Risk', 'Correlation']

        return contrib, weighted_covar

    def var_contrib_pct(self, weights):
        var_contrib = self.var_contrib(weights)[0]
        var_contrib = var_contrib / var_contrib['Vol Contribution'].sum()
        var_contrib.columns = ['Vol Contribution in %', 'Idiosyncratic Risk in %', 'Correlation in %']
        var_contrib = var_contrib.loc[(var_contrib != 0).any(axis=1)]
        return var_contrib.sort_values('Vol Contribution in %', ascending=False)

    def perf_contrib(self, weights, amount=100):
        fictive_prices = (1 + self.returns).cumprod()
        fictive_prices.iloc[0] = 1
        shares = amount * weights / fictive_prices.iloc[0]
        fictive_portfolio = shares * fictive_prices
        pnl = fictive_portfolio.iloc[-1] - fictive_portfolio.iloc[0]
        pnl_dataframe = pd.DataFrame(pnl.sort_values(ascending=False), columns=['Performance Contribution'])
        return pnl_dataframe.loc[(pnl_dataframe != 0).any(axis=1)]

    def perf_contrib_pct(self, weights, amount=100):
        pnl_dataframe = self.perf_contrib(weights, amount)
        return pnl_dataframe / pnl_dataframe.sum()

    def summary(self, weights):
        inventory = self.inventory(weights)
        perf_report = self.perf_contrib_pct(weights)
        var_contrib_pct = self.var_contrib_pct(weights)

        report = pd.concat([inventory, perf_report, var_contrib_pct], axis=1)
        return report.dropna()

    def tracking_error(self, ptf, bench):
        return (ptf - bench).std() * np.sqrt(252)
