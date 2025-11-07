/**
 * Enhanced Error Handling Utilities
 * Provides categorized errors with actionable guidance for users
 */

export enum ErrorCategory {
  NETWORK = 'network',
  VALIDATION = 'validation',
  FILE_SYSTEM = 'file_system',
  PERMISSION = 'permission',
  AI_MODEL = 'ai_model',
  STORAGE = 'storage',
  UNKNOWN = 'unknown'
}

export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

export interface ActionableError {
  title: string;
  message: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  actions?: ErrorAction[];
  technicalDetails?: string;
  timestamp: Date;
  context?: Record<string, any>;
}

export interface ErrorAction {
  label: string;
  action: () => void | Promise<void>;
  type: 'primary' | 'secondary';
}

/**
 * Creates an actionable error with context and suggestions
 */
export function createActionableError(
  error: any,
  context?: Record<string, any>
): ActionableError {
  const errorMessage = error?.message || error?.toString() || 'An unknown error occurred';
  const statusCode = error?.response?.status || error?.status;

  // Network errors
  if (error?.code === 'ERR_NETWORK' || error?.code === 'ECONNREFUSED' || !navigator.onLine) {
    return {
      title: 'Connection Error',
      message: 'Unable to connect to the server. Please check your internet connection.',
      category: ErrorCategory.NETWORK,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Retry',
          action: () => window.location.reload(),
          type: 'primary'
        },
        {
          label: 'Check Connection',
          action: () => window.open('https://www.google.com', '_blank'),
          type: 'secondary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // 404 errors
  if (statusCode === 404) {
    const isFile = context?.filePath || context?.fileName;
    return {
      title: isFile ? 'File Not Found' : 'Resource Not Found',
      message: isFile
        ? `The file "${context?.fileName || 'specified file'}" could not be found. It may have been moved, renamed, or deleted.`
        : 'The requested resource could not be found.',
      category: ErrorCategory.FILE_SYSTEM,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Refresh',
          action: () => window.location.reload(),
          type: 'primary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // 403 Permission errors
  if (statusCode === 403) {
    return {
      title: 'Permission Denied',
      message: 'You do not have permission to perform this action. Please check your access rights.',
      category: ErrorCategory.PERMISSION,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Contact Support',
          action: () => {
            const feedback = document.getElementById('feedback-button');
            if (feedback) feedback.click();
          },
          type: 'primary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // 500 Server errors
  if (statusCode && statusCode >= 500) {
    return {
      title: 'Server Error',
      message: 'An error occurred on the server. Our team has been notified. Please try again later.',
      category: ErrorCategory.UNKNOWN,
      severity: ErrorSeverity.CRITICAL,
      actions: [
        {
          label: 'Report Issue',
          action: () => {
            const feedback = document.getElementById('feedback-button');
            if (feedback) feedback.click();
          },
          type: 'primary'
        },
        {
          label: 'Retry',
          action: () => window.location.reload(),
          type: 'secondary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // File system errors
  if (errorMessage.includes('ENOENT') || errorMessage.includes('file not found')) {
    return {
      title: 'File System Error',
      message: 'Unable to access the file. It may have been moved or deleted.',
      category: ErrorCategory.FILE_SYSTEM,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Refresh List',
          action: () => window.location.reload(),
          type: 'primary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // Validation errors
  if (statusCode === 400 || errorMessage.includes('validation') || errorMessage.includes('invalid')) {
    return {
      title: 'Invalid Input',
      message: 'Please check your input and try again. ' + (error?.response?.data?.detail || errorMessage),
      category: ErrorCategory.VALIDATION,
      severity: ErrorSeverity.WARNING,
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // AI Model errors
  if (errorMessage.includes('ollama') || errorMessage.includes('model') || errorMessage.includes('analysis')) {
    return {
      title: 'AI Processing Error',
      message: 'The AI model is currently unavailable or encountered an error. Please ensure Ollama is running.',
      category: ErrorCategory.AI_MODEL,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Check Ollama',
          action: () => window.open('http://localhost:11434', '_blank'),
          type: 'primary'
        },
        {
          label: 'View Docs',
          action: () => window.open('https://ollama.ai/docs', '_blank'),
          type: 'secondary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // Storage errors
  if (errorMessage.includes('storage') || errorMessage.includes('upload') || errorMessage.includes('download')) {
    return {
      title: 'Storage Error',
      message: 'Failed to access cloud storage. Please check your storage configuration and credentials.',
      category: ErrorCategory.STORAGE,
      severity: ErrorSeverity.ERROR,
      actions: [
        {
          label: 'Check Settings',
          action: () => {
            window.location.hash = '#/settings';
          },
          type: 'primary'
        }
      ],
      technicalDetails: errorMessage,
      timestamp: new Date(),
      context
    };
  }

  // Generic error
  return {
    title: 'Error',
    message: errorMessage,
    category: ErrorCategory.UNKNOWN,
    severity: ErrorSeverity.ERROR,
    actions: [
      {
        label: 'Report Issue',
        action: () => {
          const feedback = document.getElementById('feedback-button');
          if (feedback) feedback.click();
        },
        type: 'primary'
      }
    ],
    technicalDetails: errorMessage,
    timestamp: new Date(),
    context
  };
}

/**
 * Formats an error message for display to the user
 */
export function formatErrorMessage(error: ActionableError): string {
  let message = `${error.title}: ${error.message}`;

  if (error.actions && error.actions.length > 0) {
    const actionLabels = error.actions.map(a => a.label).join(' or ');
    message += `\n\nSuggested actions: ${actionLabels}`;
  }

  return message;
}

/**
 * Retry logic with exponential backoff
 */
export async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  options: {
    maxRetries?: number;
    initialDelay?: number;
    maxDelay?: number;
    backoffFactor?: number;
    onRetry?: (attempt: number, error: any) => void;
  } = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    backoffFactor = 2,
    onRetry
  } = options;

  let lastError: any;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt < maxRetries) {
        const delay = Math.min(initialDelay * Math.pow(backoffFactor, attempt), maxDelay);

        if (onRetry) {
          onRetry(attempt + 1, error);
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Logs error to backend for monitoring
 */
export async function logError(error: ActionableError): Promise<void> {
  try {
    await fetch('/api/errors/log', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        title: error.title,
        message: error.message,
        category: error.category,
        severity: error.severity,
        technicalDetails: error.technicalDetails,
        timestamp: error.timestamp.toISOString(),
        context: error.context,
        userAgent: navigator.userAgent,
        url: window.location.href
      })
    });
  } catch (e) {
    // Silently fail - don't let error logging cause more errors
    console.error('Failed to log error to backend:', e);
  }
}

/**
 * Error boundary helper for React components
 */
export function handleComponentError(error: Error, errorInfo: React.ErrorInfo): ActionableError {
  return {
    title: 'Component Error',
    message: 'A component failed to render. Please refresh the page.',
    category: ErrorCategory.UNKNOWN,
    severity: ErrorSeverity.CRITICAL,
    actions: [
      {
        label: 'Refresh Page',
        action: () => window.location.reload(),
        type: 'primary'
      }
    ],
    technicalDetails: `${error.message}\n\nComponent Stack:\n${errorInfo.componentStack}`,
    timestamp: new Date(),
    context: {
      errorMessage: error.message,
      errorStack: error.stack,
      componentStack: errorInfo.componentStack
    }
  };
}
