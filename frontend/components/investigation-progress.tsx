"use client";

export type PipelineStage = {
  step: string;
  title: string;
  detail: string;
  state: "running" | "finished" | "failed";
  elapsed_seconds?: number;
};

type InvestigationProgressProps = {
  stages: PipelineStage[];
  backendStatus: string;
  failed: boolean;
};

export default function InvestigationProgress({
  stages,
  backendStatus,
  failed,
}: InvestigationProgressProps) {
  const activeStage = [...stages]
    .reverse()
    .find((stage) => stage.state === "running");

  const latestStage = stages[stages.length - 1];

  return (
    <div className="min-h-[340px] space-y-5 py-2">
      <div className="flex items-start gap-4">
        <div className="relative mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-red-400/15 bg-red-500/[0.06]">
          {failed ? (
            <span className="text-lg font-semibold text-red-300">!</span>
          ) : activeStage ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
          ) : stages.length > 0 &&
            stages.every((stage) => stage.state === "finished") ? (
            <span className="text-lg text-emerald-300">✓</span>
          ) : (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-zinc-200">
            {failed
              ? "Investigation failed"
              : activeStage?.title ??
                latestStage?.title ??
                "Preparing investigation results"}
          </p>

          <p className="mt-2 text-xs leading-5 text-zinc-500">
            {failed
              ? "The backend reported an error while processing this investigation."
              : activeStage?.detail ??
                (stages.length === 0
                  ? "Waiting for the backend to start reporting progress."
                  : "The backend is finalizing the investigation results.")}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] uppercase tracking-wider text-zinc-600">
            Backend status
          </span>
          <span className="max-w-[65%] truncate text-right text-[10px] text-zinc-400">
            {backendStatus}
          </span>
        </div>
      </div>

      {stages.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-500">
              Pipeline progress
            </p>
            <p className="text-[10px] tabular-nums text-zinc-600">
              {stages.filter((stage) => stage.state === "finished").length}
              {" / "}
              {stages.length} steps completed
            </p>
          </div>

          <div className="space-y-2">
            {stages.map((stage) => (
              <div
                key={stage.step}
                className={`flex items-start gap-3 rounded-xl border p-3 transition-colors ${
                  stage.state === "running"
                    ? "border-red-400/20 bg-red-500/[0.045]"
                    : stage.state === "failed"
                      ? "border-red-400/20 bg-red-950/20"
                      : "border-white/[0.06] bg-white/[0.015]"
                }`}
              >
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
                  {stage.state === "running" ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
                  ) : stage.state === "finished" ? (
                    <span className="text-sm text-emerald-400">✓</span>
                  ) : (
                    <span className="text-sm font-semibold text-red-400">
                      !
                    </span>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p
                    className={`text-xs font-medium ${
                      stage.state === "running"
                        ? "text-red-200"
                        : stage.state === "failed"
                          ? "text-red-300"
                          : "text-zinc-300"
                    }`}
                  >
                    {stage.title}
                  </p>

                  <p className="mt-1 text-[11px] leading-5 text-zinc-500">
                    {stage.detail}
                  </p>
                </div>

                {stage.elapsed_seconds !== undefined && (
                  <span className="shrink-0 pt-0.5 font-mono text-[10px] text-zinc-600">
                    {stage.elapsed_seconds.toFixed(2)}s
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}