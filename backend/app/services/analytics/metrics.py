"""Performance and risk tables for assets and allocations.

Ported from the legacy `src/Metrics.py` module (Risk Management project).
Plotly figures and notebook HTML helpers were left out: the API returns the
underlying data and the frontend draws the charts.

`dataframe` arguments are allocation grids: index = allocation names,
columns = assets, values = weights.
"""
import datetime

import numpy as np
import pandas as pd
from scipy.stats import norm

from .rebalancing import buy_and_hold, rebalanced_portfolio
from .risk_metrics import RiskAnalysis


def get_expected_metrics(returns, dataframe):
    """Expected return, volatility and Sharpe ratio of each allocation."""
    portfolio = RiskAnalysis(returns)
    allocation_dict = {idx: dataframe.loc[idx].to_numpy() for idx in dataframe.index}

    metrics = {'Expected Returns': {}, 'Expected Volatility': {}, 'Sharpe Ratio': {}}

    for key, weights in allocation_dict.items():
        perf = portfolio.performance(weights)
        vol = portfolio.variance(weights)
        metrics['Expected Returns'][key] = np.round(perf, 4)
        metrics['Expected Volatility'][key] = np.round(vol, 4)
        metrics['Sharpe Ratio'][key] = np.round(perf / vol, 2)

    indicators = pd.DataFrame(metrics, index=allocation_dict.keys())
    return indicators.T.round(4)


def rebalanced_time_series(prices, dataframe, frequency='Monthly'):
    """Value (base 100) of the buy-and-hold and rebalanced version of each allocation."""
    portfolio_returns = pd.DataFrame()

    for key in dataframe.index:
        portfolio_returns['Buy and Hold ' + key] = buy_and_hold(prices, dataframe.loc[key]).sum(axis=1)
        portfolio_returns['Rebalanced ' + key] = rebalanced_portfolio(
            prices, dataframe.loc[key], frequency=frequency).sum(axis=1)

    portfolio_returns.index.name = 'Date'
    return portfolio_returns


def _ytd_return(levels):
    """Return since the previous year's last close (YTD includes the first
    trading day of the year). Falls back to the first close of the year when
    the history starts this year."""
    year_start = datetime.datetime(max(levels.index.year), 1, 1)
    this_year = levels.loc[year_start:]
    before = levels[levels.index < year_start]
    base = before.ffill().iloc[-1] if len(before) else this_year.iloc[0]
    if isinstance(base, pd.Series):
        base = base.fillna(this_year.bfill().iloc[0])
    return this_year.iloc[-1] / base - 1


def _return_table(levels):
    ret = levels.iloc[-1] / levels.iloc[0] - 1
    annualized = (1 + ret) ** (365 / (levels.index[-1] - levels.index[0]).days) - 1
    ret_ytd = _ytd_return(levels)

    perfs = pd.concat([ret, ret_ytd, annualized], axis=1)
    perfs.columns = ['Returns since ' + pd.to_datetime(levels.index[0]).strftime("%Y-%m-%d"),
                     'Returns since ' + datetime.datetime(max(levels.index.year), 1, 1).strftime("%Y-%m-%d"),
                     'Annualized Returns']
    return perfs.T.round(4)


def rebalanced_metrics(portfolio_returns):
    """Total, YTD and annualized return of each portfolio series."""
    return _return_table(portfolio_returns)


def get_asset_returns(prices):
    """Total, YTD and annualized return of each asset."""
    return _return_table(prices)


