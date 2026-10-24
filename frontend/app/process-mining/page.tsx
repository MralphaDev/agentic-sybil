"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, GitBranch, Activity, Users, Repeat2, TrendingUp, Filter, Network } from "lucide-react";

type AnyRecord = Record<string, unknown>;
type Edge = { source: string; target: string; count: number; transition_probability?: number; probability?: number };
type Dfg = { edges?: Edge[]; start_activities?: Record<string, number>; end_activities?: Record<string, number>; statistics?: AnyRecord; filtering_statistics?: AnyRecord };
type Payload = { analysis?: { process_mining_result?: AnyRecord } };
const record = (value: unknown): AnyRecord => value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
const array = (value: unknown): unknown[] => Array.isArray(value) ? value : [];
const number = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : typeof value === "string" && value.trim() && Number.isFinite(Number(value)) ? Number(value) : null;
const pretty = (key: string) => key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
const label = (value: unknown): string => typeof value === "string" ? value : typeof value === "number" ? value.toLocaleString() : typeof value === "boolean" ? (value ? "Yes" : "No") : Array.isArray(value) ? value.filter((item) => typeof item === "string").join(" → ") || "Sequence details unavailable" : value == null ? "—" : "Details available";

function Metric({ title, value, note, icon: Icon }: { title: string; value: string; note: string; icon: typeof Activity }) {
  return <div className="rounded-xl border border-white/[.09] bg-[#0b0c10]/90 p-4"><div className="flex items-center justify-between"><span className="text-[10px] tracking-[.16em] text-zinc-500">{title}</span><Icon size={15} className="text-red-300/70"/></div><p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p><p className="mt-1 text-[11px] text-zinc-600">{note}</p></div>;
}
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-xs leading-5 text-zinc-600">{text}</div>; }

