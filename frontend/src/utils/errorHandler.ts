import { AxiosError } from 'axios';

export interface AppError {
  message: string;
  code?: string;
  statusCode?: number;
}

/**
 * Extract user-friendly error message from various error types
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response?.data?.detail) {
      return typeof error.response.data.detail === 'string'
        ? error.response.data.detail
        : JSON.stringify(error.response.data.detail);
    }
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (error.message) {
      return error.message;
    }
    return 'An error occurred while communicating with the server';
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  return 'An unexpected error occurred';
}

/**
 * Create AppError from unknown error type
 */
export function createAppError(error: unknown): AppError {
  if (error instanceof AxiosError) {
    return {
      message: getErrorMessage(error),
      code: error.code,
      statusCode: error.response?.status,
    };
  }

  return {
    message: getErrorMessage(error),
  };
}

/**
 * Check if error is a network error
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof AxiosError) {
    return !error.response && error.code !== 'ECONNABORTED';
  }
  return false;
}

/**
 * Check if error is an authentication error
 */
export function isAuthError(error: unknown): boolean {
  if (error instanceof AxiosError) {
    return error.response?.status === 401 || error.response?.status === 403;
  }
  return false;
}
