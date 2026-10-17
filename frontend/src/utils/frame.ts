import type { Cell, Frame } from '@/types/workspace';

export const emptyFrame: Frame = { index: [], columns: [], data: [] };

export const isEmptyFrame = (frame?: Frame | null): boolean =>
  !frame || frame.index.length === 0 || frame.columns.length === 0;

/** Values of one column, in index order */
export const frameColumn = (frame: Frame, column: string): Cell[] => {
  const position = frame.columns.indexOf(column);
  return position < 0 ? [] : frame.data.map((row) => row[position]);
};

/** {row label: {column: value}} → frame (row and column order from the object) */
export const frameFromRecords = (records: Record<string, Record<string, Cell>>): Frame => {
  const index = Object.keys(records);
  const columns = Array.from(new Set(index.flatMap((row) => Object.keys(records[row]))));
  return {
    index,
    columns,
    data: index.map((row) => columns.map((column) => records[row][column] ?? null)),
  };
};

/** Rows become columns and columns become rows */
export const transposeFrame = (frame: Frame): Frame => ({
  index: frame.columns,
  columns: frame.index,
  data: frame.columns.map((_, j) => frame.data.map((row) => row[j])),
});

export const pickColumns = (frame: Frame, columns: string[]): Frame => {
  const positions = columns.map((c) => frame.columns.indexOf(c)).filter((p) => p >= 0);
  return {
    index: frame.index,
    columns: positions.map((p) => frame.columns[p]),
    data: frame.data.map((row) => positions.map((p) => row[p])),
  };
};

/** Value at (row, column), or null */
export const frameValue = (frame: Frame, row: string, column: string): Cell => {
  const i = frame.index.indexOf(row);
  const j = frame.columns.indexOf(column);
  return i < 0 || j < 0 ? null : frame.data[i][j];
};
