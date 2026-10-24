"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, GitBranch, Activity, Users, Repeat2, TrendingUp } from "lucide-react";

type AnyRecord = Record<string, unknown>;
type Payload = { analysis?: { process_mining_result?: AnyRecord } };

function record(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
}
function array(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }
function number(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}
function label(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number") return value.toLocaleString();
  if (value === null || value === undefined) return "—";
  return JSON.stringify(value);
}
function pretty(key: string) { return key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()); }

function Metric({ title, value, note, icon: Icon }: { title: string; value: string; note: string; icon: typeof Activity }) {
  return <div className="rounded-xl border border-white/[0.09] bg-[#0b0c10]/90 p-4"><div className="flex items-center justify-between"><span className="text-[10px] tracking-[0.16em] text-zinc-500">{title}</span><Icon size={15} className="text-red-300/70" /></div><p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p><p className="mt-1 text-[11px] text-zinc-600">{note}</p></div>;
}

export default function ProcessMiningPage() {
  const [data, setData] = useState<AnyRecord>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (!runId) { setError("No investigation run found. Start a forensic investigation first."); setLoading(false); return; }
    fetch(`/backend/api/investigations/result/${encodeURIComponent(runId)}`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load Process Mining results.");
        const result = await response.json();
        const payload = (result.result ?? result) as Payload;
        setData(record(payload.analysis?.process_mining_result));
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Failed to load Process Mining data."))
      .finally(() => setLoading(false));
  }, []);

  const topVariants = array(data.top_variants);
  const dfg = record(data.stochastic_dfg);
  const dfgEdges = array(dfg.edges ?? dfg.transitions ?? data.dfg);
  const concentration = record(data.first_activity_concentration);
  const intermediaries = record(data.intermediary_analysis);
  const coordinated = record(data.coordinated_intermediary_analysis);
  const seller = record(data.seller_behavior);
  const variants = array(data.variants);
  const clusters = record(data.clustering);
  const transitionRows = useMemo(() => dfgEdges.slice(0, 14).map((item) => record(item)), [data]);
  const maxVariant = Math.max(1, ...topVariants.map((item) => number(record(item).count ?? record(item).wallet_count ?? record(item).frequency) ?? 0));

  return <main className="relative min-h-screen overflow-hidden bg-[#07080b] text-zinc-100">
    <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(127,29,29,0.15),transparent_58%)]" />
    <header className="relative z-10 flex items-center justify-between border-b border-white/[0.08] px-5 py-4 md:px-8">
      <div className="flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-white/10 bg-white/[0.03] p-2 text-zinc-400 hover:text-white"><ArrowLeft size={17}/></Link><div><p className="text-[10px] tracking-[0.24em] text-red-300">SYBILTRACE / BEHAVIORAL INTELLIGENCE</p><h1 className="mt-1 text-lg font-semibold">Process Mining Dashboard</h1></div></div>
      <span className="hidden text-[10px] tracking-[0.16em] text-zinc-600 sm:block">EVENT LOG · DIRECTLY-FOLLOWS · VARIANTS</span>
    </header>
    <div className="relative z-10 mx-auto max-w-[1600px] space-y-6 p-5 md:p-8">
      <div><p className="text-xs uppercase tracking-[0.22em] text-zinc-500">Behavioral analysis</p><h2 className="mt-2 text-3xl font-semibold tracking-tight">How wallets behave — and where patterns repeat.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">Explore the action sequences, repeated variants, and intermediary behavior extracted from the current investigation. Values below are read from the backend result payload.</p></div>
      {error && <div className="rounded-xl border border-red-500/20 bg-red-500/[0.06] p-4 text-sm text-red-200">{error}</div>}
      {loading ? <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500"><span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-red-500/20 border-t-red-400" />Loading process evidence…</div> : <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric title="DISTINCT VARIANTS" value={String(variants.length || "—")} note="Unique wallet action sequences" icon={GitBranch}/>
          <Metric title="VARIANT CLUSTERS" value={label(array(clusters.clusters).length || number(clusters.cluster_count) || "—")} note="Behavioral groups returned by analysis" icon={Users}/>
          <Metric title="INTERMEDIARY WALLETS" value={label(array(intermediaries.wallets).length || number(intermediaries.count) || "—")} note="Potential asset relays" icon={Repeat2}/>
          <Metric title="COORDINATED RELAYS" value={label(array(coordinated.wallets).length || number(coordinated.count) || "—")} note="Intermediary activity within a short time gap" icon={TrendingUp}/>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,.8fr)]">
          <div className="rounded-2xl border border-white/[0.09] bg-[#0b0c10]/90 p-5">
            <div className="mb-5 flex items-center gap-2"><GitBranch size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">Most common wallet variants</h3><p className="mt-1 text-xs text-zinc-600">Repeated action sequences across wallets</p></div></div>
            {topVariants.length ? <div className="space-y-4">{topVariants.slice(0, 12).map((item, index) => {
              const row = record(item); const variant = row.variant ?? row.sequence ?? row.actions ?? row.name ?? `Variant ${index + 1}`; const count = number(row.count ?? row.wallet_count ?? row.frequency) ?? 0;
              return <div key={index}><div className="mb-1.5 flex items-center justify-between gap-3 text-xs"><span className="min-w-0 truncate text-zinc-300">{label(variant)}</span><span className="shrink-0 font-mono text-zinc-500">{count ? count.toLocaleString() : label(row.count ?? row.wallet_count ?? "—")}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/[0.05]"><div className="h-full rounded-full bg-gradient-to-r from-red-600 to-orange-300" style={{ width: `${Math.max(3, count / maxVariant * 100)}%` }}/></div></div>;
            })}</div> : <Empty text="Top variant details are not present in the returned payload."/>}
          </div>
          <div className="rounded-2xl border border-white/[0.09] bg-[#0b0c10]/90 p-5">
            <div className="mb-4 flex items-center gap-2"><Activity size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">First-activity concentration</h3><p className="mt-1 text-xs text-zinc-600">Temporal concentration evidence</p></div></div>
            {Object.keys(concentration).length ? <div className="space-y-3">{Object.entries(concentration).slice(0, 10).map(([key, value]) => <div key={key} className="flex items-start justify-between gap-4 border-b border-white/[0.05] pb-2"><span className="text-xs text-zinc-500">{pretty(key)}</span><span className="max-w-[65%] break-all text-right font-mono text-xs text-zinc-200">{label(value)}</span></div>)}</div> : <Empty text="No first-activity concentration summary was returned."/>}
          </div>
        </section>

        <section className="rounded-2xl border border-white/[0.09] bg-[#0b0c10]/90 p-5">
          <div className="mb-5 flex items-center gap-2"><Activity size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">Directly-follows transitions</h3><p className="mt-1 text-xs text-zinc-600">Observed transitions between wallet actions</p></div></div>
          {transitionRows.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{transitionRows.map((row, index) => <div key={index} className="rounded-xl border border-white/[0.07] bg-black/20 p-3"><div className="flex items-center gap-2"><span className="rounded-md border border-red-500/20 bg-red-500/[0.08] px-2 py-1 text-[10px] text-red-200">{label(row.source ?? row.from ?? row.start ?? row.activity)}</span><span className="text-zinc-700">→</span><span className="rounded-md border border-sky-500/20 bg-sky-500/[0.06] px-2 py-1 text-[10px] text-sky-200">{label(row.target ?? row.to ?? row.end ?? row.next_activity)}</span></div><div className="mt-3 flex justify-between text-[10px] text-zinc-600"><span>Frequency: {label(row.count ?? row.frequency ?? row.weight)}</span><span>Probability: {label(row.probability ?? row.transition_probability)}</span></div></div>)}</div> : <Empty text="Transition details are not available in the current result shape."/>}
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          {[["Intermediary analysis", intermediaries], ["Seller behavior", seller], ["Coordinated intermediary analysis", coordinated], ["Token handoff analysis", record(data.intermediary_handoff_analysis)]].map(([title, value]) => {
            const obj = record(value);
            return <div key={String(title)} className="rounded-2xl border border-white/[0.09] bg-[#0b0c10]/90 p-5"><h3 className="text-sm font-semibold">{String(title)}</h3><div className="mt-4 space-y-2">{Object.entries(obj).slice(0, 8).map(([key, item]) => <div key={key} className="flex items-start justify-between gap-3 border-b border-white/[0.05] pb-2"><span className="text-xs text-zinc-500">{pretty(key)}</span><span className="max-w-[68%] break-all text-right font-mono text-[11px] text-zinc-300">{label(item)}</span></div>)}{!Object.keys(obj).length && <Empty text="No details returned for this analysis."/>}</div></div>;
          })}
        </section>
      </>}
    </div>
  </main>;
}

function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-xs leading-5 text-zinc-600">{text}</div>; }
