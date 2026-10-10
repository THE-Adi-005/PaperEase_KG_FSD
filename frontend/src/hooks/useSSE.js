import { useState, useCallback, useRef } from 'react';

/**
 * Custom hook for SSE (Server-Sent Events) streaming.
 * Manages connection, event parsing, and state accumulation.
 */
export function useSSE() {
  const [steps, setSteps] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [subgraph, setSubgraph] = useState(null);
  const [trace, setTrace] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const startQuery = useCallback(async (url, body) => {
    // Reset state
    setSteps([]);
    setAnswer(null);
    setSubgraph(null);
    setTrace(null);
    setError(null);
    setIsStreaming(true);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              handleEvent(eventType, data);
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  function handleEvent(eventType, data) {
    switch (eventType) {
      case 'thought':
        setSteps(prev => [...prev, { type: 'thought', ...data }]);
        break;
      case 'planning':
        setSteps(prev => [...prev, { type: 'planning', ...data }]);
        break;
      case 'action':
        setSteps(prev => [...prev, { type: 'action', ...data }]);
        break;
      case 'observation':
        setSteps(prev => [...prev, { type: 'observation', ...data }]);
        break;
      case 'reasoning':
        setSteps(prev => [...prev, { type: 'reasoning', ...data }]);
        break;
      case 'verifying':
        setSteps(prev => [...prev, { type: 'verifying', ...data }]);
        break;
      case 'revision':
        setSteps(prev => [...prev, { type: 'revision', ...data }]);
        break;
      case 'lazy_completion':
        setSteps(prev => [...prev, { type: 'lazy', ...data }]);
        break;
      case 'trace':
        setTrace(data);
        break;
      case 'answer':
        setAnswer(data);
        break;
      case 'subgraph':
        setSubgraph(data);
        break;
      case 'error':
        setError(data.message);
        break;
      case 'done':
        break;
      default:
        break;
    }
  }

  const reset = useCallback(() => {
    setSteps([]);
    setAnswer(null);
    setSubgraph(null);
    setTrace(null);
    setError(null);
    setIsStreaming(false);
  }, []);

  return { steps, answer, subgraph, trace, isStreaming, error, startQuery, reset };
}
