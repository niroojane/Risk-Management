# Copyright (c) 2025 Niroojane Selvam
# Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""Regime-based allocation: the engine of the HMM Regime App, shared with the other apps.

  HMM engine        -- features (asset-class baskets, an index), Gaussian HMM fits with
                       walk-forward refits, filtered (causal) regime probabilities
  Backtest engine   -- a strategy, an exposure, asset constraints and risk limits per regime
  Scenarios         -- the settings of the HMM Regime App, saved in HMM_Scenarios.json
  Regime strategies -- a saved scenario as one more strategy of the Multi Asset App and the
                       web app ('regime:<scenario>', see regime_schedules), blended with the
                       other strategies by src.Backtest.run_backtest
"""
import os
import copy
import json
import logging
import datetime
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count

import numpy as np
import pandas as pd
from scipy.special import logsumexp
from scipy.stats import multivariate_normal
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

from . import Yahoo_API
from .RiskMetrics import (RiskAnalysis, build_constraint, vol_constraint, tracking_error_constraint,
                          information_ratio_constraint, beta_constraint, compute_per_asset_betas)
from .Yahoo_API import DEFAULT_UNIVERSE

# hmmlearn logs "Model is not converging" at every n_init restart; the fit
# keeps the best restart anyway, so the noise is silenced.
logging.getLogger("hmmlearn").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# asset classes held by the strategies but left out of the HMM feature baskets
NO_FEATURE_BASKET = {'T-Bills'}


# =============================================================================
# HMM engine
# =============================================================================
# computed on one index (e.g. ^GSPC) loaded from its own start date, not on the baskets
INDEX_FEATURES = ['Index Return', 'Index Volatility', 'Index Drawdown']
FEATURE_TYPES = ['Returns', 'Volatility', 'Market Factor (PCA)', 'Average Correlation', 'Drawdown'] + INDEX_FEATURES
COVARIANCE_TYPES = ['full', 'diag', 'spherical', 'tied']
REFIT_OPTIONS = {'Never (single fit)': None, 'Monthly': 'ME', 'Quarterly': 'QE', 'Yearly': 'YE'}
WINDOW_OPTIONS = ['Growing (expanding)', 'Sliding']
ORDER_OPTIONS = ['Volatility (low → high)', 'Return (high → low)']
INFERENCE_OPTIONS = ['Filtered (causal)', 'Smoothed (look-ahead, analysis only)']


def periods_per_year(index):
    """365 when the index trades on weekends (crypto), else 252."""
    index = pd.DatetimeIndex(index)
    if len(index) < 10:
        return 252
    return 365 if (index.dayofweek >= 5).mean() > 0.1 else 252


def asset_groups(columns, universe_table=None):
    """{asset class: [tickers]} for the loaded assets, from the universe table
    ('Asset Class' column). Tickers it doesn't know go to 'Other'."""
    classes = universe_table['Asset Class'] if universe_table is not None else pd.Series(dtype=object)
    classes = classes[~classes.index.duplicated()].reindex(list(columns)).fillna('Other')
    return {g: list(classes.index[classes == g]) for g in dict.fromkeys(classes)}


def group_returns(prices, groups, frequency='Daily'):
    """Log return of the equal-weight basket of each group (asset class).

    An asset joins its basket once it has prices; the history starts when
    every group has at least one asset."""
    px_ = prices.resample('W-FRI').last() if frequency == 'Weekly' else prices
    rets = np.log(px_).diff()
    baskets = pd.DataFrame({g: rets[list(t)].mean(axis=1) for g, t in groups.items() if len(t)})
    return baskets.iloc[1:].dropna()


def reference_returns(prices, groups, frequency='Daily'):
    """Log return of the equal-weight basket of all groups -- used to order
    and describe the states."""
    return group_returns(prices, groups, frequency).mean(axis=1).rename('Reference')


def index_returns(index_prices, frequency='Daily'):
    """Log return of the index behind the Index features -- used instead of
    the baskets to order and describe the states when those features are on."""
    px_ = index_prices.dropna()
    px_ = px_.resample('W-FRI').last() if frequency == 'Weekly' else px_
    return np.log(px_).diff().iloc[1:].rename('Reference')


