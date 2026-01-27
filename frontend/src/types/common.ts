export interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}
