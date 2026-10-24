
type DashboardHeaderProps = {
  status: string;
  isCompleted: boolean;
  isFailed: boolean;
};

export default function DashboardHeader({
  status,
  isCompleted,
  isFailed,
}: DashboardHeaderProps) {
  const indicatorColor = isFailed
    ? "bg-red-400"
    : isCompleted
      ? "bg-emerald-400"
      : "animate-pulse bg-orange-400";

  const textColor = isFailed
    ? "text-red-300"
    : isCompleted
      ? "text-emerald-300"
      : "text-orange-200";

  return (
    <header className="flex min-h-[76px] items-center justify-between gap-4 border-b border-white/[0.09]">
      <a href="/" className="flex items-center gap-3">
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
        <span className={`h-2 w-2 rounded-full ${indicatorColor}`} />

        <div className="text-right">
          <p className="text-[10px] uppercase tracking-[0.17em] text-zinc-500">
            Investigation status
          </p>
          <p
            className={`mt-1 max-w-[220px] truncate text-xs font-medium ${textColor}`}
          >
            {status}
          </p>
        </div>
      </div>
    </header>
  );
}
