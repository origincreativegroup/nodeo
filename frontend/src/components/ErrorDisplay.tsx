import React, { useState } from 'react';
import { AlertCircle, X, ChevronDown, ChevronUp } from 'lucide-react';
import { ActionableError, ErrorSeverity } from '../utils/errorHandling';
import FeedbackWidget from './FeedbackWidget';

interface ErrorDisplayProps {
  error: ActionableError;
  onDismiss?: () => void;
  showActions?: boolean;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onDismiss,
  showActions = true
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const getSeverityColor = (severity: ErrorSeverity) => {
    switch (severity) {
      case ErrorSeverity.INFO:
        return 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300';
      case ErrorSeverity.WARNING:
        return 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-300';
      case ErrorSeverity.ERROR:
        return 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300';
      case ErrorSeverity.CRITICAL:
        return 'bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-900/20 dark:border-purple-800 dark:text-purple-300';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800 dark:bg-gray-900/20 dark:border-gray-800 dark:text-gray-300';
    }
  };

  const getSeverityIcon = (severity: ErrorSeverity) => {
    const color = severity === ErrorSeverity.CRITICAL ? 'text-purple-600 dark:text-purple-400'
      : severity === ErrorSeverity.ERROR ? 'text-red-600 dark:text-red-400'
      : severity === ErrorSeverity.WARNING ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-blue-600 dark:text-blue-400';

    return <AlertCircle className={color} size={20} />;
  };

  return (
    <>
      <div className={`border rounded-lg p-4 ${getSeverityColor(error.severity)}`}>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            {getSeverityIcon(error.severity)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <h4 className="font-semibold text-sm mb-1">{error.title}</h4>
                <p className="text-sm">{error.message}</p>
              </div>

              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="flex-shrink-0 hover:opacity-70 transition-opacity"
                  aria-label="Dismiss"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            {/* Actions */}
            {showActions && error.actions && error.actions.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {error.actions.map((action, index) => (
                  <button
                    key={index}
                    onClick={action.action}
                    className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                      action.type === 'primary'
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {action.label}
                  </button>
                ))}
                <button
                  onClick={() => setShowFeedback(true)}
                  className="text-xs px-3 py-1.5 rounded-md font-medium bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Report This Issue
                </button>
              </div>
            )}

            {/* Technical Details Toggle */}
            {error.technicalDetails && (
              <div className="mt-3">
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="flex items-center gap-1 text-xs font-medium hover:underline"
                >
                  {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showDetails ? 'Hide' : 'Show'} Technical Details
                </button>

                {showDetails && (
                  <div className="mt-2 p-3 bg-black/5 dark:bg-black/20 rounded border border-black/10 dark:border-white/10">
                    <p className="text-xs font-mono whitespace-pre-wrap break-all">
                      {error.technicalDetails}
                    </p>
                    {error.context && Object.keys(error.context).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs font-medium cursor-pointer hover:underline">
                          Additional Context
                        </summary>
                        <pre className="mt-2 text-xs font-mono whitespace-pre-wrap">
                          {JSON.stringify(error.context, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Timestamp */}
            <p className="text-xs opacity-70 mt-2">
              {error.timestamp.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Feedback Widget */}
      <FeedbackWidget
        isOpen={showFeedback}
        onClose={() => setShowFeedback(false)}
        prefilledError={{
          title: error.title,
          message: error.message,
          technicalDetails: error.technicalDetails,
          context: error.context
        }}
      />
    </>
  );
};

export default ErrorDisplay;
