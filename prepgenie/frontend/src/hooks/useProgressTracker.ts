import { useState, useCallback } from 'react';

interface UseProgressTrackerProps {
  onComplete?: (taskId: string, success: boolean) => void;
  onError?: (taskId: string, error: string) => void;
}

interface ProgressState {
  isVisible: boolean;
  taskId: string | null;
}

export const useProgressTracker = ({ onComplete, onError }: UseProgressTrackerProps = {}) => {
  const [state, setState] = useState<ProgressState>({
    isVisible: false,
    taskId: null
  });

  const showProgress = useCallback((taskId: string) => {
    setState({
      isVisible: true,
      taskId
    });
  }, []);

  const hideProgress = useCallback(() => {
    setState({
      isVisible: false,
      taskId: null
    });
  }, []);

  const handleComplete = useCallback((success: boolean) => {
    if (state.taskId) {
      onComplete?.(state.taskId, success);
    }
  }, [state.taskId, onComplete]);

  const handleError = useCallback((error: string) => {
    if (state.taskId) {
      onError?.(state.taskId, error);
    }
  }, [state.taskId, onError]);

  return {
    isVisible: state.isVisible,
    taskId: state.taskId,
    showProgress,
    hideProgress,
    handleComplete,
    handleError
  };
};

export default useProgressTracker;