function DfgDiagram({ dfg, title, description }: { dfg: Dfg; title: string; description: string }) {
  const edges = (dfg.edges ?? []).filter((edge) => edge && typeof edge.source === "string" && typeof edge.target === "string");
  const starts = dfg.start_activities ?? {};
  const ends = dfg.end_activities ?? {};
  const graph = useMemo(() => {
    const names = new Set<string>();
    edges.forEach((edge) => { names.add(edge.source); names.add(edge.target); });
    Object.keys(starts).forEach((name) => names.add(name));
    Object.keys(ends).forEach((name) => names.add(name));
    const activities = [...names];
    if (!activities.length) return { nodes: [] as { id: string; x: number; y: number; rank: number; start: number; end: number }[], maxCount: 1, maxRank: 0 };
    const incoming = new Map(activities.map((name) => [name, 0]));
    const outgoing = new Map(activities.map((name) => [name, 0]));
    edges.forEach((edge) => { incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + edge.count); outgoing.set(edge.source, (outgoing.get(edge.source) ?? 0) + edge.count); });
    const ranks = new Map(activities.map((name) => [name, (incoming.get(name) ?? 0) === 0 ? 0 : 0]));
    // Longest-path relaxation creates a readable left-to-right process layout; cycles are bounded.
    for (let pass = 0; pass < Math.min(activities.length, 8); pass++) {
      let changed = false;
      edges.forEach((edge) => { const next = Math.min(5, (ranks.get(edge.source) ?? 0) + 1); if (next > (ranks.get(edge.target) ?? 0) && edge.target !== edge.source) { ranks.set(edge.target, next); changed = true; } });
      if (!changed) break;
    }
    const maxRank = Math.max(0, ...ranks.values());
    const buckets = new Map<number, string[]>();
    activities.forEach((name) => { const rank = ranks.get(name) ?? 0; buckets.set(rank, [...(buckets.get(rank) ?? []), name]); });
    const positions = new Map<string, { x: number; y: number; rank: number }>();
    for (const [rank, items] of buckets) {
      items.sort((a, b) => (incoming.get(b) ?? 0) + (outgoing.get(b) ?? 0) - ((incoming.get(a) ?? 0) + (outgoing.get(a) ?? 0)));
      items.forEach((name, index) => positions.set(name, { x: 95 + rank * (maxRank > 0 ? 210 : 0), y: 82 + (index + 1) * (Math.max(100, items.length * 68) / (items.length + 1)), rank }));
    }
    const nodes = activities.map((id) => { const p = positions.get(id)!; return { id, ...p, start: number(starts[id]) ?? 0, end: number(ends[id]) ?? 0 }; });
    return { nodes, maxCount: Math.max(1, ...edges.map((edge) => edge.count)), maxRank };
  }, [dfg]);
  if (!edges.length) return <div className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-zinc-600">{description}</p><div className="mt-5"><Empty text="No transitions remain in this DFG. Check event mapping and the frequency filter."/></div></div>;
  const nodeMap = new Map(graph.nodes.map((node) => [node.id, node]));
  const height = Math.max(360, ...graph.nodes.map((node) => node.y + 80));
  const width = Math.max(800, 190 + graph.maxRank * 210);
  const minCount = Math.min(...edges.map((edge) => edge.count));
  return <section className="overflow-hidden rounded-2xl border border-white/[.09] bg-[#0b0c10]/95">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[.07] p-5"><div className="flex items-center gap-2"><Network size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-zinc-600">{description}</p></div></div><div className="flex gap-3 text-[10px] text-zinc-500"><span>{graph.nodes.length} activities</span><span>{edges.length} transitions</span><span>Min edge {minCount}</span></div></div>
    <div className="overflow-x-auto bg-[radial-gradient(ellipse_at_50%_0%,rgba(127,29,29,.08),transparent_65%)]">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto min-h-[360px] w-full min-w-[800px]" role="img" aria-label={title}>
        <defs><marker id="dfg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f87171"/></marker><linearGradient id="dfg-edge"><stop offset="0%" stopColor="#f87171" stopOpacity=".35"/><stop offset="100%" stopColor="#fb7185" stopOpacity=".8"/></linearGradient></defs>
        {edges.map((edge, index) => {
          const a = nodeMap.get(edge.source), b = nodeMap.get(edge.target); if (!a || !b) return null;
          const same = a.id === b.id;
          const strokeWidth = 1 + Math.sqrt(edge.count / graph.maxCount) * 4;
          const path = same ? `M ${a.x + 48} ${a.y - 8} C ${a.x + 105} ${a.y - 65}, ${a.x + 105} ${a.y + 65}, ${a.x + 48} ${a.y + 8}` : `M ${a.x + 58} ${a.y} C ${a.x + 105} ${a.y}, ${b.x - 105} ${b.y}, ${b.x - 58} ${b.y}`;
          const mx = same ? a.x + 100 : (a.x + b.x) / 2;
          const my = same ? a.y - 38 : (a.y + b.y) / 2 - 8;
          return <g key={`${edge.source}-${edge.target}-${index}`}><path d={path} fill="none" stroke="url(#dfg-edge)" strokeWidth={strokeWidth} strokeOpacity=".78" markerEnd="url(#dfg-arrow)"/><rect x={mx - 24} y={my - 10} width="48" height="19" rx="6" fill="#111116" stroke="#7f1d1d" strokeOpacity=".6"/><text x={mx} y={my + 3.5} textAnchor="middle" fontSize="10" fill="#fecaca" fontFamily="ui-monospace,monospace">{edge.count.toLocaleString()}</text></g>;
        })}
        {graph.nodes.map((node) => {
          const inCount = edges.filter((edge) => edge.target === node.id).reduce((sum, edge) => sum + edge.count, 0);
          const outCount = edges.filter((edge) => edge.source === node.id).reduce((sum, edge) => sum + edge.count, 0);
          return <g key={node.id}>
            {node.start > 0 && <g><rect x={node.x - 68} y={node.y - 16} width="54" height="32" rx="16" fill="#0b211a" stroke="#34d399" strokeOpacity=".55"/><text x={node.x - 41} y={node.y + 3} textAnchor="middle" fontSize="9" fill="#a7f3d0">START {node.start}</text><path d={`M ${node.x - 14} ${node.y} L ${node.x - 5} ${node.y}`} stroke="#34d399" strokeWidth="1.5"/></g>}
            <rect x={node.x - 58} y={node.y - 25} width="116" height="50" rx="10" fill={node.id.toLowerCase().includes("sell") ? "#291015" : "#10131a"} stroke={node.id.toLowerCase().includes("sell") ? "#fb7185" : "#475569"} strokeWidth={node.id.toLowerCase().includes("sell") ? 1.6 : 1}/>
            <text x={node.x} y={node.y - 2} textAnchor="middle" fontSize="10" fontWeight="600" fill={node.id.toLowerCase().includes("sell") ? "#fda4af" : "#e2e8f0"}>{node.id.length > 18 ? node.id.slice(0, 17) + "…" : node.id}</text><text x={node.x} y={node.y + 13} textAnchor="middle" fontSize="9" fill="#64748b">{inCount} in · {outCount} out</text>
            {node.end > 0 && <g><path d={`M ${node.x + 58} ${node.y} L ${node.x + 67} ${node.y}`} stroke="#fbbf24" strokeWidth="1.5"/><rect x={node.x + 68} y={node.y - 16} width="48" height="32" rx="16" fill="#261d0b" stroke="#fbbf24" strokeOpacity=".6"/><text x={node.x + 92} y={node.y + 3} textAnchor="middle" fontSize="9" fill="#fde68a">END {node.end}</text></g>}
          </g>;
        })}
      </svg>
    </div>
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[.06] px-5 py-3 text-[10px] text-zinc-500"><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-emerald-400"/>Start activity</span><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-rose-400"/>Sell activity</span><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-amber-300"/>End activity</span><span>Edge thickness = transition frequency</span></div>
  </section>;
}