def get_portfolio_risk(dataframe, prices, portfolio_returns, benchmark):
    """Ex-post risk of each portfolio series: volatility, tracking error vs.
    the `benchmark` allocation, parametric CVaR and max drawdown."""
    allocation_dict = {idx: dataframe.loc[idx].to_numpy() for idx in dataframe.index}

    returns = prices.pct_change(fill_method=None)

    tracking_error_daily = {}
    tracking_error_monthly = {}
    monthly_returns = prices.resample('ME').last().iloc[-180:].pct_change()

    # Realized (ex-post) tracking error of each 'Buy and Hold X' / 'Rebalanced X'
    # series vs the benchmark's series of the same kind. Ex-ante (static
    # weights on asset returns) only when the series aren't in portfolio_returns.
    daily_levels = portfolio_returns.pct_change(fill_method=None)
    monthly_levels = portfolio_returns.resample('ME').last().pct_change(fill_method=None)

    for key in allocation_dict:
        if benchmark not in allocation_dict:
            continue

        for kind in ('Buy and Hold ', 'Rebalanced '):
            name, bench_name = kind + key, kind + benchmark
            if name in portfolio_returns.columns and bench_name in portfolio_returns.columns:
                tracking_error_daily[name] = (daily_levels[name] - daily_levels[bench_name]).std() * np.sqrt(252)
                tracking_error_monthly[name] = (monthly_levels[name] - monthly_levels[bench_name]).std() * np.sqrt(12)
            else:
                active = allocation_dict[key] - allocation_dict[benchmark]
                tracking_error_daily[name] = RiskAnalysis(returns).variance(active)
                tracking_error_monthly[name] = RiskAnalysis(monthly_returns).variance(active) / np.sqrt(252) * np.sqrt(12)

    tracking_error_daily = pd.DataFrame(tracking_error_daily.values(), index=tracking_error_daily.keys(),
                                        columns=['Tracking Error (daily)'])
    tracking_error_monthly = pd.DataFrame(tracking_error_monthly.values(), index=tracking_error_monthly.keys(),
                                          columns=['Tracking Error (Monthly)'])

    drawdowns = (portfolio_returns - portfolio_returns.cummax()) / portfolio_returns.cummax()
    dates_drawdown = drawdowns.idxmin().dt.date

    vol = portfolio_returns.pct_change(fill_method=None).std() * np.sqrt(252)
    monthly_vol = portfolio_returns.resample('ME').last().pct_change(fill_method=None).std() * np.sqrt(12)

    drawdown = pd.DataFrame(drawdowns.min())
    Q = 0.05
    cvar = -monthly_vol * norm.pdf(norm.ppf(Q)) / Q  # normal expected shortfall, closed form

    risk = pd.concat([vol, tracking_error_daily, monthly_vol, tracking_error_monthly, cvar, drawdown, dates_drawdown],
                     axis=1).round(4)
    risk.columns = ['Annualized Volatility (daily)', 'TEV (daily)',
                    'Annualized Volatility (Monthly)', 'TEV (Monthly)',
                    'CVar Parametric ' + str(int((1 - Q) * 100)) + '%',
                    'Max Drawdown', 'Date of Max Drawdown']

    return risk.T.round(4)


def get_asset_risk(prices):
    """Volatilities over several horizons, parametric CVaR and max drawdown of each asset."""
    drawdowns = (prices - prices.cummax()) / prices.cummax()
    dates_drawdown = drawdowns.idxmin().dt.date

    # windows match the labels below: 1Y of daily returns (252 + 1 prices),
    # 3Y of weekly (156 + 1), 5Y of monthly (60 + 1), whole history monthly
    vol = prices.pct_change(fill_method=None).iloc[-253:].std() * np.sqrt(252)
    weekly_vol = prices.resample('W').last().iloc[-157:].pct_change(fill_method=None).std() * np.sqrt(52)
    monthly_vol_5Y = prices.resample('ME').last().iloc[-61:].pct_change(fill_method=None).std() * np.sqrt(12)
    monthly_vol_all = prices.resample('ME').last().pct_change(fill_method=None).std() * np.sqrt(12)

    drawdown = pd.DataFrame(drawdowns.min())
    Q = 0.05
    cvar = -monthly_vol_all * norm.pdf(norm.ppf(Q)) / Q  # normal expected shortfall, closed form

    risk = pd.concat([vol, weekly_vol, monthly_vol_5Y, monthly_vol_all, cvar, drawdown, dates_drawdown],
                     axis=1).round(4)
    risk.columns = ['Annualized Volatility (daily)',
                    'Annualized Volatility 3Y (Weekly)',
                    'Annualized Volatility 5Y (Monthly)',
                    'Annualized Volatility since ' + str(prices.index[0].year) + ' (Monthly)',
                    'CVar Parametric ' + str(int((1 - Q) * 100)) + '%', 'Max Drawdown', 'Date of Max Drawdown']

    return risk.T.round(4)


