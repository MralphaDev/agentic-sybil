"use client";

import "@xyflow/react/dist/style.css";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, Handle, Position, MarkerType, type Node, type Edge as FlowEdge, type NodeProps, type EdgeProps, BaseEdge, EdgeLabelRenderer, getSmoothStepPath, useNodesState, useEdgesState } from "@xyflow/react";
import { ArrowLeft, GitBranch, Activity, Users, Repeat2, TrendingUp, Filter, Network, X } from "lucide-react";

type AnyRecord = Record<string, unknown>;
type DfgEdge = { source: string; target: string; count: number; transition_probability?: number; probability?: number };
type Dfg = { edges?: DfgEdge[]; start_activities?: Record<string, number>; end_activities?: Record<string, number>; statistics?: AnyRecord; filtering_statistics?: AnyRecord };
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

function ActivityNode({ data }: NodeProps<Node<{ title: string; incoming: number; outgoing: number; start: number; end: number; special?: string; rework?: number }>>) {
  const isSell = data.title.toLowerCase().includes("sell");
  if (data.special) return <div className={`flex h-[66px] w-[66px] items-center justify-center rounded-full border-2 shadow-[0_0_28px_rgba(248,113,113,.12)] ${data.special === "start" ? "border-emerald-300 bg-emerald-950/70 text-emerald-200" : "border-amber-300 bg-amber-950/70 text-amber-200"}`}>
    {data.special === "start" ? <span className="text-[10px] font-bold tracking-[.12em]">START</span> : <span className="text-[10px] font-bold tracking-[.12em]">END</span>}
    {data.special === "start" ? <Handle type="source" position={Position.Right} className="!border-0 !bg-emerald-300"/> : <Handle type="target" position={Position.Left} className="!border-0 !bg-amber-300"/>}
  </div>;
  return <div className={`relative min-w-[174px] rounded-xl border px-4 py-3 shadow-[0_8px_25px_rgba(0,0,0,.28)] ${isSell ? "border-rose-400/90 bg-gradient-to-br from-rose-950/95 to-[#101016]" : "border-slate-600/80 bg-gradient-to-br from-slate-800/95 to-[#101016]"}`}>
    <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-slate-300"/>
    <div className={`text-center text-xs font-semibold ${isSell ? "text-rose-200" : "text-slate-100"}`}>{data.title}</div>
    <div className="mt-1.5 text-center font-mono text-[10px] text-slate-400">{data.incoming.toLocaleString()} in · {data.outgoing.toLocaleString()} out</div>
    {data.rework ? <div className="mt-2 rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-center text-[9px] font-semibold tracking-wide text-amber-200">↻ REWORK LOOP · {data.rework.toLocaleString()}</div> : null}
    <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-slate-300"/>
  </div>;
}
function FrequencyEdge({ id, source, target, sourceX, sourceY, targetX, targetY, data, markerEnd, style }: EdgeProps<FlowEdge<{ count: number; probability: number | null }>>) {
  const isLoop = source === target;
  const [smoothPath, smoothX, smoothY] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, borderRadius: 18, offset: 42 });
  const loopLift = 74 + Math.min(70, Math.sqrt(data?.count ?? 0) * 2);
  const path = isLoop ? `M ${sourceX},${sourceY} C ${sourceX - 56},${sourceY - loopLift} ${targetX + 56},${targetY - loopLift} ${targetX},${targetY}` : smoothPath;
  const labelX = isLoop ? (sourceX + targetX) / 2 : smoothX;
  const labelY = isLoop ? Math.min(sourceY, targetY) - loopLift + 8 : smoothY;
  return <><BaseEdge id={id} path={path} markerEnd={markerEnd} style={style}/><EdgeLabelRenderer><div className={`nodrag nopan pointer-events-all absolute rounded-md border px-2 py-1 font-mono text-[10px] shadow ${isLoop ? "border-amber-400/40 bg-amber-950 text-amber-200" : "border-rose-400/20 bg-[#111116] text-rose-100"}`} style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }} title={data?.probability == null ? (isLoop ? "Rework / self-loop frequency" : "Transition frequency") : `Transition probability: ${(data.probability * 100).toFixed(1)}%`}>{isLoop ? `↻ ${(data?.count ?? 0).toLocaleString()}` : (data?.count ?? 0).toLocaleString()}</div></EdgeLabelRenderer></>;
}
const nodeTypes = { activity: ActivityNode };
const edgeTypes = { frequency: FrequencyEdge };