export default function ProcessMiningPage() {
  const [data, setData] = useState<AnyRecord>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dfgMode, setDfgMode] = useState<"filtered" | "raw">("filtered");
  useEffect(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (!runId) { setError("No investigation run found. Start a forensic investigation first."); setLoading(false); return; }
    fetch(`/backend/api/investigations/result/${encodeURIComponent(runId)}`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("Could not load Process Mining results."); const result = await response.json(); const payload = (result.result ?? result) as Payload; setData(record(payload.analysis?.process_mining_result)); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Failed to load Process Mining data."))
      .finally(() => setLoading(false));
  }, []);

  const topVariants = array(record(data.top_variants).top_variants ?? data.top_variants);
  const rawDfg = record(data.stochastic_dfg ?? data.dfg) as Dfg;
  const filteredDfg = record(data.filtered_dfg ?? record(data.dfg).filtered_dfg) as Dfg;
  const displayedDfg = dfgMode === "filtered" ? filteredDfg : rawDfg;
  const concentration = record(data.first_activity_concentration);
  const intermediaries = record(data.intermediary_analysis);
  const coordinated = record(data.coordinated_intermediary_analysis);
  const seller = record(data.seller_behavior);
  const variants = array(data.variants);
  const clusters = record(data.clustering);
  const maxVariant = Math.max(1, ...topVariants.map((item) => number(record(item).count ?? record(item).wallet_count ?? record(item).frequency) ?? 0));
  const rawEdges = (rawDfg.edges ?? []) as Edge[];
  const filteredEdges = (filteredDfg.edges ?? []) as Edge[];
  const rawSellEdges = rawEdges.filter((edge) => edge.source?.toLowerCase().includes("sell") || edge.target?.toLowerCase().includes("sell"));
  const filteredSellEdges = filteredEdges.filter((edge) => edge.source?.toLowerCase().includes("sell") || edge.target?.toLowerCase().includes("sell"));
  const sellWalletCount = number(seller.wallet_count ?? seller.count ?? array(seller.wallets).length);
  const mappedSellActions = number(record(data.action_counts).sell) ?? 0;

  return <main className="relative min-h-screen overflow-hidden bg-[#07080b] text-zinc-100">
    <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(127,29,29,.15),transparent_58%)]"/>
    <header className="relative z-10 flex items-center justify-between border-b border-white/[.08] px-5 py-4 md:px-8"><div className="flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-white/10 bg-white/[.03] p-2 text-zinc-400 hover:text-white"><ArrowLeft size={17}/></Link><div><p className="text-[10px] tracking-[.24em] text-red-300">SYBILTRACE / BEHAVIORAL INTELLIGENCE</p><h1 className="mt-1 text-lg font-semibold">Process Mining Dashboard</h1></div></div><span className="hidden text-[10px] tracking-[.16em] text-zinc-600 sm:block">EVENT LOG · DIRECTLY-FOLLOWS · VARIANTS</span></header>
    <div className="relative z-10 mx-auto max-w-[1700px] space-y-6 p-5 md:p-8">
      <div><p className="text-xs uppercase tracking-[.22em] text-zinc-500">Behavioral analysis</p><h2 className="mt-2 text-3xl font-semibold tracking-tight">How wallets behave — and where patterns repeat.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">The filtered DFG is the primary view: common, behaviorally meaningful transitions with noise reduced. Switch to raw DFG to inspect the full transition structure.</p></div>
      {error && <div className="rounded-xl border border-red-500/20 bg-red-500/[.06] p-4 text-sm text-red-200">{error}</div>}
      {loading ? <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500"><span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-red-500/20 border-t-red-400"/>Loading process evidence…</div> : <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric title="DISTINCT VARIANTS" value={String(variants.length || "—")} note="Unique wallet action sequences" icon={GitBranch}/>
          <Metric title="VARIANT CLUSTERS" value={label(array(clusters.clusters).length || number(clusters.cluster_count) || "—")} note="Behavioral groups returned by analysis" icon={Users}/>
          <Metric title="INTERMEDIARY WALLETS" value={label(array(intermediaries.wallets).length || number(intermediaries.count) || "—")} note="Potential asset relays" icon={Repeat2}/>
          <Metric title="SELLER WALLETS" value={label(sellWalletCount ?? "—")} note="Wallets identified by variant sell analysis" icon={TrendingUp}/>
        </section>

        <section className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-4 md:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><Filter size={15} className="text-red-300"/><div><h3 className="text-sm font-semibold">Directly-follows graph</h3><p className="mt-1 text-xs text-zinc-600">Activities are nodes; directed edges show how often one action directly follows another.</p></div></div><div className="flex rounded-xl border border-white/10 bg-black/30 p-1"><button onClick={() => setDfgMode("filtered")} className={`rounded-lg px-4 py-2 text-xs ${dfgMode === "filtered" ? "bg-red-500/15 text-red-200" : "text-zinc-500 hover:text-white"}`}>Filtered DFG</button><button onClick={() => setDfgMode("raw")} className={`rounded-lg px-4 py-2 text-xs ${dfgMode === "raw" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-white"}`}>Raw DFG</button></div></div>
          <DfgDiagram dfg={displayedDfg} title={dfgMode === "filtered" ? "Filtered directly-follows graph" : "Raw directly-follows graph"} description={dfgMode === "filtered" ? "Frequency threshold and low-value generic activities removed" : "All mapped activities and observed transitions after dust filtering"}/>
          <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-zinc-600"><span>Raw edges: {rawEdges.length}</span><span>Filtered edges: {filteredEdges.length}</span><span>Filtered sell-related edges: {filteredSellEdges.length}</span><span>Mapped sell actions: {mappedSellActions}</span></div>
          {rawSellEdges.length > 0 && filteredSellEdges.length === 0 && <p className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/[.05] p-3 text-xs leading-5 text-amber-100/80">Sell transitions exist in the raw DFG but were removed from the filtered graph. This usually means they fell below the current edge-frequency threshold, or their neighboring activities were excluded.</p>}
          {rawSellEdges.length === 0 && <p className="mt-3 rounded-lg border border-white/[.07] bg-white/[.02] p-3 text-xs leading-5 text-zinc-500">No sell-related transitions were found in the raw DFG. The backend mapped {mappedSellActions.toLocaleString()} events to the sell action. If that count is positive, sell may appear only as a start/end activity or the result payload may have an older DFG shape. If it is zero, inspect the target mint and swap token fields: a swap is labeled sell only when from_token matches the target token.</p>}
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,.8fr)]">
          <div className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><div className="mb-5 flex items-center gap-2"><GitBranch size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">Most common wallet variants</h3><p className="mt-1 text-xs text-zinc-600">Repeated action sequences across wallets</p></div></div>
            {topVariants.length ? <div className="space-y-4">{topVariants.slice(0, 12).map((item, index) => { const row = record(item); const variant = row.variant ?? row.sequence ?? row.actions ?? row.name ?? `Variant ${index + 1}`; const count = number(row.count ?? row.wallet_count ?? row.frequency) ?? 0; return <div key={index}><div className="mb-1.5 flex items-center justify-between gap-3 text-xs"><span className="min-w-0 truncate text-zinc-300">{label(variant)}</span><span className="shrink-0 font-mono text-zinc-500">{count ? count.toLocaleString() : label(row.count ?? row.wallet_count ?? "—")}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/[.05]"><div className="h-full rounded-full bg-gradient-to-r from-red-600 to-orange-300" style={{ width: `${Math.max(3, count / maxVariant * 100)}%` }}/></div></div>; })}</div> : <Empty text="Top variant details are not present in the returned payload."/>}
          </div>
          <div className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><div className="mb-4 flex items-center gap-2"><Activity size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">First-activity concentration</h3><p className="mt-1 text-xs text-zinc-600">Temporal concentration evidence</p></div></div>
            {Object.keys(concentration).length ? <div className="space-y-3">{Object.entries(concentration).filter(([, value]) => value == null || ["string", "number", "boolean"].includes(typeof value)).slice(0, 10).map(([key, value]) => <div key={key} className="flex items-start justify-between gap-4 border-b border-white/[.05] pb-2"><span className="text-xs text-zinc-500">{pretty(key)}</span><span className="max-w-[65%] break-all text-right font-mono text-xs text-zinc-200">{label(value)}</span></div>)}</div> : <Empty text="No first-activity concentration summary was returned."/>}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">{[["Intermediary analysis", intermediaries], ["Seller behavior", seller], ["Coordinated intermediary analysis", coordinated], ["Token handoff analysis", record(data.intermediary_handoff_analysis)]].map(([title, value]) => { const obj = record(value); const rows = Object.entries(obj).filter(([, item]) => item == null || ["string", "number", "boolean"].includes(typeof item)).slice(0, 8); return <div key={String(title)} className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><h3 className="text-sm font-semibold">{String(title)}</h3><div className="mt-4 space-y-2">{rows.map(([key, item]) => <div key={key} className="flex items-start justify-between gap-3 border-b border-white/[.05] pb-2"><span className="text-xs text-zinc-500">{pretty(key)}</span><span className="max-w-[68%] break-all text-right font-mono text-[11px] text-zinc-300">{label(item)}</span></div>)}{!rows.length && <Empty text="No scalar summary details returned for this analysis."/>}</div></div>; })}</section>
      </>}
    </div>
  </main>;
}
