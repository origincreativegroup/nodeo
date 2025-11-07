import React, { useState } from 'react';
import { X, Send, Bug, MessageSquare, ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface FeedbackWidgetProps {
  isOpen: boolean;
  onClose: () => void;
  prefilledError?: {
    title: string;
    message: string;
    technicalDetails?: string;
    context?: Record<string, any>;
  };
}

type FeedbackType = 'bug' | 'feature' | 'improvement' | 'other';

const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ isOpen, onClose, prefilledError }) => {
  const [feedbackType, setFeedbackType] = useState<FeedbackType>(prefilledError ? 'bug' : 'improvement');
  const [title, setTitle] = useState(prefilledError?.title || '');
  const [description, setDescription] = useState(prefilledError?.message || '');
  const [stepsToReproduce, setStepsToReproduce] = useState('');
  const [email, setEmail] = useState('');
  const [includeSystemInfo, setIncludeSystemInfo] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sentiment, setSentiment] = useState<'positive' | 'negative' | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim() || !description.trim()) {
      toast.error('Please provide a title and description');
      return;
    }

    setIsSubmitting(true);

    try {
      // Collect system information
      const systemInfo = includeSystemInfo ? {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        prefilledContext: prefilledError?.context,
        technicalDetails: prefilledError?.technicalDetails
      } : null;

      const feedbackData = {
        type: feedbackType,
        title: title.trim(),
        description: description.trim(),
        stepsToReproduce: stepsToReproduce.trim() || null,
        email: email.trim() || null,
        sentiment,
        systemInfo,
        isErrorReport: !!prefilledError
      };

      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(feedbackData)
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      const result = await response.json();

      toast.success(
        `Thank you for your feedback! ${result.ticketId ? `Ticket #${result.ticketId}` : ''}`,
        { duration: 5000 }
      );

      // Reset form
      setTitle('');
      setDescription('');
      setStepsToReproduce('');
      setEmail('');
      setSentiment(null);
      setFeedbackType('improvement');
      onClose();
    } catch (error) {
      console.error('Error submitting feedback:', error);
      toast.error('Failed to submit feedback. Please try again or contact support@jspow.app');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {prefilledError ? 'Report an Issue' : 'Send Feedback'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Help us improve jspow by sharing your experience
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close"
          >
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Sentiment (if not error report) */}
          {!prefilledError && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                How's your experience so far?
              </label>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setSentiment('positive')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                    sentiment === 'positive'
                      ? 'bg-green-50 border-green-500 text-green-700 dark:bg-green-900/20 dark:border-green-500 dark:text-green-400'
                      : 'border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-400'
                  }`}
                >
                  <ThumbsUp size={20} />
                  Positive
                </button>
                <button
                  type="button"
                  onClick={() => setSentiment('negative')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                    sentiment === 'negative'
                      ? 'bg-red-50 border-red-500 text-red-700 dark:bg-red-900/20 dark:border-red-500 dark:text-red-400'
                      : 'border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-400'
                  }`}
                >
                  <ThumbsDown size={20} />
                  Negative
                </button>
              </div>
            </div>
          )}

          {/* Feedback Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Feedback Type
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                { value: 'bug', label: 'Bug Report', icon: Bug },
                { value: 'feature', label: 'Feature Request', icon: MessageSquare },
                { value: 'improvement', label: 'Improvement', icon: ThumbsUp },
                { value: 'other', label: 'Other', icon: AlertCircle }
              ].map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFeedbackType(value as FeedbackType)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-lg border transition-colors ${
                    feedbackType === value
                      ? 'bg-blue-50 border-blue-500 text-blue-700 dark:bg-blue-900/20 dark:border-blue-500 dark:text-blue-400'
                      : 'border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-400'
                  }`}
                >
                  <Icon size={20} />
                  <span className="text-xs font-medium">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Title */}
          <div>
            <label htmlFor="feedback-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              id="feedback-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief summary of your feedback"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="feedback-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="feedback-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Please provide details about your feedback..."
              rows={5}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Steps to Reproduce (for bugs) */}
          {feedbackType === 'bug' && (
            <div>
              <label htmlFor="feedback-steps" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Steps to Reproduce
              </label>
              <textarea
                id="feedback-steps"
                value={stepsToReproduce}
                onChange={(e) => setStepsToReproduce(e.target.value)}
                placeholder="1. Go to...&#10;2. Click on...&#10;3. See error"
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          )}

          {/* Email (optional) */}
          <div>
            <label htmlFor="feedback-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email (optional)
            </label>
            <input
              id="feedback-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your.email@example.com (if you'd like a response)"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Include System Info */}
          <div className="flex items-start gap-3">
            <input
              id="include-system-info"
              type="checkbox"
              checked={includeSystemInfo}
              onChange={(e) => setIncludeSystemInfo(e.target.checked)}
              className="mt-1"
            />
            <label htmlFor="include-system-info" className="text-sm text-gray-600 dark:text-gray-400">
              Include system information (browser, OS, screen resolution) to help us debug issues.
              {prefilledError && ' Error details will also be included.'}
            </label>
          </div>

          {/* Technical Details Preview (if error report) */}
          {prefilledError?.technicalDetails && includeSystemInfo && (
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                Technical details that will be included:
              </p>
              <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto">
                {prefilledError.technicalDetails}
              </pre>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Send Feedback
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FeedbackWidget;
