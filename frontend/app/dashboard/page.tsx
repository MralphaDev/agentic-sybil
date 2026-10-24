
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

function formatTime(timestamp?: string | null) {
  if (!timestamp) return "";
  const date = new Date(timestamp);

  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
}

function prettyJSON(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export default function DashboardPage() {
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("Connecting...");
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [result, setResult] = useState<unknown>(null);
  const [resultStatus, setResultStatus] = useState("Waiting for results");
  const [streamError, setStreamError] = useState("");
  const [showRawResult, setShowRawResult] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  const isCompleted =
    status.toLowerCase() === "completed" ||
    resultStatus.toLowerCase() === "completed";

  const isFailed =
    status.toLowerCase().includes("failed") ||
    resultStatus.toLowerCase() === "failed";

  const handleEvent = useCallback((event: InvestigationEvent) => {
    setEvents((previous) => {
      // Keep the stream intact, but render consecutive LLM token chunks
      // as one continuous message instead of separate cards.
      if (event.type === "llm_token") {
        const last = previous[previous.length - 1];

        if (last?.type === "llm_token") {
          return [
            ...previous.slice(0, -1),
            {
              ...event,
              data: eventText(last) + eventText(event),
            },
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
        if (connection === "connecting") {
          setStatus("Connecting to live stream…");
        }

        if (connection === "connected") {
          setStatus("Live stream connected");
        }

        if (connection === "reconnecting") {
          setStatus("Stream interrupted — reconnecting…");
        }
      },
    );

    async function fetchResult() {
      try {
        const response = await fetch(resultUrl, {
          cache: "no-store",
        });

        if (!response.ok) {
          const detail = await response.json().catch(() => null);

          throw new Error(
            detail?.detail ??
              `Result request failed (HTTP ${response.status})`,
          );
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

        if (
          payload.status === "completed" ||
          payload.status === "error"
        ) {
          terminal = true;

          if (payload.status === "completed") {
            setStatus("Completed");
          } else {
            setStatus("Investigation failed");
          }
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error
              ? error.message
              : "Could not fetch investigation result";

          setResultStatus(
            `Waiting for backend result (${message})`,
          );
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
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [events]);

  const tokenCount = events.filter(
    (event) => event.type === "llm_token",
  ).length;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080809] text-zinc-100">
      {/* Background */}
      <video
        className="pointer-events-none fixed inset-0 h-full w-full object-cover opacity-[0.12]"
        src="/videos/bg.mp4"
        autoPlay
        muted
        loop
        playsInline
      />

      <div className="pointer-events-none fixed inset-0 bg-[#080809]/75" />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/70" />

      <div className="pointer-events-none fixed -left-40 top-20 h-96 w-96 rounded-full bg-red-800/10 blur-[120px]" />
      <div className="pointer-events-none fixed -right-40 top-1/3 h-96 w-96 rounded-full bg-orange-700/10 blur-[140px]" />

      <div className="relative z-10 mx-auto max-w-[1800px] px-4 pb-8 sm:px-6 lg:px-10">
        {/* Header */}
        <header className="flex min-h-[76px] items-center justify-between gap-4 border-b border-white/[0.09]">
          <a
            href="/"
            className="flex items-center gap-3"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-red-400/20 bg-red-500/10">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="h-5 w-5 text-red-400"
                stroke="currentColor"
                strokeWidth="1.7"
              >
                <path
                  d="M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6l8-3Z"
                  strokeLinejoin="round"
                />
                <path
                  d="m8.5 12 2.2 2.2 4.8-5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>

            <span className="text-sm font-semibold tracking-[0.17em]">
              SYBIL<span className="text-red-400">TRACE</span>
            </span>
          </a>

          <div className="flex items-center gap-3">
            <span
              className={`h-2 w-2 rounded-full ${
                isFailed
                  ? "bg-red-400"
                  : isCompleted
                    ? "bg-emerald-400"
                    : "animate-pulse bg-orange-400"
              }`}
            />

            <div className="text-right">
              <p className="text-[10px] uppercase tracking-[0.17em] text-zinc-500">
                Investigation status
              </p>
              <p
                className={`mt-1 max-w-[220px] truncate text-xs font-medium ${
                  isFailed
                    ? "text-red-300"
                    : isCompleted
                      ? "text-emerald-300"
                      : "text-orange-200"
                }`}
              >
                {status}
              </p>
            </div>
          </div>
        </header>

        {/* Page heading */}
        <section className="pb-7 pt-8 md:pb-9 md:pt-10">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.25em] text-red-300">
                <span className="h-px w-6 bg-red-400" />
                Forensic workspace
              </div>

              <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Investigation{" "}
                <span className="bg-gradient-to-r from-red-300 via-orange-200 to-red-400 bg-clip-text text-transparent">
                  Overview
                </span>
              </h1>

              <p className="mt-3 max-w-3xl break-all text-xs text-zinc-500">
                <span className="text-zinc-400">RUN ID</span>
                <span className="mx-2 text-zinc-700">/</span>
                {runId || "Initializing investigation…"}
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-lg border border-white/[0.09] bg-black/30 px-3 py-2 text-xs text-zinc-400">
              <span className="relative flex h-2 w-2">
                {!isCompleted && !isFailed && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-50" />
                )}
                <span
                  className={`relative inline-flex h-2 w-2 rounded-full ${
                    isFailed
                      ? "bg-red-400"
                      : isCompleted
                        ? "bg-emerald-400"
                        : "bg-orange-400"
                  }`}
                />
              </span>
              {isCompleted
                ? "Pipeline completed"
                : isFailed
                  ? "Pipeline failed"
                  : "Live investigation"}
            </div>
          </div>
        </section>

        {/* Error */}
        {streamError && (
          <div
            role="alert"
            className="mb-6 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-950/30 p-4 text-sm text-red-200"
          >
            <span className="mt-0.5 font-semibold">!</span>
            <p className="break-words">{streamError}</p>
          </div>
        )}

        {/* Overview cards */}
        <section className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-white/[0.09] bg-[#111113]/85 p-4 backdrop-blur-md">
            <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Run identifier
            </p>
            <p className="mt-2 truncate font-mono text-sm text-zinc-200">
              {runId ? `${runId.slice(0, 18)}…` : "—"}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              Current investigation
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.09] bg-[#111113]/85 p-4 backdrop-blur-md">
            <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Stream events
            </p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-zinc-100">
              {events.length}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              Events received by the dashboard
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.09] bg-[#111113]/85 p-4 backdrop-blur-md">
            <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Result availability
            </p>
            <p className="mt-2 text-sm font-medium text-zinc-100">
              {result !== null ? "Result available" : resultStatus}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              Automatically refreshed from backend
            </p>
          </div>
        </section>

        {/* Main workspace */}
        <section className="grid min-w-0 grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
          {/* Agent activity */}
          <section className="min-w-0 overflow-hidden rounded-2xl border border-white/[0.10] bg-[#0d0d0f]/95 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-5 py-4 sm:px-6">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-red-400/15 bg-red-500/[0.08]">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="h-[18px] w-[18px] text-red-300"
                    stroke="currentColor"
                    strokeWidth="1.7"
                  >
                    <path
                      d="M12 3v3m0 12v3M3 12h3m12 0h3M5.64 5.64l2.12 2.12m8.48 8.48 2.12 2.12m0-12.72-2.12 2.12m-8.48 8.48-2.12 2.12"
                      strokeLinecap="round"
                    />
                    <circle cx="12" cy="12" r="4" />
                  </svg>
                </div>

                <div>
                  <h2 className="text-sm font-semibold text-zinc-100">
                    Agent Activity
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Real-time investigation timeline
                  </p>
                </div>
              </div>

              <span className="inline-flex items-center gap-2 rounded-md border border-red-400/15 bg-red-500/[0.07] px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.12em] text-red-300">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    isCompleted
                      ? "bg-emerald-400"
                      : isFailed
                        ? "bg-red-400"
                        : "animate-pulse bg-red-400"
                  }`}
                />
                SSE Stream
              </span>
            </div>

            <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-2.5 text-[10px] uppercase tracking-[0.12em] text-zinc-600 sm:px-6">
              <span>Event log</span>
              <span>{events.length} events</span>
            </div>

            <div className="h-[min(68vh,760px)] min-h-[400px] space-y-3 overflow-y-auto p-4 sm:p-5">
              {events.length === 0 && (
                <div className="flex min-h-[340px] flex-col items-center justify-center text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.025]">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      className="h-5 w-5 text-zinc-500"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <circle cx="12" cy="12" r="9" />
                      <path
                        d="M12 7v5l3 2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <p className="mt-4 text-sm text-zinc-300">
                    Waiting for agent events
                  </p>
                  <p className="mt-1 max-w-xs text-xs leading-5 text-zinc-600">
                    Live reasoning and investigation events will appear here.
                  </p>
                </div>
              )}

              {events.map((event, index) => {
                const isToken = event.type === "llm_token";
                const isError = event.type === "error";
                const isStatus =
                  event.type === "status" ||
                  event.type === "completed";

                return (
                  <article
                    key={`${event.timestamp ?? "event"}-${index}`}
                    className={`min-w-0 rounded-xl border p-4 ${
                      isError
                        ? "border-red-400/20 bg-red-950/20"
                        : isToken
                          ? "border-red-400/[0.12] bg-red-500/[0.035]"
                          : "border-white/[0.07] bg-white/[0.02]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                            isError
                              ? "bg-red-400"
                              : isToken
                                ? "bg-orange-300"
                                : isStatus
                                  ? "bg-emerald-400"
                                  : "bg-zinc-500"
                          }`}
                        />
                        <span
                          className={`break-words text-[10px] font-semibold uppercase tracking-[0.12em] ${
                            isError
                              ? "text-red-300"
                              : isToken
                                ? "text-orange-200"
                                : "text-zinc-400"
                          }`}
                        >
                          {event.type.replaceAll("_", " ")}
                        </span>
                      </div>

                      {event.timestamp && (
                        <time className="shrink-0 font-mono text-[10px] text-zinc-600">
                          {formatTime(event.timestamp)}
                        </time>
                      )}
                    </div>

                    <pre
                      className={`mt-3 whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] leading-[1.85] ${
                        isError ? "text-red-200" : "text-zinc-300"
                      }`}
                    >
                      {eventText(event)}
                    </pre>
                  </article>
                );
              })}

              <div ref={bottomRef} />
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-white/[0.07] px-5 py-3 text-[10px] text-zinc-600 sm:px-6">
              <span>Live event stream</span>
              <span>
                {isCompleted
                  ? "Stream completed"
                  : isFailed
                    ? "Investigation ended with an error"
                    : "Listening for events"}
              </span>
            </div>
          </section>

          {/* Investigation results */}
          <section className="min-w-0 overflow-hidden rounded-2xl border border-white/[0.10] bg-[#0d0d0f]/95 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-5 py-4 sm:px-6">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-orange-300/15 bg-orange-400/[0.07]">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="h-[18px] w-[18px] text-orange-200"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  >
                    <path
                      d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M14 3v6h5M9 13h6M9 17h6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>

                <div>
                  <h2 className="text-sm font-semibold text-zinc-100">
                    Investigation Results
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Backend analysis output
                  </p>
                </div>
              </div>

              <span
                className={`rounded-md border px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.1em] ${
                  result !== null
                    ? "border-emerald-400/15 bg-emerald-400/[0.06] text-emerald-300"
                    : "border-white/[0.08] bg-white/[0.025] text-zinc-500"
                }`}
              >
                {result !== null ? "Available" : "Pending"}
              </span>
            </div>

            <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] px-5 py-3 sm:px-6">
              <div>
                <p className="text-xs font-medium text-zinc-300">
                  Analysis payload
                </p>
                <p className="mt-1 text-[10px] text-zinc-600">
                  {result !== null
                    ? "Latest result returned by the backend"
                    : resultStatus}
                </p>
              </div>

              {result !== null && (
                <button
                  type="button"
                  onClick={() => setShowRawResult((value) => !value)}
                  className="shrink-0 rounded-lg border border-white/[0.10] bg-white/[0.03] px-3 py-2 text-[10px] font-medium text-zinc-300 transition hover:border-red-400/30 hover:bg-red-400/[0.06] hover:text-white"
                >
                  {showRawResult ? "Hide JSON" : "View JSON"}
                </button>
              )}
            </div>

            <div className="h-[min(68vh,760px)] min-h-[400px] overflow-y-auto p-4 sm:p-5">
              {result === null ? (
                <div className="flex min-h-[340px] flex-col items-center justify-center text-center">
                  <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.025]">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/[0.08] border-t-red-400" />
                  </div>

                  <p className="mt-5 text-sm font-medium text-zinc-200">
                    Waiting for investigation results
                  </p>

                  <p className="mt-2 max-w-xs text-xs leading-5 text-zinc-600">
                    The dashboard checks the backend automatically and will
                    display the result as soon as it becomes available.
                  </p>

                  <div className="mt-6 w-full max-w-xs rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-left">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-[10px] uppercase tracking-wider text-zinc-600">
                        Backend status
                      </span>
                      <span className="text-[10px] text-zinc-400">
                        {resultStatus}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[0.035] p-4">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-300">
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          className="h-3.5 w-3.5"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path
                            d="m5 12 4 4L19 6"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>

                      <p className="text-xs font-medium text-emerald-200">
                        Backend result received
                      </p>
                    </div>

                    <p className="mt-2 text-xs leading-5 text-zinc-400">
                      The investigation output is available below. Expand the
                      raw JSON when you need to inspect the complete payload.
                    </p>
                  </div>

                  {showRawResult ? (
                    <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-xl border border-white/[0.08] bg-black/30 p-4 font-mono text-[11px] leading-[1.85] text-zinc-300">
                      {prettyJSON(result)}
                    </pre>
                  ) : (
                    <div className="space-y-3">
                      {typeof result === "object" &&
                      result !== null &&
                      !Array.isArray(result) ? (
                        Object.entries(
                          result as Record<string, unknown>,
                        ).map(([key, value]) => (
                          <div
                            key={key}
                            className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4"
                          >
                            <p className="break-words text-[10px] font-semibold uppercase tracking-[0.12em] text-red-300/90">
                              {key.replaceAll("_", " ")}
                            </p>

                            <pre className="mt-2 whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] leading-[1.8] text-zinc-300">
                              {typeof value === "string"
                                ? value
                                : prettyJSON(value)}
                            </pre>
                          </div>
                        ))
                      ) : (
                        <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-xl border border-white/[0.07] bg-white/[0.02] p-4 font-mono text-[11px] leading-[1.8] text-zinc-300">
                          {typeof result === "string"
                            ? result
                            : prettyJSON(result)}
                        </pre>
                      )}

                      <button
                        type="button"
                        onClick={() => setShowRawResult(true)}
                        className="w-full rounded-lg border border-white/[0.08] bg-white/[0.025] px-4 py-3 text-xs text-zinc-400 transition hover:border-red-400/25 hover:text-zinc-100"
                      >
                        Inspect complete raw JSON →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-white/[0.07] px-5 py-3 text-[10px] text-zinc-600 sm:px-6">
              <span>Investigation output</span>
              <span>{result !== null ? "Data received" : "Auto-refresh enabled"}</span>
            </div>
          </section>
        </section>

        {/* Footer */}
        <footer className="mt-8 flex flex-col gap-3 border-t border-white/[0.08] pt-5 text-[10px] uppercase tracking-[0.12em] text-zinc-600 sm:flex-row sm:items-center sm:justify-between">
          <span>
            <span className="text-zinc-400">SYBILTRACE</span>
            {" "}· On-chain forensics
          </span>
          <span>Investigate with evidence. Not assumptions.</span>
        </footer>
      </div>
    </main>
  );
}
