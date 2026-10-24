
type ResultContentProps = {
  result: unknown;
  showRawResult: boolean;
  onShowRawResult: () => void;
};

function prettyJSON(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function formatValue(value: unknown) {
  return typeof value === "string" ? value : prettyJSON(value);
}

export default function ResultContent({
  result,
  showRawResult,
  onShowRawResult,
}: ResultContentProps) {
  if (showRawResult) {
    return (
      <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-xl border border-white/[0.08] bg-black/30 p-4 font-mono text-[11px] leading-[1.85] text-zinc-300">
        {prettyJSON(result)}
      </pre>
    );
  }

  if (
    typeof result === "object" &&
    result !== null &&
    !Array.isArray(result)
  ) {
    return (
      <div className="space-y-3">
        {Object.entries(result as Record<string, unknown>).map(
          ([key, value]) => (
            <div
              key={key}
              className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4"
            >
              <p className="break-words text-[10px] font-semibold uppercase tracking-[0.12em] text-red-300/90">
                {key.replaceAll("_", " ")}
              </p>

              <pre className="mt-2 whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] leading-[1.8] text-zinc-300">
                {formatValue(value)}
              </pre>
            </div>
          ),
        )}

        <button
          type="button"
          onClick={onShowRawResult}
          className="w-full rounded-lg border border-white/[0.08] bg-white/[0.025] px-4 py-3 text-xs text-zinc-400 transition hover:border-red-400/25 hover:text-zinc-100"
        >
          Inspect complete raw JSON →
        </button>
      </div>
    );
  }

  return (
    <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-xl border border-white/[0.07] bg-white/[0.02] p-4 font-mono text-[11px] leading-[1.8] text-zinc-300">
      {formatValue(result)}
    </pre>
  );
}
