import { useCallback } from 'react';
import { getErrorMessage, isNetworkError, isAuthError } from '@/utils/errorHandler';

export function useErrorHandler() {
  const handleError = useCallback((error: unknown) => {
    const message = getErrorMessage(error);

    if (isNetworkError(error)) {
      console.error('Network error:', message);
      return 'Network error. Please check your connection.';
    }

    if (isAuthError(error)) {
      console.error('Authentication error:', message);
      return 'Authentication failed. Please login again.';
    }

    console.error('Error:', message);
    return message;
  }, []);

  return { handleError };
}
