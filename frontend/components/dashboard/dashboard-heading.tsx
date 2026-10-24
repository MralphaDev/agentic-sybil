
type DashboardHeadingProps = {
  runId: string;
  isCompleted: boolean;
  isFailed: boolean;
};

export default function DashboardHeading({
  runId,
  isCompleted,
  isFailed,
}: DashboardHeadingProps) {
  const indicatorColor = isFailed
    ? "bg-red-400"
    : isCompleted
      ? "bg-emerald-400"
      : "bg-orange-400";

  const pipelineLabel = isCompleted
    ? "Pipeline completed"
    : isFailed
      ? "Pipeline failed"
      : "Live investigation";

  return (
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
              className={`relative inline-flex h-2 w-2 rounded-full ${indicatorColor}`}
            />
          </span>
          {pipelineLabel}
        </div>
      </div>
    </section>
  );
}
