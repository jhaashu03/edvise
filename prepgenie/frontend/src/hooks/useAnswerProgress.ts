import { useState, useEffect, useRef, useCallback } from 'react';
export {}; // Ensure this file is treated as a module

interface ProgressUpdate {
  phase: string;
  progress: number;
  message: string;
  estimated_time?: string;
  current_page?: number;
  total_pages?: number;
}

interface UseAnswerProgressReturn {
  progress: ProgressUpdate | null;
  isConnected: boolean;
  error: string | null;
  startTracking: (answerId: string) => void;
  stopTracking: () => void;
  getProgressPercentage: () => number;
  getProgressMessage: () => string;
  getProgressPhase: () => string;
  isProcessing: boolean;
}

export const useAnswerProgress = (initialAnswerId: string | null = null): UseAnswerProgressReturn => {
  const [answerId, setAnswerId] = useState<string | null>(initialAnswerId);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnectAttempts = 5;
  const reconnectAttemptRef = useRef(0);

  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting WebSocket...');
    
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    // Reset state
    setIsConnected(false);
    setIsProcessing(false);
    setError(null);
    reconnectAttemptRef.current = 0;
  }, []);

  const connect = useCallback(() => {
    if (!answerId) {
      console.log('❌ No answer ID provided for WebSocket connection');
      return;
    }
    
    // Don't create multiple connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('✅ WebSocket already connected');
      return;
    }
    
    try {
      const wsUrl = `ws://localhost:8001/api/v1/progress/ws/progress/answer_${answerId}`;
      console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('✅ WebSocket connected successfully');
        setIsConnected(true);
        setIsProcessing(true);
        setError(null);
        reconnectAttemptRef.current = 0; // Reset reconnect attempts on successful connection
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📊 Progress update received:', data);
          
          if (data.type === 'progress') {
            setProgress(data.data);
          } else if (data.type === 'error') {
            console.error('❌ Progress error:', data.message);
            setError(data.message);
          } else if (data.type === 'complete') {
            console.log('✅ Processing completed');
            setProgress({
              phase: 'completed',
              progress: 100,
              message: 'Processing completed successfully!'
            });
            setIsProcessing(false);
          }
        } catch (err) {
          console.error('❌ Failed to parse WebSocket message:', err);
          setError('Failed to parse progress update');
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt reconnection if it wasn't a clean close and we haven't exceeded max attempts
        if (!event.wasClean && reconnectAttemptRef.current < maxReconnectAttempts && isProcessing) {
          const delay = Math.pow(2, reconnectAttemptRef.current) * 1000; // Exponential backoff
          console.log(`🔄 Attempting reconnection in ${delay}ms (attempt ${reconnectAttemptRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptRef.current++;
            connect();
          }, delay);
        } else if (reconnectAttemptRef.current >= maxReconnectAttempts) {
          console.error('❌ Max reconnection attempts reached');
          setError('Connection lost. Please refresh to try again.');
          setIsProcessing(false);
        }
      };
      
      wsRef.current.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
        setError('WebSocket connection error');
        setIsConnected(false);
      };
      
    } catch (err) {
      console.error('❌ Failed to create WebSocket connection:', err);
      setError('Failed to create WebSocket connection');
      setIsConnected(false);
    }
  }, [answerId, isProcessing, disconnect]);

  const startTracking = useCallback((newAnswerId: string) => {
    console.log(`🎯 Starting progress tracking for answer: ${newAnswerId}`);
    
    // Disconnect any existing connection
    disconnect();
    
    // Set new answer ID and reset state
    setAnswerId(newAnswerId);
    setProgress(null);
    setError(null);
    setIsProcessing(true);
  }, [disconnect]);

  const stopTracking = useCallback(() => {
    console.log('⏹️ Stopping progress tracking');
    setAnswerId(null);
    disconnect();
    setProgress(null);
  }, [disconnect]);

  // Effect to handle connection when answerId changes
  useEffect(() => {
    if (answerId && isProcessing) {
      connect();
    }
    
    return () => {
      // Cleanup on unmount or answerId change
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [answerId, connect, isProcessing]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const getProgressPercentage = useCallback(() => {
    if (!progress) return 0;
    return Math.max(0, Math.min(100, progress.progress || 0));
  }, [progress]);

  const getProgressMessage = useCallback(() => {
    if (!progress) return 'Initializing...';
    
    // Enhanced message formatting
    if (progress.current_page && progress.total_pages) {
      return `Processing page ${progress.current_page}/${progress.total_pages}`;
    }
    
    return progress.message || 'Processing...';
  }, [progress]);

  const getProgressPhase = useCallback(() => {
    return progress?.phase || 'initializing';
  }, [progress]);

  return {
    progress,
    isConnected,
    error,
    startTracking,
    stopTracking,
    getProgressPercentage,
    getProgressMessage,
    getProgressPhase,
    isProcessing
  };
};

// Default export
export default useAnswerProgress;
