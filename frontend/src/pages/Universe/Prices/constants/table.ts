export const ITEMS_PER_PAGE = 20;

// Prices columns are dynamic (symbols), so we declare the non-numeric ones
export const NON_NUMERIC_PRICES_COLUMN_IDS = ['date'];

export const NUMERIC_RETURNS_COLUMN_IDS = ['total_return', 'ytd_return', 'annualized_return'];

export const NUMERIC_RISK_COLUMN_IDS = [
  'annualized_vol_daily',
  'annualized_vol_3y_weekly',
  'annualized_vol_5y_monthly',
  'annualized_vol_since_inception_monthly',
  'inception_year',
  'cvar_parametric_95',
  'max_drawdown',
];