def build_features(prices, groups, feature_types, vol_window=21, smooth_window=5, frequency='Daily', fit_end=None,
                   index_prices=None, pca_window=252):
    """HMM features computed on the asset-class baskets of `groups`, and the
    Index features on `index_prices` (one index, e.g. ^GSPC).

    pca_window: observations the Market Factor loadings are re-estimated on at
    each date (rolling, causal). None = one fixed set of loadings fitted up to
    `fit_end`."""
    if not feature_types:
        raise ValueError("Select at least one feature type.")
    if not groups and set(feature_types) - set(INDEX_FEATURES):
        raise ValueError("No assets loaded.")

    rets = group_returns(prices, groups, frequency) if groups else pd.DataFrame()
    assets = list(rets.columns)
    ann = 52 if frequency == 'Weekly' else periods_per_year(rets.index)
    year = 52 if frequency == 'Weekly' else ann
    parts = []

    if 'Returns' in feature_types:
        f = rets.rolling(smooth_window).mean() * ann
        parts.append(f.add_suffix(' | Return'))

    if 'Volatility' in feature_types:
        # log-vol is much closer to Gaussian than vol itself
        f = np.log(rets.rolling(vol_window).std() * np.sqrt(ann))
        parts.append(f.add_suffix(' | Log Vol'))

    if 'Market Factor (PCA)' in feature_types:
        if len(assets) > 1 and pca_window:
            # loadings, mean and std re-estimated each date on the last pca_window observations
            x = rets.dropna()
            vals = x.values
            factor = np.full(len(x), np.nan)
            for t in range(pca_window - 1, len(x)):
                w = vals[t - pca_window + 1:t + 1]
                mu, sd = w.mean(axis=0), w.std(axis=0, ddof=1)
                loadings = np.linalg.eigh(np.corrcoef(w, rowvar=False))[1][:, -1]
                loadings = loadings * np.sign(loadings.sum() or 1)
                factor[t] = ((vals[t] - mu) / sd) @ loadings
            factor = pd.Series(factor, index=x.index).reindex(rets.index)
        elif len(assets) > 1:
            fit_rets = rets.loc[:fit_end].dropna() if fit_end is not None else rets.dropna()
            mu, sd = fit_rets.mean(), fit_rets.std()
            z = (rets - mu) / sd
            loadings = PCA(n_components=1).fit(((fit_rets - mu) / sd).values).components_[0]
            loadings = loadings * np.sign(loadings.sum() or 1)
            factor = z.fillna(0) @ loadings
        else:
            factor = rets.iloc[:, 0]
        parts.append((factor.rolling(smooth_window).mean() * ann).rename('Market Factor'))

    if 'Average Correlation' in feature_types and len(assets) > 1:
        n = len(assets)
        corr_sum = rets.rolling(vol_window).corr().groupby(level=0).sum(min_count=1).sum(axis=1, min_count=1)
        parts.append(((corr_sum - n) / (n * (n - 1))).rename('Average Correlation'))

    if 'Drawdown' in feature_types:
        basket = np.exp(rets.mean(axis=1).fillna(0).cumsum())
        parts.append((basket / basket.rolling(year, min_periods=vol_window).max() - 1).rename('Basket Drawdown'))

    index_types = [f for f in feature_types if f in INDEX_FEATURES]
    if index_types:
        if index_prices is None or index_prices.dropna().empty:
            raise ValueError("The Index features need the index prices.")
        px_ = index_prices.dropna()
        px_ = px_.resample('W-FRI').last() if frequency == 'Weekly' else px_
        r = np.log(px_).diff()
        ann_idx = 52 if frequency == 'Weekly' else periods_per_year(px_.index)
        if 'Index Return' in index_types:
            parts.append((r.rolling(vol_window).mean() * ann_idx).rename('Index Return'))
        if 'Index Volatility' in index_types:
            parts.append(np.log(r.rolling(vol_window).std() * np.sqrt(ann_idx)).rename('Index Log Vol'))
        if 'Index Drawdown' in index_types:
            parts.append((px_ / px_.rolling(ann_idx, min_periods=ann_idx // 2).max() - 1).rename('Index Drawdown'))

    if not parts:
        raise ValueError("The selected feature types need at least 2 asset classes.")
    return pd.concat(parts, axis=1).replace([np.inf, -np.inf], np.nan).dropna()


def fit_hmm(X, n_states, covariance_type='full', n_iter=500, tol=1e-4, n_init=5, random_state=42):
    """Best of `n_init` GaussianHMM fits on standardized X.

    Returns (model, scaler, log_likelihood)."""
    scaler = StandardScaler().fit(X)
    Z = scaler.transform(X)
    best, best_score = None, -np.inf
    for i in range(max(1, n_init)):
        model = GaussianHMM(n_components=n_states, covariance_type=covariance_type, n_iter=n_iter,
                            tol=tol, random_state=random_state + i, min_covar=1e-3)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                model.fit(Z)
                score = model.score(Z)
        except Exception:
            continue
        if np.isfinite(score) and score > best_score:
            best, best_score = model, score
    if best is None:
        raise RuntimeError("HMM failed to fit -- try fewer states, 'diag' covariance or fewer features.")
    return best, scaler, best_score


def state_order(model, Z, ref, order_by):
    """order[new_label] = raw HMM state. R0 = lowest vol (or highest return)."""
    raw = model.predict(Z)
    vols, means = [], []
    for k in range(model.n_components):
        r = ref[raw == k]
        vols.append(r.std() if len(r) > 1 else np.inf)
        means.append(r.mean() if len(r) else -np.inf)
    if order_by.startswith('Return'):
        return np.argsort(-np.nan_to_num(means, nan=-np.inf))
    return np.argsort(np.nan_to_num(vols, nan=np.inf))


def match_state_order(means, anchor_means, scale):
    """order[label] = raw state whose mean (in feature units) is closest to the
    label's mean in the first fit, so a label keeps its meaning across refits."""
    cost = np.linalg.norm((means[:, None, :] - anchor_means[None, :, :]) / scale, axis=2)
    rows, cols = linear_sum_assignment(cost)
    order = np.empty(len(cols), dtype=int)
    order[cols] = rows
    return order


def emission_loglik(model, Z):
    """log N(z_t | mean_k, cov_k), shape (T, n_states)."""
    try:
        # hmmlearn's own emission term -- exact for every covariance_type
        return model._compute_log_likelihood(Z)
    except AttributeError:
        pass
    # Fallback if the private method disappears. Note: hmmlearn 0.3.3's
    # covars_ is mis-shaped for 'spherical', hence the preference above.
    covars = model.covars_
    return np.column_stack([
        np.atleast_1d(multivariate_normal(model.means_[k], covars[k], allow_singular=True).logpdf(Z))
        for k in range(model.n_components)
    ])


def forward_filter(model, Z):
    """Filtered state probabilities P(s_t | z_1..z_t) via the forward algorithm.

    Unlike model.predict_proba (forward-backward), row t only uses data up
    to t, so it is safe to trade on."""
    log_b = emission_loglik(model, Z)
    log_a = np.log(np.maximum(model.transmat_, 1e-300))
    log_alpha = np.empty_like(log_b)
    a = np.log(np.maximum(model.startprob_, 1e-300)) + log_b[0]
    log_alpha[0] = a - logsumexp(a)
    for t in range(1, len(Z)):
        a = logsumexp(log_alpha[t - 1][:, None] + log_a, axis=0) + log_b[t]
        log_alpha[t] = a - logsumexp(a)
    return np.exp(log_alpha)


def confirm_regimes(probs, min_prob=0.0, confirm=1):
    """Most likely regime, switching only when the new regime has probability
    >= min_prob for `confirm` consecutive observations."""
    values = probs.values
    raw, pmax = values.argmax(axis=1), values.max(axis=1)
    out = np.empty(len(raw), dtype=int)
    current, candidate, streak = raw[0], raw[0], 0
    for t in range(len(raw)):
        proposal = raw[t] if pmax[t] >= min_prob else current
        if proposal == current:
            streak = 0
        else:
            streak = streak + 1 if proposal == candidate else 1
            candidate = proposal
            if streak >= confirm:
                current, streak = proposal, 0
        out[t] = current
    return pd.Series(out, index=probs.index, name='Regime')


def run_regime_model(features, ref_returns, train_start, train_end, n_states=3, covariance_type='full',
                     n_iter=500, tol=1e-4, n_init=5, random_state=42, refit='Never (single fit)',
                     order_by=ORDER_OPTIONS[0], inference=INFERENCE_OPTIONS[0], min_prob=0.0, confirm=1,
                     window=WINDOW_OPTIONS[0], window_years=5.0, match_states=False):
    feats = features.loc[pd.Timestamp(train_start):]
    train_end = pd.Timestamp(train_end)
    sliding = window == 'Sliding'
    if sliding and not window_years > 0:
        raise ValueError("The sliding window length must be positive.")
    min_obs = max(60, 15 * n_states)

    def fit_mask(fit_date):
        """Observations a model fitted at fit_date trains on."""
        mask = feats.index <= fit_date
        if sliding:
            mask &= feats.index > fit_date - pd.DateOffset(days=int(round(365.25 * window_years)))
        return mask

    n_train = int(fit_mask(train_end).sum())
    if n_train < min_obs:
        raise ValueError(f"Only {n_train} training observations -- extend the training window"
                         + (" or the sliding length." if sliding else "."))

    values = feats.values
    ref = ref_returns.reindex(feats.index).fillna(0).values
    smoothed = inference.startswith('Smoothed')

    fit_dates = [train_end]
    rule = REFIT_OPTIONS.get(refit)
    if rule and not smoothed:
        fit_dates += [d for d in pd.date_range(train_end, feats.index[-1], freq=rule) if d > train_end]

    parts, fits, anchor = [], [], None
    for i, fit_date in enumerate(fit_dates):
        in_fit = fit_mask(fit_date)
        if in_fit.sum() < min_obs:
            raise ValueError(f"Only {int(in_fit.sum())} observations in the window fitted on {fit_date.date()} "
                             "-- lengthen the sliding window.")
        model, scaler, loglik = fit_hmm(values[in_fit], n_states, covariance_type, n_iter, tol, n_init, random_state)
        Z = scaler.transform(values)
        means = scaler.inverse_transform(model.means_)   # state means in feature units
        if match_states and anchor is not None:
            order = match_state_order(means, *anchor)
        else:
            order = state_order(model, Z[in_fit], ref[in_fit], order_by)
        if anchor is None:
            # the first fit defines what each label means; matched refits keep it
            anchor = (means[order], values[in_fit].std(axis=0))

        seg_end = fit_dates[i + 1] if i + 1 < len(fit_dates) else feats.index[-1]
        upto = feats.index <= seg_end
        probs = model.predict_proba(Z[upto]) if smoothed else forward_filter(model, Z[upto])
        probs = probs[:, order]
        keep = np.ones(upto.sum(), dtype=bool) if i == 0 else feats.index[upto] > fit_date
        parts.append(pd.DataFrame(probs[keep], index=feats.index[upto][keep]))
        fits.append({'Fit date': fit_date, 'Window start': feats.index[in_fit][0],
                     'Observations': int(in_fit.sum()), 'Log-Likelihood': loglik,
                     'model': model, 'scaler': scaler, 'order': order})

    probs = pd.concat(parts)
    probs.columns = list(range(n_states))
    last = fits[-1]
    transmat = pd.DataFrame(last['model'].transmat_[np.ix_(last['order'], last['order'])],
                            index=range(n_states), columns=range(n_states))
    return {
        'probs': probs,
        'regimes': confirm_regimes(probs, min_prob, confirm),
        'fits': fits,
        'transmat': transmat,
        'features': feats,
        'train_end': train_end,
    }


def select_n_states(features, train_start, train_end, max_states=6, covariance_type='full',
                    n_iter=500, tol=1e-4, n_init=3, random_state=42):
    """Information criteria for 2..max_states on the training window (lower BIC = better)."""
    X = features.loc[pd.Timestamp(train_start):pd.Timestamp(train_end)].values
    rows = []
    for k in range(2, max_states + 1):
        try:
            model, scaler, loglik = fit_hmm(X, k, covariance_type, n_iter, tol, n_init, random_state)
        except RuntimeError:
            continue
        Z = scaler.transform(X)
        rows.append({'States': k, 'Log-Likelihood': loglik, 'AIC': model.aic(Z), 'BIC': model.bic(Z)})
    return pd.DataFrame(rows).set_index('States').round(1)


def regime_summary(regimes, transmat, labels):
    runs = (regimes != regimes.shift()).cumsum()
    episodes = regimes.groupby(runs).agg(['first', 'size'])
    summary = pd.DataFrame({
        '% of Time': regimes.value_counts(normalize=True),
        'Episodes': episodes.groupby('first').size(),
        'Avg Duration (obs)': episodes.groupby('first')['size'].mean(),
    }).reindex(transmat.index)
    summary['Expected Duration (model)'] = 1 / (1 - np.diag(transmat.values)).clip(1e-9)
    summary.index = [labels[k] for k in summary.index]
    return summary.round(3)


def regime_asset_statistics(prices, regimes_daily, ann):
    """Annualized return / vol / Sharpe of every asset, conditional on the regime of the day."""
    rets = prices.pct_change(fill_method=None)
    grouped = rets.groupby(regimes_daily)
    mean, vol = grouped.mean() * ann, grouped.std() * np.sqrt(ann)
    return mean, vol, mean / vol


def empirical_transitions(regimes):
    return pd.crosstab(regimes.shift().dropna().astype(int), regimes.iloc[1:], normalize='index')


# =============================================================================
# Backtest engine
# =============================================================================
STRATEGIES = {
    'Minimum Variance': 'minimum_variance',
    'Risk Parity': 'risk_parity',
    'Sharpe Ratio': 'sharpe_ratio',
    'Maximum Diversification': 'maximum_diversification',
    'Eigen Strategy': 'eigenportfolio',
    'Minimum Tracking Error': 'tracking_error',        # vs the TE / IR benchmark
    'Maximum Information Ratio': 'information_ratio',  # vs the TE / IR benchmark
    'Equal Weight': 'equal_weight',
    'Inverse Volatility': 'inverse_vol',
    'Custom Weights': 'custom',
    'Cash': 'cash',
}
OPTIMIZED = {'minimum_variance', 'risk_parity', 'sharpe_ratio', 'maximum_diversification', 'eigenportfolio',
             'tracking_error', 'information_ratio'}
RELATIVE = {'tracking_error', 'information_ratio'}   # need the benchmark weights
REBALANCING = {'Weekly': 'W-FRI', 'Monthly': 'ME', 'Quarterly': 'QE', 'Yearly': 'YE'}
RISK_TYPES = ['Volatility', 'Tracking Error', 'Information Ratio', 'Beta']


def period_end_dates(index, frequency):
    """Last available date of each calendar period."""
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(pd.Grouper(freq=REBALANCING[frequency])).last().dropna().values)


def benchmark_weights(columns, te_benchmark='Equal Weight'):
    """TE / IR benchmark over the eligible assets: equal weight, or 100% in
    one asset (equal weight when that asset isn't eligible at this date)."""
    if te_benchmark in columns:
        return pd.Series(np.where(columns == te_benchmark, 1.0, 0.0), index=columns)
    return pd.Series(1 / max(len(columns), 1), index=columns)


def expand_all_rows(asset_constraints, columns):
    """'All' rows -> one row per asset, except the assets with their own row of the
    same sign: All ≤ 0.35 + IB01.L ≤ 0.6 caps IB01.L at 60% and every other asset at 35%."""
    own = {(asset, sign) for asset, sign, _ in asset_constraints if asset != 'All'}
    rows = []
    for asset, sign, limit in asset_constraints:
        if asset == 'All':
            rows += [[c, sign, limit] for c in columns if (c, sign) not in own and (c, '=') not in own]
        else:
            rows.append([asset, sign, limit])
    return rows


def compute_target_weights(window, strategy, asset_constraints=None, risk_limits=None, custom=None, bench=None):
    """Fully-invested target weights (before exposure scaling) for one decision.

    window: returns of the eligible assets. asset_constraints: rows
    [Asset, Sign, Limit]. risk_limits: rows [Risk, Sign, Limit] with Risk in
    RISK_TYPES (annualized; TE in decimals, IR and beta as ratios). bench: benchmark
    weights for TE / IR / beta (Series over window's columns). custom: Series of weights.
    An asset capped at 0 (sign ≤ or = with limit 0) is left out of the window,
    so every strategy leaves it out (Equal Weight and Custom Weights included).
    Returns (weights Series, note)."""
    # benchmark returns for a Beta limit, taken before zero-capped assets are left out
    # (a beta to ^GSPC stays a beta to ^GSPC in a regime that can't hold ^GSPC)
    bench_returns = None
    if any(row[0] == 'Beta' for row in (risk_limits or [])):
        b = bench if bench is not None else benchmark_weights(window.columns)
        bench_returns = window @ b.reindex(window.columns).fillna(0.0)
    zero = {a for a, sign, limit in (asset_constraints or [])
            if a != 'All' and sign in ('≤', '=') and float(limit) <= 0}
    if zero:
        window = window.loc[:, [c for c in window.columns if c not in zero]]
        if bench is not None:
            bench = bench.reindex(window.columns).fillna(0.0)
            bench = bench / bench.sum() if bench.sum() > 0 else None
    key = STRATEGIES[strategy]
    cols = window.columns
    n = len(cols)
    if key == 'cash' or n == 0:
        return pd.Series(0.0, index=cols), ''
    if key == 'custom':
        return (custom if custom is not None else pd.Series(dtype=float)).reindex(cols).fillna(0.0), ''
    if key == 'equal_weight' or n == 1:
        return pd.Series(1 / n, index=cols), ''
    if key == 'inverse_vol':
        inv = 1 / window.std().replace(0, np.nan)
        return (inv / inv.sum()).fillna(0.0), ''

    bench = bench if bench is not None else benchmark_weights(cols)
    cons = []
    if asset_constraints:
        cons += build_constraint(window, np.array(expand_all_rows(asset_constraints, cols), dtype=object))
    for risk, sign, limit in (risk_limits or []):
        if risk == 'Volatility':
            cons += vol_constraint(window.cov().values, sign, float(limit))
        elif risk == 'Tracking Error':
            cons += tracking_error_constraint(window.cov(), bench, sign, float(limit))
        elif risk == 'Information Ratio':
            cons += information_ratio_constraint(window, bench, sign, float(limit))
        elif risk == 'Beta':
            cons += beta_constraint(compute_per_asset_betas(window, bench_returns), sign, float(limit))
    try:
        w = RiskAnalysis(window).optimize(key, constraints=cons if cons else False,
                                          bench_weights=bench if key in RELATIVE else None)
        w = np.clip(np.nan_to_num(w), 0, None)
        if w.sum() <= 0:
            raise ValueError("degenerate solution")
        w = w / w.sum()
        # Constraints that conflict can't all hold: the optimizer then returns its best
        # attempt. Say so in the Decisions log (checked on the final weights).
        broken = sum(1 for c in cons
                     if (c['type'] == 'ineq' and np.min(c['fun'](w)) < -1e-4)
                     or (c['type'] == 'eq' and np.max(np.abs(c['fun'](w))) > 1e-4))
        note = f"{broken} constraint(s) not met -- limits may conflict" if broken else ''
        return pd.Series(w, index=cols), note
    except Exception as e:
        return pd.Series(1 / n, index=cols), f"{strategy} failed ({e}); equal weight used"


def regime_backtest(prices, regimes, mapping, asset_constraints=None, risk_constraints=None, custom_weights=None,
                    start=None, end=None, rebalance='Monthly', rebalance_on_change=True, lookback=252,
                    regime_conditional=False, min_obs=60, cost_bps=10.0, te_benchmark='Equal Weight'):
    """Backtest of a strategy whose allocation rule depends on the regime.

    regimes: Series of int regimes (any frequency; forward-filled to the price
             dates, which is causal).
    mapping: {regime: {'Strategy': name, 'Exposure': float}}
    asset_constraints: DataFrame [Regime, Asset, Sign, Limit] -- Regime is an
             int or 'All Regimes'.
    risk_constraints: DataFrame [Regime, Risk, Sign, Limit], Risk in RISK_TYPES.
    custom_weights: DataFrame, index = regime, columns = assets.
    te_benchmark: 'Equal Weight' or a ticker -- what tracking error and
             information ratio are measured against (see benchmark_weights).
    """
    prices = prices.sort_index()
    rets = prices.pct_change(fill_method=None)
    reg_all = regimes.reindex(prices.index, method='ffill')
    idx = prices.loc[pd.Timestamp(start) if start else None:pd.Timestamp(end) if end else None].index
    idx = idx[reg_all.loc[idx].notna().values]
    if len(idx) < 2:
        raise ValueError("No overlap between the backtest dates and the regime history.")
    reg = reg_all.loc[idx].astype(int)

    decisions = {idx[0]} | set(period_end_dates(idx, rebalance)).intersection(idx)
    if rebalance_on_change:
        decisions |= set(idx[reg.ne(reg.shift()).values])
    decisions = sorted(d for d in decisions if d != idx[-1])

    def rows_for(df, regime, columns):
        if df is None or df.empty:
            return []
        sel = df[(df['Regime'] == regime) | (df['Regime'] == 'All Regimes')]
        return sel[columns].values.tolist()

    def decide(date):
        r = int(reg.loc[date])
        spec = mapping.get(r, {'Strategy': 'Equal Weight', 'Exposure': 1.0})
        window = rets.loc[:date].iloc[1:].tail(lookback)
        if regime_conditional:
            same = (reg_all.reindex(window.index) == r).values
            if same.sum() >= min_obs:
                window = window[same]
        live = prices.loc[date].notna()
        window = window.loc[:, live[live].index]
        window = window.loc[:, window.notna().mean() >= 0.9].fillna(0.0)
        custom = custom_weights.loc[r] if custom_weights is not None and r in custom_weights.index else None
        w, note = compute_target_weights(window, spec['Strategy'],
                                         rows_for(asset_constraints, r, ['Asset', 'Sign', 'Limit']),
                                         rows_for(risk_constraints, r, ['Risk', 'Sign', 'Limit']), custom,
                                         bench=benchmark_weights(window.columns, te_benchmark))
        return date, r, w.reindex(prices.columns).fillna(0.0) * float(spec['Exposure']), note

    targets, notes = {}, {}
    decision_regime = {}
    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        for future in as_completed([executor.submit(decide, d) for d in decisions]):
            date, r, w, note = future.result()
            targets[date], decision_regime[date] = w, r
            if note:
                notes[date] = note
    targets = pd.DataFrame(targets).T.sort_index()

    R = rets.loc[idx].fillna(0.0).values
    T, N = R.shape
    target_at = {idx.get_loc(d): targets.loc[d].values for d in targets.index}
    w = np.zeros(N)
    nav, value = np.empty(T), 1.0
    weights, turnover = np.empty((T, N)), np.zeros(T)
    for t in range(T):
        if t > 0:
            port = w @ R[t]
            value *= 1 + port
            if 1 + port > 0:
                w = w * (1 + R[t]) / (1 + port)
        if t in target_at:
            tgt = target_at[t]
            turnover[t] = np.abs(tgt - w).sum()
            value *= 1 - turnover[t] * cost_bps / 1e4
            w = tgt.copy()
        nav[t], weights[t] = value, w

    decisions_df = pd.DataFrame({
        'Regime': pd.Series(decision_regime),
        'Strategy': pd.Series({d: mapping.get(r, {}).get('Strategy', 'Equal Weight') for d, r in decision_regime.items()}),
        'Invested': targets.sum(axis=1),
        'Turnover': pd.Series(turnover, index=idx).reindex(targets.index),
        # reindexed so an empty `notes` doesn't turn the index into plain objects
        'Note': pd.Series(notes, dtype=object).reindex(targets.index),
    }).sort_index()
    return {
        'nav': pd.Series(nav * 100, index=idx),
        'weights': pd.DataFrame(weights, index=idx, columns=prices.columns),
        'targets': targets,
        'turnover': pd.Series(turnover, index=idx),
        'decisions': decisions_df,
        'regimes': reg,
    }


def clean_benchmark_returns(returns):
    """External portfolio returns (dates x portfolios), e.g. the Crypto App's
    `global_returns` or `performance_pct`."""
    if returns is None:
        return pd.DataFrame()
    if isinstance(returns, pd.Series):
        returns = returns.to_frame()
    returns = returns.copy()
    returns.index = pd.to_datetime(returns.index)
    if returns.index.tz is not None:
        returns.index = returns.index.tz_localize(None)
    returns = returns[~returns.index.duplicated(keep='last')].sort_index()
    returns = returns.apply(pd.to_numeric, errors='coerce')
    return returns.dropna(axis=1, how='all')


def benchmark_nav(returns, index):
    """Return series -> level rebased to 100 on the backtest dates.

    Compounded on its own dates first, then read on the backtest dates, so a
    7-day crypto fund lines up with a 5-day ETF backtest (and vice versa)."""
    level = (1 + returns.dropna()).cumprod()
    level = level.reindex(level.index.union(index)).ffill().reindex(index)
    first = level.first_valid_index()
    return level / level.loc[first] * 100 if first is not None else level


def performance_metrics(navs, ann, references=(), turnovers=None):
    """Same metrics as the Crypto App's strategy results (Returns, Volatility,
    Sharpe Ratio, Drawdown, Date Drawdown, Tracking Error to each reference
    series). Each column is measured over its own history (an external
    portfolio may start after the backtest); tracking errors over the overlap."""
    returns = navs.pct_change(fill_method=None)

    def one(name):
        nav = navs[name].dropna()
        rets = nav.pct_change(fill_method=None)
        years = max((nav.index[-1] - nav.index[0]).days / 365.25, 1e-9)
        total = nav.iloc[-1] / nav.iloc[0] - 1
        vol = rets.std() * np.sqrt(ann)
        drawdown = nav / nav.cummax() - 1
        metrics = {
            'Start': nav.index[0].date(),
            'Returns': total,
            'Volatility': vol,
            # annualized return / volatility, as in the Crypto App
            'Sharpe Ratio': ((1 + total) ** (1 / years) - 1) / vol,
            'Drawdown': drawdown.min(),
            'Date Drawdown': drawdown.idxmin().date(),
        }
        for ref in references:
            metrics[f'Tracking Error to {ref}'] = (returns[name] - returns[ref]).std() * np.sqrt(ann)
        if turnovers is not None:
            metrics['Annual Turnover'] = turnovers[name].sum() / years if name in turnovers else np.nan
        return pd.Series(metrics)

    return pd.DataFrame({c: one(c) for c in navs.columns if navs[c].notna().sum() > 1}).fillna(0)


def performance_by_regime(navs, regimes, ann, labels):
    """Annualized return / vol / Sharpe of each series, grouped by the regime
    in force (the regime known at the previous close, when weights were set)."""
    rets = navs.pct_change(fill_method=None)
    in_force = regimes.reindex(rets.index).shift(1)
    grouped = rets.groupby(in_force)
    mean, vol = grouped.mean() * ann, grouped.std() * np.sqrt(ann)
    out = pd.concat({'Ann. Return': mean, 'Ann. Volatility': vol, 'Sharpe': mean / vol}, axis=1)
    out.index = [labels.get(int(k), k) for k in out.index]
    return out.round(4)


# =============================================================================
# Scenarios
# =============================================================================
# Default scenario: the one the HMM Regime App opens with, and the 'Regime · Default (initial)'
# strategy of the other apps. On the UCITS universe. 5 regimes of ^GSPC (return, volatility,
# drawdown) trained from 2007 on a growing window, refitted every quarter with the labels
# kept across refits: R0 calm bull, R1 normal market,
# R2 correction, R3 bear market, R4 crash. Fully invested, every asset <= 35%. Max
# Information Ratio vs the S&P 500 (CSPX.L) everywhere except the bear regime: tracking
# error <= 5% and beta <= 1 in the bull regimes, <= 10% in corrections and crashes (staying
# close to the index there avoids selling the dips that recover). Bear regime: Minimum
# Variance with T-bills (IB01.L <= 60%), as bonds can fall with equities (2022), and a
# commodity sleeve (gold >= 10%, broad commodities CMOD.L >= 10%) for inflation-driven bear
# markets; IB01.L and CMOD.L are only held in that regime.
DEFAULT_SCENARIO = {
    'universe': DEFAULT_UNIVERSE,               # UNIVERSES entry of the Data tab
    'features': INDEX_FEATURES,
    'index': '^GSPC',
    'index_start': datetime.date(2005, 1, 1),   # index history for the features (prices can start later)
    'train_start': datetime.date(2007, 7, 11),  # with 5 restarts an earlier start can stop at a weaker fit
    'train_end': datetime.date(2019, 12, 31),
    'bt_start': datetime.date(2020, 1, 1),
    'n_states': 5,
    'refit': 'Quarterly',
    'window': 'Growing (expanding)',
    'window_years': 5.0,
    'match_states': True,
    'min_prob': 0.6,
    'confirm': 3,
    'strategies': {0: 'Maximum Information Ratio',   # calm bull
                   1: 'Maximum Information Ratio',   # normal market
                   2: 'Maximum Information Ratio',   # correction
                   3: 'Minimum Variance',            # bear market
                   4: 'Maximum Information Ratio'},  # crash / deep drawdown, rebounds included
    'asset_constraints': [{'Regime': r, 'Asset': 'All', 'Sign': '≤', 'Limit': 0.35} for r in range(5)]
                         + [{'Regime': 3, 'Asset': 'IB01.L', 'Sign': '≤', 'Limit': 0.6},
                            {'Regime': 3, 'Asset': 'GOLD.PA', 'Sign': '≥', 'Limit': 0.1},
                            {'Regime': 3, 'Asset': 'CMOD.L', 'Sign': '≥', 'Limit': 0.1}]
                         + [{'Regime': r, 'Asset': a, 'Sign': '≤', 'Limit': 0.0} for r in (0, 1, 2, 4) for a in ('IB01.L', 'CMOD.L')],
    'risk_constraints': [{'Regime': r, 'Risk': 'Tracking Error', 'Sign': '≤', 'Limit': 0.05} for r in (0, 1)]
                        + [{'Regime': r, 'Risk': 'Beta', 'Sign': '≤', 'Limit': 1.0} for r in (0, 1)]
                        + [{'Regime': r, 'Risk': 'Tracking Error', 'Sign': '≤', 'Limit': 0.10} for r in (2, 4)],
    'te_benchmark': 'CSPX.L',
}

# Settings of a scenario that DEFAULT_SCENARIO leaves at their usual value (the starting
# values of the HMM Regime App's widgets)
SCENARIO_DEFAULTS = {
    'frequency': 'Daily', 'smooth_window': 5, 'vol_window': 21,
    'cov_type': 'full', 'n_iter': 500, 'tol': 1e-4, 'n_init': 5, 'seed': 42,
    'inference': INFERENCE_OPTIONS[0], 'order_by': ORDER_OPTIONS[0],
    'bt_end': None, 'rebalance': 'Monthly', 'rebalance_on_change': True, 'lookback': 252,
    'regime_conditional': False, 'min_obs': 60, 'cost_bps': 10.0, 'bench_strategy': 'Equal Weight',
    'custom_weights': {},
}

# Saved scenarios: the settings of the HMM Model, Regime Strategies and Backtest tabs,
# with the result of their last backtest, in a JSON file at the project root.
SCENARIO_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'HMM_Scenarios.json')
DEFAULT_SCENARIO_NAME = 'Default (initial)'
SCENARIO_DATES = ('index_start', 'train_start', 'train_end', 'bt_start', 'bt_end')
# universe of the scenarios saved before the universe was part of a scenario
LEGACY_UNIVERSE = 'US ETFs (research)'


def comparable(value):
    """Settings as plain values (ISO dates, string keys, rounded floats), so two
    copies compare equal after a JSON round trip."""
    if isinstance(value, dict):
        return {str(k): comparable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [comparable(v) for v in value]
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, datetime.date):
        return value.isoformat()[:10]
    return value


def same_settings(a, b):
    return comparable(a) == comparable(b)


def settings_from_json(raw):
    """Inverse of comparable() for one scenario's settings: dates and regime numbers back."""
    settings = dict(raw)
    for key in SCENARIO_DATES:
        if settings.get(key):
            settings[key] = datetime.date.fromisoformat(settings[key][:10])
    for key in ('strategies', 'exposures', 'custom_weights'):
        if key in settings:
            settings[key] = {int(r): v for r, v in settings[key].items()}
    for key in ('asset_constraints', 'risk_constraints'):
        settings[key] = [{**c, 'Regime': c['Regime'] if c['Regime'] == 'All Regimes' else int(c['Regime'])}
                         for c in settings.get(key, [])]
    return settings


def load_scenarios(path):
    """{name: {'settings', 'result', 'saved'}} from the scenario file ({} when there is none)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    scenarios = {}
    for name, entry in raw.items():
        result = entry.get('result')
        if result:
            result = {**result, 'nav': pd.Series(result['nav']['values'], index=pd.to_datetime(result['nav']['dates']))}
        settings = settings_from_json(entry['settings'])
        settings.setdefault('universe', LEGACY_UNIVERSE)
        scenarios[name] = {**entry, 'settings': settings, 'result': result}
    return scenarios


def save_scenarios(scenarios, path):
    raw = {}
    for name, entry in scenarios.items():
        result = entry.get('result')
        if result:
            nav = result['nav']
            result = {**result, 'nav': {'dates': [d.strftime('%Y-%m-%d') for d in nav.index],
                                        'values': [round(float(v), 6) for v in nav.values]}}
        raw[name] = {**entry, 'settings': comparable(entry['settings']), 'result': result}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(raw, f, indent=1, ensure_ascii=False)


def default_settings():
    """Every setting of the built-in default scenario."""
    settings = {**copy.deepcopy(SCENARIO_DEFAULTS), **copy.deepcopy(DEFAULT_SCENARIO)}
    settings['features'] = list(DEFAULT_SCENARIO['features'])
    settings['exposures'] = {k: 1.0 for k in DEFAULT_SCENARIO['strategies']}
    return settings


def complete_settings(settings):
    """A saved scenario completed with the default of every setting it doesn't have."""
    scenario = {**default_settings(), **copy.deepcopy(settings)}
    scenario['features'] = [f for f in FEATURE_TYPES if f in scenario['features']]
    return scenario


# =============================================================================
# Regime strategies -- a scenario as a strategy of the other apps
# =============================================================================
REGIME_PREFIX = 'regime:'
# days of returns before the first rebalancing of a regime strategy
MIN_HISTORY = 60
# what the regimes depend on: two scenarios with the same values share one fit
HMM_KEYS = ('features', 'frequency', 'smooth_window', 'vol_window', 'index', 'index_start', 'n_states', 'cov_type',
            'n_iter', 'tol', 'n_init', 'seed', 'train_start', 'train_end', 'refit', 'window', 'window_years',
            'inference', 'order_by', 'match_states', 'min_prob', 'confirm')
_regime_cache = {}


def regime_key(name):
    """Strategy key of a scenario: 'regime:<name>'."""
    return REGIME_PREFIX + name


def is_regime_key(key):
    return isinstance(key, str) and key.startswith(REGIME_PREFIX)


def regime_label(key):
    """'regime:Default (initial)' -> 'Regime · Default (initial)'."""
    return 'Regime · ' + key[len(REGIME_PREFIX):]


def regime_scenarios(path=None):
    """{name: complete settings}: the built-in default, then the scenarios saved by the HMM
    Regime App in `path` (default SCENARIO_FILE; left out when the file can't be read)."""
    path = path or SCENARIO_FILE
    scenarios = {DEFAULT_SCENARIO_NAME: default_settings()}
    try:
        saved = load_scenarios(path)
    except Exception as e:
        logger.warning("Could not read %s (%s): only the default regime scenario is available", path, e)
        saved = {}
    for name, entry in saved.items():
        if name != DEFAULT_SCENARIO_NAME:   # the built-in default comes from the code
            scenarios[name] = complete_settings(entry['settings'])
    return scenarios


def load_index_prices(ticker, start):
    """Prices of the index behind the Index features, in its own currency (never converted)."""
    data = Yahoo_API.get_close([ticker], start=start, end=datetime.date.today())
    if data.empty:
        raise ValueError(f"No prices for the index {ticker}.")
    series = data.iloc[:, 0]
    return series.where(series > 0).dropna()


def fit_regimes(settings, prices=None, groups=None, index_prices=None):
    """Output of run_regime_model for a scenario, as the HMM Regime App's 'Fit HMM' computes it.

    groups: {asset class: tickers} of `prices`, for the asset-class basket features.
    index_prices: the index of the Index features (loaded from Yahoo when None).
    Fits are cached on the HMM settings and the data, so scenarios that only differ in their
    strategies share one fit, and a second backtest doesn't refit."""
    s = complete_settings(settings)
    uses_index = bool(set(s['features']) & set(INDEX_FEATURES))
    uses_baskets = bool(set(s['features']) - set(INDEX_FEATURES))
    if uses_baskets and not groups:
        raise ValueError("The scenario uses asset-class basket features: they need the asset class of each asset.")
    if uses_index and index_prices is None:
        index_prices = load_index_prices(s['index'], s['index_start'])
    key = json.dumps(comparable({k: s[k] for k in HMM_KEYS}), sort_keys=True)
    if uses_index:
        key += f"|{index_prices.index[0]}|{index_prices.index[-1]}|{len(index_prices)}|{index_prices.iloc[-1]}"
    if uses_baskets:
        key += f"|{json.dumps(groups, sort_keys=True)}|{prices.index[0]}|{prices.index[-1]}|{prices.shape}"
    if key not in _regime_cache:
        features = build_features(prices if uses_baskets else pd.DataFrame(), groups if uses_baskets else {},
                                  s['features'], vol_window=max(2, s['vol_window']),
                                  smooth_window=max(1, s['smooth_window']), frequency=s['frequency'],
                                  fit_end=pd.Timestamp(s['train_end']),
                                  index_prices=index_prices if uses_index else None)
        ref = (index_returns(index_prices, s['frequency']) if uses_index
               else reference_returns(prices, groups, s['frequency']))
        _regime_cache[key] = run_regime_model(
            features, ref, s['train_start'], s['train_end'], n_states=s['n_states'], covariance_type=s['cov_type'],
            n_iter=s['n_iter'], tol=s['tol'], n_init=s['n_init'], random_state=s['seed'], refit=s['refit'],
            order_by=s['order_by'], inference=s['inference'], min_prob=s['min_prob'], confirm=max(1, s['confirm']),
            window=s['window'], window_years=s['window_years'], match_states=s['match_states'])
    return _regime_cache[key]


def regime_schedule(prices, settings, groups=None, index_prices=None):
    """Target weights of a scenario's regime strategy on `prices` (dates x assets, the
    universe of the calling app), as the HMM Regime App's backtest sets them: at each
    rebalancing date (calendar + regime changes), the strategy, exposure and constraints of
    the regime known at that close, on the last `lookback` days. Starts once there are
    MIN_HISTORY days of returns.

    Returns {'weights': DataFrame (rebalancing dates x assets), 'decisions', 'regimes'
    (regime of each price date), 'current' (regime of the last date), 'warnings'}."""
    s = complete_settings(settings)
    if s['inference'].startswith('Smoothed'):
        raise ValueError("Smoothed inference uses future data: it can't drive a strategy.")
    if len(prices) < MIN_HISTORY + 2:
        raise ValueError(f"A regime strategy needs more than {MIN_HISTORY} days of prices.")
    result = fit_regimes(s, prices, groups, index_prices)
    n = s['n_states']
    regimes = result['regimes'].reindex(prices.index, method='ffill')
    mapping = {k: {'Strategy': s['strategies'].get(k, 'Equal Weight'), 'Exposure': s['exposures'].get(k, 1.0)}
               for k in range(n)}
    in_model = lambda r: r == 'All Regimes' or r < n
    asset_rows = [c for c in s['asset_constraints'] if in_model(c['Regime'])]
    risk_rows = [c for c in s['risk_constraints'] if in_model(c['Regime'])]
    custom = pd.DataFrame.from_dict(s['custom_weights'], orient='index') if s['custom_weights'] else None
    if custom is not None:
        custom.index = custom.index.astype(int)
    bt = regime_backtest(
        prices, regimes, mapping,
        asset_constraints=pd.DataFrame(asset_rows) if asset_rows else None,
        risk_constraints=pd.DataFrame(risk_rows) if risk_rows else None,
        custom_weights=custom, start=prices.index[MIN_HISTORY], rebalance=s['rebalance'],
        rebalance_on_change=s['rebalance_on_change'],
        lookback=max(20, s['lookback']), regime_conditional=s['regime_conditional'], min_obs=s['min_obs'],
        cost_bps=s['cost_bps'], te_benchmark=s['te_benchmark'])

    messages = []
    missing = sorted({c['Asset'] for c in asset_rows if c['Asset'] != 'All'} - set(prices.columns))
    if missing:
        messages.append(f"{', '.join(missing)} not in the universe: their constraints are left out.")
    if s['te_benchmark'] != 'Equal Weight' and s['te_benchmark'] not in prices.columns:
        messages.append(f"TE / IR / Beta benchmark {s['te_benchmark']} not in the universe: "
                        "equal weight of the assets instead.")
    if bt['targets'].index[0] <= pd.Timestamp(s['train_end']):
        messages.append(f"regimes up to {s['train_end']} are in-sample (the HMM was fitted on them).")
    notes = bt['decisions']['Note'].dropna()
    if len(notes):
        messages.append(f"{len(notes)} of {len(bt['decisions'])} rebalancings could not meet every constraint "
                        "or fell back to equal weight.")
    known = regimes.dropna()
    current = int(known.iloc[-1])
    since = known.index[known.ne(known.shift()).values][-1]
    messages.append(f"current regime R{current} ({mapping[current]['Strategy']}) since {since.date()}.")
    return {'weights': bt['targets'], 'decisions': bt['decisions'], 'regimes': regimes, 'current': current,
            'warnings': messages}


def regime_schedules(prices, strategies, path=None, groups=None):
    """Weight schedules of the regime strategies among `strategies` (keys 'regime:<scenario>'),
    for src.Backtest.run_backtest(schedules=...). Returns (schedules, messages)."""
    keys = [k for k in dict.fromkeys(strategies) if is_regime_key(k)]
    if not keys:
        return {}, []
    scenarios = regime_scenarios(path)
    schedules, messages = {}, []
    for key in keys:
        name = key[len(REGIME_PREFIX):]
        if name not in scenarios:
            raise ValueError(f"Unknown regime scenario '{name}' (saved scenarios: {', '.join(scenarios)}).")
        out = regime_schedule(prices, scenarios[name], groups=groups)
        schedules[key] = out['weights']
        messages += [f"{regime_label(key)}: {m}" for m in out['warnings']]
    return schedules, messages
