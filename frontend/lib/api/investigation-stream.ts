export type InvestigationEvent = {
  type: string;
  timestamp?: string;
  data?: unknown;
};

export function connectInvestigationStream(
  runId: string,
  onEvent: (event: InvestigationEvent) => void,
  onError?: () => void,
): () => void {
  const source = new EventSource(
    `/backend/api/investigations/stream/${encodeURIComponent(runId)}`,
  );

  source.onmessage = (message: MessageEvent<string>) => {
    try {
      onEvent(JSON.parse(message.data) as InvestigationEvent);
    } catch (error) {
      console.error("Failed to parse SSE event:", error);
    }
  };

  source.onerror = () => onError?.();

  return () => source.close();
}