function DfgDiagram({ dfg, title, description }: { dfg: Dfg; title: string; description: string }) {
  const [selectedItem, setSelectedItem] = useState<{ kind: "activity" | "transition"; title: string; details: Record<string, string> } | null>(null);
  const built = useMemo(() => {
    const edges = (dfg.edges ?? []).filter((edge) => edge && typeof edge.source === "string" && typeof edge.target === "string" && edge.source !== "__START__" && edge.target !== "__END__");
    const starts = dfg.start_activities ?? {}, ends = dfg.end_activities ?? {};
    const names = new Set<string>();
    edges.forEach((edge) => { names.add(edge.source); names.add(edge.target); });
    Object.keys(starts).forEach((name) => names.add(name));
    Object.keys(ends).forEach((name) => names.add(name));
    if (!names.size) return { nodes: [] as Node[], edges: [] as FlowEdge[], activityCount: 0 };
    const activityStats = new Map<string, { incoming: number; outgoing: number; rework: number }>();
    names.forEach((name) => activityStats.set(name, { incoming: 0, outgoing: 0, rework: 0 }));
    edges.forEach((edge) => {
      activityStats.get(edge.source)!.outgoing += edge.count;
      activityStats.get(edge.target)!.incoming += edge.count;
      if (edge.source === edge.target) activityStats.get(edge.source)!.rework += edge.count;
    });
    const startNames = Object.keys(starts).filter((name) => names.has(name));
    const endNames = Object.keys(ends).filter((name) => names.has(name));
    const roots = startNames.length ? startNames : [...names].filter((name) => !edges.some((edge) => edge.target === name));
    const sinks = endNames.length ? endNames : [...names].filter((name) => !edges.some((edge) => edge.source === name));
    const rank = new Map<string, number>();
    const adjacency = new Map<string, string[]>();
    names.forEach((name) => adjacency.set(name, []));
    edges.forEach((edge) => adjacency.get(edge.source)?.push(edge.target));
    const seedQueue = [...roots];
    roots.forEach((name) => rank.set(name, 1));
    // BFS assigns each activity its shortest forward rank, so loops never push
    // the graph into an enormous number of columns.
    const assignRanks = (queue: string[]) => {
      while (queue.length) {
        const current = queue.shift()!;
        for (const target of adjacency.get(current) ?? []) {
          if (!rank.has(target)) { rank.set(target, (rank.get(current) ?? 1) + 1); queue.push(target); }
        }
      }
    };
    assignRanks(seedQueue);
    // Include disconnected cyclic components that cannot be reached from START.
    for (const name of names) if (!rank.has(name)) { rank.set(name, 1); assignRanks([name]); }
    const maxRank = Math.max(2, ...rank.values());
    const columns = new Map<number, string[]>();
    for (const name of names) {
      const col = Math.max(1, Math.min(maxRank, rank.get(name) ?? 1));
      if (!columns.has(col)) columns.set(col, []);
      columns.get(col)!.push(name);
    }
    for (const col of columns.values()) col.sort((a, b) =>
      (activityStats.get(b)!.incoming + activityStats.get(b)!.outgoing) -
      (activityStats.get(a)!.incoming + activityStats.get(a)!.outgoing) || a.localeCompare(b)
    );
    const positions = new Map<string, { x: number; y: number }>();
    const xGap = 300, yGap = 150;
    for (const [col, values] of columns) values.forEach((name, index) => positions.set(name, {
      x: col * xGap, y: (index - (values.length - 1) / 2) * yGap,
    }));
    const startY = roots.length ? roots.reduce((sum, name) => sum + (positions.get(name)?.y ?? 0), 0) / roots.length : 0;
    const endY = sinks.length ? sinks.reduce((sum, name) => sum + (positions.get(name)?.y ?? 0), 0) / sinks.length : 0;
    const nodes: Node[] = [
      { id: "__START__", type: "activity", position: { x: 0, y: startY - 33 }, data: { title: "START", incoming: 0, outgoing: Object.values(starts).reduce((sum, n) => sum + (number(n) ?? 0), 0), start: 0, end: 0, special: "start" } },
      ...[...names].map((name) => {
        const point = positions.get(name) ?? { x: xGap, y: 0 }, stats = activityStats.get(name)!;
        return { id: name, type: "activity", position: { x: point.x, y: point.y - 41 }, data: { title: name, incoming: stats.incoming, outgoing: stats.outgoing, start: number(starts[name]) ?? 0, end: number(ends[name]) ?? 0, rework: stats.rework } };
      }),
      { id: "__END__", type: "activity", position: { x: (maxRank + 1) * xGap, y: endY - 33 }, data: { title: "END", incoming: Object.values(ends).reduce((sum, n) => sum + (number(n) ?? 0), 0), outgoing: 0, start: 0, end: 0, special: "end" } },
    ];
    const maxCount = Math.max(1, ...edges.map((item) => item.count), ...Object.values(starts).map((v) => number(v) ?? 0), ...Object.values(ends).map((v) => number(v) ?? 0));
    const flowEdges: FlowEdge[] = [
      ...edges.map((edge, index) => ({
        id: `transition-${index}-${edge.source}-${edge.target}`, source: edge.source, target: edge.target, type: "frequency",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#fda4af", width: 15, height: 15 },
        style: { stroke: "#fb7185", strokeOpacity: .72, strokeWidth: 1.1 + Math.sqrt(Math.max(0, edge.count) / maxCount) * 3 },
        data: { count: edge.count, probability: number(edge.transition_probability ?? edge.probability) },
      })),
      ...Object.entries(starts).filter(([name]) => names.has(name)).map(([name, count], index) => ({ id: `start-edge-${index}`, source: "__START__", target: name, type: "frequency", markerEnd: { type: MarkerType.ArrowClosed, color: "#6ee7b7" }, style: { stroke: "#34d399", strokeOpacity: .8, strokeWidth: 1.2 + Math.sqrt((number(count) ?? 0) / maxCount) * 3 }, data: { count: number(count) ?? 0, probability: null } })),
      ...Object.entries(ends).filter(([name]) => names.has(name)).map(([name, count], index) => ({ id: `end-edge-${index}`, source: name, target: "__END__", type: "frequency", markerEnd: { type: MarkerType.ArrowClosed, color: "#fcd34d" }, style: { stroke: "#fbbf24", strokeOpacity: .8, strokeWidth: 1.2 + Math.sqrt((number(count) ?? 0) / maxCount) * 3 }, data: { count: number(count) ?? 0, probability: null } })),
    ];
    return { nodes, edges: flowEdges, activityCount: names.size };
  }, [dfg]);
  const [nodes, setNodes, onNodesChange] = useNodesState(built.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(built.edges);
  useEffect(() => { setNodes(built.nodes); setEdges(built.edges); setSelectedItem(null); }, [built, setNodes, setEdges]);
  const originalEdges = dfg.edges ?? [];
  if (!originalEdges.length) return <section className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-zinc-600">{description}</p><div className="mt-5"><Empty text="No transitions remain in this DFG. Check event mapping and the frequency filter."/></div></section>;
  return <section className="overflow-hidden rounded-2xl border border-white/[.09] bg-[#0b0c10]/95">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[.07] p-5"><div className="flex items-center gap-2"><Network size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-zinc-600">{description}</p></div></div><div className="flex gap-3 text-[10px] text-zinc-500"><span>{built.activityCount} activities</span><span>{originalEdges.length} transitions</span><span>Click node/edge for evidence</span></div></div>
    <div className="relative h-[650px] bg-[radial-gradient(ellipse_at_50%_0%,rgba(127,29,29,.09),transparent_65%)]">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView fitViewOptions={{ padding: .12, minZoom: .12, maxZoom: 1.1 }} minZoom={.12} maxZoom={2} onNodeClick={(_, node) => { const d = node.data as AnyRecord; setSelectedItem({ kind: "activity", title: String(d.title ?? node.id), details: { Activity: String(d.title ?? node.id), "Incoming frequency": String(d.incoming ?? 0), "Outgoing frequency": String(d.outgoing ?? 0), "Start count": String(d.start ?? 0), "End count": String(d.end ?? 0) } }); }} onEdgeClick={(_, edge) => { const d = record(edge.data); setSelectedItem({ kind: "transition", title: `${edge.source} → ${edge.target}`, details: { Source: edge.source, Target: edge.target, "Transition frequency": String(d.count ?? edge.label ?? "—"), "Transition probability": d.probability == null ? "Not available" : `${(Number(d.probability) * 100).toFixed(2)}%` } }); }} proOptions={{ hideAttribution: true }}>
        <Background color="#27212a" gap={24} size={1}/><Controls className="!overflow-hidden !rounded-lg !border !border-white/10 !bg-[#111116] [&>button]:!border-white/10 [&>button]:!bg-[#111116] [&>button]:!fill-zinc-300"/><MiniMap pannable zoomable nodeColor={(node) => String((node.data as AnyRecord).title ?? "").toLowerCase().includes("sell") ? "#fb7185" : "#64748b"} className="!border !border-white/10 !bg-[#0a0b10]"/>
      </ReactFlow>
      {selectedItem && <aside className="absolute right-3 top-3 z-10 w-[min(300px,calc(100%-24px))] rounded-xl border border-white/10 bg-[#0b0c10]/95 p-4 shadow-2xl backdrop-blur"><div className="flex items-start justify-between gap-3"><div><p className="text-[9px] tracking-[.2em] text-red-300">{selectedItem.kind === "activity" ? "ACTIVITY DETAILS" : "TRANSITION DETAILS"}</p><h4 className="mt-1 break-words text-sm font-semibold">{selectedItem.title}</h4></div><button onClick={() => setSelectedItem(null)} className="text-zinc-500 hover:text-white"><X size={15}/></button></div><div className="mt-4 space-y-2">{Object.entries(selectedItem.details).map(([key, value]) => <div key={key} className="flex justify-between gap-3 border-b border-white/[.06] pb-2"><span className="text-[10px] text-zinc-500">{key}</span><span className="max-w-[60%] break-all text-right font-mono text-[10px] text-zinc-200">{value}</span></div>)}</div></aside>}
    </div>
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[.06] px-5 py-3 text-[10px] text-zinc-500"><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-rose-400"/>Sell activity</span><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-emerald-400"/>Start activity</span><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-amber-300"/>End activity</span><span>Edge thickness = transition frequency · scroll to zoom · drag to pan</span></div>
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
  const concentration = record(data.first_activity_concentration);
  const concentrationBuckets = Object.entries(record(concentration.four_hour_distribution)).map(([time, count]) => ({ time, count: number(count) ?? 0 })).sort((a, b) => a.time.localeCompare(b.time));
  const concentrationPeak = Math.max(1, ...concentrationBuckets.map((item) => item.count));
  const concentrationStats = record(concentration.four_hour_stats);
  const intermediaries = record(data.intermediary_analysis);
  const coordinated = record(data.coordinated_intermediary_analysis);
  const seller = record(data.seller_behavior);
  const variants = array(data.variants);
  const clusters = record(data.clustering);
  const maxVariant = Math.max(1, ...topVariants.map((item) => number(record(item).count ?? record(item).wallet_count ?? record(item).frequency) ?? 0));
  const rawEdges = rawDfg.edges ?? [], filteredEdges = filteredDfg.edges ?? [];
  const rawSellEdges = rawEdges.filter((edge) => edge.source?.toLowerCase().includes("sell") || edge.target?.toLowerCase().includes("sell"));
  const filteredSellEdges = filteredEdges.filter((edge) => edge.source?.toLowerCase().includes("sell") || edge.target?.toLowerCase().includes("sell"));
  const sellWalletCount = number(seller.wallet_count ?? seller.count ?? array(seller.wallets).length);
  const mappedSellActions = number(record(data.action_counts).sell) ?? 0;
  return <main className="relative min-h-screen overflow-hidden bg-[#07080b] text-zinc-100">
    <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(127,29,29,.15),transparent_58%)]"/>
    <header className="relative z-10 flex items-center justify-between border-b border-white/[.08] px-5 py-4 md:px-8"><div className="flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-white/10 bg-white/[.03] p-2 text-zinc-400 hover:text-white"><ArrowLeft size={17}/></Link><div><p className="text-[10px] tracking-[.24em] text-red-300">SYBILTRACE / BEHAVIORAL INTELLIGENCE</p><h1 className="mt-1 text-lg font-semibold">Process Mining Dashboard</h1></div></div><span className="hidden text-[10px] tracking-[.16em] text-zinc-600 sm:block">EVENT LOG · DIRECTLY-FOLLOWS · VARIANTS</span></header>
    <div className="relative z-10 mx-auto max-w-[1700px] space-y-6 p-5 md:p-8">
      <div><p className="text-xs uppercase tracking-[.22em] text-zinc-500">Behavioral analysis</p><h2 className="mt-2 text-3xl font-semibold tracking-tight">How wallets behave — and where patterns repeat.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">The filtered DFG is the primary view. Inspect each activity or transition directly, then switch to the raw graph to compare against the full event structure.</p></div>
      {error && <div className="rounded-xl border border-red-500/20 bg-red-500/[.06] p-4 text-sm text-red-200">{error}</div>}
      {loading ? <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500"><span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-red-500/20 border-t-red-400"/>Loading process evidence…</div> : <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric title="DISTINCT VARIANTS" value={String(variants.length || "—")} note="Unique wallet action sequences" icon={GitBranch}/><Metric title="VARIANT CLUSTERS" value={label(array(clusters.clusters).length || number(clusters.cluster_count) || "—")} note="Behavioral groups returned by analysis" icon={Users}/><Metric title="INTERMEDIARY WALLETS" value={label(array(intermediaries.wallets).length || number(intermediaries.count) || "—")} note="Potential asset relays" icon={Repeat2}/><Metric title="SELLER WALLETS" value={label(sellWalletCount ?? "—")} note="Wallets identified by variant sell analysis" icon={TrendingUp}/></section>
        <section className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-4 md:p-5"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><Filter size={15} className="text-red-300"/><div><h3 className="text-sm font-semibold">Directly-follows graph</h3><p className="mt-1 text-xs text-zinc-600">A process-map layout inspired by ProM/Celonis: activities, frequency-weighted arcs, and inspectable evidence.</p></div></div><div className="flex rounded-xl border border-white/10 bg-black/30 p-1"><button onClick={() => setDfgMode("filtered")} className={`rounded-lg px-4 py-2 text-xs ${dfgMode === "filtered" ? "bg-red-500/15 text-red-200" : "text-zinc-500 hover:text-white"}`}>Filtered DFG</button><button onClick={() => setDfgMode("raw")} className={`rounded-lg px-4 py-2 text-xs ${dfgMode === "raw" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-white"}`}>Raw DFG</button></div></div>
          <DfgDiagram key={dfgMode} dfg={dfgMode === "filtered" ? filteredDfg : rawDfg} title={dfgMode === "filtered" ? "Filtered directly-follows graph" : "Raw directly-follows graph"} description={dfgMode === "filtered" ? "Frequency threshold and low-value generic activities removed" : "All mapped activities and observed transitions after dust filtering"}/>
          <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-zinc-600"><span>Raw edges: {rawEdges.length}</span><span>Filtered edges: {filteredEdges.length}</span><span>Filtered sell-related edges: {filteredSellEdges.length}</span><span>Mapped sell actions: {mappedSellActions}</span></div>
          {rawSellEdges.length > 0 && filteredSellEdges.length === 0 && <p className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/[.05] p-3 text-xs leading-5 text-amber-100/80">Sell transitions exist in the raw DFG but were removed from the filtered graph. Check frequency filtering and adjacent activity exclusions.</p>}
          {rawSellEdges.length === 0 && <p className="mt-3 rounded-lg border border-white/[.07] bg-white/[.02] p-3 text-xs leading-5 text-zinc-500">No sell-related transitions were found in the raw DFG. Backend mapped {mappedSellActions.toLocaleString()} events to sell. If zero, inspect the target mint and swap token fields.</p>}
        </section>
        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,.8fr)]"><div className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><div className="mb-5 flex items-center gap-2"><GitBranch size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">Most common wallet variants</h3><p className="mt-1 text-xs text-zinc-600">Repeated action sequences across wallets</p></div></div>{topVariants.length ? <div className="space-y-4">{topVariants.slice(0, 12).map((item, index) => { const row = record(item); const variant = row.variant ?? row.sequence ?? row.actions ?? row.name ?? `Variant ${index + 1}`; const count = number(row.count ?? row.wallet_count ?? row.frequency) ?? 0; return <div key={index}><div className="mb-1.5 flex items-center justify-between gap-3 text-xs"><span className="min-w-0 truncate text-zinc-300">{label(variant)}</span><span className="shrink-0 font-mono text-zinc-500">{count ? count.toLocaleString() : label(row.count ?? row.wallet_count ?? "—")}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/[.05]"><div className="h-full rounded-full bg-gradient-to-r from-red-600 to-orange-300" style={{ width: `${Math.max(3, count / maxVariant * 100)}%` }}/></div></div>; })}</div> : <Empty text="Top variant details are not present in the returned payload."/>}</div>
          <div className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><div className="mb-4 flex items-center gap-2"><Activity size={16} className="text-red-300"/><div><h3 className="text-sm font-semibold">First-activity concentration</h3><p className="mt-1 text-xs text-zinc-600">Temporal concentration evidence</p></div></div>{concentrationBuckets.length ? <><div className="mb-4 grid grid-cols-2 gap-3"><div className="rounded-lg border border-white/[.06] bg-white/[.025] p-3"><p className="text-[10px] text-zinc-500">WALLETS IN WINDOW</p><p className="mt-1 text-xl font-semibold text-white">{label(concentrationStats.wallets_in_window ?? 0)}</p></div><div className="rounded-lg border border-white/[.06] bg-white/[.025] p-3"><p className="text-[10px] text-zinc-500">PEAK 4H BUCKET</p><p className="mt-1 text-xl font-semibold text-rose-200">{label(concentrationStats.peak_count ?? concentrationPeak)}</p></div></div><div className="relative h-[230px] rounded-lg border border-white/[.06] bg-black/20 px-3 pb-8 pt-4"><div className="absolute inset-x-3 bottom-8 top-4 flex items-end gap-[3px]">{concentrationBuckets.map((bucket) => <div key={bucket.time} className="group relative flex h-full min-w-0 flex-1 items-end" title={`${bucket.time}: ${bucket.count} wallets`}><div className="w-full rounded-t-sm bg-gradient-to-t from-red-700/90 via-rose-500/80 to-orange-300/90 transition-opacity group-hover:opacity-100" style={{ height: `${Math.max(1.5, bucket.count / concentrationPeak * 100)}%`, opacity: bucket.count === concentrationPeak ? 1 : .72 }}/><div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded border border-white/10 bg-[#111116] px-2 py-1 text-[10px] text-white group-hover:block">{new Date(bucket.time).toLocaleString("en-GB", { timeZone: "UTC", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZoneName: "short" })} · {bucket.count}</div></div>)}</div><div className="absolute inset-x-3 bottom-2 flex justify-between text-[9px] text-zinc-600"><span>{new Date(concentrationBuckets[0].time).toLocaleDateString("en-GB", { timeZone: "UTC", month: "short", day: "numeric" })}</span><span>4-hour buckets · UTC</span><span>{new Date(concentrationBuckets[concentrationBuckets.length - 1].time).toLocaleDateString("en-GB", { timeZone: "UTC", month: "short", day: "numeric" })}</span></div></div><p className="mt-3 text-[11px] leading-5 text-zinc-500">Each wallet contributes only its earliest recorded activity. Hover bars to inspect the number of wallets first active in each four-hour interval.</p></> : <Empty text="No first-activity time buckets were returned for this investigation."/>}</div></section>
        <section className="grid gap-4 lg:grid-cols-2">{[["Intermediary analysis", intermediaries], ["Seller behavior", seller], ["Coordinated intermediary analysis", coordinated], ["Token handoff analysis", record(data.intermediary_handoff_analysis)]].map(([title, value]) => { const obj = record(value); const rows = Object.entries(obj).filter(([, item]) => item == null || ["string", "number", "boolean"].includes(typeof item)).slice(0, 8); return <div key={String(title)} className="rounded-2xl border border-white/[.09] bg-[#0b0c10]/90 p-5"><h3 className="text-sm font-semibold">{String(title)}</h3><div className="mt-4 space-y-2">{rows.map(([key, item]) => <div key={key} className="flex items-start justify-between gap-3 border-b border-white/[.05] pb-2"><span className="text-xs text-zinc-500">{pretty(key)}</span><span className="max-w-[68%] break-all text-right font-mono text-[11px] text-zinc-300">{label(item)}</span></div>)}{!rows.length && <Empty text="No scalar summary details returned for this analysis."/>}</div></div>; })}</section>
      </>}
    </div>
  </main>;
}
