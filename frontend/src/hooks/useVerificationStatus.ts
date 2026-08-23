import { useState, useEffect, useCallback, useRef } from 'react';
import { VerifyJobStatus } from '../lib/types';
import { getVerifyJobStatus } from '../lib/api';

interface UseVerificationStatusOptions {
  pollingIntervalMs?: number;
  onComplete?: (status: VerifyJobStatus) => void;
  onError?: (error: Error) => void;
}

export function useVerificationStatus(
  jobId: string | null,
  options: UseVerificationStatusOptions = {}
) {
  const { 
    pollingIntervalMs = 1200, 
    onComplete, 
    onError 
  } = options;

  const [status, setStatus] = useState<VerifyJobStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const timerRef = useRef<number | null>(null);
  const isPollingRef = useRef<boolean>(false);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    isPollingRef.current = false;
  }, []);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const result = await getVerifyJobStatus(jobId);
      setStatus(result);
      setError(null);

      if (result.status === 'complete') {
        stopPolling();
        if (onCompleteRef.current) {
          onCompleteRef.current(result);
        }
      } else if (result.status === 'failed') {
        stopPolling();
        const err = new Error('Verification job failed execution');
        setError(err.message);
        if (onErrorRef.current) {
          onErrorRef.current(err);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to poll verification status';
      setError(message);
      if (onErrorRef.current) {
        onErrorRef.current(err instanceof Error ? err : new Error(message));
      }
    } finally {
      setIsLoading(false);
    }
  }, [jobId, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      setStatus(null);
      setIsLoading(false);
      setError(null);
      stopPolling();
      return;
    }

    setIsLoading(true);
    isPollingRef.current = true;

    // First immediate fetch
    fetchStatus();

    // Setup polling interval
    timerRef.current = window.setInterval(() => {
      if (isPollingRef.current) {
        fetchStatus();
      }
    }, pollingIntervalMs);

    return () => {
      stopPolling();
    };
  }, [jobId, pollingIntervalMs, fetchStatus, stopPolling]);

  return {
    status,
    isLoading,
    isComplete: status?.status === 'complete',
    isFailed: status?.status === 'failed',
    error,
    refetch: fetchStatus,
    stopPolling,
  };
}
