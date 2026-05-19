import React from 'react';
import type { FeedbackMessageProps } from '../types/props';

/**
 * BR-NL-FE-008: inline success/error feedback
 */
export default function FeedbackMessage({
  message,
  type,
}: FeedbackMessageProps): React.JSX.Element | null {
  if (!message || !type) return null;

  return (
    <div
      className={`feedback-message feedback-${type}`}
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
    >
      {message}
    </div>
  );
}