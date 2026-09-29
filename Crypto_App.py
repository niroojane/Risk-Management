# Copyright (c) 2025 Niroojane Selvam
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import random
import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
import requests
from scipy.stats import norm, chi2,gumbel_l
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count

import ipywidgets as widgets
from ipydatagrid import DataGrid, TextRenderer
from IPython.display import display,Markdown
from IPython.display import HTML
import plotly.express as px
import plotly.graph_objects as go
import threading

from src import GitHub
from src import BinanceAPI
from src.RiskMetrics import *
from src import PnL
from src import get_close
from src.Rebalancing import *
from src.Metrics import *

def display_crypto_app(Binance,Pnl_calculation,git):
    # =========================================================================
    # Constants / shared config
    # =========================================================================
    def _set_dropdown_options(dd, options, fallback=None):
        """Reassign a Dropdown's .options while preserving its current
        .value whenever possible.

        ipywidgets resets .value to options[0] the instant .options'
        CONTENT changes at all -- even a pure superset where the old value
        is still present at the same position, not just on reorder. A
        "check-after" guard (`dd.options = opts; if dd.value not in opts:
        ...`) can't detect this: by the time it reads .value the reset has
        already silently happened, and options[0] always looks "valid" to
        the check. Capturing .value BEFORE the reassignment and restoring
        it explicitly afterward sidesteps that.

        `fallback` is used only when the previous value is no longer in
        the new options (it defaults to options[0] when omitted or itself
        not present).
        """
        options = list(options)
        if not options:
            dd.options = options
            return
        old_value = dd.value
        dd.options = options
        if old_value in options:
            dd.value = old_value
        else:
            dd.value = fallback if fallback in options else options[0]
    dico_strategies = {
        'Minimum Variance': 'minimum_variance',
        'Risk Parity': 'risk_parity',
        'Sharpe Ratio': 'sharpe_ratio',
        'Maximum Diversification': 'maximum_diversification',
        'Eigen Strategy': 'eigenportfolio'}
    options_strat = list(dico_strategies.keys())

    # 'Vol' is offered in the Risk Type dropdown but there is no downstream
    # implementation for it yet -- only 'Beta' constraints actually get built.
    RISK_TYPES_IMPLEMENTED = {'Beta','Volatility'}

    # --- globals ---
    global tickers_dataframe, tickers, dataframe, returns_to_use, prices
    global rolling_optimization, performance_pct, performance_fund, dates_end, quantities, quantities_core, quantities_overlay, cumulative_results, global_returns
    global book_cost, realized_pnl, profit_and_loss, holding_tickers, current_weights, fund_names, grid, trades

    tickers_dataframe = (
        Binance.get_market_cap()
        .set_index('Ticker')
        .loc[lambda df: ~df['Long name'].str.contains(r'\(bStocks\)', na=False)]
    )

    tickers = []
    holding_tickers = []
    dataframe = pd.DataFrame()
    cumulative_results = pd.DataFrame()
    global_returns = pd.DataFrame()
    fund_names = []
    current_weights = pd.DataFrame()
    book_cost = pd.DataFrame()
    realized_pnl = pd.DataFrame()
    trades = pd.DataFrame()
    profit_and_loss = pd.DataFrame()
    returns_to_use = pd.DataFrame()
    prices = pd.DataFrame()

    rolling_optimization = pd.DataFrame()
    quantities = pd.DataFrame()
    quantities_core = pd.DataFrame()
    quantities_overlay = pd.DataFrame()

    performance_pct = pd.DataFrame()
    performance_fund = pd.DataFrame()

    dates_end = []
    constraint_container = {'constraints': [], 'allocation_df': pd.DataFrame()}

    # =========================================================================
    # Shared beta helper (used by on_optimize_clicked, get_result's worker(),
    # and ex_ante_metrics). Previously this per-asset regression was copy-pasted
    # in three places with slightly different variable names each time -- that's
    # exactly how the `subset` NameError bug crept into ex_ante_metrics. One
    # definition now, one thing to test.
    # =========================================================================
    # def compute_rolling_per_asset_betas(returns_window, benchmark_return_series, window):
    #     """Rolling per-asset beta (slope of each asset's return vs. a benchmark
    #     return series), computed as rolling covariance / rolling variance.

    #     This is mathematically identical to the per-window `lstsq` slope used
    #     by `compute_per_asset_betas`, but vectorized across the whole history
    #     in one pass instead of one `lstsq` call per asset per window -- the
    #     difference matters a lot here since this runs on every window change.
    #     """
    #     common_index = returns_window.index.intersection(benchmark_return_series.index)
    #     returns_aligned = returns_window.loc[common_index]
    #     benchmark_aligned = benchmark_return_series.loc[common_index]

    #     rolling_cov = returns_aligned.rolling(window).cov(benchmark_aligned)
    #     rolling_var = benchmark_aligned.rolling(window).var()
    #     return rolling_cov.div(rolling_var, axis=0)

    # def compute_per_asset_betas(returns_window, benchmark_return_series):
    #     """Simple-regression beta of each asset in `returns_window` vs. a benchmark.

    #     `benchmark_return_series` should already be a return series (e.g. the
    #     output of `some_price_series.pct_change()`), not raw prices/levels.
    #     Returns a numpy array of length `returns_window.shape[1]`, one beta per
    #     asset column, in the same column order as `returns_window`.
    #     """
    #     X_raw = returns_window.fillna(0)
    #     if X_raw.shape[1] == 0 or X_raw.shape[0] == 0:
    #         return np.zeros(X_raw.shape[1])

    #     y = benchmark_return_series.reindex(X_raw.index).fillna(0)
    #     ones = np.ones((X_raw.shape[0], 1))
    #     beta = np.zeros(X_raw.shape[1])

    #     for i in range(X_raw.shape[1]):
    #         X_i = np.hstack([ones, X_raw.iloc[:, [i]].to_numpy()])
    #         beta[i] = np.linalg.lstsq(X_i, y, rcond=None)[0][1]

    #     return beta

    def build_beta_risk_constraints(returns_window, benchmark_price_or_level_series, risk_constraint_dataframe):
        """Build the beta constraint list for `risk.optimize(constraints=...)`.

        Returns [] (never raises) if there is no 'Beta' row in
        risk_constraint_dataframe -- e.g. because the user only added an
        unimplemented 'Vol' constraint -- so callers can safely `extend()`
        with the result unconditionally.
        """
        beta_rows = risk_constraint_dataframe[risk_constraint_dataframe['Risk'] == 'Beta']
        if beta_rows.empty:
            return []

        beta = compute_per_asset_betas(returns_window, benchmark_price_or_level_series.pct_change())
        beta_data = beta_rows.iloc[0]
        return beta_constraint(beta, beta_data['Sign'], beta_data['Limit'])
            
    def build_vol_risk_constraints(returns_window, risk_constraint_dataframe):
        """Build the volatility constraint list for `risk.optimize(constraints=...)`.
    
        Returns [] (never raises) if there's no 'Volatility' row -- including
        when risk_constraint_dataframe has no 'Risk' column at all, which
        happens whenever risk_constraints is empty: pd.DataFrame([]) has zero
        columns, and .drop_duplicates(subset=['Risk']) short-circuits on an
        empty frame without validating that 'Risk' exists, so this must be
        checked before indexing rather than after.
        """
        if 'Risk' not in risk_constraint_dataframe.columns:
            return []
    
        vol_rows = risk_constraint_dataframe[risk_constraint_dataframe['Risk'] == 'Volatility']
        if vol_rows.empty:
            return []
    
        vol_data = vol_rows.iloc[0]  # scalar row, not a Series -- matches build_beta_risk_constraints
        return vol_constraint(returns_window.cov(), vol_data['Sign'], vol_data['Limit'])
    # =========================================================================
    # INVESTMENT UNIVERSE TAB -- asset scope + price loading
    # =========================================================================
    start_date = widgets.DatePicker(
        value=datetime.date(2020, 1, 1),
        description='Starting Date of Backtest',
        style={'description_width': '200px'},
        layout=widgets.Layout(width='350px')
    )
    n_crypto = widgets.IntSlider(
        min=1, max=100, value=20,
        description='Number of Crypto',
        style={'description_width': '200px'},
        layout=widgets.Layout(width='500px')
    )

    loading_bar = widgets.IntProgress(description='Loading prices...', min=0, max=100, style={'description_width': '150px'})

    data_button = widgets.Button(description='Get Prices', button_style='info')
    scope_output = widgets.Output()
    strategy_output = widgets.Output()
    main_output = widgets.Output()
    output_returns = widgets.Output()
    constraint_output = widgets.Output()

    dropdown_asset1 = widgets.Dropdown(description='Asset 1:', style={'description_width': '150px'})
    dropdown_asset2 = widgets.Dropdown(description='Asset 2:', style={'description_width': '150px'})

    def scope_update(n):
        nonlocal scope_output
        global tickers_dataframe, tickers
        try:
            selected_tickers = tickers_dataframe.iloc[:n]
            selected_tickers_list = list(set(selected_tickers.index))
        except Exception as e:
            with scope_output:
                scope_output.clear_output(wait=True)
                print("Error fetching market caps:", e)
            return

        with scope_output:
            scope_output.clear_output(wait=True)
            display(display_scrollable_df(selected_tickers))

            checkboxes = {
                t: widgets.Checkbox(description=t, value=True)
                for t in selected_tickers_list
            }

            rows = [
                widgets.HBox(list(checkboxes.values())[i:i + 5])
                for i in range(0, len(checkboxes), 5)
            ]

            ui = widgets.VBox(rows)

            def on_change(change=None):
                selected = [k for k, cb in checkboxes.items() if cb.value]
                global tickers
                tickers = selected

            for cb in checkboxes.values():
                cb.observe(on_change, names="value")

            on_change()
            display(Markdown("### Selected Tickers"))
            display(ui)

    scope_update(n_crypto.value)
    n_crypto.observe(lambda ch: scope_update(ch['new']) if ch['name'] == 'value' else None, names='value')

    price_output = widgets.Output()

    def get_price_threading(tickers, start_date):
        today = datetime.date.today()
        days_total = (today - start_date).days
        if days_total <= 0:
            print("Start date must be in the past.")
            return
        remaining = days_total % 500
        numbers_of_table = days_total // 500
        loading_bar.value = 0
        display(loading_bar)
        loading_bar.max = numbers_of_table + 1

        start_dt = datetime.datetime.combine(start_date, datetime.time())
        end_dates = [
            start_dt + datetime.timedelta(days=500 * i)
            for i in range(numbers_of_table + 1)
        ]

        end_dates.append(
            datetime.datetime.combine(
                today - datetime.timedelta(days=remaining),
                datetime.time()
            )
        )

        def fetch_prices(end_date):
            return Binance.get_price(tickers, end_date)

        price = None
        try:
            with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
                futures = [executor.submit(fetch_prices, d) for d in end_dates]
                for future in as_completed(futures):
                    data = future.result()
                    if price is None:
                        price = data
                    else:
                        price = price.combine_first(data)
                    loading_bar.value += 1
        except Exception as e:
            print("❌ Error while fetching prices:", e)
            return
        price = price.sort_index()
        price = price[~price.index.duplicated(keep="first")]
        price.index = pd.to_datetime(price.index)

        loading_bar.value = loading_bar.max
        return price

    def get_prices(_=None):
        global prices, dataframe, returns_to_use, dates_end, valid_cols_model

        get_holdings(None)
        combined_tickers = sorted(list(set(tickers + holding_tickers)))

        with main_output:
            main_output.clear_output(wait=True)

            if not tickers:
                print("No tickers available. Please fetch tickers first.")
                return

            start = start_date.value
            if not isinstance(start, datetime.date):
                print("Please select a valid start date.")
                return

            scope_prices = get_price_threading(combined_tickers, start)

            prices = scope_prices.loc[:, scope_prices.columns != "USDCUSDT"]

            # returns = np.log(1 + prices.pct_change(fill_method=None))
            returns =prices.pct_change(fill_method=None)

            returns.index = pd.to_datetime(returns.index)

            valid_cols = returns.columns[returns.isna().sum() < 30]
            returns_to_use = returns[valid_cols].sort_index()

            dataframe = prices[valid_cols].sort_index().dropna()
            dataframe.index = pd.to_datetime(dataframe.index)
            returns_to_use = returns_to_use[~returns_to_use.index.duplicated(keep="first")]

            main_output.clear_output()

            dropdown_asset.options = list(dataframe.columns) + ["All"]

            dropdown_asset1.options = dataframe.columns
            dropdown_asset1.value = dataframe.columns[0]

            dropdown_asset2.options = dataframe.columns
            dropdown_asset2.value = dataframe.columns[1]

            print(
                f"✅ Loaded prices for {len(dataframe.columns)} assets "
                f"from {dataframe.index[0].date()} to {dataframe.index[-1].date()}"
            )

            asset_risk = get_asset_risk(dataframe)
            asset_returns = get_asset_returns(dataframe)

            display(display_scrollable_df(asset_returns))
            display(display_scrollable_df(asset_risk))

        with price_output:
            price_output.clear_output(wait=True)
            price_output_graph = widgets.Output()
            return_output_graph = widgets.Output()

            with price_output_graph:
                fig = px.line(
                    dataframe.loc[start_date_perf.value:end_date_perf.value],
                    title="Price", width=800, height=400, render_mode='svg')
                fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig.update_traces(visible="legendonly", selector=lambda t: t.name != "BTCUSDT")
                fig.show()
            with return_output_graph:
                cumulative_returns = returns_to_use.loc[start_date_perf.value:end_date_perf.value].copy()
                cumulative_returns.iloc[0] = 0
                cumulative_returns = (1 + cumulative_returns).cumprod() * 100
                fig2 = px.line(
                    cumulative_returns, title="Cumulative Performance",
                    width=800, height=400, render_mode='svg')
                fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig2.update_traces(visible="legendonly", selector=lambda t: t.name != "BTCUSDT")
                fig2.show()
            ui = widgets.HBox([price_output_graph, return_output_graph])
            display(ui)
            display(display_scrollable_df(dataframe))

            # Reloading prices invalidates any previously-added constraints/
            # overlays/risk limits (they may reference tickers no longer in
            # scope), so reset them rather than leave stale, possibly-invalid
            # state lying around for the next optimize click.
            on_clear_constraints(None)
            on_clear_overlays(None)
            on_clear_risk(None)

    data_button.on_click(get_prices)
    start_date.observe(lambda ch: get_prices() if ch['name'] == 'value' and ch['new'] else None, names='value')

    # =========================================================================
    # STRATEGY TAB -- constraints, overlays, risk limits, allocation grid
    # =========================================================================
    dropdown_asset = widgets.Dropdown(description='Asset:', options=['All'], value=None)
    dropdown_sign = widgets.Dropdown(description='Sign:', options=["=", "≥", "≤"])
    dropdown_limit = widgets.FloatText(description='Limit')
    add_constraint_btn = widgets.Button(description='Add Constraint', button_style='success')
    clear_constraints_btn = widgets.Button(description='Clear All', button_style='danger')
    constraints = []

    selected_fund = widgets.Dropdown(description="Fund:")
    selected_bench = widgets.Dropdown(description="Bench:")
    selected_fund_var = widgets.Dropdown(description="Fund:")
    options_risk = ['Beta', 'Volatility']

    add_strategy_btn = widgets.Button(description='Add Strategy', style={'description_width': '150px'})
    clear_strategy_btn = widgets.Button(description='Clear Strategy', style={'description_width': '150px'})
    add_risk_btn = widgets.Button(description='Add Risk Strat', style={'description_width': '150px'})
    clear_risk_btn = widgets.Button(description='Clear Risk Strat', style={'description_width': '150px'})

    dropdown_strategy_limit = widgets.FloatText(description='Overlay Limit', style={'description_width': '150px'})
    strat_overlay = widgets.Dropdown(description='Strategy Overlay', options=options_strat, value='Minimum Variance', style={'description_width': '150px'})
    risk_type = widgets.Dropdown(description='Risk Type', value=None, options=options_risk, style={'description_width': '150px'})
    risk_limit = widgets.FloatText(description='Risk Limit', value=None, style={'description_width': '150px'})
    dropdown_risk_sign = widgets.Dropdown(description='Sign:', options=["=", "≥", "≤"], style={'description_width': '150px'})
    overlays = []
    overlay_output = widgets.Output()

    def on_add_overlays(_):
        overlays.append({
            'Strategy': strat_overlay.value,
            'Limit': dropdown_strategy_limit.value
        })
        with overlay_output:
            overlay_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(overlays)))

    def on_clear_overlays(_):
        overlays.clear()
        with overlay_output:
            overlay_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(columns=['Strategy', 'Limit'])))

    add_strategy_btn.on_click(on_add_overlays)
    clear_strategy_btn.on_click(on_clear_overlays)

    risk_constraints = []
    risk_constraints_output = widgets.Output()

    def on_add_risk(_):
        # Guard against adding a row with no Risk Type selected (dropdown
        # defaults to None), which would otherwise silently poison
        # risk_constraint_dataframe downstream.
        if risk_type.value is None:
            with risk_constraints_output:
                risk_constraints_output.clear_output(wait=True)
                print("⚠️ Select a Risk Type before adding.")
                display(display_scrollable_df(
                    pd.DataFrame(risk_constraints).drop_duplicates(subset=['Risk'], keep='last')
                    if risk_constraints else pd.DataFrame(columns=['Risk', 'Sign', 'Limit'])
                ))
            return

        if risk_type.value not in RISK_TYPES_IMPLEMENTED:
            with risk_constraints_output:
                risk_constraints_output.clear_output(wait=True)
                print(f"⚠️ '{risk_type.value}' isn't implemented yet in the optimizer -- "
                      f"only {sorted(RISK_TYPES_IMPLEMENTED)} constraints are actually applied.")

        risk_constraints.append({
            'Risk': risk_type.value, 'Sign': dropdown_risk_sign.value,
            'Limit': risk_limit.value
        })

        with risk_constraints_output:
            risk_constraints_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(risk_constraints).drop_duplicates(subset=['Risk'], keep='last')))

    def on_clear_risk(_):
        risk_constraints.clear()
        with risk_constraints_output:
            risk_constraints_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(columns=['Risk', 'Sign', 'Limit'])))

    add_risk_btn.on_click(on_add_risk)
    clear_risk_btn.on_click(on_clear_risk)

    def on_add_constraint_clicked(_):
        if dropdown_asset.value is None:
            with constraint_output:
                constraint_output.clear_output(wait=True)
                print("⚠️ Select an Asset before adding a constraint.")
                display(display_scrollable_df(pd.DataFrame(constraints) if constraints else pd.DataFrame(columns=['Asset', 'Sign', 'Limit'])))
            return
        constraints.append({
            'Asset': dropdown_asset.value,
            'Sign': dropdown_risk_sign.value,
            'Limit': dropdown_limit.value
        })
        with constraint_output:
            constraint_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(constraints)))

    def on_clear_constraints(_):
        constraints.clear()
        with constraint_output:
            constraint_output.clear_output(wait=True)
            display(display_scrollable_df(pd.DataFrame(columns=['Asset', 'Sign', 'Limit'])))

    add_constraint_btn.on_click(on_add_constraint_clicked)
    clear_constraints_btn.on_click(on_clear_constraints)

    def on_add_click(b):
        global fund_names, grid
        if grid.data is None or grid.data.empty:
            return
        new_row = np.zeros(dataframe.shape[1])
        label = f"Allocation {grid.data.shape[0]}"
        new_df = pd.DataFrame([new_row], columns=grid.data.columns, index=[label])
        updated_df = pd.concat([pd.DataFrame(grid.data), new_df])
        grid.data = updated_df

        _set_dropdown_options(benchmark_tracking_error, grid.data.index)
        _set_dropdown_options(selected_fund, grid.data.index)
        _set_dropdown_options(selected_bench, grid.data.index)
        _set_dropdown_options(selected_fund_var, grid.data.index)

    def clear_allocation(b):
        nonlocal constraint_container
        if constraint_container.get('allocation_df') is not None:
            grid.data = constraint_container['allocation_df']

    button_add = widgets.Button(description="Add Allocation")
    button_clear = widgets.Button(description="Clear Allocation")
    button_add.on_click(on_add_click)
    button_clear.on_click(clear_allocation)

    # --- date pickers for performance ---
    if isinstance(start_date.value, datetime.date):
        sd = start_date.value
        start_perf_date = datetime.date(sd.year, sd.month + 2, 1)
    else:
        start_perf_date = datetime.date.today() - datetime.timedelta(days=365)
    start_date_perf = widgets.DatePicker(value=start_perf_date, layout=widgets.Layout(width='350px'))
    end_date_perf = widgets.DatePicker(value=datetime.date.today(), layout=widgets.Layout(width='350px'))

    frequency_graph = widgets.Dropdown(description='Frequency:', options=['Year', 'Month'], value='Year')
    # Hard-loaded to the intended Fund vs Core pair from the start, so the
    # Calendar Return chart already shows that pairing even before any data
    # is loaded, and update_dropdown_options' "value not in options" guard
    # has nothing to do once real options arrive (both are already right).
    # Distinct values matter here -- see benchmark_ex_post below for what
    # goes wrong when a fund/benchmark pair share the same placeholder.
    fund = widgets.Dropdown(description='Fund:', options=['Fund', 'Core'], value='Fund')
    benchmark = widgets.Dropdown(description='Benchmark:', options=['Fund', 'Core'], value='Core')
    benchmark_tracking_error = widgets.Dropdown(description='Benchmark:')
    perf_output = widgets.Output()
    vol_output = widgets.Output()
    drawdown_output = widgets.Output()
    frontier_output = widgets.Output()

    def updated_cumulative_perf(_):
        global performance_pct, performance_fund, cumulative_results, global_returns

        try:
            start_ts = pd.to_datetime(start_date_perf.value)
            end_ts = pd.to_datetime(end_date_perf.value)
        except Exception:
            with output_returns:
                output_returns.clear_output(wait=True)
                print("⚠️ Invalid start/end dates.")
            return

        if dataframe.empty:
            with main_output:
                main_output.clear_output(wait=True)
                print("⚠️ Load Prices.")
                return
        else:
            with main_output:
                main_output.clear_output(wait=True)
                range_prices = dataframe.loc[start_ts:end_ts]
                range_returns = range_prices.pct_change(fill_method=None)

                asset_risk = get_asset_risk(range_prices)
                asset_returns = get_asset_returns(range_prices)
                display(display_scrollable_df(asset_returns))
                display(display_scrollable_df(asset_risk))

            with price_output:
                price_output.clear_output(wait=True)
                price_output_graph = widgets.Output()
                return_output_graph = widgets.Output()

                with price_output_graph:
                    fig = px.line(dataframe.loc[start_date_perf.value:end_date_perf.value], title='Price', width=800, height=400, render_mode='svg')
                    fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                    fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["BTCUSDT"])
                    fig.show()
                with return_output_graph:
                    cumulative_returns = returns_to_use.loc[start_date_perf.value:end_date_perf.value].copy()
                    cumulative_returns.iloc[0] = 0
                    cumulative_returns = (1 + cumulative_returns).cumprod() * 100

                    fig2 = px.line(cumulative_returns, title='Cumulative Performance', width=800, height=400, render_mode='svg')
                    fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                    fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ["BTCUSDT"])
                    fig2.show()

                ui = widgets.HBox([price_output_graph, return_output_graph])
                display(ui)
                display(display_scrollable_df(dataframe))
        if performance_pct is None or performance_pct.empty:
            with output_returns:
                output_returns.clear_output(wait=True)
                print("⚠️ No performance data available yet. Please run an optimization first.")
            return

        if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
            with main_output:
                main_output.clear_output()
                print("⚠️ Invalid date range.")
            with output_returns:
                output_returns.clear_output()
                print("⚠️ Invalid date range.")
            with vol_output:
                vol_output.clear_output()
            with perf_output:
                perf_output.clear_output()
            with drawdown_output:
                drawdown_output.clear_output()
            with frontier_output:
                frontier_output.clear_output()
            return

        constraint_df = pd.DataFrame(constraints)
        cons = None
        if not constraint_df.empty:
            try:
                cons = build_constraint(dataframe, constraint_df.to_numpy())
            except Exception as e:
                print("Error building constraints:", e)
        performance_pct.index = pd.to_datetime(performance_pct.index)
        cumulative_performance = performance_pct.loc[start_ts:end_ts]
        if cumulative_performance.empty:
            available_start = performance_pct.index.min().date()
            available_end = performance_pct.index.max().date()
            with output_returns:
                output_returns.clear_output(wait=True)
                print(f"⚠️ No data found for this date range. Available range: {available_start} → {available_end}")
            return
        cumulative_performance.iloc[0] = 0
        cumulative_results = (1 + cumulative_performance).cumprod() * 100

        # Rebalanced X and Buy and Hold X are both anchored on the full
        # backtest history (dataframe) now, matching _build_weight_series_dict
        # in the P&L Analysis tab below -- one continuous simulation each,
        # with start_ts/end_ts only cropping which slice is shown, drift
        # included, instead of restarting Rebalanced X from target weights
        # every time the window changes. Rebased to 100 at the window's own
        # start so it's on the same scale as cumulative_performance above,
        # which is rebased the same way.
        portfolio_returns = rebalanced_time_series(dataframe, grid.data, frequency=rebalancing_frequency.value)
        portfolio_returns = portfolio_returns.loc[start_ts:end_ts]
        portfolio_returns = portfolio_returns.div(portfolio_returns.iloc[0]) * 100
        cumulative_results = pd.concat([cumulative_results, portfolio_returns], axis=1)
        global_returns = cumulative_results.pct_change(fill_method=None)

        drawdown = (cumulative_results - cumulative_results.cummax()) / cumulative_results.cummax()
        rolling_vol_ptf = cumulative_results.pct_change(fill_method=None).rolling(window_vol.value).std() * np.sqrt(260)
        frontier_indicators, fig4 = get_frontier(range_returns, grid.data, cons)
        update_dropdown_options()

        with output_returns:
            output_returns.clear_output(wait=True)
            display(display_scrollable_df(rebalanced_metrics(cumulative_results)))
            display(display_scrollable_df(get_portfolio_risk(grid.data, range_prices, cumulative_results, benchmark_tracking_error.value)))
            display(display_scrollable_df(frontier_indicators))
        with perf_output:
            perf_output.clear_output(wait=True)
            fig = px.line(cumulative_results, title='Performance', width=800, height=400, render_mode='svg')
            fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
            fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Fund", "Bitcoin"])
            fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig.show()
        with drawdown_output:
            drawdown_output.clear_output(wait=True)
            fig2 = px.line(drawdown, title='Drawdown', width=800, height=400, render_mode='svg')
            fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
            fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Fund", "Bitcoin"])
            fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig2.show()
        with vol_output:
            vol_output.clear_output(wait=True)
            fig3 = px.line(rolling_vol_ptf, title="Portfolio Rolling Volatility", render_mode='svg')
            fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
            fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Fund", "Bitcoin"])
            fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig3.show()
        with frontier_output:
            frontier_output.clear_output(wait=True)
            fig4.update_layout(width=800, height=400, title={'text': "Efficient Frontier"}, yaxis_tickformat=".2%", xaxis_tickformat=".2%")
            fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig4.show()

    refresh_perf_button = widgets.Button(description='Refresh')
    refresh_perf_button.on_click(updated_cumulative_perf)

    # =========================================================================
    # OPTIMIZATION
    # =========================================================================
    rebalancing_frequency = widgets.Dropdown(description='Frequency', options=['Monthly', 'Quarterly', 'Yearly'], value='Monthly')
    strat = widgets.Dropdown(description='Strategy', options=options_strat, value='Minimum Variance')
    window_vol = widgets.IntText(value=252, description='Vol Window:', disabled=False)
    calendar_output = widgets.Output()

    def show_graph(_):
        with calendar_output:
            calendar_output.clear_output(wait=True)

            if cumulative_results.empty or cumulative_results.shape[1] < 2:
                print("⚠️ No performance data available yet. Please run an optimization first.")
                return
            if fund.value == benchmark.value:
                print("⚠️ Benchmark and Fund must be different.")
                return

            graphs = get_calendar_graph(cumulative_results,
                                         freq=frequency_graph.value,
                                         benchmark=benchmark.value,
                                         fund=fund.value)

            return_and_vol_graph = widgets.Output()
            sharpe_and_te_graph = widgets.Output()
            keys = list(graphs.keys())

            with return_and_vol_graph:
                graphs[keys[0]].show()
                graphs[keys[2]].show()
            with sharpe_and_te_graph:
                graphs[keys[1]].show()
                graphs[keys[3]].show()

            ui = widgets.HBox([return_and_vol_graph, sharpe_and_te_graph])
            display(ui)

    graph_button = widgets.Button(description='Update Perf', button_style='info')
    graph_button.on_click(show_graph)
    optimize_btn = widgets.Button(description='Optimize Portfolio', button_style='primary')
    grid = DataGrid(pd.DataFrame(), editable=True, layout={"height": "250px"})

    def update_dropdown_options():
        """Safely refresh fund/benchmark dropdowns after cumulative_results is updated."""
        if 'cumulative_results' not in globals() or cumulative_results.empty:
            return
        global fund_names

        options = list(cumulative_results.columns)

        # Capture BEFORE reassigning .options below -- ipywidgets' Dropdown
        # resets .value to options[0] the instant .options' CONTENT changes
        # at all (even a pure superset, old value still present at the same
        # position), not just on reorder. Reading .value after the
        # reassignment can't detect that, since options[0] is itself
        # "valid" -- restoring the captured value explicitly sidesteps it.
        old_fund_value = fund.value
        old_bench_value = benchmark.value

        fund.options = options
        benchmark.options = options

        if old_fund_value in options:
            fund.value = old_fund_value
        else:
            fund.value = options[0]
        if old_bench_value in options:
            benchmark.value = old_bench_value
        else:
            benchmark.value = options[1] if len(options) > 1 else options[0]
        fund_names = list(grid.data.index)
        _set_dropdown_options(benchmark_tracking_error, grid.data.index)
        _set_dropdown_options(selected_fund, grid.data.index)
        _set_dropdown_options(selected_bench, grid.data.index)
        _set_dropdown_options(selected_fund_var, grid.data.index)

    def on_optimize_clicked(_):
        global fund_names, grid
        # Without this, the `constraint_container = {...}` assignment below
        # creates a function-local shadow instead of updating the outer
        # variable -- clear_allocation's "Clear Allocation" button reads that
        # outer constraint_container via its own nonlocal, so it would always
        # see the initial empty placeholder ({'allocation_df': pd.DataFrame()})
        # and reset grid.data to empty instead of restoring the last optimized
        # allocation table.
        nonlocal constraint_container
        with constraint_output:
            constraint_output.clear_output(wait=True)
            if dataframe.empty or returns_to_use.empty:
                print("⚠️ Load price data before optimizing.")
                return

            all_constraints = []
            constraint_df = pd.DataFrame(constraints)
            risk_constraint_dataframe = pd.DataFrame(risk_constraints).drop_duplicates(subset=['Risk'], keep='last')
            cons = None
            if not constraint_df.empty:
                try:
                    cons = build_constraint(dataframe, constraint_df.to_numpy())
                    all_constraints.extend(cons)
                except Exception as e:
                    print("Error building constraints:", e)

            if not risk_constraint_dataframe.empty and not grid.data.empty and benchmark_tracking_error.value in grid.data.index:
                try:
                    window_returns = returns_to_use.loc[start_date_perf.value:end_date_perf.value]
                    benchmark_price_series = rebalanced_portfolio(
                        dataframe.loc[start_date_perf.value:end_date_perf.value],
                        grid.data.loc[benchmark_tracking_error.value],
                        frequency=rebalancing_frequency.value
                    ).sum(axis=1)
                    risk_cons = build_beta_risk_constraints(window_returns, benchmark_price_series, risk_constraint_dataframe)
                    vol_cons=build_vol_risk_constraints(window_returns,risk_constraint_dataframe)
                    if risk_cons:
                        all_constraints.extend(risk_cons)
                    if vol_cons:
                        all_constraints.extend(vol_cons)
                except Exception as e:
                    print("Error building risk constraints:", e)
            elif not risk_constraint_dataframe.empty:
                print("⚠️ Skipping risk constraints: no benchmark allocation selected yet.")

            portfolio = RiskAnalysis(returns_to_use.loc[start_date_perf.value:end_date_perf.value])
            sharpe = portfolio.optimize("sharpe_ratio")
            minvar = portfolio.optimize("minimum_variance")
            rp = portfolio.optimize("risk_parity")
            max_div = portfolio.optimize("maximum_diversification")

            sharpe_c = minvar_c = rp_c = max_div_c = eigen_portfolio_c = None
            equal_weights = np.ones(returns_to_use.shape[1]) / returns_to_use.shape[1]
            eigen_portfolio = portfolio.optimize("eigenportfolio")

            if all_constraints:
                sharpe_c = portfolio.optimize("sharpe_ratio", constraints=all_constraints)
                minvar_c = portfolio.optimize("minimum_variance", constraints=all_constraints)
                rp_c = portfolio.optimize("risk_parity", constraints=all_constraints)
                max_div_c = portfolio.optimize("maximum_diversification", constraints=all_constraints)
                eigen_portfolio_c = portfolio.optimize("eigenportfolio", constraints=all_constraints)

            allocation = {
                'Optimal Portfolio': sharpe.tolist(),
                'Constrained Optimal Portfolio': sharpe_c.tolist() if sharpe_c is not None else sharpe.tolist(),
                'Min Variance': minvar.tolist(),
                'Constrained Min Var': minvar_c.tolist() if minvar_c is not None else minvar.tolist(),
                'Max Diversification': max_div.tolist(),
                'Max Diversification Constrained': max_div_c.tolist() if max_div_c is not None else max_div.tolist(),
                'Risk Parity': rp.tolist(),
                'Constrained RP': rp_c.tolist() if rp_c is not None else rp.tolist(),
                'Eigen Portfolio': eigen_portfolio.tolist(),
                'Eigen Portfolio Constrained': eigen_portfolio_c.tolist() if eigen_portfolio_c is not None else eigen_portfolio.tolist(),
                'Equal Weighted': equal_weights.tolist()}
            allocation_df = pd.DataFrame(allocation, index=dataframe.columns).T.round(4)
            if set(current_weights.index).issubset(dataframe.columns):
                allocation_df = allocation_df.combine_first(current_weights.T).fillna(0)

            constraint_container = {'constraints_dataframe': constraints, 'constraints': cons, 'allocation_df': allocation_df}
            grid.data = allocation_df

            # Preserves whatever fund/benchmark you'd already picked in the
            # risk tabs when re-running Optimize (e.g. after tweaking a
            # constraint), if that name is still a valid row in the new
            # grid.data -- see _set_dropdown_options for why a plain
            # "options = ...; if value not in options" guard can't do that
            # (ipywidgets has already reset .value to options[0] by the
            # time such a guard reads it).
            _set_dropdown_options(benchmark_tracking_error, grid.data.index)
            _set_dropdown_options(selected_fund, grid.data.index)
            _set_dropdown_options(selected_bench, grid.data.index)
            _set_dropdown_options(selected_fund_var, grid.data.index)

            with constraint_output:
                constraint_output.clear_output(wait=True)
                display(display_scrollable_df(pd.DataFrame(constraints)))

            reset_stress(None)
            refresh_trajectory_dropdowns()

    def get_result(_):
        nonlocal constraint_container
        global rolling_optimization, performance_pct, performance_fund, dates_end, quantities, quantities_core, quantities_overlay

        with strategy_output:
            strategy_output.clear_output(wait=True)
            if dataframe.empty or returns_to_use.empty:
                print("⚠️ Load price data before optimizing.")
                return

            cons = None
            risk_constraint_dataframe = pd.DataFrame(risk_constraints).drop_duplicates(subset=['Risk'], keep='last')

            # Computed ONCE here, not per-window inside worker(): the benchmark
            # fund's realized returns over the FULL price history. Every
            # rolling-window worker just reindexes/slices this shared series
            # instead of recomputing rebalanced_portfolio() from scratch on
            # every thread call -- previously the main perf bottleneck for
            # rolling optimizations with many windows/overlays.
            benchmark_price_series_full = None
            if not risk_constraint_dataframe.empty and not grid.data.empty and benchmark_tracking_error.value in grid.data.index:
                benchmark_price_series_full = rebalanced_portfolio(
                    dataframe, grid.data.loc[benchmark_tracking_error.value], frequency=rebalancing_frequency.value
                ).sum(axis=1)
            elif not risk_constraint_dataframe.empty:
                print("⚠️ Skipping risk constraints: no benchmark allocation selected yet.")

            if constraints:
                try:
                    cons = build_constraint(dataframe, pd.DataFrame(constraints).to_numpy())
                except Exception as e:
                    print("Error building constraints:", e)

            freq_map = {
                'Monthly': pd.offsets.BMonthEnd(),
                'Quarterly': pd.offsets.BQuarterEnd(),
                'Yearly': pd.offsets.BYearEnd()
            }
            offset = freq_map.get(rebalancing_frequency.value, pd.offsets.BMonthEnd())
            candidate_anchors = pd.DatetimeIndex(sorted(set(dataframe.index + offset)))
            if candidate_anchors.empty:
                candidate_anchors = pd.DatetimeIndex([returns_to_use.index[-1]])

            idx = returns_to_use.index.get_indexer(candidate_anchors, method='nearest')
            idx = np.array(idx)
            idx = idx[idx >= 0]
            selected_dates = returns_to_use.index[idx].tolist()
            dates_end = sorted(list(set(selected_dates + [returns_to_use.index[-1]])))

            if len(dates_end) < 2:
                print("⚠️ Not enough anchor dates to perform rolling optimization.")
                return

            strategy_key = dico_strategies[strat.value]
            tasks = [(returns_to_use.loc[dates_end[i]:dates_end[i + 1]], dates_end[i], dates_end[i + 1], strategy_key) for i in range(len(dates_end) - 1)]
            overlays_tasks = [
                (
                    returns_to_use.loc[dates_end[i]:dates_end[i + 1]],
                    dates_end[i],
                    dates_end[i + 1],
                    dico_strategies[row['Strategy']]
                )
                for i in range(len(dates_end) - 1)
                for row in overlays
            ]

            all_tasks = tasks + overlays_tasks
            global results
            results = {}
            # Two rolling windows for the same strategy can finish at the same
            # instant on different threads. Without this lock, the
            # check-then-set "if key not in results: results[key] = {}" pattern
            # is a classic race: both threads could create a fresh dict for the
            # same strategy at once, and whichever assignment lands second
            # silently discards the other thread's window result.
            results_lock = threading.Lock()

            def worker(subset, start, end, strategy_key):
                risk_cons = []

                if subset.empty or len(subset) < 2:
                    return None
                    
                vol_cons = []
                try:
                    vol_cons = build_vol_risk_constraints(subset, risk_constraint_dataframe)
                except Exception as e:
                    print(f"Vol constraint failed {start} -> {end}: {e}")
                    vol_cons = []
                    
                if benchmark_price_series_full is not None:
                    try:
                        risk_cons = build_beta_risk_constraints(subset, benchmark_price_series_full, risk_constraint_dataframe)

                    except Exception as e:
                        print(f"Beta constraint failed {start} -> {end}: {e}")
                        risk_cons = []
                
                
                try:
                    risk = RiskAnalysis(subset)
                    constraints_to_use = []

                    if cons:
                        constraints_to_use.extend(cons)
                    if risk_cons:
                        constraints_to_use.extend(risk_cons)
                    if vol_cons:
                        constraints_to_use.extend(vol_cons)
                    if constraints_to_use:
                        opt = risk.optimize(objective=strategy_key, constraints=constraints_to_use)
                    else:
                        opt = risk.optimize(objective=strategy_key)

                    return subset.index[-1], np.round(opt, 6), strategy_key

                except Exception as e:
                    print(f"Optimization failed {start} -> {end}: {e}")
                    return None

            with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
                futures = {
                    executor.submit(worker, subset, start, end, strat_): (subset, start, end, strat_)
                    for subset, start, end, strat_ in all_tasks
                }

                for future in as_completed(futures):
                    out = future.result()
                    if out is not None:
                        date_key, weights, strategy_selected = out
                        with results_lock:
                            results.setdefault(strategy_selected, {})[date_key] = weights

            rolling_optimization = pd.DataFrame(results[strategy_key], index=dataframe.columns).T.sort_index()
            total_overlay = pd.DataFrame(0, index=rolling_optimization.index, columns=rolling_optimization.columns)
            core_weights = 1
            overlays_df = pd.DataFrame(overlays)
            core_strat = rolling_optimization.copy()  # keep copy of core strategy

            for _, row in overlays_df.iterrows():
                strat_key = dico_strategies[row['Strategy']]
                overlay_df = (
                    pd.DataFrame(results[strat_key], index=dataframe.columns)
                    .T
                    .sort_index()
                    * row['Limit']
                )
                total_overlay = total_overlay.add(overlay_df, fill_value=0)
                core_weights -= row['Limit']

            if core_weights < -1e-9:
                raise ValueError("⚠️ Overlay weights exceed 100%")
            core_weights = max(core_weights, 0.0)

            rolling_optimization = rolling_optimization * core_weights + total_overlay

            if not rolling_optimization.empty:
                first_row = pd.Series(1 / len(dataframe.columns), index=dataframe.columns, name=dates_end[0])
                rolling_optimization = pd.concat([pd.DataFrame([first_row]), rolling_optimization])
                core_strat = pd.concat([pd.DataFrame([first_row]), core_strat])
                denom = (1 - core_weights) if core_weights < 1 else 1
                total_overlay = pd.concat([pd.DataFrame([first_row]), total_overlay / denom])

            core_output = widgets.Output()
            overlay_weights_output = widgets.Output()
            final_weights_output = widgets.Output()
            with core_output:
                display(Markdown("### Core Strategy"))
                display(display_scrollable_df(core_strat))
            with overlay_weights_output:
                display(Markdown("### Tactical Allocation"))
                display(display_scrollable_df(total_overlay))
            with final_weights_output:
                display(Markdown("### Final Strategy"))
                display(display_scrollable_df(rolling_optimization)),
            strategies_decomposition = widgets.HBox([final_weights_output, core_output, overlay_weights_output])
            display(strategies_decomposition)

            model = pd.DataFrame(rolling_optimization.iloc[-2])
            model.columns = ['Model']
            if 'Model' not in grid.data.index:
                grid.data = pd.concat([grid.data, model.T], axis=0)

            quantities = rebalanced_dynamic_quantities(dataframe, rolling_optimization)
            quantities_core = rebalanced_dynamic_quantities(dataframe, core_strat)
            quantities_overlay = rebalanced_dynamic_quantities(dataframe, total_overlay)
            performance_fund = pd.DataFrame({'Fund': (quantities * dataframe).sum(axis=1),
                                              'Core': (quantities_core * dataframe).sum(axis=1),
                                              'Overlay': (quantities_overlay * dataframe).sum(axis=1)})

            if 'BTCUSDT' in dataframe.columns:
                performance_fund['Bitcoin'] = dataframe['BTCUSDT']
            performance_pct = performance_fund.pct_change(fill_method=None)

            cumulative = (1 + performance_pct).cumprod() * 100
            drawdown = pd.DataFrame((cumulative - cumulative.cummax())) / cumulative.cummax()
            date_drawdown = drawdown.idxmin().dt.date
            max_drawdown = drawdown.min()

            metrics = pd.DataFrame()
            # '- 1' here: this is a return (e.g. 0.5 for +50%), not a growth
            # multiplier (1.5) -- the Sharpe Ratio line below assumes that.
            metrics['Returns'] = performance_fund.iloc[-2] / performance_fund.iloc[0] - 1
            metrics['Volatility'] = performance_pct.std() * np.sqrt(252)
            # Annualize the return (**(1/years), matching the multiplier form,
            # then '- 1' back to a return) before dividing by volatility.
            # Previously this added 1 to an already-a-return figure a second
            # time and never subtracted 1 back off after annualizing --
            # neither the Returns nor the Sharpe Ratio columns were computing
            # what their labels said.
            annualized_return = (1 + metrics['Returns']) ** (1 / len(set(returns_to_use.index.year))) - 1
            metrics['Sharpe Ratio'] = annualized_return / metrics['Volatility']
            metrics['Drawdown'] = max_drawdown
            metrics['Date Drawdown'] = date_drawdown
            excess_returns_to_btc = performance_pct.loc[:, performance_pct.columns != 'Bitcoin'].sub(
                performance_pct['Bitcoin'], axis=0
            )
            metrics['Tracking Error to Bitcoin'] = (excess_returns_to_btc).std() * np.sqrt(252)

            excess_returns_to_core = performance_pct.loc[:, performance_pct.columns != 'Core'].sub(
                performance_pct['Core'], axis=0
            )
            metrics['Tracking Error to Core'] = (excess_returns_to_core).std() * np.sqrt(252)
            metrics = metrics.fillna(0).T
            display(display_scrollable_df(metrics.round(4)))
            updated_cumulative_perf(None)
            show_graph(None)
            get_holdings(None)
            refresh_trajectory_dropdowns()
            # 'Fund' just became available (or newly refreshed) here via
            # `quantities` -- if 'Get P&L' already ran, the Current Portfolio
            # Calendar Return chart was sitting there mid-load (fund_ex_post/
            # benchmark_ex_post both stuck on 'Historical Portfolio', see
            # show_graph_ex_post) and nothing else would ever re-render it.
            # Harmless to call before 'Get P&L' has run -- it just prints
            # "P&L not computed." and returns.
            show_graph_ex_post(None)

    optimize_btn.on_click(on_optimize_clicked)
    results_button = widgets.Button(description='Get Results', button_style='info')
    results_button.on_click(get_result)
    positions_output = widgets.Output()
    holding_output = widgets.Output()
    loading_bar_pnl = widgets.IntProgress(description='Loading P&L...', min=0, max=100, style={'description_width': '150px'})

    def get_holdings(_):
        global holding_tickers, current_weights, pnl

        quantities_api = Binance.binance_api.user_asset()
        current_quantities = pd.DataFrame(quantities_api).sort_values(by='free', ascending=False)
        current_quantities['asset'] = current_quantities['asset'] + 'USDT'
        current_quantities = current_quantities.set_index('asset')

        current_positions = Binance.get_inventory().round(4)
        current_positions.columns = ['Current Portfolio in USDT', 'Current Weights']
        amount = current_positions.loc['Total']['Current Portfolio in USDT']
        condition = current_positions.index != 'Total'
        holding_tickers = current_positions.index[condition]
        holding_tickers = holding_tickers.to_list()

        inventory_weights = (current_positions['Current Weights'].apply(lambda x: np.round(x, 4))).to_dict()
        # These keys may legitimately be absent (e.g. no USDC/USDT held that
        # day) -- .pop(..., None) so a missing key never crashes holdings.
        inventory_weights.pop('Total', None)
        inventory_weights.pop('USDCUSDT', None)
        inventory_weights.pop('USDTUSDT', None)

        current_weights = pd.DataFrame(inventory_weights.values(), index=inventory_weights.keys(), columns=['Current Weights'])

        with positions_output:
            positions_output.clear_output(wait=True)

            if dataframe.empty or returns_to_use.empty:
                print("⚠️ Load Prices.")
            elif quantities.empty:
                print("⚠️ Load Model.")
            else:
                last_prices = Binance.get_price(list(quantities.iloc[-1].keys()))
                positions = pd.DataFrame(quantities.iloc[-1] * last_prices).T

                amount_ex_out_of_positions = (
                    current_positions.loc[
                        ~(current_positions.index.isin(positions.index) | (current_positions.index == 'Total')),
                        'Current Portfolio in USDT'
                    ].sum()
                )

                positions['Weights Model'] = positions / positions.sum()
                positions['Model (without out of Model Positions)'] = (
                    positions['Weights Model'] * (amount - amount_ex_out_of_positions)
                )
                positions['Model'] = positions['Weights Model'] * amount

                portfolio = pd.concat(
                    [positions[['Model', 'Model (without out of Model Positions)', 'Weights Model']],
                     current_positions.loc[condition]],
                    axis=1
                ).fillna(0)

                portfolio['Spread'] = portfolio['Current Portfolio in USDT'] - portfolio['Model']
                portfolio.loc['Total'] = portfolio.sum(axis=0)
                portfolio = (
                    portfolio.loc[~(portfolio == 0).all(axis=1)]
                    .sort_values(by='Weights Model', ascending=False)
                    .round(4)
                )

                display(display_scrollable_df(portfolio))

        with holding_output:
            holding_output.clear_output(wait=True)

            if book_cost.empty and realized_pnl.empty:
                display(display_scrollable_df(current_positions))
                print("⚠️ P&L not Computed.")
            else:
                last_book_cost = book_cost.iloc[-1] if not book_cost.empty else pd.Series(dtype=float)
                realized_pnl_filled = realized_pnl if not realized_pnl.empty else pd.Series(dtype=float)

                pnl = pd.concat(
                    [last_book_cost, last_book_cost, current_positions.loc[condition], realized_pnl_filled],
                    axis=1
                )
                pnl.columns = ['Average Cost', 'Book Cost', 'Price in USDT', 'Weights', 'Realized P&L']

                pnl['Book Cost'] = (pnl['Book Cost'] * current_quantities['free'].astype(float)).fillna(0)
                pnl['Unrealized P&L'] = (pnl['Price in USDT'] - pnl['Book Cost']).round(2)
                pnl = pnl.fillna(0)
                pnl['Weights'] = pnl['Weights'].round(4)

                pnl['Total P&L'] = pnl['Unrealized P&L']  # realized P&L intentionally excluded
                pnl.loc['Total'] = pnl.sum()
                pnl.loc['Total', 'Average Cost'] = np.nan
                pnl.loc['Total', 'Book Cost'] = pnl.loc['Total', 'Price in USDT'] - pnl.loc['Total', 'Total P&L']

                if pnl.loc['Total', 'Book Cost'] != 0:
                    pnl['Total P&L %'] = pnl['Total P&L'] / pnl.loc['Total', 'Book Cost'] * 100
                else:
                    pnl['Total P&L %'] = 0

                display(display_scrollable_df(pnl.sort_values(by='Weights', ascending=False).round(4)))
                display(display_scrollable_df(trades))

    def get_pnl_on_click(_):
        global book_cost, realized_pnl, profit_and_loss, trades

        url = 'https://github.com/niroojane/Risk-Management/raw/refs/heads/main/BinancePTF/Trade%20History%20Reconstructed.xlsx'
        trade_history = read_excel_from_url(url)

        if trade_history is None:
            raise FileNotFoundError("Trade history could not be loaded. Execution stopped.")
        loading_bar_pnl.value = 0

        with holding_output:
            display(loading_bar_pnl)

        trades = Pnl_calculation.get_trade_in_usdt(trade_history)
        loading_bar_pnl.value += 100 / 3
        book_cost = Pnl_calculation.get_book_cost(trades)
        book_cost['MANTRAUSDT'] = book_cost['OMUSDT'] / 4
        loading_bar_pnl.value += 100 / 3
        realized_pnl, profit_and_loss = Pnl_calculation.get_pnl(book_cost, trades)
        trades = trades.set_index('Date(UTC)')
        loading_bar_pnl.value += 100 / 3
        with holding_output:
            holding_output.clear_output()

        get_holdings(None)

    pnl_button = widgets.Button(description='Get P&L', button_style='info')
    pnl_button.on_click(get_pnl_on_click)

    position_button = widgets.Button(description='Get Positions', button_style='info')
    position_button.on_click(get_holdings)

    # --- layout ---
    overlay_ui = widgets.VBox([widgets.HBox([widgets.VBox([strat_overlay, dropdown_strategy_limit]),
                                              widgets.VBox([add_strategy_btn, clear_strategy_btn])]),
                                overlay_output])
    risk_strat_ui = widgets.VBox([widgets.HBox([widgets.VBox([risk_type, dropdown_risk_sign, risk_limit]),
                                                 widgets.VBox([add_risk_btn, clear_risk_btn])]),
                                   risk_constraints_output])

    allocation_ui = widgets.VBox([widgets.HBox([
        widgets.VBox([dropdown_asset, dropdown_sign, dropdown_limit]),
        widgets.VBox([add_constraint_btn, clear_constraints_btn, optimize_btn])]),
        constraint_output,
        grid, overlay_ui, risk_strat_ui,
        widgets.HBox([button_add, button_clear, results_button])])
    constraint_ui = widgets.VBox([widgets.HBox([start_date_perf, end_date_perf, refresh_perf_button]),
                                   main_output,
                                   widgets.VBox([strat, rebalancing_frequency, benchmark_tracking_error, window_vol]),
                                   allocation_ui, strategy_output,
                                   widgets.HBox([start_date_perf, end_date_perf, refresh_perf_button]),
                                   output_returns, widgets.HBox([perf_output, drawdown_output]), widgets.HBox([vol_output, frontier_output])
                                   ])
    universe_ui = widgets.VBox([
        widgets.HBox([n_crypto, start_date, data_button]),
        scope_output,
        widgets.HBox([start_date_perf, end_date_perf, refresh_perf_button]),
        main_output, price_output
    ])

    calendar_perf = widgets.VBox([widgets.HBox([frequency_graph, fund, benchmark, graph_button]), calendar_output])
    positions_ui = widgets.VBox([widgets.HBox([position_button, pnl_button]), positions_output, holding_output])
    rebalancing_frequency_pnl = widgets.Dropdown(description='Frequency:', options=['Yearly', 'Quarterly', 'Monthly'], value='Monthly')

    # =========================================================================
    # RISK ANALYSIS TAB -- ex-ante risk contribution
    # =========================================================================
    global var_scenarios, cvar_scenarios, fund_results, grid_stress, grid_mean_shock
    risk_output = widgets.Output()

    start_date_perf_risk = widgets.DatePicker(value=start_perf_date, layout=widgets.Layout(width='350px'))
    end_date_perf_risk = widgets.DatePicker(value=datetime.date.today(), layout=widgets.Layout(width='350px'))

    def update_fund_display(_):
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Invalid start or end date.")
            with risk_output:
                risk_output.clear_output()
            return

        if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Error with date range.")
            with risk_output:
                risk_output.clear_output()
                return

        if dataframe.empty or returns_to_use.empty or grid.data.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Please compute optimization results first.")
            with risk_output:
                risk_output.clear_output()
                return
        range_prices = dataframe.loc[start_ts:end_ts]

        if range_prices.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ No data available in selected date range.")
            with risk_output:
                risk_output.clear_output()
            return

        range_returns = range_prices.pct_change(fill_method=None).dropna()

        if grid.data.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ No Allocation.")
            with risk_output:
                risk_output.clear_output()
            return

        if selected_fund.value not in grid.data.index:
            with risk_output:
                risk_output.clear_output()
                print("⚠️ Select a fund from the allocation grid.")
            return
                
        if selected_bench.value not in grid.data.index:
            with risk_output:
                risk_output.clear_output()
                print("⚠️ Select a benchmark from the allocation grid.")
            return
            
        portfolio = RiskAnalysis(range_returns)
        selected_weights = grid.data.loc[selected_fund.value]
        bench_weights = grid.data.loc[selected_bench.value]
        
        decomposition = pd.DataFrame(portfolio.var_contrib(selected_weights)[0]) * 100
        te_decomposition = pd.DataFrame(portfolio.var_contrib(selected_weights-bench_weights)[0]) * 100
        bench_returns=portfolio.portfolio(bench_weights)
        
        beta_asset=compute_per_asset_betas(range_returns,bench_returns)
        beta_decomposition=(beta_asset*selected_weights).to_frame(name='Beta Contribution')
        
        quantities_rebalanced = rebalanced_portfolio(range_prices, selected_weights, frequency=rebalancing_frequency_pnl.value) / range_prices
        quantities_buy_hold = buy_and_hold(range_prices, selected_weights) / range_prices

        cost_rebalanced = rebalanced_book_cost(range_prices, quantities_rebalanced)
        cost_buy_and_hold = rebalanced_book_cost(range_prices, quantities_buy_hold)

        mtm_rebalanced = quantities_rebalanced * range_prices
        mtm_buy_and_hold = quantities_buy_hold * range_prices

        pnl_buy_and_hold = pd.DataFrame((mtm_buy_and_hold - cost_buy_and_hold).iloc[-1])
        pnl_buy_and_hold.columns = ['Profit and Loss (Buy and Hold)']

        pnl_rebalanced = pd.DataFrame((mtm_rebalanced - cost_rebalanced).iloc[-1])
        pnl_rebalanced.columns = ['Profit and Loss (Rebalanced)']

        profit_and_loss_simulated = pd.concat([pnl_buy_and_hold, pnl_rebalanced, decomposition], axis=1)
        profit_and_loss_simulated.loc['Total'] = profit_and_loss_simulated.sum(axis=0)
        profit_and_loss_simulated = profit_and_loss_simulated.fillna(0)

        bench_quantities_rebalanced = rebalanced_portfolio(range_prices, selected_weights-bench_weights, frequency=rebalancing_frequency_pnl.value) / range_prices
        bench_quantities_buy_hold = buy_and_hold(range_prices, selected_weights-bench_weights) / range_prices

        bench_cost_rebalanced = rebalanced_book_cost(range_prices, bench_quantities_rebalanced)
        bench_cost_buy_and_hold = rebalanced_book_cost(range_prices, bench_quantities_buy_hold)

        bench_mtm_rebalanced = bench_quantities_rebalanced * range_prices
        bench_mtm_buy_and_hold = bench_quantities_buy_hold * range_prices

        bench_pnl_buy_and_hold = pd.DataFrame((bench_mtm_buy_and_hold - bench_cost_buy_and_hold).iloc[-1])
        bench_pnl_buy_and_hold.columns = ['Profit and Loss (Buy and Hold)']

        bench_pnl_rebalanced = pd.DataFrame((bench_mtm_rebalanced - bench_cost_rebalanced).iloc[-1])
        bench_pnl_rebalanced.columns = ['Profit and Loss (Rebalanced)']

        bench_profit_and_loss_simulated = pd.concat([bench_pnl_buy_and_hold, bench_pnl_rebalanced, te_decomposition,beta_decomposition], axis=1)
        bench_profit_and_loss_simulated.loc['Total'] = bench_profit_and_loss_simulated.sum(axis=0)
        bench_profit_and_loss_simulated = bench_profit_and_loss_simulated.fillna(0)

        with risk_output:
            risk_output.clear_output(wait=True)
            display(Markdown("### Performance and Risk Contribution"))
            display(display_scrollable_df(
                profit_and_loss_simulated.sort_values(by='Vol Contribution', ascending=False)
            ))
            display(Markdown("### Excess P&L and TE Contribution"))
            display(display_scrollable_df(
                bench_profit_and_loss_simulated.sort_values(by='Vol Contribution', ascending=False)
            ))
    def on_fund_change(change):
        if change['name'] == 'value' and change['new'] in grid.data.index:
            update_fund_display(change['new'])

    selected_fund.observe(on_fund_change)

    def on_freq_change(change):
        if change['name'] == 'value' and change['new'] in rebalancing_frequency_pnl.options:
            update_fund_display(change['new'])

    rebalancing_frequency_pnl.observe(on_freq_change, names='value')

    # ---------- Ex-Ante Metrics ----------
    ex_ante_output = widgets.Output()

    def ex_ante_metrics(bench_name):
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Invalid start or end date.")
            with risk_output:
                risk_output.clear_output()
            return
        if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Error with date range.")
            with risk_output:
                risk_output.clear_output()
                return

        if dataframe.empty or returns_to_use.empty or grid.data.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Please compute optimization results first.")
            with ex_ante_output:
                ex_ante_output.clear_output()
                return

        if bench_name not in grid.data.index:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Select a benchmark from the allocation grid.")
                return

        range_prices = dataframe.loc[start_ts:end_ts]

        if range_prices.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ No data available in selected date range.")
            return

        range_returns = range_prices.pct_change(fill_method=None).dropna()

        if range_returns.empty:
            with ex_ante_output:
                ex_ante_output.clear_output()
                print("⚠️ Not enough data to compute returns.")
            return

        vol_ex_ante = {}
        tracking_error_ex_ante = {}
        beta_ex_ante = {}
        portfolio = RiskAnalysis(range_returns)

        # Benchmark's realized (price-level) series over this window, used
        # both for the per-asset betas below and for tracking-error vs. it.
        benchmark_price_series = portfolio.portfolio(grid.data.loc[bench_name])
        beta = compute_per_asset_betas(range_returns, benchmark_price_series)

        for idx in grid.data.index:
            vol_ex_ante[idx] = portfolio.variance(grid.data.loc[idx])
            tracking_error_ex_ante[idx] = portfolio.variance(grid.data.loc[idx] - grid.data.loc[bench_name])
            beta_ex_ante[idx] = np.dot(grid.data.loc[idx], beta)

        data = {
            'Vol Ex Ante': vol_ex_ante,
            'Tracking Error Ex Ante': tracking_error_ex_ante,
            'Beta Ex Ante': beta_ex_ante,
        }
        ex_ante_dataframe = pd.DataFrame(data)

        with ex_ante_output:
            ex_ante_output.clear_output(wait=True)
            display(Markdown("### Ex Ante Metrics"))
            display(display_scrollable_df(ex_ante_dataframe))

    def on_bench_change(change):
        if change['name'] == 'value' and change['new'] in grid.data.index:
            ex_ante_metrics(change['new'])
            update_fund_display(change['new'])

    def update_contrib_and_ex_ante(_):
        update_fund_display(None)
        ex_ante_metrics(selected_bench.value)

    ex_ante_metrics(selected_bench.value)
    selected_bench.observe(on_bench_change, names='value')
    end_date_perf_risk.observe(update_contrib_and_ex_ante)
    start_date_perf_risk.observe(update_contrib_and_ex_ante)

    # =========================================================================
    # RISK ANALYSIS TAB -- VaR / CVaR simulation
    # =========================================================================
    var_output = widgets.Output()
    var_scenarios, cvar_scenarios, fund_results = {}, {}, {}
    stress_factor = widgets.BoundedFloatText(value=1.0, min=1.0, max=3.0, step=0.1, description='Stress Factor:')
    mean_factor = widgets.BoundedFloatText(value=1.0, min=0.0, max=3.0, step=0.1, description='Mean Factor:')
    iterations = widgets.BoundedIntText(value=10000, min=1000, max=100000, step=1, description='Iterations:')
    num_scenarios = widgets.BoundedIntText(value=100, min=1, max=1000, step=1, description='Scenarios:')
    var_centile = widgets.BoundedFloatText(value=0.05, min=0, max=1, step=0.01, description='VaR Centile:')
    loading_bar_var = widgets.IntProgress(description='Loading scenarios...', min=0, max=100, style={'description_width': '150px'})

    grid_stress = DataGrid(pd.DataFrame(), editable=True, layout={"height": "250px"})
    grid_mean_shock = DataGrid(pd.DataFrame(), editable=True, layout={"height": "250px"})

    def update_stress_grid(change):
        global grid_stress
        grid_stress.unobserve(update_stress_grid)

        new_matrix = set_symmetric(grid_stress.data.to_numpy(), limit=2)
        new_dataframe = pd.DataFrame(new_matrix, columns=dataframe.columns, index=dataframe.columns)

        grid_stress.data = new_dataframe
        grid_stress.observe(update_stress_grid)
        grid_mean_shock.observe(update_stress_grid)
        update_stress_data(None)

    def update_stress_data(_):
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with var_output:
                var_output.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        range_prices = dataframe.loc[start_ts:end_ts]
        range_returns = range_prices.pct_change(fill_method=None)
        stress_vol_output = widgets.Output()
        stress_mean_output = widgets.Output()
        cov = range_returns.cov()

        stress_matrix = np.diag(np.diag(grid_stress.data))
        stressed_cov = stress_matrix @ cov @ stress_matrix
        stressed_std = np.sqrt(np.diag(stressed_cov))
        vol = stressed_std * np.sqrt(250)
        shocked_means = (range_returns.mean() * grid_mean_shock.data['Mean Shock']) * 250

        corr_matrix = stressed_cov / np.outer(stressed_std, stressed_std)
        corr_matrix = corr_matrix + np.tril(grid_stress.data) + np.tril(grid_stress.data).T
        corr_matrix = np.clip(corr_matrix, -1, 1)
        corr_matrix = cov_nearest(corr_matrix)

        corr_dataframe = pd.DataFrame(corr_matrix, index=range_returns.columns, columns=range_returns.columns)
        mean_shocked_dataframe = pd.concat([range_returns.mean() * 250, shocked_means], axis=1)
        mean_shocked_dataframe.columns = ['Means', 'Shocked Means']
        original_vol = range_returns.std() * np.sqrt(250)
        vol_dataframe = pd.DataFrame(index=range_returns.columns)

        vol_dataframe['Vol'] = original_vol
        vol_dataframe['Shocked Vol'] = vol
        original_corr = range_returns.corr()
        expected_data = pd.concat([mean_shocked_dataframe, vol_dataframe], axis=1)
        correlation_output_old = widgets.Output()
        correlation_output_new = widgets.Output()
        mean_output = widgets.Output()

        with stress_grid_output:
            stress_grid_output.clear_output(wait=True)
            with stress_vol_output:
                display(Markdown('## Correlation Shock'))
                display(grid_stress)
            with stress_mean_output:
                display(Markdown('## Returns Shock'))
                display(grid_mean_shock)
            with mean_output:
                display(Markdown('## Mean and Vol Changes'))
                display(display_scrollable_df(expected_data))
            with correlation_output_old:
                display(Markdown('### Original Correlation'))
                display(display_scrollable_df(original_corr))
            with correlation_output_new:
                display(Markdown('### New Correlation'))
                display(display_scrollable_df(corr_dataframe))
            ui_corr = widgets.HBox([correlation_output_old, correlation_output_new])
            ui_mean = widgets.VBox([stress_vol_output, stress_mean_output, mean_output])
            display(ui_mean)
            display(Markdown('## Correlation Changes'))
            display(ui_corr)

    def reset_stress(_):
        global grid_stress, grid_mean_shock
        if returns_to_use.empty:
            with stress_grid_output:
                print("⚠️ Load Prices")
            return
        stress_vec = np.linspace(stress_factor.value, stress_factor.value, returns_to_use.shape[1])
        stress_matrix = np.diag(stress_vec)
        stress_mean = np.linspace(mean_factor.value, mean_factor.value, returns_to_use.shape[1])
        grid_stress = DataGrid(
            pd.DataFrame(stress_matrix, columns=dataframe.columns, index=dataframe.columns),
            editable=True, layout={"height": "250px"}
        )
        grid_mean_shock = DataGrid(
            pd.DataFrame(stress_mean, columns=['Mean Shock'], index=dataframe.columns),
            editable=True, layout={"height": "250px"}
        )

        grid_stress.observe(update_stress_grid)
        grid_mean_shock.observe(update_stress_data)
        update_stress_data(None)

    stress_grid_output = widgets.Output()
    stress_grid_button = widgets.Button(description="Refresh")
    stress_grid_button.on_click(reset_stress)

    def get_var_metrics(_):
        global var_scenarios, cvar_scenarios, fund_results

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with var_output:
                var_output.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        with var_output:
            var_output.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return
            if returns_to_use.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return

            horizon = 1 / 250
            spot = dataframe.iloc[-1]
            theta = 2
            stress_matrix = grid_stress.data.to_numpy()
            mean_shock_vec = grid_mean_shock.data['Mean Shock']

            distrib_functions = {
                'multivariate_distribution': (iterations.value, stress_matrix, mean_shock_vec),
                'gaussian_copula': (iterations.value, stress_matrix, mean_shock_vec),
                't_copula': (iterations.value, stress_matrix, mean_shock_vec),
                'gumbel_copula': (iterations.value, theta, stress_factor.value, mean_shock_vec),
                'monte_carlo': (spot, horizon, iterations.value, stress_matrix, mean_shock_vec)
            }

            range_prices = dataframe.loc[start_ts:end_ts]
            range_returns = range_prices.pct_change(fill_method=None)

            portfolio = RiskAnalysis(range_returns)
            var_scenarios, cvar_scenarios, fund_results = {}, {}, {}
            display(loading_bar_var)

            def process_index(index):
                vs, cvs = {}, {}
                for func_name, args in distrib_functions.items():
                    func = getattr(portfolio, func_name)
                    scenarios = {}

                    for i in range(num_scenarios.value):
                        if func_name == 'monte_carlo':
                            distrib = pd.DataFrame(func(*args)[1], columns=portfolio.returns.columns)
                        else:
                            distrib = pd.DataFrame(func(*args), columns=portfolio.returns.columns)

                        distrib = distrib * grid.data.loc[index]
                        distrib = distrib[distrib.columns[grid.data.loc[index] > 0]]
                        distrib['Portfolio'] = distrib.sum(axis=1)

                        results = distrib.sort_values(by='Portfolio').iloc[int(distrib.shape[0] * var_centile.value)]
                        scenarios[i] = results

                    scenario = pd.DataFrame(scenarios).T
                    mean_scenario = scenario.mean()
                    index_cvar = scenario['Portfolio'] < mean_scenario['Portfolio']
                    cvar = scenario.loc[index_cvar].mean()

                    vs[func_name] = mean_scenario
                    cvs[func_name] = cvar

                fund_result = {
                    'Value At Risk': mean_scenario.loc['Portfolio'],
                    'CVaR': cvar.loc['Portfolio']
                }
                return index, vs, cvs, fund_result

            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(process_index, idx): idx for idx in grid.data.index}
                for future in as_completed(futures):
                    idx, vs, cvs, fund_result = future.result()
                    var_scenarios[idx] = vs
                    cvar_scenarios[idx] = cvs
                    fund_results[idx] = fund_result
                    loading_bar_var.value += 100 / len(grid.data.index)

            loading_bar_var.value = 0

        display_var_results(selected_fund_var.value)
        loading_bar_var.value = 0

    global result_var, result_cvar

    var_function_names = {'Multivariate': 'multivariate_distribution',
                           'Gaussian Copula': 'gaussian_copula',
                           'Monte Carlo': 'monte_carlo',
                           'Gumbel Copula': 'gumbel_copula',
                           'T-Copula': 't_copula'}

    result_var = pd.DataFrame()
    result_cvar = pd.DataFrame()

    value_at_risk_trajectory_output = widgets.Output()
    selected_fund_to_decompose_var = widgets.Dropdown(options=['Fund', 'Historical Portfolio'], value='Fund', description='Fund:')
    var_risk_trajectory_refresh_button = widgets.Button(description='Refresh')
    var_trajectory_button = widgets.Button(description='Get VaR', button_style='success')
    func_name = widgets.Dropdown(description='Method', options=list(var_function_names.keys()), value='Gumbel Copula')
    window_var = widgets.IntText(value=252, description='Window:', disabled=False)

    def value_at_risk_trajectory(_):
        global result_var, result_cvar, series_dict_var, current_underlying_returns

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with value_at_risk_trajectory_output:
                value_at_risk_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        with value_at_risk_trajectory_output:
            value_at_risk_trajectory_output.clear_output(wait=True)
            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return

            if len(returns_to_use.loc[start_ts:end_ts]) < window_risk.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            else:
                display(loading_bar)
                display(loading_bar_risk)

        # Single shared helper for Rebalanced/Buy and Hold/Fund/Core/Overlay/
        # Bitcoin weights -- see _build_weight_series_dict's docstring for why
        # both Rebalanced and Buy and Hold are anchored on the full dataframe.
        series_dict_var = _build_weight_series_dict(start_ts, end_ts)

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])
        weights_ex_post = weights_ex_post.drop(columns=['Total'], errors='ignore')
        weights_ex_post = weights_ex_post.fillna(0.0)

        tickers_combined = list(quantities.columns) + list(weights_ex_post.columns)
        tickers_combined = list(set(tickers_combined))

        current_underlying_prices = get_price_threading(tickers_combined, weights_ex_post.index[0].date())
        current_underlying_returns = current_underlying_prices.pct_change(fill_method=None)
        horizon = 1 / 250
        spot = dataframe.iloc[-1]
        theta = 2
        distrib_functions = {
            'multivariate_distribution': (iterations.value, stress_factor.value, mean_factor.value),
            'gaussian_copula': (iterations.value, stress_factor.value, mean_factor.value),
            't_copula': (iterations.value, stress_factor.value, mean_factor.value),
            'gumbel_copula': (iterations.value, theta, stress_factor.value, mean_factor.value),
            'monte_carlo': (spot, horizon, iterations.value, stress_factor.value, mean_factor.value)}

        method = var_function_names[func_name.value]
        args = distrib_functions[method]
        tasks = [(key, method, args, returns_to_use.loc[start_ts:end_ts], series_dict_var[key], window_var.value, var_centile.value) for key in series_dict_var]
        series_dict_var['Historical Portfolio'] = weights_ex_post.loc[start_ts:end_ts]

        if method in ['gumbel_copula']:
            tasks.append(
                (
                    'Historical Portfolio', method, args,
                    current_underlying_returns.loc[weights_ex_post.index].loc[start_ts:end_ts],
                    weights_ex_post.loc[start_ts:end_ts],
                    window_var.value, var_centile.value
                )
            )

        results_dict_var = {}
        results_dict_cvar = {}

        loading_bar_risk.value = 0
        loading_bar_risk.max = len(tasks)

        for name, func, arg, returns, weight, window, centile in tasks:
            common_col = returns.columns.intersection(weight.columns)
            common_index = returns.index.intersection(weight.index)

            var_data, cvar_data = get_var_contribution(func, arg, returns.loc[common_index, common_col], weight.loc[common_index, common_col], window, centile)
            results_dict_var[name] = var_data['Portfolio']
            results_dict_cvar[name] = cvar_data['Portfolio']
            loading_bar_risk.value += 1

        loading_bar_risk.value = loading_bar_risk.max

        with value_at_risk_trajectory_output:
            if not results_dict_var or not results_dict_cvar:
                print("⚠️ No risk results were computed.")
                return

            result_var = pd.concat(results_dict_var.values(), axis=1)
            result_cvar = pd.concat(results_dict_cvar.values(), axis=1)

            if result_var.shape[1] == 0 or result_cvar.shape[1] == 0:
                print("⚠️ Risk results are empty.")
                return
        result_var.columns = results_dict_var.keys()
        result_cvar.columns = results_dict_cvar.keys()
        # 'Fund' only exists as a column once `quantities` is non-empty (see
        # series_dict_var construction above). Preserves whatever was
        # already selected across a re-run of 'Get VaR' (e.g. after
        # widening the date range) instead of always snapping back to
        # 'Fund' -- see _set_dropdown_options.
        _set_dropdown_options(selected_fund_to_decompose_var, result_var.columns, fallback='Fund')

        show_var_graph(None)

    var_trajectory_button.on_click(value_at_risk_trajectory)

    def show_var_graph(_):
        global result_var, result_cvar

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with value_at_risk_trajectory_output:
                value_at_risk_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        output1 = widgets.Output()
        output2 = widgets.Output()

        with value_at_risk_trajectory_output:
            value_at_risk_trajectory_output.clear_output(wait=True)

            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty or global_returns.empty:
                print("⚠️ Please compute optimization results first.")
                return
            if result_var.empty or result_cvar.empty:
                print("⚠️ Load VaR History.")
                return

            if len(returns_to_use.loc[start_ts:end_ts]) < window_risk.value:
                print("⚠️ Date range is shorter than rolling window.")
                return

            if not series_dict_var:
                print("⚠️ Weights Empty.")
                return
            else:
                horizon = 1 / 250
                spot = dataframe.iloc[-1]
                theta = 2
                distrib_functions = {
                    'multivariate_distribution': (iterations.value, stress_factor.value, mean_factor.value),
                    'gaussian_copula': (iterations.value, stress_factor.value, mean_factor.value),
                    't_copula': (iterations.value, stress_factor.value, mean_factor.value),
                    'gumbel_copula': (iterations.value, theta, stress_factor.value, mean_factor.value),
                    'monte_carlo': (spot, horizon, iterations.value, stress_factor.value, mean_factor.value)}
                value_at_risk_trajectory_output.clear_output(wait=True)
                series_weights = series_dict_var[selected_fund_to_decompose_var.value]
                method = var_function_names[func_name.value]
                args = distrib_functions[method]
                if selected_fund_to_decompose_var.value != 'Historical Portfolio':
                    common = series_weights.columns.intersection(returns_to_use.columns)
                    common_index = series_weights.index.intersection(returns_to_use.index)
                    var, cvar = get_var_contribution(method, args, returns_to_use.loc[common_index, common].loc[start_ts:end_ts], series_weights.loc[common_index, common].loc[start_ts:end_ts], window_var.value, var_centile.value)
                else:
                    common = series_weights.columns.intersection(current_underlying_returns.columns)
                    common_index = series_weights.index.intersection(current_underlying_returns.index)
                    var, cvar = get_var_contribution(method, args, current_underlying_returns.loc[common_index].loc[start_ts:end_ts, common], series_weights.loc[common_index].loc[start_ts:end_ts, common], window_var.value, var_centile.value)

                with output1:
                    fig = px.line(result_var.loc[start_ts:end_ts], title='Portfolios Value At Risk', width=800, height=400, render_mode='svg')
                    fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Historical Portfolio", "Fund"])
                    fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig.show()
                    fig4 = px.line(var, title='Value at Risk History', width=800, height=400, render_mode='svg')
                    fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Portfolio"])
                    fig4.show()

                with output2:
                    fig2 = px.line(result_cvar, title='Portfolio Expected Shortfall', width=800, height=400, render_mode='svg')
                    fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Historical Portfolio", "Fund"])
                    fig2.show()

                    fig3 = px.line(cvar, title='Expected Shortfall History', width=800, height=400, render_mode='svg')
                    fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Portfolio"])
                    fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig3.show()

                ui = widgets.HBox([output1, output2])
                display(ui)

    var_risk_trajectory_refresh_button.on_click(show_var_graph)

    def display_var_results(fund_name):
        if fund_name not in var_scenarios:
            with var_output:
                var_output.clear_output(wait=True)
                print(f"⚠️ No VaR data found for '{fund_name}'. Run simulation first.")
            return
        columns = ['Multivariate', 'Gaussian Copula', 'T-Student Copula', 'Gumbel Copula', 'Monte Carlo']
        var_dataframe = pd.DataFrame(var_scenarios[fund_name])
        var_dataframe.columns = columns
        cvar_dataframe = pd.DataFrame(cvar_scenarios[fund_name])
        cvar_dataframe.columns = columns
        fund_results_dataframe = pd.DataFrame(fund_results).T
        with var_output:
            var_output.clear_output(wait=True)
            display(Markdown("### Summary"))
            display(display_scrollable_df(fund_results_dataframe))
            display(Markdown(f"### VaR Results for **{fund_name}**"))
            display(display_scrollable_df(var_dataframe))
            display(Markdown(f"### CVaR Results for **{fund_name}**"))
            display(display_scrollable_df(cvar_dataframe))

    def update_var_metrics(change):
        if change['name'] == 'value' and change['new'] in var_scenarios:
            display_var_results(change['new'])

    selected_fund_var.observe(update_var_metrics, names='value')
    get_var_button = widgets.Button(description='Run Simulation', button_style='info')
    get_var_button.on_click(get_var_metrics)

    # ---------- Layout ----------
    ex_ante_ui = widgets.VBox([widgets.HBox([start_date_perf_risk, end_date_perf_risk]),
                                widgets.VBox([selected_fund, selected_bench, rebalancing_frequency_pnl]),
                                risk_output,
                                ex_ante_output
                                ])
    var_ui = widgets.VBox([widgets.HBox([start_date_perf_risk, end_date_perf_risk]),
                            widgets.VBox([selected_fund_var, stress_factor, mean_factor, iterations, num_scenarios, var_centile, stress_grid_output, widgets.HBox([get_var_button, stress_grid_button])]),
                            var_output
                            ])
    var_history_ui = widgets.VBox([widgets.HBox([start_date_perf_risk, end_date_perf_risk, var_trajectory_button, var_risk_trajectory_refresh_button]),
                                    selected_fund_to_decompose_var, func_name, window_var, var_centile, value_at_risk_trajectory_output])

    # =========================================================================
    # MARKET RISK TAB -- PCA factor decomposition
    # =========================================================================
    global quantities_eigen, perf_index_eigen
    pca_output = widgets.Output()
    pca_components = widgets.Output()
    start_date_market_risk = widgets.DatePicker(value=start_perf_date, layout=widgets.Layout(width='350px'))
    end_date_market_risk = widgets.DatePicker(value=datetime.date.today(), layout=widgets.Layout(width='350px'))
    quantities_eigen = pd.DataFrame()
    perf_index_eigen = pd.DataFrame()

    def get_market_risk_metrics(_):
        try:
            start_ts = pd.to_datetime(start_date_market_risk.value)
            end_ts = pd.to_datetime(end_date_market_risk.value)
        except Exception:
            with pca_output:
                pca_output.clear_output()
            with pca_components:
                pca_components.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
            with pca_output:
                pca_output.clear_output()
            with pca_components:
                pca_components.clear_output()
                print("⚠️ Error with date range.")
            return
        if returns_to_use.empty:
            with pca_output:
                pca_output.clear_output()
            with pca_components:
                pca_components.clear_output()
                print('⚠️ Load Prices.')
            return

        market_tickers = [t for t in tickers if t in dataframe.columns]
        range_returns = returns_to_use.loc[start_ts:end_ts, market_tickers]
        portfolio = RiskAnalysis(range_returns)
        eigval, eigvec, portfolio_components = portfolio.pca(num_components=num_components.value)
        # Without capturing/restoring .value here, re-running 'Get Market
        # Risk Metrics' (e.g. after widening the date range, with the same
        # number of components) would silently reset whichever PC you'd
        # selected back to the first one -- see _set_dropdown_options.
        _set_dropdown_options(selected_components, portfolio_components.columns)
        num_components.max = len(range_returns.columns) + 1
        num_closest_to_pca.max = len(range_returns.columns)

        variance_explained = eigval / eigval.sum()
        variance_explained_dataframe = pd.DataFrame(variance_explained, index=portfolio_components.columns, columns=['Variance Explained'])

        pca_weight = dict((portfolio_components[selected_components.value] / (portfolio_components[selected_components.value]).sum()))
        pca_portfolio = pd.DataFrame(portfolio_components[selected_components.value]).sort_values(by=selected_components.value, ascending=False)

        historical_PCA = pd.DataFrame(np.array(list(pca_weight.values())).dot(np.transpose(portfolio.returns)), index=portfolio.returns.index, columns=['PCA'])
        historical_PCA = historical_PCA.dropna()
        historical_PCA.iloc[0] = 0

        comparison = portfolio.returns.copy()
        comparison['PCA'] = historical_PCA
        distances = np.sqrt(np.sum(comparison.apply(lambda y: (y - historical_PCA['PCA']) ** 2), axis=0)).sort_values()

        pca_similarity = comparison[distances.index[:num_closest_to_pca.value]]
        pca_similarity.iloc[0] = 0
        pca_similarity = (1 + pca_similarity).cumprod() * 100

        with pca_components:
            pca_components.clear_output(wait=True)
            fig = px.bar(variance_explained_dataframe, title='Variance Explanation in %')
            fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
            fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig2 = px.bar(pca_portfolio, title='Eigen Weights')
            fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
            fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig.show()
            fig2.show()

        with pca_output:
            pca_output.clear_output(wait=True)
            fig3 = px.line((1 + historical_PCA).cumprod() * 100, title='Eigen Index', render_mode='svg')
            fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
            fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig4 = px.line(pca_similarity, title='PCA Similarity', render_mode='svg')
            fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
            fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
            fig3.show()
            fig4.show()

    asset_output_corr = widgets.Output()
    button_corr = widgets.Button(description="Show Correlation", button_style="success")

    window_corr = widgets.IntText(value=252, description='Rolling Correlation:', disabled=False, style={'description_width': '150px'})

    def update_correlation(change=None):
        try:
            start_ts = pd.to_datetime(start_date_market_risk.value)
            end_ts = pd.to_datetime(end_date_market_risk.value)
        except Exception:
            with asset_output_corr:
                asset_output_corr.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        if returns_to_use.empty:
            with asset_output_corr:
                asset_output_corr.clear_output()
                print('⚠️Load Prices.')
                return

        if dropdown_asset1.value == dropdown_asset2.value:
            with asset_output_corr:
                asset_output_corr.clear_output()
                print('⚠️Same asset')
                return

        with asset_output_corr:
            asset_output_corr.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return

        range_returns = returns_to_use.loc[start_ts:end_ts]
        pca_over_time = first_pca_over_time(returns=range_returns, window=window_corr.value)
        rolling_corr_output = widgets.Output()
        correlation_matrix = widgets.Output()
        pca_overtime_output = widgets.Output()
        mean_returns_output = widgets.Output()

        with asset_output_corr:
            asset_output_corr.clear_output(wait=True)

            rolling_correlation = range_returns[dropdown_asset1.value].rolling(window_corr.value).corr(
                range_returns[dropdown_asset2.value]
            ).dropna()
            rolling_mean_returns = range_returns.rolling(window_corr.value).mean().dropna() * 252

            with rolling_corr_output:
                fig = px.line(rolling_correlation, title=f"{dropdown_asset1.value}/{dropdown_asset2.value} Correlation", render_mode='svg')
                fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig.show()
            with correlation_matrix:
                fig2 = px.imshow(range_returns.corr().round(2), title='Correlation Matrix', color_continuous_scale='Blues', text_auto=True, aspect="auto")
                fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig2.update_traces(xgap=2, ygap=2)
                fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig2.show()
            with pca_overtime_output:
                fig3 = px.line(pca_over_time, title='First principal component (Variance Explained in %)', render_mode='svg')
                fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig3.update_layout(xaxis_title=None, yaxis_title=None)
                fig3.show()
            with mean_returns_output:
                fig4 = px.line(rolling_mean_returns, title='Mean Return', render_mode='svg')
                fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig4.update_layout(xaxis_title=None, yaxis_title=None)
                fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in [dropdown_asset1.value, dropdown_asset2.value])
                fig4.show()

            ui = widgets.HBox([widgets.VBox([rolling_corr_output, mean_returns_output]), widgets.VBox([pca_overtime_output, correlation_matrix])])
            display(ui)

    selected_components = widgets.Dropdown(options=['PC1'], description='Select PCA:', style={'description_width': '150px'})
    num_components = widgets.BoundedIntText(min=1, max=5, value=5, description='PCA Components:', style={'description_width': '150px'})
    num_closest_to_pca = widgets.BoundedIntText(min=1, max=20, value=5, description='PCA Closest:', style={'description_width': '150px'})
    market_button = widgets.Button(description='Market Risk Analysis', button_style='info', style={'description_width': '150px'})
    market_button.on_click(get_market_risk_metrics)
    correlation_button = widgets.Button(description='Get Correlation', button_style='info', style={'description_width': '150px'})
    correlation_button.on_click(update_correlation)
    market_ui = widgets.VBox([widgets.HBox([start_date_market_risk, end_date_market_risk, market_button]),
                               num_components, selected_components, num_closest_to_pca,
                               widgets.HBox([pca_components, pca_output])])

    correlation_ui = widgets.VBox([widgets.HBox([start_date_market_risk, end_date_market_risk, correlation_button]), dropdown_asset1, dropdown_asset2, window_corr, asset_output_corr])

    frequency_eigen = widgets.Dropdown(description='Frequency:', options=['Yearly', 'Quarterly', 'Monthly'], value='Quarterly', style={'description_width': '150px'})
    selected_pca_market = widgets.Dropdown(description='PCA:', options=['PC1', 'PC2', 'PC3'], value='PC1', style={'description_width': '150px'})
    market_vol_window = widgets.IntText(value=252, description='Window:', disabled=False, style={'description_width': '150px'})

    market_factor_output = widgets.Output()
    market_factors_button = widgets.Button(description="Get Market Drivers", button_style="info", style={'description_width': '150px'})

    def show_market_graph(_):
        try:
            start_ts = pd.to_datetime(start_date_market_risk.value)
            end_ts = pd.to_datetime(end_date_market_risk.value)
        except Exception:
            with market_factor_output:
                market_factor_output.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        if returns_to_use.empty:
            with market_factor_output:
                asset_output_corr.clear_output()
                print('⚠️Load Prices.')
                return
        if quantities_eigen.empty:
            with market_factor_output:
                market_factor_output.clear_output()
                print('⚠️Load Factors.')
                return
        with market_factor_output:
            market_factor_output.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return

        range_prices = dataframe.loc[start_ts:end_ts]
        range_returns = returns_to_use.loc[start_ts:end_ts]

        market_portfolio = (quantities_eigen.loc[range_prices.index] * range_prices)
        market_index = market_portfolio.sum(axis=1).to_frame()
        market_index.columns = ['Market Index']
        market_cost = rebalanced_book_cost(range_prices, quantities_eigen.loc[range_prices.index])

        weights_series = market_portfolio.copy()
        weights_series = weights_series.apply(lambda x: x / market_portfolio.sum(axis=1))

        updated_perf_index_eigen = perf_index_eigen.copy()
        updated_perf_index_eigen = updated_perf_index_eigen.loc[start_ts:end_ts]
        updated_perf_index_eigen.iloc[0] = 0

        market_results = (1 + updated_perf_index_eigen).cumprod() * 100

        market_pnl = market_portfolio - rebalanced_book_cost(range_prices, quantities_eigen.loc[range_prices.index])
        market_pnl['Market Index'] = market_pnl.sum(axis=1)

        vol_contribution = get_ex_ante_vol_contribution(weights_series, range_returns, window=market_vol_window.value)
        correlation_contribution = get_correlation_contribution(weights_series, range_returns, window=market_vol_window.value)
        idiosyncratic_contribution = get_idiosyncratic_contribution(weights_series, range_returns, window=market_vol_window.value)

        output1 = widgets.Output()
        output2 = widgets.Output()

        with market_factor_output:
            market_factor_output.clear_output(wait=True)

            with output1:
                fig = px.line(market_results, title='Performance Comparison', width=800, height=400, render_mode='svg')
                fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Market Index", "Fund", "Bitcoin", "Historical Portfolio"])
                fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig.show()

                fig2 = px.line(market_pnl, title='Market Drivers', width=800, height=400, render_mode='svg')
                fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Market Index"])
                fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig2.show()

                fig3 = px.line(correlation_contribution, title='Market Correlation', width=800, height=400, render_mode='svg')
                fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Correlation"])
                fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig3.show()

            with output2:
                fig4 = px.line(vol_contribution, title='Market Volatility', width=800, height=400, render_mode='svg')
                fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Vol"])
                fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig4.show()

                fig5 = px.line(idiosyncratic_contribution, title='Market Intrinsic Volatility', width=800, height=400, render_mode='svg')
                fig5.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                fig5.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Idiosyncratic Vol"])
                fig5.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig5.show()

                fig6 = px.line(weights_series, title='Market Weights', width=800, height=400, render_mode='svg')
                fig6.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                fig6.update_traces(visible="legendonly", selector=lambda t: not t.name in ["BTCUSDT"])
                fig6.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig6.show()

            ui = widgets.HBox([output1, output2])
            display(ui)

    def get_market_factors(_):
        global quantities_eigen, perf_index_eigen
        try:
            start_ts = pd.to_datetime(start_date_market_risk.value)
            end_ts = pd.to_datetime(end_date_market_risk.value)
        except Exception:
            with market_factor_output:
                market_factor_output.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        if returns_to_use.empty:
            with market_factor_output:
                market_factor_output.clear_output()
                print('⚠️Load Prices.')
                return

        with market_factor_output:
            market_factor_output.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return

        results = {}
        range_prices = dataframe.loc[start_ts:end_ts]
        range_returns = returns_to_use.loc[start_ts:end_ts]

        dates = get_rebalancing_dates(range_returns, frequency=frequency_eigen.value)
        tasks = [(returns_to_use.loc[dates[i]:dates[i + 1]], dates[i], dates[i + 1]) for i in range(len(dates) - 1)]
        results = {}
        loading_bar_market = widgets.IntProgress(description='Loading Drivers...', min=0, max=len(tasks), style={'description_width': '150px'})
        loading_bar_market.value = 0

        with market_factor_output:
            display(loading_bar_market)

        def worker(subset, start, end):
            if subset.empty or len(subset) < 2:
                return None
            try:
                risk = RiskAnalysis(subset)
                eigval, eigvec, portfolio_components = risk.pca(num_components=5)
                weights = np.real(portfolio_components[selected_pca_market.value].to_numpy())
                return subset.index[-1], np.round(weights, 6)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
            futures = {executor.submit(worker, subset, start, end): (subset, start, end) for subset, start, end in tasks}
            for future in as_completed(futures):
                out = future.result()
                if out is not None:
                    date_key, weights = out
                    results[date_key] = weights
                    loading_bar_market.value += 1

        if not results:
            print("⚠️ No valid Eigen values computed.")
            return

        weights = pd.DataFrame(results).T
        quantities_eigen = rebalanced_dynamic_quantities(range_prices, weights)

        market_portfolio = (quantities_eigen * range_prices)
        market_index = market_portfolio.sum(axis=1).to_frame()
        market_index.columns = ['Market Index']
        perf_index_eigen = market_index.pct_change(fill_method=None)
        if not performance_ex_post.empty:
            perf_index_eigen = pd.concat([perf_index_eigen, performance_ex_post], axis=1)
        elif not global_returns.empty:
            perf_index_eigen = pd.concat([perf_index_eigen, global_returns], axis=1)

        show_market_graph(None)

    refresh_market_dates_button = widgets.Button(description='Refresh')
    market_factors_button.on_click(get_market_factors)
    refresh_market_dates_button.on_click(show_market_graph)

    market_factors_ui = widgets.VBox([widgets.HBox([start_date_market_risk, end_date_market_risk, market_factors_button, refresh_market_dates_button]),
                                       widgets.VBox([frequency_eigen, selected_pca_market, market_vol_window, market_factor_output])])

    # =========================================================================
    # CURRENT PORTFOLIO TAB -- ex-post (realized) P&L, reconciled vs. Git history
    # =========================================================================
    global daily_pnl, pnl_history, historical_ptf, performance_ex_post, positions, quantities_holding

    daily_pnl = pd.DataFrame()
    pnl_history = pd.DataFrame()
    historical_ptf = pd.DataFrame()
    performance_ex_post = pd.DataFrame()
    positions = pd.DataFrame()
    quantities_holding = pd.DataFrame()

    def check_connection(_):
        global quantities_holding, positions
        url_positions = 'https://github.com/niroojane/Risk-Management/raw/refs/heads/main/BinancePTF/Positions.xlsx'
        url_quantities = 'https://github.com/niroojane/Risk-Management/raw/refs/heads/main/BinancePTF/Quantities.xlsx'

        with ex_post_perf:
            ex_post_perf.clear_output(wait=True)

            position = read_excel_from_url(url_positions, index_col=0)
            if position is None:
                raise FileNotFoundError("Positions.xlsx could not be loaded. Execution stopped.")

            quantities_history = read_excel_from_url(url_quantities, index_col=0)
            if quantities_history is None:
                raise FileNotFoundError("Quantities.xlsx could not be loaded. Execution stopped.")

            positions, quantities_holding = Binance.get_positions_history(enddate=datetime.datetime.today())
            positions = positions.sort_index()
            positions.index = pd.to_datetime(positions.index)
            positions = pd.concat([position, positions])
            positions.index = pd.to_datetime(positions.index)
            positions = pd.concat([position, positions]).sort_index()
            positions = positions.loc[~positions.index.duplicated(keep='last'), :]
            positions['Total'] = positions.loc[:, positions.columns != 'Total'].sum(axis=1)

            quantities_holding.index = pd.to_datetime(quantities_holding.index)
            quantities_holding = pd.concat([quantities_holding, quantities_history])
            quantities_holding = quantities_holding.loc[~quantities_holding.index.duplicated(), :]

            quantities_holding = quantities_holding.sort_index()
            start_date_perf_ex_post.value = positions.index[0].date()

    start_date_perf_ex_post = widgets.DatePicker(value=datetime.date.today(), layout=widgets.Layout(width='350px'))
    end_date_perf_ex_post = widgets.DatePicker(value=datetime.date.today(), layout=widgets.Layout(width='350px'))
    ex_post_perf = widgets.Output()
    ex_post_calendar = widgets.Output()
    performance_output = widgets.Output()
    # Hard-loaded to the intended Historical Portfolio vs Fund pair from the
    # start -- fund_ex_post and benchmark_ex_post must NOT share the same
    # initial value here: they used to both start as 'Historical Portfolio',
    # which is always a valid option once data loads, so show_graph_ex_post's
    # "value not in options" guard never fired for benchmark_ex_post and it
    # silently stayed on 'Historical Portfolio' forever instead of ever
    # moving to 'Fund'. Distinct initial values sidestep that entirely.
    fund_ex_post = widgets.Dropdown(value='Historical Portfolio', options=['Historical Portfolio', 'Fund'], description='Select Fund:', style={'description_width': '150px'})
    benchmark_ex_post = widgets.Dropdown(value='Fund', options=['Historical Portfolio', 'Fund'], description='Select Benchmark:', style={'description_width': '150px'})
    frequency_graph_ex_post = widgets.Dropdown(options=['Year', 'Month'], value='Year', description='Select Frequency:', style={'description_width': '150px'})
    calendar_button_ex_post = widgets.Button(description='Update', button_style='info')

    def show_graph_ex_post(_):
        try:
            start_ts = pd.to_datetime(start_date_perf_ex_post.value)
            end_ts = pd.to_datetime(end_date_perf_ex_post.value)
        except Exception:
            with ex_post_calendar:
                ex_post_calendar.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        with ex_post_calendar:
            ex_post_calendar.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return
            if pnl_history.empty:
                print("⚠️ P&L not computed.")
                return
        cumulative_performance_ex_post = pd.DataFrame()

        ex_post_return_series = _build_ex_post_return_series(start_ts, end_ts)
        performance_ex_post = historical_ptf['Historical Portfolio'].copy().to_frame()
        if not ex_post_return_series.empty:
            performance_ex_post = pd.concat([performance_ex_post, ex_post_return_series], axis=1).sort_index()

        options = list(performance_ex_post.columns)

        # Capture BEFORE reassigning .options below, not after: ipywidgets'
        # Dropdown resets .value to options[0] the instant .options'
        # CONTENT changes at all -- not just on reorder, but even a pure
        # superset (old value still present, same position) triggers it.
        # Reading .value after the reassignment can't tell that happened,
        # because options[0] is itself "valid" -- the old "if value not in
        # options: reset" guard was therefore a no-op almost every time the
        # option list actually grew (e.g. a new strategy/fund added), which
        # is exactly why fund_ex_post and benchmark_ex_post kept ending up
        # on the same value. Restoring the captured value explicitly below
        # sidesteps ipywidgets' auto-reset entirely.
        old_fund_value = fund_ex_post.value
        old_bench_value = benchmark_ex_post.value

        fund_ex_post.options = options
        benchmark_ex_post.options = options

        # options[0] is always 'Historical Portfolio' (the base frame above,
        # always present) and options[1] is 'Fund' whenever quantities isn't
        # empty (Fund is the first key _build_weight_series_dict adds) --
        # that ordering is guaranteed by construction, so there's no need to
        # name-match 'Historical Portfolio'/'Fund' here: options[0]/[1] ARE
        # those values whenever they exist, and naturally fall through to
        # whatever's next in priority order (Core, Overlay, ...) otherwise.
        if old_fund_value in options:
            fund_ex_post.value = old_fund_value
        else:
            fund_ex_post.value = options[0]
        if old_bench_value in options:
            benchmark_ex_post.value = old_bench_value
        else:
            benchmark_ex_post.value = options[1] if len(options) > 1 else options[0]

        with ex_post_calendar:
            return_and_vol_graph = widgets.Output()
            sharpe_and_te_graph = widgets.Output()

            ex_post_calendar.clear_output()

            if performance_ex_post.empty:
                print("⚠️ Load Ex Post Performance.")
                return
            if fund_ex_post.value == benchmark_ex_post.value:
                print("⚠️ Benchmark and Fund must be different.")
                return
            if performance_ex_post.empty or performance_ex_post.shape[1] < 2:
                print("⚠️ No performance data available yet. Please run an optimization first.")
                return
            cumulative_performance_ex_post = performance_ex_post.loc[start_date_perf_ex_post.value:end_date_perf_ex_post.value].copy()
            cumulative_performance_ex_post.iloc[0] = 0
            cumulative_performance_ex_post = (1 + cumulative_performance_ex_post).cumprod() * 100
            graphs = get_calendar_graph(cumulative_performance_ex_post,
                                         freq=frequency_graph_ex_post.value,
                                         benchmark=benchmark_ex_post.value,
                                         fund=fund_ex_post.value)

            keys = list(graphs.keys())
            with return_and_vol_graph:
                graphs[keys[0]].show()
                graphs[keys[2]].show()
            with sharpe_and_te_graph:
                graphs[keys[1]].show()
                graphs[keys[3]].show()
            ui = widgets.HBox([return_and_vol_graph, sharpe_and_te_graph])
            display(ui)

            update_ex_post_chart(None)

    calendar_button_ex_post.on_click(show_graph_ex_post)

    def show_performance_chart(_):
        global performance_ex_post
        try:
            start_ts = pd.to_datetime(start_date_perf_ex_post.value)
            end_ts = pd.to_datetime(end_date_perf_ex_post.value)
        except Exception:
            with performance_output:
                performance_output.clear_output()
                print("⚠️ Invalid start or end date.")
            return
        with performance_output:
            performance_output.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return

        if historical_ptf.empty:
            with performance_output:
                print("⚠️ P&L not computed.")
                return

        ex_post_return_series = _build_ex_post_return_series(start_ts, end_ts)
        performance_ex_post = historical_ptf['Historical Portfolio'].copy().to_frame()
        if not ex_post_return_series.empty:
            performance_ex_post = pd.concat([performance_ex_post, ex_post_return_series], axis=1).sort_index()

        cumulative_performance_ex_post = performance_ex_post.loc[start_ts:end_ts].copy()
        cumulative_performance_ex_post.iloc[0] = 0
        cumulative_performance_ex_post = (1 + cumulative_performance_ex_post).cumprod() * 100

        if grid.data.empty or quantities.empty:
            weighted_returns_bench = historical_ptf.loc[start_ts:end_ts, historical_ptf.columns != 'Historical Portfolio']
        else:
            # Single shared helper (see _build_weight_series_dict's docstring):
            # both Rebalanced and Buy and Hold are anchored on the full
            # dataframe, and shift=1 shifts each series BEFORE slicing to the
            # display window, so the window's first day still gets a real
            # (not NaN) lagged weight instead of being orphaned. That lagged
            # weight is then multiplied against that day's asset return
            # (assets_returns.mul(returns_ptf, axis=0), below); not shifting
            # at all would apply each day's weight to its own same-day return,
            # which is the realized-P&L bug fixed in get_ex_post_returns above.
            series_dict_returns = _build_weight_series_dict(start_ts, end_ts, shift=1)

        if benchmark_ex_post.value == 'Historical Portfolio':
            weighted_returns_bench = historical_ptf.loc[start_ts:end_ts, historical_ptf.columns != 'Historical Portfolio']
        else:
            returns_bench = series_dict_returns[benchmark_ex_post.value].loc[start_ts:end_ts]
            assets_returns = returns_to_use.loc[start_ts:end_ts]
            weighted_returns_bench = assets_returns.mul(returns_bench, axis=0)
        if fund_ex_post.value == 'Historical Portfolio':
            weighted_returns_historical = historical_ptf.loc[start_ts:end_ts, historical_ptf.columns != 'Historical Portfolio']
            performance_contrib = performance_contribution(weighted_returns_historical)
            contribution_to_drawdown = drawdown_contribution(weighted_returns_historical)
        else:
            returns_ptf = series_dict_returns[fund_ex_post.value].loc[start_ts:end_ts]
            assets_returns = returns_to_use.loc[start_ts:end_ts]
            weighted_returns = assets_returns.mul(returns_ptf, axis=0)
            performance_contrib = performance_contribution(weighted_returns)
            contribution_to_drawdown = drawdown_contribution(weighted_returns)
        performance_contrib['Total Return'] = performance_contrib.sum(axis=1)

        performance_contrib_bench = performance_contribution(weighted_returns_bench)
        performance_contrib_bench['Total Return'] = performance_contrib_bench.sum(axis=1)
        excess_returns = performance_contrib.subtract(performance_contrib_bench, fill_value=0)
        perf_output_local = widgets.Output()
        perf_output_local2 = widgets.Output()
        with performance_output:
            performance_output.clear_output(wait=True)
            with perf_output_local:
                fig2 = px.line(performance_contrib, title='Return Contribution', render_mode='svg')
                fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Total Return'])
                fig2.update_layout(xaxis_title=None, yaxis_title=None)
                fig2.show()

                fig3 = px.line(performance_contrib_bench, title='Benchmark Return Contribution', render_mode='svg')
                fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Total Return'])
                fig3.update_layout(xaxis_title=None, yaxis_title=None)
                fig3.show()

            with perf_output_local2:
                drawdown = (cumulative_performance_ex_post[fund_ex_post.value] - cumulative_performance_ex_post[fund_ex_post.value].cummax()) / cumulative_performance_ex_post[fund_ex_post.value].cummax()
                drawdown = pd.concat([contribution_to_drawdown, drawdown], axis=1)

                fig6 = px.line(drawdown, title='Drawdown', render_mode='svg')
                fig6.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig6.update_traces(visible="legendonly", selector=lambda t: not t.name in [fund_ex_post.value])
                fig6.update_layout(xaxis_title=None, yaxis_title=None)
                fig6.show()

                fig7 = px.line(excess_returns, title='Active Return Contribution', render_mode='svg')
                fig7.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400, yaxis_tickformat=".2%")
                fig7.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Total Return'])
                fig7.update_layout(xaxis_title=None, yaxis_title=None)
                fig7.show()

            ui = widgets.HBox([perf_output_local, perf_output_local2])
            display(ui)

    def update_ex_post_chart(_):
        global performance_ex_post

        try:
            start_ts = pd.to_datetime(start_date_perf_ex_post.value)
            end_ts = pd.to_datetime(end_date_perf_ex_post.value)
        except Exception:
            with ex_post_perf:
                ex_post_perf.clear_output()
                print("⚠️ Invalid start or end date.")
            return

        with ex_post_perf:
            ex_post_perf.clear_output()
            if pd.isna(start_ts) or pd.isna(end_ts) or start_ts > end_ts:
                print("⚠️ Error with date range.")
                return
            if pnl_history.empty:
                print("⚠️ P&L not computed.")
                return

        selected_cumulative_pnl = daily_pnl.loc[start_ts:end_ts, 'Total'].copy()
        selected_cumulative_pnl.iloc[0] = 0

        selected_history = pd.concat([selected_cumulative_pnl.cumsum(), pnl_history['Total'].loc[start_ts:end_ts]], axis=1)
        selected_history.columns = ['Cumulative P&L', 'Total P&L']

        selected_daily_pnl = daily_pnl.loc[start_ts:end_ts].copy()
        selected_positions = positions.loc[start_ts:end_ts]

        ex_post_return_series = _build_ex_post_return_series(start_ts, end_ts)
        performance_ex_post = historical_ptf['Historical Portfolio'].copy().to_frame()
        if not ex_post_return_series.empty:
            performance_ex_post = pd.concat([performance_ex_post, ex_post_return_series], axis=1).sort_index()

        cumulative_performance_ex_post = performance_ex_post.loc[start_ts:end_ts].copy()
        cumulative_performance_ex_post.iloc[0] = 0
        cumulative_performance_ex_post = (1 + cumulative_performance_ex_post).cumprod() * 100
        pnl_contribution = (pnl_history - pnl_history.shift(1)).loc[start_ts:end_ts]

        cumulative_pnl_contrib = pnl_contribution.loc[:, pnl_contribution.columns != 'Total'].cumsum()
        cumulative_pnl_contrib = pd.concat([cumulative_pnl_contrib, selected_history], axis=1)
        git_output = widgets.Output()

        def git_push(_):
            with git_output:
                git_output.clear_output(wait=True)
                quantities_holding.to_excel('Quantities.xlsx', index=True)
                positions.to_excel('Positions.xlsx', index=True)
                if not trades.empty:
                    trades.to_excel('Trade History Reconstructed.xlsx', index=True)
                    git.push_or_update_file(trades, 'Trade History Reconstructed')
                git.push_or_update_file(positions, 'Positions')
                git.push_or_update_file(quantities_holding, 'Quantities')

        push_button = widgets.Button(description='Upload Files', button_style='success')
        push_button.on_click(git_push)
        expost_output = widgets.Output()
        expost_output1 = widgets.Output()
        with ex_post_perf:
            ex_post_perf.clear_output(wait=True)
            with expost_output:
                fig = px.line(selected_positions, title='Portfolio Value', render_mode='svg')
                fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Total'])
                fig.update_layout(xaxis_title=None, yaxis_title=None)
                fig.show()

                fig4 = px.line(cumulative_pnl_contrib, title='Cumulative P&L Contribution', render_mode='svg')
                fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Cumulative P&L'])
                fig4.update_layout(xaxis_title=None, yaxis_title=None)
                fig4.show()

            with expost_output1:
                fig5 = px.line(cumulative_performance_ex_post, title='Cumulative Return', render_mode='svg')
                fig5.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig5.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Historical Portfolio', 'Fund', 'Bitcoin'])
                fig5.update_layout(xaxis_title=None, yaxis_title=None)
                fig5.show()
                fig8 = px.bar(pnl_contribution, x=pnl_contribution.index, y=pnl_contribution.columns,
                              title="Daily P&L", barmode="relative")
                fig8.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", width=800, height=400)
                fig8.update_traces(visible="legendonly", selector=lambda t: t.name in ['Total'])
                fig8.update_layout(xaxis_title=None, yaxis_title=None, showlegend=True)
                fig8.show()

            ui = widgets.HBox([expost_output, expost_output1])
            display(ui)
            display(display_scrollable_df(pnl_contribution))
            display(push_button)
            display(git_output)

    def get_ex_post_returns(_):
        global daily_pnl, pnl_history, historical_ptf, performance_ex_post, weights_ex_post

        loading_bar.value = 0
        with ex_post_perf:
            ex_post_perf.clear_output()
            display(loading_bar_pnl)
            display(loading_bar)

        if book_cost.empty:
            get_pnl_on_click(None)
        quantities_tickers = list(quantities_holding.columns)
        daily_book_cost = book_cost.resample("D").last().dropna().sort_index()
        book_cost_history = pd.DataFrame()
        book_cost_history.index = set(daily_book_cost.index.append(quantities_holding.index))

        book_cost_history = book_cost_history.sort_index()
        cols = quantities_holding.columns[quantities_holding.columns != 'USDCUSDT']

        for col in cols:
            book_cost_history[col] = daily_book_cost[col]
        book_cost_history = book_cost_history.ffill()
        book_cost_history = book_cost_history.loc[quantities_holding.index]

        today = datetime.date.today()
        start_pnl = quantities_holding.index[0]
        days_total = (today - start_pnl.date()).days

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])

        start_date_local = weights_ex_post.index[0].date()
        binance_data = get_price_threading(quantities_tickers, start_date_local)
        binance_data = binance_data.sort_index()
        binance_data = binance_data.loc[~binance_data.index.duplicated(keep='last')]

        pnl_history = pd.DataFrame()
        pnl_history.index = quantities_holding.index
        pnl_history = pnl_history.sort_index()
        for col in cols:
            pnl_history[col] = quantities_holding[col] * (binance_data[col] - book_cost_history[col])
        pnl_history['Total'] = pnl_history.sum(axis=1)

        daily_pnl = pnl_history['Total'] - pnl_history['Total'].shift(1)
        daily_pnl = pd.DataFrame(daily_pnl)
        daily_pnl['color'] = daily_pnl['Total'].apply(lambda v: 'green' if v >= 0 else 'red')

        # Simple returns, not log returns -- (1+r).cumprod() below is only
        # valid for simple returns. Log returns understate large moves and
        # can even flip the compounding sign on a big single-day drop.
        binance_data_return = binance_data.pct_change(fill_method=None)
        weight_date = set(weights_ex_post.index)
        binance_date = set(binance_data_return.index)
        common_date = weight_date.intersection(binance_date)

        binance_data2 = binance_data_return.loc[list(common_date)].copy().sort_index()
        weights_ex_post2 = weights_ex_post.loc[list(common_date)].copy().sort_index()

        # weights_ex_post2[col] on date t is derived from that day's
        # post-move `positions`, i.e. it already reflects that day's price
        # change. Multiplying it by that same day's return double-counts
        # the move and dampens/distorts it. Lag the weight by one day so
        # each day's return is applied to the weight that was actually in
        # place going into that day.
        weights_ex_post_lagged = weights_ex_post2.shift(1)
        historical_ptf = pd.DataFrame()

        for col in binance_data:
            historical_ptf[col] = weights_ex_post_lagged[col] * binance_data2[col]

        historical_ptf['Historical Portfolio'] = historical_ptf.sum(axis=1)

        # Just the minimal frame here -- show_graph_ex_post (called below) rebuilds
        # performance_ex_post properly windowed to start_date_perf_ex_post /
        # end_date_perf_ex_post via _build_ex_post_return_series, and that's also
        # where fund_ex_post / benchmark_ex_post's options and defaults get set.
        performance_ex_post = historical_ptf['Historical Portfolio'].copy().to_frame()
        update_ex_post_chart(None)
        show_graph_ex_post(None)
        show_performance_chart(None)
        # 'Historical Portfolio' just became available (or newly refreshed) --
        # push it into the Risk Trajectory / Tracking Error / VaR trajectory
        # dropdowns too, so they don't wait for their own 'Get ...' button.
        refresh_trajectory_dropdowns()

    ex_post_button = widgets.Button(description='Get P&L', button_style='info')
    ex_post_button.on_click(get_ex_post_returns)

    refresh_ex_post_button = widgets.Button(description='Refresh')
    refresh_ex_post_button.on_click(update_ex_post_chart)

    refresh_performance_analysis_button = widgets.Button(description='Refresh')
    refresh_performance_analysis_button.on_click(show_performance_chart)

    ex_post_ui = widgets.VBox([widgets.HBox([start_date_perf_ex_post, end_date_perf_ex_post, ex_post_button, refresh_ex_post_button]), ex_post_perf])
    calendar_ui_ex_post = widgets.VBox([widgets.HBox([frequency_graph_ex_post, fund_ex_post, benchmark_ex_post, calendar_button_ex_post]), ex_post_calendar])
    performance_analysis_ui = widgets.VBox([widgets.HBox([start_date_perf_ex_post, end_date_perf_ex_post, ex_post_button, refresh_performance_analysis_button]), widgets.HBox([fund_ex_post, benchmark_ex_post]), performance_output])

    # series_dict_var / series_dict_risk: separate globals per tab. They used
    # to be one shared `series_dict` written by both value_at_risk_trajectory
    # (VaR tab) and get_risk_trajectory (Risk Trajectory tab) -- whichever
    # tab's 'Get ...' button was clicked last silently overwrote the other
    # tab's data, so show_risk_graph / show_var_graph could end up reading
    # weights from the wrong tab's last run (different date range, possibly
    # different funds) while still showing a dropdown selection that looked
    # valid. get_tracking_error_trajectory never shared this global to begin
    # with (it assigns a same-named local without declaring it `global`,
    # which is its own separate variable) -- renamed to series_dict_te below
    # purely for clarity, no behavior change there.
    global results_vol, series_dict_var, series_dict_risk, current_underlying_returns, results_tracking_error
    global te_series_dict_cache
    results_vol = pd.DataFrame()
    results_tracking_error = pd.DataFrame()
    current_underlying_returns = pd.DataFrame()
    # Cache of the raw, benchmark-independent per-fund weight series from the
    # last 'Get Ex Ante TE' run ('Historical Portfolio', 'Fund', 'Core',
    # every 'Rebalanced X'/'Buy and Hold X', 'Bitcoin', ...). 'Refresh'
    # (show_tracking_error_graph / _decompose_spread) reads straight out of
    # this to build the spread for whichever fund/benchmark pair is
    # currently selected, without paying for get_price_threading (network
    # fetch) or _build_weight_series_dict (rebuilds every Rebalanced/Buy and
    # Hold series) again -- those only happen here, in the full compute.
    te_series_dict_cache = {}
    series_dict_var = {}
    series_dict_risk = {}

    risk_trajectory_output = widgets.Output()
    tracking_error_trajectory_output = widgets.Output()
    selected_fund_to_decompose = widgets.Dropdown(options=['Fund', 'Historical Portfolio'], value='Historical Portfolio', description='Fund:')
    # Separate widget from selected_fund_to_decompose above: the two tabs
    # populate their 'Fund' dropdown from different column sets
    # (results_vol.columns vs. results_tracking_error.columns, which excludes
    # whichever fund is picked as the TE benchmark). They used to share one
    # widget, which meant running 'Get Ex Ante Vol' in one tab and 'Get Ex
    # Ante TE' in the other kept overwriting the same dropdown's options/value
    # out from under whichever tab you were actually looking at.
    selected_fund_to_decompose_te = widgets.Dropdown(options=['Fund', 'Historical Portfolio'], value='Historical Portfolio', description='Fund:')
    selected_bench_risk = widgets.Dropdown(options=['Fund', 'Historical Portfolio'], value='Fund', description='Bench:')

    window_risk = widgets.IntText(value=252, description='Window:', disabled=False)
    window_te = widgets.IntText(value=252, description='Window:', disabled=False)

    loading_bar_risk = widgets.IntProgress(description='Loading Vol...', min=0, max=100, style={'description_width': '150px'})
    loading_bar_tracking_error = widgets.IntProgress(description='Loading TE...', min=0, max=100, style={'description_width': '150px'})

    risk_trajectory_button = widgets.Button(description="Get Ex Ante Vol", button_style="success")
    tracking_error_trajectory_button = widgets.Button(description="Get Ex Ante TE", button_style="success")
    risk_trajectory_refresh_button = widgets.Button(description="Refresh")
    tracking_error_refresh_button = widgets.Button(description="Refresh")

    def _build_weight_series_dict(start_ts, end_ts, shift=0):
        """Single source of truth for every tab's 'Rebalanced X' / 'Buy and Hold
        X' / 'Fund' / 'Core' / 'Overlay' / 'Bitcoin' weight history -- used by
        value_at_risk_trajectory, show_performance_chart,
        _build_ex_post_return_series, get_risk_trajectory and
        get_tracking_error_trajectory, instead of each of them re-deriving the
        same computation with whatever price series they happened to have on
        hand (that's exactly how 'Buy and Hold' ended up meaning two different
        things in two different charts).

        Both `rebalanced_portfolio` AND `buy_and_hold` are anchored on the FULL
        `dataframe`, not the display window. `buy_and_hold` never resets, so it
        has to be one continuous simulation across the whole backtest for
        start_ts/end_ts to just crop the view rather than restart the
        simulation from target weights every time the window changes.
        `rebalanced_portfolio` is anchored the same way here for consistency --
        it resets to target weights on its own fixed calendar regardless of
        what price series it's given, so nothing about its own trajectory
        changes, but every consumer of this dict now gets weights built
        identically, which is what keeps the same name meaning the same thing
        everywhere it's shown.

        `shift`: shift each series (via .shift()) BEFORE slicing to
        [start_ts:end_ts], so the window's first day still gets a real
        (not NaN) lagged weight from the day before the window starts,
        instead of being orphaned by shifting an already-sliced frame. Pass
        shift=1 when the caller is about to multiply these weights against
        returns (yesterday's weight earns today's return); leave the default
        0 when the caller wants the weights themselves (e.g. VaR).
        """
        # Insertion order here is the display order everywhere this dict ends
        # up as chart columns / dropdown options: Fund, Core, Overlay first
        # (the headline series people actually compare against), then each
        # grid row's Rebalanced/Buy and Hold pair, with Bitcoin last.
        series = {}
        if not quantities.empty:
            portfolio = quantities * dataframe
            series['Fund'] = portfolio.apply(lambda x: x / portfolio.sum(axis=1)).shift(shift).loc[start_ts:end_ts]
        if not quantities_core.empty:
            portfolio = quantities_core * dataframe
            series['Core'] = portfolio.apply(lambda x: x / portfolio.sum(axis=1)).shift(shift).loc[start_ts:end_ts]
        if not quantities_overlay.empty:
            portfolio = quantities_overlay * dataframe
            series['Overlay'] = portfolio.apply(lambda x: x / portfolio.sum(axis=1)).shift(shift).loc[start_ts:end_ts]

        for key in grid.data.index:
            # Same frequency argument as everywhere else in the P&L Analysis tab
            # (VaR trajectory, etc.) -- leaving it unset defaults to
            # rebalanced_portfolio's own 'Quarterly', silently ignoring
            # rebalancing_frequency_pnl.
            rebalanced_series = rebalanced_portfolio(dataframe, grid.data.loc[key], frequency=rebalancing_frequency_pnl.value)
            rebalanced_series_weights = rebalanced_series.apply(lambda x: x / rebalanced_series.sum(axis=1))
            buy_and_hold_series = buy_and_hold(dataframe, grid.data.loc[key])
            buy_and_hold_series_weights = buy_and_hold_series.apply(lambda x: x / buy_and_hold_series.sum(axis=1))
            series['Rebalanced ' + key] = rebalanced_series_weights.shift(shift).loc[start_ts:end_ts]
            series['Buy and Hold ' + key] = buy_and_hold_series_weights.shift(shift).loc[start_ts:end_ts]

        # Bitcoin buy-and-hold, single-asset so the choice of anchor doesn't
        # change its trajectory -- but it's built the same way for the same
        # reason as everything else above: one place, one convention.
        bitcoin_allocation = pd.DataFrame([{col: 1 if col == 'BTCUSDT' else 0 for col in dataframe.columns}])
        bitcoin_series = buy_and_hold(dataframe, bitcoin_allocation.iloc[0])
        bitcoin_series_weights = bitcoin_series.apply(lambda x: x / bitcoin_series.sum(axis=1))
        series['Bitcoin'] = bitcoin_series_weights.shift(shift).loc[start_ts:end_ts]
        return series

    def _fund_universe_keys():
        """The same key set _build_weight_series_dict would return, without
        paying for the actual rebalanced_portfolio/buy_and_hold computation --
        just to populate dropdown option lists cheaply. Ordered so the most
        commonly picked funds/benchmarks (Historical Portfolio, Fund, Core,
        Overlay -- whichever are actually available) come first, ahead of the
        per-strategy Rebalanced/Buy and Hold rows and Bitcoin."""
        priority = []
        if not historical_ptf.empty:
            priority.append('Historical Portfolio')
        if not quantities.empty:
            priority.append('Fund')
        if not quantities_core.empty:
            priority.append('Core')
        if not quantities_overlay.empty:
            priority.append('Overlay')

        rest = []
        for name in grid.data.index:
            rest += ['Rebalanced ' + name, 'Buy and Hold ' + name]
        rest.append('Bitcoin')

        return priority + rest

    # Remembers, per dropdown, the option list refresh_trajectory_dropdowns
    # last applied -- so it can tell "this dropdown's preferred default just
    # became available for the first time" apart from "it's been available
    # all along and the value is just whatever it is". Keyed by id(widget)
    # since ipywidgets Dropdown objects aren't hashable in a useful way.
    _trajectory_dropdown_prev_options = {}

    def refresh_trajectory_dropdowns():
        """One canonical fund list, applied to every 'Fund'/'Benchmark' picker
        in the Risk Trajectory / Tracking Error / VaR trajectory tabs, so all
        of them show the same available parameters as soon as either 'Get
        Results' (grid.data) or 'Get P&L' (Historical Portfolio) makes a new
        one available -- instead of only after that tab's own 'Get Ex Ante
        Vol' / 'Get Ex Ante TE' / 'Get VaR' button has been clicked at least
        once. Preserves each dropdown's current selection when it's still
        valid, same guard as everywhere else -- EXCEPT right when a
        dropdown's own preferred default (e.g. 'Historical Portfolio' for
        the fund pickers) newly becomes available: if 'Get Result' runs
        before 'Get P&L', 'Historical Portfolio' isn't in `options` yet, so
        selected_fund_to_decompose_te falls back to options[0] (typically
        'Fund') -- landing on the exact same value as selected_bench_risk's
        own default. Once 'Get P&L' then makes 'Historical Portfolio'
        available, 'Fund' is still a perfectly valid value, so the plain
        guard would never move it back -- it'd stay stuck matching the
        benchmark picker forever. Snapping to the preferred default the one
        time it newly appears fixes that without ever overriding a pick made
        after that default was already on offer."""
        if grid.data.empty:
            return
        options = _fund_universe_keys()
        if not options:
            return
        # The benchmark picker gets its own ordering: Fund moved to the front
        # (when available), ahead of Historical Portfolio -- a benchmark
        # defaults to Fund more often than to your own realized history.
        bench_options = options[:]
        if 'Fund' in bench_options:
            bench_options.remove('Fund')
            bench_options.insert(0, 'Fund')
        for dd, default, opts in ((selected_fund_to_decompose, 'Historical Portfolio', options),
                                  (selected_fund_to_decompose_te, 'Historical Portfolio', options),
                                  (selected_bench_risk, 'Fund', bench_options),
                                  (selected_fund_to_decompose_var, 'Fund', options)):
            prev_opts = _trajectory_dropdown_prev_options.get(id(dd))
            default_newly_available = (default in opts) and (prev_opts is not None) and (default not in prev_opts)
            # Capture .value BEFORE reassigning .options -- see
            # _set_dropdown_options. Read directly (rather than calling
            # that helper) because the "newly available default" case
            # needs to override even a still-valid old value.
            old_value = dd.value
            dd.options = opts
            if default_newly_available:
                dd.value = default
            elif old_value in opts:
                dd.value = old_value
            else:
                dd.value = default if default in opts else opts[0]
            _trajectory_dropdown_prev_options[id(dd)] = list(opts)

    def _build_ex_post_return_series(start_ts, end_ts):
        """Realized daily-return series for 'Rebalanced X' / 'Buy and Hold X' /
        'Fund' / 'Core' / 'Overlay' / 'Bitcoin' over [start_ts, end_ts].

        This is the single source of truth for the P&L Analysis tab's non-
        'Historical Portfolio' series: it reuses _build_weight_series_dict
        (the exact same weights show_performance_chart uses for Return
        Contribution), lagged by one day and multiplied against
        returns_to_use, rather than `global_returns` -- which is a
        *different* simulation, tied to the Optimization tab's own date
        range (start_date_perf/end_date_perf) and its own
        rebalancing_frequency widget. Building both charts from this one
        function is what makes Cumulative Return match Return Contribution
        by construction, instead of requiring the two tabs' date pickers
        (and frequency dropdowns) to be kept in sync by hand.
        """
        if returns_to_use.empty or dataframe.empty:
            return pd.DataFrame()

        assets_returns = returns_to_use.loc[start_ts:end_ts]
        return_series = {}

        if not grid.data.empty:
            # shift=1: yesterday's weight (from the day before the window
            # starts, not NaN) earns today's return -- _build_weight_series_dict
            # already includes 'Bitcoin' alongside Rebalanced/Buy and
            # Hold/Fund/Core/Overlay, all anchored the same way.
            series_dict_local = _build_weight_series_dict(start_ts, end_ts, shift=1)
            for key, weights_series in series_dict_local.items():
                return_series[key] = assets_returns.mul(weights_series, axis=0).sum(axis=1)

        return pd.DataFrame(return_series)

    def show_risk_graph(_):
        global results_vol

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with risk_trajectory_output:
                risk_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return
        output1 = widgets.Output()
        output2 = widgets.Output()

        with risk_trajectory_output:
            risk_trajectory_output.clear_output(wait=True)

            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return
            if results_vol.empty:
                print("⚠️ Load Ex Ante Vol.")
                return

            if len(returns_to_use.loc[start_ts:end_ts]) < window_risk.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            if not series_dict_risk:
                print("⚠️ Weights Empty.")
                return
            else:
                risk_trajectory_output.clear_output(wait=True)

                series_weights = series_dict_risk[selected_fund_to_decompose.value]
                if selected_fund_to_decompose.value != 'Historical Portfolio':
                    contribution_to_vol = get_ex_ante_vol_contribution(series_weights.loc[start_ts:end_ts], returns_to_use.loc[start_ts:end_ts], window_risk.value)
                    correlation_contrib = get_correlation_contribution(series_weights.loc[start_ts:end_ts], returns_to_use.loc[start_ts:end_ts], window_risk.value)
                    idiosyncratic_contrib = get_idiosyncratic_contribution(series_weights.loc[start_ts:end_ts], returns_to_use.loc[start_ts:end_ts], window_risk.value)
                else:
                    contribution_to_vol = get_ex_ante_vol_contribution(series_weights.loc[start_ts:end_ts], current_underlying_returns.loc[series_weights.index].loc[start_ts:end_ts], window_risk.value)
                    correlation_contrib = get_correlation_contribution(series_weights.loc[start_ts:end_ts], current_underlying_returns.loc[series_weights.index].loc[start_ts:end_ts], window_risk.value)
                    idiosyncratic_contrib = get_idiosyncratic_contribution(series_weights.loc[start_ts:end_ts], current_underlying_returns.loc[series_weights.index].loc[start_ts:end_ts], window_risk.value)

                with output1:
                    fig = px.line(results_vol.loc[start_ts:end_ts], title='Ex Ante Volatility', width=800, height=400, render_mode='svg')
                    fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Historical Portfolio", "Fund"])
                    fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig.show()
                    fig4 = px.line(idiosyncratic_contrib, title='Idiosyncratic Contribution', width=800, height=400, render_mode='svg')
                    fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Idiosyncratic Vol"])
                    fig4.show()

                with output2:
                    fig2 = px.line(contribution_to_vol, title='Volatility Contribution', width=800, height=400, render_mode='svg')
                    fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ['Total Vol'])
                    fig2.show()

                    fig3 = px.line(correlation_contrib, title='Correlation Contribution', width=800, height=400, render_mode='svg')
                    fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Correlation"])
                    fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig3.show()
                ui = widgets.HBox([output1, output2])
                display(ui)

    def get_risk_trajectory(_):
        global results_vol, series_dict_risk, current_underlying_returns
        results_vol = pd.DataFrame()

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with risk_trajectory_output:
                risk_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        with risk_trajectory_output:
            risk_trajectory_output.clear_output(wait=True)
            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return

            if len(returns_to_use.loc[start_ts:end_ts]) < window_risk.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            else:
                display(loading_bar)
                display(loading_bar_risk)
        series_dict_risk = _build_weight_series_dict(start_ts, end_ts)

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])
        weights_ex_post = weights_ex_post.drop(columns=['Total'], errors='ignore')
        weights_ex_post = weights_ex_post.fillna(0.0)

        tickers_combined = list(quantities.columns) + list(weights_ex_post.columns)
        tickers_combined = list(set(tickers_combined))

        current_underlying_prices = get_price_threading(tickers_combined, weights_ex_post.index[0].date())
        current_underlying_returns = current_underlying_prices.pct_change(fill_method=None)
        # Historical Portfolio first (its own returns source, current_underlying_
        # returns, differs from every other row's returns_to_use), then Fund/
        # Core/Overlay/Rebalanced/Buy and Hold/Bitcoin in series_dict_risk's own
        # order -- so results_vol's columns read Historical Portfolio, Fund,
        # Core, Overlay, ..., matching every other tab's ordering.
        series_dict_risk = {'Historical Portfolio': weights_ex_post.loc[start_ts:end_ts], **series_dict_risk}
        tasks = [('Historical Portfolio', weights_ex_post.loc[start_ts:end_ts],
                  current_underlying_returns.loc[weights_ex_post.index].loc[start_ts:end_ts], window_risk.value)]
        tasks += [(key, series_dict_risk[key], returns_to_use.loc[start_ts:end_ts], window_risk.value)
                  for key in series_dict_risk if key != 'Historical Portfolio']
        loading_bar_risk.value = 0
        loading_bar_risk.max = len(tasks)

        results_dict = {}
        for name, weight, returns, window in tasks:
            results_dict[name] = get_ex_ante_vol(weight, returns, window)
            loading_bar_risk.value += 1

        loading_bar_risk.value = loading_bar_risk.max

        with risk_trajectory_output:
            if not results_dict:
                print("⚠️ No risk results were computed.")
                return

            results_vol = pd.concat(results_dict.values(), axis=1)
            if results_vol.shape[1] == 0:
                print("⚠️ Risk results are empty.")
                return
        results_vol.columns = results_dict.keys()
        # 'Historical Portfolio' isn't guaranteed to be a column here.
        # Preserves whatever was already selected across a re-run of
        # 'Get Ex Ante Vol' -- see _set_dropdown_options.
        _set_dropdown_options(selected_fund_to_decompose, results_vol.columns, fallback='Historical Portfolio')

        show_risk_graph(None)

    show_risk_graph(None)

    def _decompose_spread(fund_key, bench_key, start_ts, end_ts):
        """Fresh, on-demand spread (fund weights - benchmark weights) between
        exactly the two entries of te_series_dict_cache currently picked in
        the Fund/Bench dropdowns, and the 3 decomposition charts built from
        it. This is ALL 'Refresh' recomputes -- it never touches the
        expensive multi-fund vol loop, so it doesn't matter whether it's the
        fund-to-decompose or the benchmark that changed, either is just a
        different pair of keys into the same cache. The top 'Ex Ante
        Tracking Error' chart (results_tracking_error) is deliberately NOT
        recomputed here: it shows every fund's TE at once, which is
        expensive (one rolling-vol pass per fund) and only needs to reflect
        whichever benchmark 'Get Ex Ante TE' was last run against, not
        whatever pair you're currently decomposing below it."""
        fund_series = te_series_dict_cache[fund_key]
        bench_series = te_series_dict_cache[bench_key]

        all_cols = sorted(set(fund_series.columns) | set(bench_series.columns))
        fund_series = fund_series.reindex(columns=all_cols, fill_value=0)
        bench_series = bench_series.reindex(columns=all_cols, fill_value=0)

        # 'Historical Portfolio' is built from real position snapshots
        # (weights_ex_post), which can land on a different calendar than
        # every other key -- those are all built off the same continuous
        # `dataframe` and so already share one index with each other, but
        # not necessarily with the real portfolio's actual reporting dates.
        # Subtracting two frames on mismatched indexes takes the UNION of
        # both calendars, and fillna(0) would then quietly manufacture a
        # spread on every day one side never actually reported -- e.g. fund
        # - 0 on a day the benchmark has no real value, which isn't a
        # spread at all, it's just the fund's own weight (and its vol from
        # there on is the fund's own vol, not a tracking error). Restrict to
        # the dates BOTH sides actually have instead of filling either one.
        if fund_series.index.equals(bench_series.index):
            common_index = fund_series.index
        else:
            common_index = fund_series.index.intersection(bench_series.index)
        fund_series = fund_series.loc[common_index]
        bench_series = bench_series.loc[common_index]

        # Both sides now share an index and a column set, so this fillna(0)
        # only mops up genuine within-cell NaNs (e.g. a price gap), not an
        # index mismatch -- that's already been excluded above.
        series_weights = (fund_series - bench_series).fillna(0).loc[start_ts:end_ts]

        # 'Historical Portfolio' columns come from weights_ex_post (the
        # real portfolio's own holdings), while every other key's columns
        # come from `quantities` (the strategy universe, same tickers as
        # returns_to_use) -- two ticker sets that aren't identical.
        # current_underlying_returns is the one built over their UNION
        # (tickers_combined), so it's the only side guaranteed to cover
        # series_weights' columns whenever EITHER key is 'Historical
        # Portfolio' -- checking fund_key alone missed the case where only
        # the benchmark was 'Historical Portfolio', leaving series_weights
        # with Historical's columns but returns_to_use not covering them.
        if 'Historical Portfolio' in (fund_key, bench_key):
            returns_for_decomp = current_underlying_returns.loc[series_weights.index].loc[start_ts:end_ts]
        else:
            returns_for_decomp = returns_to_use.loc[series_weights.index].loc[start_ts:end_ts]

        contribution_to_vol = get_ex_ante_vol_contribution(series_weights, returns_for_decomp, window_te.value)
        correlation_contrib = get_correlation_contribution(series_weights, returns_for_decomp, window_te.value)
        idiosyncratic_contrib = get_idiosyncratic_contribution(series_weights, returns_for_decomp, window_te.value)
        return contribution_to_vol, correlation_contrib, idiosyncratic_contrib

    def show_tracking_error_graph(_):
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with tracking_error_trajectory_output:
                tracking_error_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return
        output1 = widgets.Output()
        output2 = widgets.Output()

        with tracking_error_trajectory_output:
            tracking_error_trajectory_output.clear_output(wait=True)

            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return
            if results_tracking_error.empty:
                print("⚠️ Load Ex Ante TE.")
                return
            fund_key = selected_fund_to_decompose_te.value
            bench_key = selected_bench_risk.value
            if not te_series_dict_cache or fund_key not in te_series_dict_cache or bench_key not in te_series_dict_cache:
                print("⚠️ Weights Empty.")
                return
            if len(returns_to_use.loc[start_ts:end_ts]) < window_te.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            else:
                tracking_error_trajectory_output.clear_output(wait=True)

                # This is the only recompute 'Refresh' does -- fresh every
                # time, for whatever fund/benchmark pair is selected right
                # now, regardless of which one last changed.
                contribution_to_vol, correlation_contrib, idiosyncratic_contrib = _decompose_spread(fund_key, bench_key, start_ts, end_ts)

                with output1:
                    fig = px.line(results_tracking_error.loc[start_ts:end_ts], title='Ex Ante Tracking Error', width=800, height=400, render_mode='svg')
                    fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Historical Portfolio", "Fund"])
                    fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig.show()
                    fig4 = px.line(idiosyncratic_contrib, title='Idiosyncratic Contribution', width=800, height=400, render_mode='svg')
                    fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Idiosyncratic Vol"])
                    fig4.show()

                with output2:
                    fig2 = px.line(contribution_to_vol, title='Tracking Error Contribution', width=800, height=400, render_mode='svg')
                    fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig2.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Vol"])
                    fig2.show()

                    fig3 = px.line(correlation_contrib, title='Correlation Contribution', width=800, height=400, render_mode='svg')
                    fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white", yaxis_tickformat=".2%")
                    fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Correlation"])
                    fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
                    fig3.show()
                ui = widgets.HBox([output1, output2])
                display(ui)

    def get_tracking_error_trajectory(_):
        """'Get Ex Ante TE' button: the ONE place that pays for
        get_price_threading (network) and _build_weight_series_dict
        (rebuilds every Rebalanced/Buy and Hold series), and the only place
        that recomputes the top 'Ex Ante Tracking Error' chart (a
        get_ex_ante_vol pass over every fund vs whichever benchmark is
        selected right now). 'Refresh' (show_tracking_error_graph) never
        redoes any of this -- it only recomputes the 3 decomposition charts,
        on demand, from the series_dict_te this caches below."""
        global results_tracking_error, current_underlying_returns, te_series_dict_cache
        results_tracking_error = pd.DataFrame()

        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with tracking_error_trajectory_output:
                risk_trajectory_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        with tracking_error_trajectory_output:
            tracking_error_trajectory_output.clear_output(wait=True)
            if dataframe.empty:
                print('⚠️Load Prices.')
                return
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return

            if len(returns_to_use.loc[start_ts:end_ts]) < window_te.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            else:
                display(loading_bar)
                display(loading_bar_risk)
        # Local on purpose (no `global` declaration) -- this tab has never
        # shared its weights with VaR/Risk Trajectory's series_dict_var /
        # series_dict_risk, but is named series_dict_te to make that
        # explicit rather than relying on an implicit local shadow.
        series_dict_te = _build_weight_series_dict(start_ts, end_ts)

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])
        weights_ex_post = weights_ex_post.drop(columns=['Total'], errors='ignore')
        weights_ex_post = weights_ex_post.fillna(0.0)

        tickers_combined = list(quantities.columns) + list(weights_ex_post.columns)
        tickers_combined = list(set(tickers_combined))

        current_underlying_prices = get_price_threading(tickers_combined, weights_ex_post.index[0].date())
        current_underlying_returns = current_underlying_prices.pct_change(fill_method=None)
        # Historical Portfolio first, then Fund/Core/Overlay/Rebalanced/Buy and
        # Hold/Bitcoin in series_dict_te's own order -- matching the same
        # column order as the Risk Trajectory and VaR trajectory tabs.
        series_dict_te = {'Historical Portfolio': weights_ex_post.loc[start_ts:end_ts], **series_dict_te}
        bench = selected_bench_risk.value

        # Cache the raw, benchmark-independent per-fund weight series so
        # show_tracking_error_graph's Refresh can spread any two of them
        # on demand (_decompose_spread) without coming back through here.
        te_series_dict_cache = series_dict_te

        selected_weights = series_dict_te[bench]
        not_in_bench = list(set(weights_ex_post.columns) - set(selected_weights.columns))
        not_in_fund = list(set(selected_weights.columns) - set(weights_ex_post.columns))

        selected_weights = selected_weights.copy()
        weights_ex_post = weights_ex_post.copy()

        weights_ex_post[not_in_fund] = 0
        selected_weights[not_in_bench] = 0
        spread_weights = {}
        for key in series_dict_te:
            spread_weights[key] = (series_dict_te[key] - selected_weights).fillna(0)

        spread_ex_post = (weights_ex_post - selected_weights).loc[weights_ex_post.index].loc[start_ts:end_ts].fillna(0)
        spread_weights['Historical Portfolio'] = spread_ex_post

        tasks = [('Historical Portfolio', spread_ex_post, current_underlying_returns.loc[spread_ex_post.index].loc[start_ts:end_ts], window_te.value)]
        tasks += [(key, spread_weights[key].loc[start_ts:end_ts], returns_to_use.loc[spread_weights[key].loc[start_ts:end_ts].index], window_te.value)
                  for key in series_dict_te if key != 'Historical Portfolio']
        loading_bar_risk.value = 0
        loading_bar_risk.max = len(tasks)

        results_dict = {}
        for name, weight, returns, window in tasks:
            results_dict[name] = get_ex_ante_vol(weight, returns, window)
            loading_bar_risk.value += 1

        loading_bar_risk.value = loading_bar_risk.max

        with tracking_error_trajectory_output:
            tracking_error_trajectory_output.clear_output(wait=True)
            if not results_dict:
                print("⚠️ No risk results were computed.")
                return

            results_tracking_error = pd.concat(results_dict.values(), axis=1)
            if results_tracking_error.shape[1] == 0:
                print("⚠️ Risk results are empty.")
                return

        results_tracking_error.columns = results_dict.keys()

        # Capture .value BEFORE reassigning .options below -- ipywidgets'
        # Dropdown tracks selection by POSITION, not by label: if the new
        # options list has the same names in a different order (which can
        # happen here since it comes from a dict, not a fixed schema), it
        # silently snaps .value back to options[0] the moment .options is
        # set, before this function ever gets to check it. Reading .value
        # afterwards can't tell that happened, because options[0] is itself
        # a "valid" option -- the guard below never fires, and the reset
        # looks like it "just happens" on every run. Grabbing the old value
        # first and restoring it explicitly sidesteps that entirely.
        old_fund_value = selected_fund_to_decompose_te.value
        old_bench_value = selected_bench_risk.value

        selected_bench_risk.options = results_tracking_error.columns
        selected_fund_to_decompose_te.options = results_tracking_error.columns

        if old_fund_value in results_tracking_error.columns:
            selected_fund_to_decompose_te.value = old_fund_value
        else:
            selected_fund_to_decompose_te.value = ('Historical Portfolio' if 'Historical Portfolio' in results_tracking_error.columns
                                                    else results_tracking_error.columns[0])
        # Same guard as elsewhere: 'Fund' only exists once `quantities` is
        # non-empty, unlike 'Historical Portfolio' which is always present.
        if old_bench_value in results_tracking_error.columns:
            selected_bench_risk.value = old_bench_value
        else:
            selected_bench_risk.value = 'Fund' if 'Fund' in results_tracking_error.columns else results_tracking_error.columns[0]

        show_tracking_error_graph(None)

    show_tracking_error_graph(None)

    risk_trajectory_button.on_click(get_risk_trajectory)
    risk_trajectory_refresh_button.on_click(show_risk_graph)
    risk_exposure_ui = widgets.VBox([widgets.HBox([start_date_perf_risk, end_date_perf_risk, risk_trajectory_button, risk_trajectory_refresh_button]),
                                      selected_fund_to_decompose, window_risk, risk_trajectory_output])
    tracking_error_trajectory_button.on_click(get_tracking_error_trajectory)
    tracking_error_refresh_button.on_click(show_tracking_error_graph)
    tracking_error_exposure_ui = widgets.VBox([widgets.HBox([start_date_perf_risk, end_date_perf_risk, tracking_error_trajectory_button, tracking_error_refresh_button]),
                                                selected_fund_to_decompose_te, selected_bench_risk, window_te, tracking_error_trajectory_output])

    check_connection(None)

    # =========================================================================
    # RISK ANALYSIS TAB -- rolling beta vs. a chosen benchmark
    # =========================================================================
    beta_output = widgets.Output()
    window_beta = widgets.IntText(value=252, description='Window:',style={'description_width': '150px'})
    get_beta_button = widgets.Button(description='Get Beta', button_style='info')
    refresh_beta_button = widgets.Button(description='Refresh')

    # Holds everything fetched/built by get_beta_trajectory so that
    # show_beta_graph can redraw on a window-size change without refetching
    # prices or rebuilding weight series each time.
    beta_state = {}

    def get_beta_trajectory(_):
        """Fetch price history + build weight series for the beta charts.

        This is the expensive step (network calls via get_price_threading);
        it only needs to re-run when the date range / fund / benchmark
        selection changes, not when the rolling window changes.
        """
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with beta_output:
                beta_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        with beta_output:
            beta_output.clear_output(wait=True)
            if dataframe.empty or returns_to_use.empty or grid.data.empty:
                print("⚠️ Please compute optimization results first.")
                return
            if historical_ptf.empty:
                print("⚠️ P&L not computed.")
                return
            if len(returns_to_use.loc[start_ts:end_ts]) < window_beta.value:
                print("⚠️ Date range is shorter than rolling window.")
                return
            display(loading_bar)

        ex_post_return_series = _build_ex_post_return_series(start_ts, end_ts)
        performance_ex_post_local = historical_ptf['Historical Portfolio'].copy().to_frame()
        if not ex_post_return_series.empty:
            performance_ex_post_local = pd.concat(
                [performance_ex_post_local, ex_post_return_series], axis=1
            ).sort_index()

        # NOTE: the Beta tab was relocated to reuse the P&L Analysis dropdowns
        # (fund_ex_post / benchmark_ex_post) rather than its own
        # selected_fund_to_decompose / selected_fund_to_decompose_te /
        # selected_bench_risk widgets, which belong one-to-one to the Risk
        # Trajectory and Tracking Error sub-tabs respectively (each tab has
        # its own 'Fund' dropdown -- see selected_fund_to_decompose_te above).
        # Guard checks and lookups here must both reference fund_ex_post /
        # benchmark_ex_post -- checking one dropdown's value and then
        # indexing with another's is how the earlier mismatch bug crept in.
        if benchmark_ex_post.value not in performance_ex_post_local.columns:
            with beta_output:
                beta_output.clear_output(wait=True)
                print(f"⚠️ Benchmark '{benchmark_ex_post.value}' not found in performance data.")
            return

        series_dict_local = _build_weight_series_dict(start_ts, end_ts)

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])
        weights_ex_post = weights_ex_post.drop(columns=['Total'], errors='ignore')
        weights_ex_post = weights_ex_post.fillna(0.0)
        series_dict_local['Historical Portfolio'] = weights_ex_post.loc[start_ts:end_ts]

        if fund_ex_post.value not in series_dict_local:
            with beta_output:
                beta_output.clear_output(wait=True)
                print(f"⚠️ '{fund_ex_post.value}' has no weight series available.")
            return

        selected_weights = series_dict_local[fund_ex_post.value]

        tickers_combined = list(quantities.columns) + list(weights_ex_post.columns)
        tickers_combined = list(set(tickers_combined))
        current_underlying_prices = get_price_threading(tickers_combined, weights_ex_post.index[0].date())
        current_underlying_returns_local = current_underlying_prices.pct_change(fill_method=None)

        beta_state['current_underlying_returns'] = current_underlying_returns_local
        beta_state['performance_ex_post'] = performance_ex_post_local
        beta_state['selected_weights'] = selected_weights
        beta_state['bench_col'] = benchmark_ex_post.value
        beta_state['start_ts'] = start_ts
        beta_state['end_ts'] = end_ts

        show_beta_graph(None)

    def show_beta_graph(_):
        """Redraw the beta charts from cached `beta_state` using the current
        `window_beta` value. Cheap -- no network calls -- so this is safe to
        wire up to the window widget directly as well as a Refresh button.
        """
        try:
            start_ts = pd.to_datetime(start_date_perf_risk.value)
            end_ts = pd.to_datetime(end_date_perf_risk.value)
        except Exception:
            with beta_output:
                beta_output.clear_output(wait=True)
                print("⚠️ Invalid start or end date.")
            return

        if not beta_state:
            with beta_output:
                beta_output.clear_output(wait=True)
                print("⚠️ Click 'Get Beta' first.")
            return

        current_underlying_returns_local = beta_state['current_underlying_returns']
        performance_ex_post_local = beta_state['performance_ex_post']
        series_dict_local = _build_weight_series_dict(start_ts, end_ts)

        weights_ex_post = positions.copy()
        weights_ex_post = weights_ex_post.drop(columns=['USDTUSDT'], errors='ignore')
        weights_ex_post = weights_ex_post.apply(lambda x: x / weights_ex_post['Total'])
        weights_ex_post = weights_ex_post.drop(columns=['Total'], errors='ignore')
        weights_ex_post = weights_ex_post.fillna(0.0)

        series_dict_local['Historical Portfolio'] = weights_ex_post.loc[start_ts:end_ts]

        if fund_ex_post.value not in series_dict_local:
            with beta_output:
                beta_output.clear_output(wait=True)
                print(f"⚠️ '{fund_ex_post.value}' has no weight series available.")
            return

        selected_weights = series_dict_local[fund_ex_post.value]

        bench_col = benchmark_ex_post.value
        start_ts = start_ts
        end_ts = end_ts

        if bench_col not in performance_ex_post_local.columns:
            with beta_output:
                beta_output.clear_output(wait=True)
                print(f"⚠️ Benchmark '{bench_col}' no longer available -- click 'Get Beta' again.")
            return

        with beta_output:
            beta_output.clear_output(wait=True)

            # 1) Rolling beta of each underlying asset vs. the chosen benchmark
            beta_rolling = compute_rolling_per_asset_betas(
                returns_window=current_underlying_returns_local,
                benchmark_return_series=performance_ex_post_local[bench_col],
                window=window_beta.value,
            )

            # 2) Weight the per-asset betas by the selected fund's weights ->
            #    a single portfolio-level rolling beta series. Align on both
            #    index and columns first since weights/betas won't necessarily
            #    share identical tickers or dates.
            common_cols = beta_rolling.columns.intersection(selected_weights.columns)
            weights_aligned = selected_weights.reindex(index=beta_rolling.index, columns=common_cols).fillna(0.0)
            betas_aligned = beta_rolling.reindex(columns=common_cols)

            weighted_beta_contrib = betas_aligned * weights_aligned
            
            weighted_beta_contrib['Total Beta'] = weighted_beta_contrib.sum(axis=1, min_count=1).to_frame(name='Portfolio Beta')

            # 3) Rolling beta of each fund-level series (Historical Portfolio,
            #    Fund, Core, Overlay, Bitcoin, ...) vs. the same benchmark.
            perf_ex_post_beta = compute_rolling_per_asset_betas(
                returns_window=performance_ex_post_local,
                benchmark_return_series=performance_ex_post_local[bench_col],
                window=window_beta.value,
            )

            output1 = widgets.Output()
            output2 = widgets.Output()

            with output1:
                fig = px.line(beta_rolling.loc[start_ts:end_ts], title='Rolling Asset Beta', width=800, height=400, render_mode='svg')
                fig.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig.update_traces(visible="legendonly", selector=lambda t: not t.name in ["BTCUSDT"])
                fig.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig.show()

                fig2 = px.line(weights_aligned.loc[start_ts:end_ts], title='Historical Weights', width=800, height=400, render_mode='svg')
                fig2.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white",yaxis_tickformat=".2%")
                fig2.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig2.show()

            with output2:
                fig3 = px.line(perf_ex_post_beta.loc[start_ts:end_ts], title=f'Portfolio Rolling Beta vs {bench_col}', width=800, height=400, render_mode='svg')
                fig3.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig3.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Historical Portfolio", "Fund"])
                fig3.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig3.show()
                
                fig4 = px.line(weighted_beta_contrib.loc[start_ts:end_ts], title='Beta Contribution', width=800, height=400, render_mode='svg')
                fig4.update_layout(plot_bgcolor="black", paper_bgcolor="black", font_color="white")
                fig4.update_traces(visible="legendonly", selector=lambda t: not t.name in ["Total Beta"])
                fig4.update_traces(textfont=dict(family="Arial Narrow", size=15))
                fig4.show()

            ui = widgets.HBox([output1, output2])
            display(ui)

    get_beta_button.on_click(get_beta_trajectory)
    refresh_beta_button.on_click(show_beta_graph)
    # Changing just the window redraws immediately from cached data -- no
    # need to click Refresh for a pure window-size change.
    window_beta.observe(lambda ch: show_beta_graph(None) if ch['name'] == 'value' and beta_state else None, names='value')

    beta_ui = widgets.VBox([
        widgets.HBox([start_date_perf_risk, end_date_perf_risk, get_beta_button, refresh_beta_button]),
        fund_ex_post, benchmark_ex_post, window_beta, beta_output
    ])

    # =========================================================================
    # TAB ASSEMBLY
    # =========================================================================
    investment_universe_tab = widgets.Output()
    strategy_tab = widgets.Output()
    positioning_tab = widgets.Output()
    ex_post_tab = widgets.Output()
    risk_analysis_tab = widgets.Output()
    market_risk_tab = widgets.Output()

    main_tabs = widgets.Tab(children=[
        investment_universe_tab,
        strategy_tab,
        ex_post_tab,
        risk_analysis_tab,
        market_risk_tab
    ])

    main_tabs.set_title(0, 'Investment Universe')
    main_tabs.set_title(1, 'Strategy')
    main_tabs.set_title(2, 'Current Portfolio')
    main_tabs.set_title(3, 'Risk Analysis')
    main_tabs.set_title(4, 'Market Risk')

    with investment_universe_tab:
        display(universe_ui)
    strategy_constraints_tab = widgets.Output()
    strategy_positions_tab = widgets.Output()
    strategy_returns_tab = widgets.Output()

    strategy_subtabs = widgets.Tab(children=[
        strategy_constraints_tab,
        strategy_positions_tab,
        strategy_returns_tab
    ])

    strategy_subtabs.set_title(0, 'Strategy')
    strategy_subtabs.set_title(1, 'Positioning')
    strategy_subtabs.set_title(2, 'Strategy Return')

    with strategy_tab:
        display(strategy_subtabs)

    with strategy_constraints_tab:
        display(constraint_ui)

    with strategy_positions_tab:
        display(positions_ui)

    with strategy_returns_tab:
        display(calendar_perf)
    performance_subtab = widgets.Output()
    pnl_analysis_tab = widgets.Output()
    beta_tab = widgets.Output()

    pnl_sub_tab = widgets.Tab(children=[pnl_analysis_tab, performance_subtab,beta_tab])
    positions_subtab = widgets.Output()
    calendar_ex_post_subtab = widgets.Output()

    ex_post_subtabs = widgets.Tab(children=[
        pnl_sub_tab,
        positions_subtab,
        calendar_ex_post_subtab
    ])
    pnl_sub_tab.set_title(0, 'P&L Analysis')
    pnl_sub_tab.set_title(1, 'Return Analysis')
    pnl_sub_tab.set_title(2, 'Beta Analysis')

    ex_post_subtabs.set_title(0, 'P&L')
    ex_post_subtabs.set_title(1, 'Positioning')
    ex_post_subtabs.set_title(2, 'Calendar Return')

    with ex_post_tab:
        display(ex_post_subtabs)

    with pnl_analysis_tab:
        display(ex_post_ui)

    with performance_subtab:
        display(performance_analysis_ui)
    with positions_subtab:
        display(positions_ui)
    with calendar_ex_post_subtab:
        display(calendar_ui_ex_post)
    with beta_tab:
        display(beta_ui)
        
    risk_contribution_tab = widgets.Output()
    var_tab = widgets.Output()
    var_history_tab = widgets.Output()

    risk_exposure = widgets.Output()
    tracking_error_exposure = widgets.Output()

    risk_subtabs = widgets.Tab(children=[
        risk_contribution_tab,
        risk_exposure,
        tracking_error_exposure])

    var_subtabs = widgets.Tab(children=[var_tab, var_history_tab])
    var_subtabs.set_title(0, 'Value at Risk')
    var_subtabs.set_title(1, 'Value at Risk History')
    risk_subtabs.set_title(0, 'Risk Contribution')
    risk_subtabs.set_title(1, 'Risk Trajectory')
    risk_subtabs.set_title(2, 'Tracking Error')
    with risk_analysis_tab:
        risk_tabs = widgets.Tab(children=[risk_subtabs, var_subtabs])
        risk_tabs.set_title(0, 'Volatility Analysis')
        risk_tabs.set_title(1, 'Value at Risk')
        display(risk_tabs)

    with risk_contribution_tab:
        display(ex_ante_ui)

    with var_tab:
        display(var_ui)

    with var_history_tab:
        display(var_history_ui)

    with risk_exposure:
        display(risk_exposure_ui)
    with tracking_error_exposure:
        display(tracking_error_exposure_ui)



    market_risk_detail_tab = widgets.Output()
    correlation_tab = widgets.Output()
    market_factors_tab = widgets.Output()

    market_risk_subtabs = widgets.Tab(children=[
        market_risk_detail_tab,
        correlation_tab,
        market_factors_tab])

    market_risk_subtabs.set_title(0, 'Market Risk')
    market_risk_subtabs.set_title(1, 'Correlation')
    market_risk_subtabs.set_title(2, 'Market Drivers')
    with market_risk_tab:
        display(market_risk_subtabs)

    with market_risk_detail_tab:
        display(market_ui)

    with correlation_tab:
        display(correlation_ui)

    with market_factors_tab:
        display(market_factors_ui)

    display(main_tabs)