def _calendar_metrics(portfolio_returns, fund, bench, period_format, annualize_return):
    portfolio_returns = portfolio_returns[[fund, bench]].ffill()
    portfolio_returns_pct = portfolio_returns.pct_change(fill_method=None)

    period_returns = {}
    period_vol = {}
    period_tracking_error = {}
    period_sharpe_ratio = {}

    labels = portfolio_returns.index.strftime(period_format)
    periods = sorted(labels.unique())

    for i, period in enumerate(periods):
        mask_curr = labels == period
        temp = portfolio_returns_pct.loc[mask_curr]
        temp_prices = portfolio_returns.loc[mask_curr]

        if len(temp_prices) < 2:
            continue

        # the period's return starts from the previous period's last close
        first_price = temp_prices.iloc[0]
        if i > 0:
            prev_prices = portfolio_returns.loc[labels == periods[i - 1]]
            if not prev_prices.empty:
                first_price = prev_prices.iloc[-1]

        perf = temp_prices.iloc[-1] / first_price - 1
        vol = temp.std() * np.sqrt(252)

        period_returns[period] = perf
        period_vol[period] = vol
        period_tracking_error[period] = (temp[fund] - temp[bench]).std() * np.sqrt(252)
        period_sharpe_ratio[period] = annualize_return(perf) / vol

    returns_df = pd.DataFrame(period_returns).round(4)
    vol_df = pd.DataFrame(period_vol).round(4)
    tracking_error_df = pd.DataFrame.from_dict(period_tracking_error, orient='index',
                                               columns=['Tracking Error']).round(4)
    sharpe_ratio_df = pd.DataFrame(period_sharpe_ratio).round(4)

    return returns_df, vol_df, tracking_error_df, sharpe_ratio_df


def get_yearly_metrics(portfolio_returns, fund='Fund', bench='Bitcoin'):
    """Return, volatility, tracking error and Sharpe ratio by calendar year."""
    return _calendar_metrics(portfolio_returns, fund, bench, '%Y', lambda perf: perf)


def get_monthly_metrics(portfolio_returns, fund='Fund', bench='Bitcoin'):
    """Return, volatility, tracking error and Sharpe ratio by calendar month."""
    # annualize the month's return to match the annualized volatility
    return _calendar_metrics(portfolio_returns, fund, bench, '%Y-%m', lambda perf: (1 + perf) ** 12 - 1)


def get_frontier(returns, dataframe, cons=None, points=100):
    """Efficient frontier (unconstrained and, with `cons`, constrained) and
    the return / volatility / Sharpe ratio of each allocation of `dataframe`.

    Returns (indicators, frontier, frontier_constrained or None).
    """
    portfolio = RiskAnalysis(returns)
    _, frontier_returns, frontier_risks, frontier_sharpe_ratio = portfolio.efficient_frontier(points=points)

    frontier = pd.DataFrame({
        "Returns": frontier_returns,
        "Volatility": frontier_risks,
        "Sharpe Ratio": frontier_sharpe_ratio,
    })

    frontier_c = None
    if cons:
        _, returns_c, risks_c, sharpe_c = portfolio.efficient_frontier(constraints=cons, points=points)
        frontier_c = pd.DataFrame({
            "Returns": returns_c,
            "Volatility": risks_c,
            "Sharpe Ratio": sharpe_c,
        })

    metrics = {'Returns': {}, 'Volatility': {}, 'Sharpe Ratio': {}}
    for key in dataframe.index:
        weights = dataframe.loc[key].to_numpy()
        metrics['Returns'][key] = np.round(portfolio.performance(weights), 4)
        metrics['Volatility'][key] = np.round(portfolio.variance(weights), 4)
        metrics['Sharpe Ratio'][key] = np.round(metrics['Returns'][key] / metrics['Volatility'][key], 4)

    indicators = pd.DataFrame(metrics, index=dataframe.index).T

    return indicators, frontier, frontier_c
