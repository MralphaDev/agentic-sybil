
type DashboardStatCardsProps = {
  runId: string;
  eventCount: number;
  resultAvailable: boolean;
  resultStatus: string;
};

export default function DashboardStatCards({
  runId,
  eventCount,
  resultAvailable,
  resultStatus,
}: DashboardStatCardsProps) {
  const cards = [
    {
      label: "Run identifier",
      value: runId ? `${runId.slice(0, 18)}…` : "—",
      description: "Current investigation",
      className: "font-mono text-sm text-zinc-200",
    },
    {
      label: "Stream events",
      value: String(eventCount),
      description: "Events received by the dashboard",
      className: "text-2xl font-semibold tabular-nums text-zinc-100",
    },
    {
      label: "Result availability",
      value: resultAvailable ? "Result available" : resultStatus,
      description: "Automatically refreshed from backend",
      className: "text-sm font-medium text-zinc-100",
    },
  ];

  return (
    <section className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-white/[0.09] bg-[#111113]/85 p-4 backdrop-blur-md"
        >
          <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
            {card.label}
          </p>
          <p className={`mt-2 truncate ${card.className}`}>
            {card.value}
          </p>
          <p className="mt-1 text-xs text-zinc-600">
            {card.description}
          </p>
        </div>
      ))}
    </section>
  );
}
