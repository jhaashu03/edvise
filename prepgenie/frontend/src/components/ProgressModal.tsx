import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import PDFProcessingProgress from './PDFProcessingProgress';

interface ProgressModalProps {
  isOpen: boolean;
  taskId: string;
  onClose: () => void;
  onComplete?: (success: boolean) => void;
  onError?: (error: string) => void;
}

export const ProgressModal: React.FC<ProgressModalProps> = ({
  isOpen,
  taskId,
  onClose,
  onComplete,
  onError
}) => {
  if (!isOpen) return null;

  const handleComplete = (success: boolean) => {
    onComplete?.(success);
    // Auto-close modal after 3 seconds on success
    if (success) {
      setTimeout(() => {
        onClose();
      }, 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-2xl bg-white rounded-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Processing Your Answer Sheet
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Close"
            >
              <XMarkIcon className="h-5 w-5 text-gray-500" />
            </button>
          </div>
          
          {/* Progress Content */}
          <div className="p-6">
            <PDFProcessingProgress
              taskId={taskId}
              onComplete={handleComplete}
              onError={onError}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressModal;
