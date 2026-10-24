"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Bot, ChevronRight, CircleHelp, Network, Search, Send, X } from "lucide-react";

type AnyRecord = Record<string, unknown>;
type GraphNode = { id: string; [key: string]: unknown };
type GraphEdge = { source: string; target: string; [key: string]: unknown };
type GraphData = { nodes?: GraphNode[]; edges?: GraphEdge[] };
type GraphSummary = { nodes?: number; edges?: number; data?: GraphData };
type Payload = { analysis?: { first_fund_graph?: GraphSummary; aggregated_tx_graph?: GraphSummary; wallet_features?: Record<string, AnyRecord> } };

const tour = [
  { title: "Welcome to the evidence map", body: "This is the transaction network from the current investigation. Each point represents a wallet; connecting lines represent observed relationships." },
  { title: "Switch the relationship model", body: "Use these controls to compare first-funding relationships with aggregated wallet-to-wallet transfers. The same wallet can play a different role in each graph." },
  { title: "Inspect any wallet", body: "Select a node to inspect its available features, including transaction counts, funding time, and graph connectivity." },
  { title: "Your AI analyst", body: "The assistant is a visual preview for now. You can open it and type a message, but conversational responses are not connected yet." },
];

function shortAddress(value: string) {
  return value.length > 17 ? value.slice(0, 7) + "…" + value.slice(-5) : value;
}
function display(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function num(value: unknown) {
  return typeof value === "number" ? value : 0;
}

export default function BubblemapPage() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"aggregated" | "funding">("aggregated");
  const [selected, setSelected] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<string[]>([]);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (!runId) {
      setError("No investigation run found. Start a forensic investigation first.");
      setLoading(false);
      return;
    }
    const tourKey = `sybiltrace_bubble_tour_${runId}`;
    if (!sessionStorage.getItem(tourKey)) setTourStep(0);
    fetch(`/backend/api/investigations/result/${encodeURIComponent(runId)}`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load the investigation graph.");
        const result = await response.json();
        setPayload(result.result ?? result);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Failed to load graph data."))
      .finally(() => setLoading(false));
  }, []);

  const graph = mode === "funding" ? payload?.analysis?.first_fund_graph : payload?.analysis?.aggregated_tx_graph;
  const nodes = graph?.data?.nodes ?? [];
  const edges = graph?.data?.edges ?? [];
  const features = payload?.analysis?.wallet_features ?? {};

  const positions = useMemo(() => {
    const result = new Map<string, { x: number; y: number }>();
    const count = nodes.length;
    const width = 1100, height = 650;
    nodes.forEach((node, index) => {
      const id = String(node.id ?? "");
      // Deterministic spiral layout: stable across renders and usable without a graph-layout dependency.
      const angle = index * 2.399963229728653;
      const radius = Math.sqrt((index + 1) / Math.max(count, 1)) * Math.min(width * 0.43, height * 0.43);
      result.set(id, { x: width / 2 + Math.cos(angle) * radius, y: height / 2 + Math.sin(angle) * radius });
    });
    return result;
  }, [nodes]);

  const visibleNodes = useMemo(() => {
    if (!search.trim()) return nodes;
    const query = search.trim().toLowerCase();
    return nodes.filter((node) => String(node.id ?? "").toLowerCase().includes(query));
  }, [nodes, search]);
  const visibleIds = useMemo(() => new Set(visibleNodes.map((node) => String(node.id ?? ""))), [visibleNodes]);
  const degrees = useMemo(() => {
    const result = new Map<string, number>();
    for (const edge of edges) {
      const source = String(edge.source ?? "");
      const target = String(edge.target ?? "");
      result.set(source, (result.get(source) ?? 0) + 1);
      result.set(target, (result.get(target) ?? 0) + 1);
    }
    return result;
  }, [edges]);
  const selectedNode = nodes.find((node) => String(node.id ?? "") === selected);
  const selectedFeatures = selected ? { ...(features[selected] ?? {}), ...(selectedNode ?? {}) } : null;

  const finishTour = useCallback(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (runId) sessionStorage.setItem(`sybiltrace_bubble_tour_${runId}`, "done");
    setTourStep(null);
  }, []);

  function sendMessage() {
    const message = chatInput.trim();
    if (!message) return;
    setChatMessages((previous) => [...previous, message]);
    setChatInput("");
  }

  const totalNodes = nodes.length;
  const totalEdges = edges.length;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07080b] text-zinc-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_50%_20%,rgba(127,29,29,0.16),transparent_55%)]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.055]" style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px),linear-gradient(90deg,rgba(255,255,255,.18) 1px,transparent 1px)", backgroundSize: "42px 42px" }} />
      <header className="relative z-10 flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] px-5 py-4 md:px-8">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="rounded-lg border border-white/10 bg-white/[0.03] p-2 text-zinc-400 transition hover:text-white"><ArrowLeft size={17} /></Link>
          <div><div className="text-[10px] tracking-[0.25em] text-red-300">SYBILTRACE / NETWORK INTELLIGENCE</div><h1 className="mt-1 text-lg font-semibold tracking-tight">Bubblemap <span className="text-zinc-500">/ Investigation Graph</span></h1></div>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-500"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> LIVE RESULT DATA <span className="hidden sm:inline">· {totalNodes.toLocaleString()} NODES · {totalEdges.toLocaleString()} EDGES</span></div>
      </header>

      <div className="relative z-10 mx-auto max-w-[1800px] p-4 md:p-7">
        <div className="mb-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div><p className="text-xs uppercase tracking-[0.22em] text-zinc-500">Visual forensics</p><h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">Follow the money. Find the pattern.</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">Explore funding provenance and transfer relationships from this investigation. Select a wallet to inspect its known features.</p></div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-xl border border-white/10 bg-[#0d0e12] p-1">
              <button onClick={() => { setMode("aggregated"); setSelected(null); }} className={`rounded-lg px-4 py-2.5 text-xs font-medium transition ${mode === "aggregated" ? "bg-red-500/15 text-red-200 shadow-[0_0_22px_rgba(239,68,68,.1)]" : "text-zinc-500 hover:text-white"}`}>Aggregated TX graph</button>
              <button onClick={() => { setMode("funding"); setSelected(null); }} className={`rounded-lg px-4 py-2.5 text-xs font-medium transition ${mode === "funding" ? "bg-red-500/15 text-red-200 shadow-[0_0_22px_rgba(239,68,68,.1)]" : "text-zinc-500 hover:text-white"}`}>First-fund graph</button>
            </div>
            <button onClick={() => setTourStep(0)} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2.5 text-xs text-zinc-400 transition hover:border-red-400/30 hover:text-white"><CircleHelp size={14} /> Guided tour</button>
          </div>
        </div>

        {error && <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/[0.06] p-4 text-sm text-red-200">{error} <Link className="ml-2 underline" href="/forensic">Start investigation</Link></div>}
        {loading ? <div className="flex min-h-[55vh] items-center justify-center"><div className="text-center"><div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-red-500/20 border-t-red-400" /><p className="text-sm text-zinc-400">Reconstructing wallet network…</p></div></div> : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <section className="min-w-0 overflow-hidden rounded-2xl border border-white/[0.09] bg-[#0a0b0f]/90 shadow-[0_20px_80px_rgba(0,0,0,.3)]">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3">
                <div className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-red-400 shadow-[0_0_10px_rgba(248,113,113,.6)]" /><div><p className="text-sm font-medium">{mode === "aggregated" ? "Aggregated transaction network" : "First-funding provenance"}</p><p className="mt-1 text-[11px] text-zinc-600">{mode === "aggregated" ? "Directed wallet transfer connections" : "Initial funding source → funded wallet"}</p></div></div>
                <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2"><Search size={13} className="text-zinc-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find wallet…" className="w-32 bg-transparent text-xs outline-none placeholder:text-zinc-700 sm:w-44" /></label>
              </div>
              <div className="relative min-h-[480px] overflow-auto bg-[radial-gradient(ellipse_at_center,rgba(127,29,29,.08),transparent_60%)]">
                {nodes.length ? <svg viewBox="0 0 1100 650" className="h-[520px] min-w-[760px] w-full md:h-[650px]" role="img" aria-label="Interactive wallet relationship graph">
                  <defs><filter id="nodeGlow"><feGaussianBlur stdDeviation="3.5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter><linearGradient id="edgeGlow"><stop offset="0%" stopColor="#ef4444" stopOpacity=".55" /><stop offset="100%" stopColor="#64748b" stopOpacity=".14" /></linearGradient></defs>
                  {edges.slice(0, 3500).map((edge, index) => {
                    const source = String(edge.source ?? ""), target = String(edge.target ?? "");
                    const a = positions.get(source), b = positions.get(target);
                    if (!a || !b || !visibleIds.has(source) || !visibleIds.has(target)) return null;
                    return <line key={`${source}-${target}-${index}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="url(#edgeGlow)" strokeWidth={selected && (selected === source || selected === target) ? 1.8 : .65} strokeOpacity={selected && selected !== source && selected !== target ? .12 : .65} />;
                  })}
                  {visibleNodes.map((node, index) => {
                    const id = String(node.id ?? "");
                    const p = positions.get(id);
                    if (!p) return null;
                    const degree = Math.max(num(node.in_degree) + num(node.out_degree), degrees.get(id) ?? 0);
                    const radius = Math.min(7, 2.3 + Math.log2(degree + 1) * 1.2);
                    const active = selected === id;
                    const color = mode === "funding" ? (degree >= 4 ? "#fb7185" : "#f59e0b") : (degree >= 5 ? "#fb7185" : degree >= 2 ? "#38bdf8" : "#71717a");
                    return <g key={id} onClick={() => setSelected(id)} role="button" tabIndex={0} aria-label={`Inspect wallet ${id}`} className="cursor-pointer" onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelected(id); }}>
                      {active && <circle cx={p.x} cy={p.y} r={radius + 8} fill="none" stroke="#fca5a5" strokeWidth="1" strokeDasharray="3 4"><animateTransform attributeName="transform" type="rotate" from={`0 ${p.x} ${p.y}`} to={`360 ${p.x} ${p.y}`} dur="12s" repeatCount="indefinite" /></circle>}
                      <circle cx={p.x} cy={p.y} r={radius + (active ? 2 : 0)} fill={color} fillOpacity={active ? .95 : .7} stroke={active ? "#fff" : color} strokeWidth={active ? 1.5 : .5} filter={active ? "url(#nodeGlow)" : undefined} />
                    </g>;
                  })}
                </svg> : <div className="flex min-h-[480px] items-center justify-center px-6 text-center"><div><Network className="mx-auto h-9 w-9 text-zinc-700" /><p className="mt-4 text-sm text-zinc-400">Graph data is not available in this result.</p><p className="mt-1 text-xs text-zinc-600">Complete a new investigation to populate the network.</p></div></div>}
                <div className="pointer-events-none absolute bottom-4 left-4 flex flex-wrap gap-3 rounded-lg border border-white/[0.08] bg-[#08090c]/90 px-3 py-2 text-[10px] text-zinc-500 backdrop-blur"><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red-400" /> High connectivity</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-sky-400" /> Connected wallet</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-zinc-500" /> Peripheral wallet</span></div>
              </div>
              <div className="grid grid-cols-3 border-t border-white/[0.07]">
                {[["WALLETS", totalNodes.toLocaleString()], ["RELATIONSHIPS", totalEdges.toLocaleString()], ["GRAPH MODE", mode === "aggregated" ? "TRANSFER" : "FUNDING"]].map(([label, value]) => <div key={label} className="border-r border-white/[0.06] px-4 py-3 last:border-r-0"><p className="text-[9px] tracking-[0.16em] text-zinc-600">{label}</p><p className="mt-1 font-mono text-sm text-zinc-200">{value}</p></div>)}
              </div>
            </section>

            <aside className="space-y-4">
              <section className="rounded-2xl border border-white/[0.09] bg-[#0a0b0f]/90 p-4">
                <div className="mb-4 flex items-center justify-between"><div><p className="text-[10px] tracking-[0.18em] text-zinc-500">WALLET INSPECTOR</p><h3 className="mt-1 text-sm font-semibold">Node intelligence</h3></div><span className="rounded-md border border-red-500/20 bg-red-500/[0.07] px-2 py-1 text-[9px] text-red-300">FEATURES</span></div>
                {selected && selectedFeatures ? <><p className="break-all font-mono text-xs leading-5 text-zinc-300">{selected}</p><div className="mt-4 space-y-2">{Object.entries(selectedFeatures).filter(([key, value]) => key !== "id" && value !== undefined && value !== null).slice(0, 18).map(([key, value]) => <div key={key} className="flex items-start justify-between gap-3 border-b border-white/[0.05] pb-2"><span className="shrink-0 text-[11px] text-zinc-600">{key.replaceAll("_", " ")}</span><span className="max-w-[60%] break-all text-right font-mono text-[10px] text-zinc-300">{display(value)}</span></div>)}</> : <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.015] px-4 py-8 text-center"><Network className="mx-auto h-6 w-6 text-zinc-700" /><p className="mt-3 text-xs text-zinc-400">Select a node to inspect its features</p><p className="mt-1 text-[10px] text-zinc-600">Click any point in the network</p></div>}
              </section>
              <button onClick={() => setShowChat(true)} className="group relative w-full overflow-hidden rounded-2xl border border-red-400/20 bg-gradient-to-br from-[#1b0d11] to-[#0b0b10] p-5 text-left transition hover:border-red-400/50">
                <div className="absolute -right-6 -top-8 h-28 w-28 rounded-full bg-red-500/10 blur-2xl transition group-hover:bg-red-500/20" /><div className="relative flex items-center gap-3"><div className="relative flex h-12 w-12 items-center justify-center rounded-full border border-red-400/30 bg-red-500/10 text-red-300 shadow-[0_0_28px_rgba(239,68,68,.15)]"><Bot size={21} /><span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-[#140b0d] bg-amber-300" /></div><div><p className="text-sm font-semibold text-white">Ask the analyst</p><p className="mt-1 text-xs text-zinc-500">AI assistant preview · not connected</p></div><ChevronRight className="ml-auto h-4 w-4 text-zinc-600 transition group-hover:translate-x-1 group-hover:text-red-300" /></div>
                <p className="relative mt-4 text-xs leading-5 text-zinc-500">Ask about a wallet, funding path, or suspicious cluster. Chat replies are disabled in this preview.</p>
              </button>
            </aside>
          </div>
        )}
      </div>

      <button onClick={() => setShowChat(true)} aria-label="Open AI analyst" className="fixed bottom-6 right-6 z-30 flex h-14 w-14 items-center justify-center rounded-full border border-red-300/40 bg-gradient-to-br from-red-500/30 to-[#160b10] text-red-200 shadow-[0_0_35px_rgba(239,68,68,.25)] transition hover:scale-105"><Bot size={23} /><span className="absolute inset-[-6px] rounded-full border border-red-400/15 animate-ping" /></button>

      <AnimatePresence>
        {showChat && <motion.aside initial={{ opacity: 0, x: 35 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 35 }} className="fixed bottom-24 right-5 z-40 flex h-[min(560px,70vh)] w-[min(390px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-red-400/20 bg-[#0b0c11]/[.97] shadow-[0_25px_100px_rgba(0,0,0,.65)] backdrop-blur-2xl">
          <div className="flex items-center gap-3 border-b border-white/[0.08] p-4"><div className="flex h-9 w-9 items-center justify-center rounded-full border border-red-400/30 bg-red-500/10 text-red-300"><Bot size={17} /></div><div className="flex-1"><p className="text-sm font-semibold">Investigation copilot</p><p className="mt-0.5 text-[10px] text-amber-300">PREVIEW MODE · RESPONSES DISABLED</p></div><button onClick={() => setShowChat(false)} className="text-zinc-500 hover:text-white"><X size={17} /></button></div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4"><div className="max-w-[90%] rounded-xl rounded-tl-sm border border-white/[0.07] bg-white/[0.035] p-3 text-xs leading-5 text-zinc-400">I’m your investigation copilot preview. I can’t respond yet, but this panel will eventually help explain wallet relationships and evidence from the current investigation.</div>{chatMessages.map((message, index) => <div key={index} className="ml-auto max-w-[88%] rounded-xl rounded-tr-sm border border-red-400/20 bg-red-500/[0.09] p-3 text-xs leading-5 text-zinc-200">{message}</div>)}</div>
          <form onSubmit={(event) => { event.preventDefault(); sendMessage(); }} className="flex items-center gap-2 border-t border-white/[0.08] p-3"><input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Ask about this investigation…" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-xs outline-none placeholder:text-zinc-700 focus:border-red-400/30" /><button aria-label="Send message" type="submit" className="rounded-lg border border-red-400/20 bg-red-500/10 p-2.5 text-red-300 hover:bg-red-500/20"><Send size={14} /></button></form>
        </motion.aside>}
      </AnimatePresence>

      <AnimatePresence>
        {tourStep !== null && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-5 backdrop-blur-sm">
          <motion.div initial={{ opacity: 0, y: 18, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12 }} className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-red-400/25 bg-[#0c0d12] p-6 shadow-[0_0_80px_rgba(239,68,68,.12)]">
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-red-400 to-transparent" /><div className="flex items-center justify-between"><span className="text-[10px] tracking-[0.2em] text-red-300">FIELD GUIDE / 0{tourStep + 1}</span><button onClick={finishTour} className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-white">Skip tour <X size={13} /></button></div>
            <div className="mt-5 flex gap-4"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-red-400/20 bg-red-500/[0.08] text-red-300"><Network size={19} /></div><div><h3 className="text-xl font-semibold tracking-tight">{tour[tourStep].title}</h3><p className="mt-3 text-sm leading-6 text-zinc-400">{tour[tourStep].body}</p></div></div>
            <div className="mt-6 flex items-center justify-between"><div className="flex gap-1.5">{tour.map((step, index) => <span key={step.title} className={`h-1 rounded-full transition-all ${index === tourStep ? "w-7 bg-red-400" : "w-3 bg-white/10"}`} />)}</div><button onClick={() => tourStep === tour.length - 1 ? finishTour() : setTourStep(tourStep + 1)} className="inline-flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-red-400">{tourStep === tour.length - 1 ? "Start exploring" : "Continue"} <ChevronRight size={14} /></button></div>
          </motion.div>
        </motion.div>}
      </AnimatePresence>
    </main>
  );
}
