export const isNumericColumn = (columnId: string): boolean => {
  const numericColumns = [
    'price',
    'supply',
    'market_cap',
    'quantity',
    'value',
    'weight',
    'open',
    'high',
    'low',
    'close',
    'volume',
  ];
  return numericColumns.includes(columnId);
};

export const getAriaSortValue = (
  isSorted: false | 'asc' | 'desc'
): 'ascending' | 'descending' | 'none' => {
  if (isSorted === 'asc') return 'ascending';
  if (isSorted === 'desc') return 'descending';
  return 'none';
};
