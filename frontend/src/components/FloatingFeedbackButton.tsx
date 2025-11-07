import React, { useState } from 'react';
import { MessageCircle } from 'lucide-react';
import FeedbackWidget from './FeedbackWidget';

const FloatingFeedbackButton: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        id="feedback-button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg hover:shadow-xl transition-all duration-200 z-40 group"
        aria-label="Send Feedback"
        title="Send Feedback or Report an Issue"
      >
        <MessageCircle size={24} />
        <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-gray-900 text-white text-sm px-3 py-2 rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          Send Feedback
        </span>
      </button>

      <FeedbackWidget
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  );
};

export default FloatingFeedbackButton;
