"use client";

import { useCallback, useEffect, useState } from "react";
import {
  connectInvestigationStream,
  type InvestigationEvent,
} from "@/lib/api/investigation-stream";
import type { PipelineStage } from "@/components/investigation-progress";

type ResultResponse = {
  run_id: string;
  status: string;
  result?: unknown;
  error?: string;
};

function eventText(event: InvestigationEvent): string {
  const data = event.data;

  if (typeof data === "string") return data;

  if (!data || typeof data !== "object") {
    return JSON.stringify(data ?? "");
  }

  const value = data as Record<string, unknown>;

  for (const key of ["message", "content", "name", "error"]) {
    if (typeof value[key] === "string") {
      return value[key] as string;
    }
  }

  return JSON.stringify(data);
}

function parsePipelineStage(value: unknown): PipelineStage | null {
  if (!value || typeof value !== "object") return null;

  const stage = value as Record<string, unknown>;
  if (
    typeof stage.step !== "string" ||
    typeof stage.title !== "string" ||
    typeof stage.detail !== "string" ||
    !["running", "finished", "failed"].includes(String(stage.state))
  ) {
    return null;
  }

  return {
    step: stage.step,
    title: stage.title,
    detail: stage.detail,
    state: stage.state as PipelineStage["state"],
    ...(typeof stage.elapsed_seconds === "number"
      ? { elapsed_seconds: stage.elapsed_seconds }
      : {}),
  };
}

export function useInvestigationDashboard() {
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("Connecting...");
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);
  const [result, setResult] = useState<unknown>(null);
  const [resultStatus, setResultStatus] = useState("Waiting for results");
  const [streamError, setStreamError] = useState("");

  const handleEvent = useCallback((event: InvestigationEvent) => {
    // Pipeline progress belongs in Investigation Results, not Agent Activity.
    if (event.type === "stage") {
      const stage = parsePipelineStage(event.data);
      if (!stage) return;

      setPipelineStages((previous) => {
        const index = previous.findIndex((item) => item.step === stage.step);

        if (index === -1) return [...previous, stage];

        return previous.map((item, itemIndex) =>
          itemIndex === index ? { ...item, ...stage } : item,
        );
      });
      return;
    }

    setEvents((previous) => {
      if (event.type === "llm_token") {
        const last = previous[previous.length - 1];

        if (last?.type === "llm_token") {
          return [
            ...previous.slice(0, -1),
            { ...event, data: eventText(last) + eventText(event) },
          ];
        }
      }

      return [...previous, event];
    });

    if (event.type === "connected") {
      setStatus("Live stream connected");
      setStreamError("");
    } else if (event.type === "status") {
      setStatus(eventText(event));
    } else if (event.type === "completed") {
      setStatus("Completed");
      setResultStatus("Completed");
    } else if (event.type === "error") {
      setStatus("Investigation failed");
      setStreamError(eventText(event));
      setResultStatus("Failed");
    } else if (event.type === "final_response") {
      setStatus("Agent finished — finalizing results");
    }
  }, []);

  useEffect(() => {
    const id = sessionStorage.getItem("sybiltrace_run_id");

    if (!id) {
      setStatus("No active investigation");
      setResultStatus("No active investigation");
      setStreamError("Upload a CSV to start an investigation.");
      return;
    }

    setRunId(id);

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let terminal = false;

    const resultUrl =
      `/backend/api/investigations/result/${encodeURIComponent(id)}`;

    const disconnect = connectInvestigationStream(
      id,
      handleEvent,
      (connection) => {
        if (cancelled) return;

        if (connection === "connecting") {
          setStatus("Connecting to live stream…");
        } else if (connection === "connected") {
          setStatus("Live stream connected");
        } else if (connection === "reconnecting") {
          setStatus("Stream interrupted — reconnecting…");
        }
      },
    );

    async function fetchResult() {
      try {
        const response = await fetch(resultUrl, { cache: "no-store" });

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(
            detail?.detail ??
              `Result request failed (HTTP ${response.status})`,
          );
        }

        const payload: ResultResponse = await response.json();
        if (cancelled) return;

        const normalizedStatus = payload.status.toLowerCase();
        setResultStatus(payload.status);

        if (payload.result !== undefined && payload.result !== null) {
          setResult(payload.result);
        }

        if (payload.error) setStreamError(payload.error);

        if (
          normalizedStatus === "completed" ||
          normalizedStatus === "error" ||
          normalizedStatus === "failed"
        ) {
          terminal = true;

          if (normalizedStatus === "completed") {
            setStatus("Completed");
          } else {
            setStatus("Investigation failed");
            if (payload.error) setStreamError(payload.error);
          }
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error
              ? error.message
              : "Could not fetch investigation result";

          setResultStatus(`Waiting for backend result (${message})`);
        }
      } finally {
        if (!cancelled && !terminal) {
          timer = setTimeout(fetchResult, 2000);
        }
      }
    }

    void fetchResult();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      disconnect();
    };
  }, [handleEvent]);

  const isCompleted =
    status.toLowerCase() === "completed" ||
    resultStatus.toLowerCase() === "completed";

  const isFailed =
    status.toLowerCase().includes("failed") ||
    resultStatus.toLowerCase() === "failed" ||
    resultStatus.toLowerCase() === "error";

  return {
    runId,
    status,
    events,
    pipelineStages,
    result,
    resultStatus,
    streamError,
    isCompleted,
    isFailed,
  };
}
