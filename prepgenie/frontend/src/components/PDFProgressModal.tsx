import React, { useState, useEffect, useRef } from 'react';
import { CheckCircleIcon, ExclamationCircleIcon, ClockIcon, DocumentIcon } from '@heroicons/react/24/outline';

interface ProgressData {
  phase: string;
  progress: number;
  current_page?: number;
  current_question?: number;
  total_pages?: number;
  total_questions?: number;
  message: string;
  estimated_remaining_minutes?: number;
  details?: string;
  timestamp: string;
  type?: string;
}

interface PDFProcessingProgressProps {
  taskId: string;
  onComplete?: (success: boolean) => void;
  onError?: (error: string) => void;
}

export const PDFProcessingProgress: React.FC<PDFProcessingProgressProps> = ({
  taskId,
  onComplete,
  onError
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [startTime] = useState(new Date());
  const wsRef = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    // Connect to WebSocket for real-time progress updates
    const connectWebSocket = () => {
      const wsUrl = `ws://localhost:8001/api/v1/progress/ws/progress/${taskId}`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('📡 Connected to progress tracker');
        setIsConnected(true);
        setError(null);
      };
      
      ws.onmessage = (event) => {
        try {
          const data: ProgressData = JSON.parse(event.data);
          console.log('📊 Progress update:', data);
          
          setProgress(data);
          
          // Handle completion
          if (data.phase === 'completed') {
            setIsComplete(true);
            onComplete?.(true);
          } else if (data.phase === 'error') {
            setError(data.message);
            onError?.(data.message);
          }
        } catch (err) {
          console.error('Failed to parse progress data:', err);
        }
      };
      
      ws.onclose = (event) => {
        console.log('📡 WebSocket connection closed', event.code);
        setIsConnected(false);
        
        // Attempt to reconnect if not complete and not a normal closure
        if (!isComplete && event.code !== 1000) {
          setTimeout(connectWebSocket, 2000);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error - trying to reconnect...');
      };
      
      wsRef.current = ws;
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000);
      }
    };
  }, [taskId, isComplete, onComplete, onError]);
  
  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-6 w-6 text-red-500" />;
      default:
        return <ClockIcon className="h-6 w-6 text-blue-500 animate-spin" />;
    }
  };
  
  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case 'initializing':
        return 'Initializing';
      case 'page_processing':
        return 'Processing Pages';
      case 'question_extraction':
        return 'Extracting Questions';
      case 'answer_evaluation':
        return 'Evaluating Answers';
      case 'finalizing':
        return 'Finalizing Results';
      case 'completed':
        return 'Complete';
      case 'error':
        return 'Error';
      default:
        return 'Processing';
    }
  };
  
  const formatElapsedTime = () => {
    const elapsed = Math.floor((new Date().getTime() - startTime.getTime()) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };
  
  if (error && !progress) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <ExclamationCircleIcon className="h-6 w-6 text-red-500" />
          <div>
            <h3 className="text-lg font-medium text-red-800">Connection Error</h3>
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <DocumentIcon className="h-8 w-8 text-blue-500" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              PDF Processing Progress
            </h3>
            <p className="text-sm text-gray-600">
              Task ID: {taskId.substring(0, 8)}... • Elapsed: {formatElapsedTime()}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-400' : 'bg-red-400'
          }`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      {progress && (
        <>
          {/* Current Phase */}
          <div className="flex items-center space-x-3 mb-4">
            {getPhaseIcon(progress.phase)}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">
                  {getPhaseLabel(progress.phase)}
                </span>
                {progress.estimated_remaining_minutes !== undefined && (
                  <span className="text-sm text-gray-600">
                    ~{progress.estimated_remaining_minutes} min remaining
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Overall Progress
              </span>
              <span className="text-sm text-gray-600">
                {progress.progress}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  progress.phase === 'error'
                    ? 'bg-red-500'
                    : progress.phase === 'completed'
                    ? 'bg-green-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.max(progress.progress, 5)}%` }}
              />
            </div>
          </div>
          
          {/* Current Status Message */}
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-800 font-medium mb-1">
              {progress.message}
            </p>
            {progress.details && (
              <p className="text-xs text-gray-600">
                {progress.details}
              </p>
            )}
          </div>
          
          {/* Page & Question Progress */}
          {(progress.current_page || progress.current_question) && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              {progress.current_page && progress.total_pages && (
                <div className="bg-blue-50 rounded-lg p-3">
                  <div className="text-xs text-blue-600 font-medium mb-1">
                    Pages Processed
                  </div>
                  <div className="text-lg font-bold text-blue-700">
                    {progress.current_page} / {progress.total_pages}
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2 mt-2">
                    <div
                      className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                      style={{
                        width: `${(progress.current_page / progress.total_pages) * 100}%`
                      }}
                    />
                  </div>
                </div>
              )}
              
              {progress.current_question && progress.total_questions && (
                <div className="bg-green-50 rounded-lg p-3">
                  <div className="text-xs text-green-600 font-medium mb-1">
                    Questions Evaluated
                  </div>
                  <div className="text-lg font-bold text-green-700">
                    {progress.current_question} / {progress.total_questions}
                  </div>
                  <div className="w-full bg-green-200 rounded-full h-2 mt-2">
                    <div
                      className="h-2 bg-green-500 rounded-full transition-all duration-300"
                      style={{
                        width: `${(progress.current_question / progress.total_questions) * 100}%`
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Time Estimate */}
          {progress.estimated_remaining_minutes !== undefined && progress.estimated_remaining_minutes > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <ClockIcon className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-yellow-800">
                  <strong>Estimated time remaining:</strong> {progress.estimated_remaining_minutes} minute
                  {progress.estimated_remaining_minutes !== 1 ? 's' : ''}
                </span>
              </div>
              <p className="text-xs text-yellow-700 mt-1">
                Processing time varies based on PDF quality and content complexity
              </p>
            </div>
          )}
          
          {/* Success Message */}
          {isComplete && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
              <div className="flex items-center space-x-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                <span className="text-sm font-medium text-green-800">
                  Processing completed successfully!
                </span>
              </div>
              <p className="text-xs text-green-700 mt-1">
                Your answer evaluation is ready. You can view the results in your answers section.
              </p>
            </div>
          )}
        </>
      )}
      
      {/* Connection Status */}
      {!isConnected && !error && (
        <div className="text-center py-8">
          <ClockIcon className="h-8 w-8 text-gray-400 mx-auto mb-2 animate-spin" />
          <p className="text-sm text-gray-600">Connecting to progress tracker...</p>
        </div>
      )}
    </div>
  );
};

export default PDFProcessingProgress;
