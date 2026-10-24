
"use client";

import { useEffect, useRef } from "react";
import type { InvestigationEvent } from "@/lib/api/investigation-stream";
import ActivityEvent from "./activity-event";

type AgentActivityPanelProps = {
  events: InvestigationEvent[];
  isCompleted: boolean;
  isFailed: boolean;
};

export default function AgentActivityPanel({
  events,
  isCompleted,
  isFailed,
}: AgentActivityPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    const container = containerRef.current;

    if (container && autoScrollRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [events]);

  function handleScroll() {
    const container = containerRef.current;
    if (!container) return;

    const distanceFromBottom =
      container.scrollHeight -
      container.scrollTop -
      container.clientHeight;

    autoScrollRef.current = distanceFromBottom < 100;
  }

  const streamColor = isFailed
    ? "bg-red-400"
    : isCompleted
      ? "bg-emerald-400"
      : "animate-pulse bg-red-400";

  return (
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
          <span className={`h-1.5 w-1.5 rounded-full ${streamColor}`} />
          SSE Stream
        </span>
      </div>

      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-2.5 text-[10px] uppercase tracking-[0.12em] text-zinc-600 sm:px-6">
        <span>Event log</span>
        <span>{events.length} events</span>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-[min(68vh,760px)] min-h-[400px] space-y-3 overflow-y-auto p-4 sm:p-5"
      >
        {events.length === 0 ? (
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
        ) : (
          events.map((event, index) => (
            <ActivityEvent
              key={`${event.timestamp ?? "event"}-${index}`}
              event={event}
            />
          ))
        )}
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
  );
}
