"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  connectInvestigationStream,
  type InvestigationEvent,
} from "@/lib/api/investigation-stream";

type ResultResponse = {
  run_id: string;
  status: string;
  result?: unknown;
  error?: string;
};

function eventText(event: InvestigationEvent): string {
  const data = event.data;
  if (typeof data === "string") return data;
  if (!data || typeof data !== "object") return JSON.stringify(data ?? "");

  const value = data as Record<string, unknown>;
  for (const key of ["message", "content", "name", "error"]) {
    if (typeof value[key] === "string") return value[key] as string;
  }
  return JSON.stringify(data);
}

export default function DashboardPage() {
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("Connecting...");
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [result, setResult] = useState<unknown>(null);
  const [resultStatus, setResultStatus] = useState("Waiting for results");
  const [streamError, setStreamError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const handleEvent = useCallback((event: InvestigationEvent) => {
    setEvents((previous) => [...previous, event]);

    if (event.type === "connected") {
      setStatus("Connected — receiving live events");
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
    const resultUrl = `/backend/api/investigations/result/${encodeURIComponent(id)}`;
    let terminal = false;

    const disconnect = connectInvestigationStream(id, handleEvent, (connection) => {
      if (connection === "connecting") setStatus("Connecting to live stream…");
      if (connection === "connected") setStatus("Live stream connected");
      if (connection === "reconnecting") setStatus("Stream interrupted — reconnecting…");
    });

    async function fetchResult() {
      try {
        const response = await fetch(resultUrl, { cache: "no-store" });
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail ?? `Result request failed (HTTP ${response.status})`);
        }

        const payload: ResultResponse = await response.json();
        if (cancelled) return;

        setResultStatus(payload.status);
        if (payload.result !== undefined && payload.result !== null) {
          setResult(payload.result);
        }
        if (payload.error) {
          setStreamError(payload.error);
          terminal = true;
        }
        if (payload.status === "completed" || payload.status === "error") {
          terminal = true;
          if (payload.status === "completed") setStatus("Completed");
          else setStatus("Investigation failed");
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not fetch investigation result";
          // A run may still be starting; keep polling rather than treating this
          // one request as the final outcome.
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080809] text-white">
      <video className="pointer-events-none fixed inset-0 h-full w-full object-cover opacity-20" src="/videos/bg.mp4" autoPlay muted loop playsInline />
      <div className="fixed inset-0 bg-[#080809]/80" />

      <div className="relative z-10 mx-auto max-w-[1600px] px-5 py-8 md:px-10">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-6">
          <a href="/" className="text-lg font-semibold tracking-[0.22em]">SYBIL<span className="text-cyan-400">TRACE</span></a>
          <div className="text-right">
            <p className="text-xs uppercase tracking-[0.18em] text-gray-500">Investigation status</p>
            <p className="mt-1 text-sm text-cyan-300">{status}</p>
          </div>
        </header>

        <section className="py-8">
          <p className="text-xs uppercase tracking-[0.25em] text-cyan-400">Forensic workspace</p>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Investigation Dashboard</h1>
          <p className="mt-3 break-all text-sm text-gray-500">Run ID: {runId || "Loading..."}</p>
        </section>

        {streamError && <div role="alert" className="mb-6 rounded-lg border border-red-400/20 bg-red-400/5 p-4 text-sm text-red-300">{streamError}</div>}

        <div className="grid gap-6 xl:grid-cols-2">
          <section className="min-w-0 rounded-2xl border border-cyan-400/20 bg-black/40">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div><h2 className="font-medium">Agent Activity</h2><p className="mt-1 text-xs text-gray-500">Live events from the investigation backend</p></div>
              <span className="flex items-center gap-2 text-xs text-cyan-300"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />SSE</span>
            </div>
            <div className="h-[600px] space-y-3 overflow-y-auto p-5">
              {events.length === 0 && <p className="text-sm text-gray-500">Waiting for agent events…</p>}
              {events.map((event, index) => (
                <article key={`${event.timestamp ?? "event"}-${index}`} className="rounded-lg border border-white/[0.07] bg-white/[0.025] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium uppercase tracking-wider text-cyan-300">{event.type.replaceAll("_", " ")}</span>
                    {event.timestamp && <span className="shrink-0 text-[10px] text-gray-600">{new Date(event.timestamp).toLocaleTimeString()}</span>}
                  </div>
                  <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-xs leading-6 text-gray-300">{eventText(event)}</pre>
                </article>
              ))}
              <div ref={bottomRef} />
            </div>
          </section>

          <section className="min-w-0 rounded-2xl border border-white/10 bg-black/40">
            <div className="border-b border-white/10 px-5 py-4"><h2 className="font-medium">Investigation Results</h2><p className="mt-1 text-xs text-gray-500">Backend analysis output · refreshed automatically</p></div>
            <div className="h-[600px] overflow-auto p-5">
              {result === null ? (
                <div className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-cyan-400" />
                  <p className="text-sm text-gray-400">{resultStatus}</p>
                  <p className="text-xs text-gray-600">Results appear when the backend makes them available.</p>
                </div>
              ) : <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-6 text-gray-300">{JSON.stringify(result, null, 2)}</pre>}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
