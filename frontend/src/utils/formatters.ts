export const formatUSD = (value: number): string => {
  return `$${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

export const formatLargeNumber = (value: number): string => {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 0,
  });
};

export const formatMarketCap = (value: number): string => {
  return `$${(value / 1e9).toFixed(2)}B`;
};

export const formatPercentage = (value: number, decimals: number = 2): string => {
  return `${value.toFixed(decimals)}%`;
};
