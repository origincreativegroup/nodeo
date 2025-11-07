import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';

interface ErrorLog {
  errorId: string;
  title: string;
  message: string;
  category: string;
  severity: string;
  timestamp: string;
  url?: string;
  userAgent?: string;
  context?: Record<string, any>;
}

interface FeedbackItem {
  ticketId: string;
  type: string;
  title: string;
  description: string;
  email?: string;
  sentiment?: string;
  timestamp: string;
}

export default function ErrorMonitoring() {
  const [errors, setErrors] = useState<ErrorLog[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [activeTab, setActiveTab] = useState<'errors' | 'feedback'>('errors');

  // In a real implementation, this would fetch from an API
  useEffect(() => {
    // This is a placeholder - in production you'd fetch from /api/monitoring/errors
    // and /api/monitoring/feedback endpoints
  }, []);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="text-red-600" size={20} />;
      case 'error':
        return <AlertTriangle className="text-orange-600" size={20} />;
      case 'warning':
        return <AlertTriangle className="text-yellow-600" size={20} />;
      default:
        return <Info className="text-blue-600" size={20} />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'error':
        return 'bg-orange-50 border-orange-200 text-orange-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'bug':
        return <XCircle className="text-red-600" size={20} />;
      case 'feature':
        return <CheckCircle className="text-green-600" size={20} />;
      case 'improvement':
        return <AlertTriangle className="text-blue-600" size={20} />;
      default:
        return <Info className="text-gray-600" size={20} />;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">
        Error Monitoring & Feedback
      </h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('errors')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'errors'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Error Logs
          </button>
          <button
            onClick={() => setActiveTab('feedback')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'feedback'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            User Feedback
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'errors' ? (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-800">
            <p className="text-sm">
              <strong>Note:</strong> This is a demonstration view. In production, error logs would be
              stored in a database and displayed here. Errors are currently logged to the application
              log files.
            </p>
          </div>

          {errors.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <CheckCircle className="mx-auto text-green-500 mb-4" size={48} />
              <h3 className="text-lg font-medium text-gray-900">No errors logged</h3>
              <p className="text-gray-500 mt-2">
                Error logs will appear here when users encounter issues.
              </p>
            </div>
          ) : (
            errors.map((error) => (
              <div
                key={error.errorId}
                className={`border rounded-lg p-4 ${getSeverityColor(error.severity)}`}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(error.severity)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{error.title}</h3>
                      <span className="text-xs opacity-70">{error.errorId}</span>
                    </div>
                    <p className="mt-1 text-sm">{error.message}</p>
                    <div className="mt-2 text-xs">
                      <p>Category: {error.category}</p>
                      <p>Time: {new Date(error.timestamp).toLocaleString()}</p>
                      {error.url && <p>URL: {error.url}</p>}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-800">
            <p className="text-sm">
              <strong>Note:</strong> This is a demonstration view. In production, feedback would be
              stored in a database and displayed here. Feedback is currently logged to the application
              log files.
            </p>
          </div>

          {feedback.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <Info className="mx-auto text-blue-500 mb-4" size={48} />
              <h3 className="text-lg font-medium text-gray-900">No feedback yet</h3>
              <p className="text-gray-500 mt-2">
                User feedback will appear here when submitted.
              </p>
            </div>
          ) : (
            feedback.map((item) => (
              <div
                key={item.ticketId}
                className="bg-white border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start gap-3">
                  {getTypeIcon(item.type)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{item.title}</h3>
                      <span className="text-xs text-gray-500">#{item.ticketId}</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-700">{item.description}</p>
                    <div className="mt-2 text-xs text-gray-500">
                      <p>Type: {item.type}</p>
                      <p>Time: {new Date(item.timestamp).toLocaleString()}</p>
                      {item.email && <p>Email: {item.email}</p>}
                      {item.sentiment && (
                        <p>
                          Sentiment:{' '}
                          <span
                            className={
                              item.sentiment === 'positive'
                                ? 'text-green-600'
                                : 'text-red-600'
                            }
                          >
                            {item.sentiment}
                          </span>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
