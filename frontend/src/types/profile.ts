/** Market served by the backend: start-binance.bat (crypto) or start-yahoo.bat (multi_asset) */
export type MarketName = 'crypto' | 'multi_asset';

export interface CurrencySettings {
  base_currency: string;
  convert_to_base: boolean;
  positions_currency: string;
  choices: string[];
}

export interface Profile {
  name: MarketName;
  label: string;
  price_source: string;
  /** Ticker of the benchmark series, and its name in the workspace ('Bitcoin', 'Benchmark') */
  benchmark_ticker: string;
  benchmark_label: string;
  /** Cash / stablecoin assets: never in the universe, nor in the current weights */
  cash_assets: string[];
  excluded_symbols: string[];
  /** Get Prices adds the held assets to the universe (crypto) */
  include_holdings_in_universe: boolean;
  data_folder: string;
  /** {asset class: tickers} of a new Yahoo universe */
  default_universe: Record<string, string[]>;
  asset_classes: string[];
  /** The HMM Regime App's scenarios are strategies too ('regime:<scenario>') */
  regime_strategies: boolean;
  currency: CurrencySettings;
}

/** A Yahoo ticker of the multi-asset universe */
export interface UniverseTicker {
  ticker: string;
  assetClass: string;
}

export interface TickerCheck {
  ticker: string;
  type: string | null;
  asset_class: string;
  name: string | null;
}
