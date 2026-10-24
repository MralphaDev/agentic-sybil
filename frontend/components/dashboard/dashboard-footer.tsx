
export default function DashboardFooter() {
  return (
    <footer className="mt-8 flex flex-col gap-3 border-t border-white/[0.08] pt-5 text-[10px] uppercase tracking-[0.12em] text-zinc-600 sm:flex-row sm:items-center sm:justify-between">
      <span>
        <span className="text-zinc-400">SYBILTRACE</span>
        {" "}· On-chain forensics
      </span>

      <span>Investigate with evidence. Not assumptions.</span>
    </footer>
  );
}
