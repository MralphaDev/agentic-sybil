export type InvestigationEvent = {
  type: string;
  timestamp?: string | null;
  data?: unknown;
};

export function connectInvestigationStream(
  runId: string,
  onEvent: (event: InvestigationEvent) => void,
  onConnectionChange?: (state: "connecting" | "connected" | "reconnecting") => void,
): () => void {
  const source = new EventSource(
    `/backend/api/investigations/stream/${encodeURIComponent(runId)}`,
  );

  onConnectionChange?.("connecting");

  source.onopen = () => onConnectionChange?.("connected");

  source.onmessage = (message: MessageEvent<string>) => {
    try {
      const event = JSON.parse(message.data) as InvestigationEvent;
      onEvent(event);

      if (event.type === "completed" || event.type === "error") {
        source.close();
      }
    } catch (error) {
      console.error("Failed to parse SSE event:", error);
    }
  };

  source.onerror = () => {
    // EventSource reconnects automatically unless explicitly closed.
    if (source.readyState !== EventSource.CLOSED) {
      onConnectionChange?.("reconnecting");
    }
  };

  return () => source.close();
}
