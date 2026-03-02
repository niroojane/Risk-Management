export const getAriaSortValue = (
  isSorted: false | 'asc' | 'desc'
): 'ascending' | 'descending' | 'none' => {
  if (isSorted === 'asc') return 'ascending';
  if (isSorted === 'desc') return 'descending';
  return 'none';
};
