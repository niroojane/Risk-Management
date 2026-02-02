export interface PricesResponse {
  success: boolean;
  data: {
    symbols: string[];
    start_date: string;
    end_date: string;
    data: {
      [date: string]: {
        [symbol: string]: number;
      };
    };
  };
}

export interface PriceRow {
  date: string;
  [symbol: string]: string | number;
}
