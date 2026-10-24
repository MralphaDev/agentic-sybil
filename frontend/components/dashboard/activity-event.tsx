
import type { InvestigationEvent } from "@/lib/api/investigation-stream";

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

type ActivityEventProps = {
  event: InvestigationEvent;
};

export default function ActivityEvent({ event }: ActivityEventProps) {
  const isToken = event.type === "llm_token";
  const isError = event.type === "error";
  const isStatus =
    event.type === "status" || event.type === "completed";

  const cardStyle = isError
    ? "border-red-400/20 bg-red-950/20"
    : isToken
      ? "border-red-400/[0.12] bg-red-500/[0.035]"
      : "border-white/[0.07] bg-white/[0.02]";

  const dotStyle = isError
    ? "bg-red-400"
    : isToken
      ? "bg-orange-300"
      : isStatus
        ? "bg-emerald-400"
        : "bg-zinc-500";

  const labelStyle = isError
    ? "text-red-300"
    : isToken
      ? "text-orange-200"
      : "text-zinc-400";

  return (
    <article
      className={`min-w-0 rounded-xl border p-4 ${cardStyle}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${dotStyle}`}
          />
          <span
            className={`break-words text-[10px] font-semibold uppercase tracking-[0.12em] ${labelStyle}`}
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
}
