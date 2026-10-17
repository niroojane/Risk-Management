import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { ErrorMessage } from './ErrorMessage';
import { Button } from '@/components/ui/button';
import { Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Route-level Error Boundary with home navigation
 */
export class RouteErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Route Error Boundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  handleGoHome = () => {
    this.handleReset();
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
          <ErrorMessage
            title="Page Error"
            message={
              this.state.error?.message ||
              'This page encountered an error. Please try reloading or return to the dashboard.'
            }
            onRetry={this.handleReset}
          />
          <Button onClick={this.handleGoHome} className="mt-4" variant="default">
            <Home className="mr-2 h-4 w-4" />
            Go to Dashboard
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
