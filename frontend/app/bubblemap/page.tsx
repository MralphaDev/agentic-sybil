"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type Simulation, type SimulationLinkDatum } from "d3-force";
import { ArrowLeft, Bot, CircleHelp, Maximize2, Minus, Network, Plus, Search, Send, X } from "lucide-react";

type AnyRecord = Record<string, unknown>;
type SimNode = { id: string; x?: number; y?: number; vx?: number; vy?: number; fx?: number | null; fy?: number | null; [key: string]: unknown };
type SimLink = SimulationLinkDatum<SimNode> & { source: string | SimNode; target: string | SimNode; count?: number };
type GraphData = { nodes?: AnyRecord[]; edges?: AnyRecord[] };
type GraphSummary = { data?: GraphData };
type Payload = { analysis?: { first_fund_graph?: GraphSummary; aggregated_tx_graph?: GraphSummary; wallet_features?: Record<string, AnyRecord> } };
type View = { x: number; y: number; k: number };

const tour = [
  { title: "Welcome to the evidence map", body: "Each point is a wallet. Links show observed on-chain relationships. The force layout brings connected wallets closer together." },
  { title: "Switch graph models", body: "Compare aggregated transfers with first-funding provenance. The same wallet may play different roles in each graph." },
  { title: "Explore the network", body: "Drag a wallet to reposition it, scroll to zoom, and drag empty space to pan. Click any wallet to inspect its features." },
  { title: "Investigation copilot", body: "The floating assistant is a UI preview. You can type messages, but it is not connected to an AI backend yet." },
];
const shortAddress = (value: string) => value.length > 18 ? value.slice(0, 7) + "…" + value.slice(-5) : value;
const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : 0;
const display = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value);

export default function BubblemapPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);
  const viewRef = useRef<View>({ x: 0, y: 0, k: 1 });
  const dragRef = useRef<{ kind: "node" | "pan"; node?: SimNode; px: number; py: number; moved: boolean } | null>(null);
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
  const [canvasReady, setCanvasReady] = useState(false);
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);
  const renderStateRef = useRef({ mode, searchQuery: "", selected: null as string | null });

  useEffect(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (!runId) { setError("No investigation run found. Start a forensic investigation first."); setLoading(false); return; }
    if (!sessionStorage.getItem(`sybiltrace_bubble_tour_${runId}`)) setTourStep(0);
    fetch(`/backend/api/investigations/result/${encodeURIComponent(runId)}`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("Could not load the investigation graph."); const result = await response.json(); setPayload(result.result ?? result); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Failed to load graph data."))
      .finally(() => setLoading(false));
  }, []);

  const graph = mode === "funding" ? payload?.analysis?.first_fund_graph : payload?.analysis?.aggregated_tx_graph;
  const sourceNodes = graph?.data?.nodes ?? [];
  const sourceEdges = graph?.data?.edges ?? [];
  const features = payload?.analysis?.wallet_features ?? {};
  const selectedNode = nodesRef.current.find((node) => node.id === selected);
  const selectedFeatures = selected ? { ...(features[selected] ?? {}), ...(selectedNode ?? {}) } : null;
  const searchQuery = search.trim().toLowerCase();
  renderStateRef.current = { mode, searchQuery, selected };

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const host = hostRef.current;
    if (!canvas || !host) return;
    const rect = host.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const { mode: currentMode, searchQuery: currentSearch, selected: currentSelected } = renderStateRef.current;
    const gradient = ctx.createRadialGradient(width * .5, height * .48, 20, width * .5, height * .48, Math.max(width, height) * .75);
    gradient.addColorStop(0, "#140d12"); gradient.addColorStop(.58, "#090a0e"); gradient.addColorStop(1, "#06070a");
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height);
    ctx.save();
    const view = viewRef.current;
    ctx.translate(view.x, view.y); ctx.scale(view.k, view.k);
    // Subtle infinite-looking grid, rendered in world coordinates.
    const step = 52;
    const left = -view.x / view.k, top = -view.y / view.k;
    const right = left + width / view.k, bottom = top + height / view.k;
    ctx.beginPath(); ctx.strokeStyle = "rgba(255,255,255,.035)"; ctx.lineWidth = 1 / view.k;
    for (let x = Math.floor(left / step) * step; x < right; x += step) { ctx.moveTo(x, top); ctx.lineTo(x, bottom); }
    for (let y = Math.floor(top / step) * step; y < bottom; y += step) { ctx.moveTo(left, y); ctx.lineTo(right, y); }
    ctx.stroke();
    const nodes = nodesRef.current, links = linksRef.current;
    const visible = new Set(nodes.filter((node) => !currentSearch || node.id.toLowerCase().includes(currentSearch)).map((node) => node.id));
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const edgeLimit = Math.min(links.length, 12000);
    for (let i = 0; i < edgeLimit; i++) {
      const link = links[i];
      const source = typeof link.source === "string" ? nodeById.get(link.source) : link.source;
      const target = typeof link.target === "string" ? nodeById.get(link.target) : link.target;
      if (!source || !target || source.x == null || source.y == null || target.x == null || target.y == null) continue;
      const relevant = !currentSelected || source.id === currentSelected || target.id === currentSelected;
      ctx.beginPath(); ctx.moveTo(source.x, source.y); ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = relevant ? (currentMode === "funding" ? "rgba(251,146,60,.34)" : "rgba(248,113,113,.25)") : "rgba(148,163,184,.035)";
      ctx.lineWidth = (relevant ? .75 : .45) / view.k; ctx.stroke();
    }
    for (const node of nodes) {
      if (node.x == null || node.y == null) continue;
      const isMatch = !currentSearch || visible.has(node.id);
      const active = currentSelected === node.id;
      const degree = number(node.in_degree) + number(node.out_degree);
      const radius = Math.max(2.2, Math.min(8.5, 2.1 + Math.log2(degree + 1) * 1.2));
      const color = currentMode === "funding" ? (degree >= 4 ? "#fb7185" : "#f59e0b") : (degree >= 5 ? "#fb7185" : degree >= 2 ? "#38bdf8" : "#8b929f");
      if (active) { ctx.beginPath(); ctx.arc(node.x, node.y, radius + 8, 0, Math.PI * 2); ctx.strokeStyle = "rgba(254,202,202,.8)"; ctx.lineWidth = 1.2 / view.k; ctx.setLineDash([3 / view.k, 4 / view.k]); ctx.stroke(); ctx.setLineDash([]); }
      if (isMatch && currentSearch) { ctx.beginPath(); ctx.arc(node.x, node.y, radius + 6, 0, Math.PI * 2); ctx.fillStyle = "rgba(248,113,113,.15)"; ctx.fill(); }
      ctx.beginPath(); ctx.arc(node.x, node.y, radius + (active ? 1.8 : 0), 0, Math.PI * 2);
      ctx.fillStyle = isMatch ? color : "rgba(100,110,125,.13)"; ctx.globalAlpha = isMatch ? (active ? 1 : .78) : .22; ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = active ? "#fff" : color; ctx.lineWidth = (active ? 1.4 : .45) / view.k; ctx.stroke();
      if (active || (currentSearch && isMatch) || (view.k > 1.4 && nodes.length < 300)) {
        ctx.font = `${active ? 11 : 9}px ui-monospace, SFMono-Regular, monospace`;
        ctx.fillStyle = active ? "#fff" : "#b9c0cb"; ctx.fillText(shortAddress(node.id), node.x + radius + 5, node.y + 3);
      }
    }
    ctx.restore();
  }, []);

  useEffect(() => {
    if (loading || !hostRef.current) return;
    simRef.current?.stop();
    const width = hostRef.current.clientWidth || window.innerWidth;
    const height = hostRef.current.clientHeight || window.innerHeight;
    const nodes: SimNode[] = sourceNodes.map((node) => ({ ...node, id: String(node.id ?? "") })).filter((node) => node.id);
    const validIds = new Set(nodes.map((node) => node.id));
    const links: SimLink[] = sourceEdges.map((edge) => ({ source: String(edge.source ?? ""), target: String(edge.target ?? ""), count: number(edge.count) })).filter((edge) => validIds.has(edge.source as string) && validIds.has(edge.target as string));
    nodesRef.current = nodes; linksRef.current = links;
    setNodeCount(nodes.length); setEdgeCount(links.length); setSelected(null);
    viewRef.current = { x: width / 2, y: height / 2, k: 1 };
    const simulation = forceSimulation<SimNode>(nodes)
      .force("link", forceLink<SimNode, SimLink>(links).id((node) => node.id).distance(mode === "funding" ? 72 : 58).strength(.22))
      .force("charge", forceManyBody<SimNode>().strength(nodes.length > 1500 ? -22 : -42).distanceMax(280))
      .force("center", forceCenter<SimNode>(0, 0))
      .force("collision", forceCollide<SimNode>().radius((node) => Math.max(4, 3 + Math.log2(number(node.in_degree) + number(node.out_degree) + 1))).iterations(2))
      .alpha(1).alphaDecay(.035);
    simulation.on("tick", draw);
    simRef.current = simulation;
    setCanvasReady(true);
    const observer = new ResizeObserver(() => draw());
    observer.observe(hostRef.current);
    draw();
    return () => { observer.disconnect(); simulation.stop(); };
  }, [sourceNodes, sourceEdges, mode, loading, draw]);

  useEffect(() => { draw(); }, [draw, selected, search, payload]);

  const finishTour = useCallback(() => {
    const runId = sessionStorage.getItem("sybiltrace_run_id");
    if (runId) sessionStorage.setItem(`sybiltrace_bubble_tour_${runId}`, "done");
    setTourStep(null);
  }, []);
  const sendMessage = () => { const message = chatInput.trim(); if (!message) return; setChatMessages((previous) => [...previous, message]); setChatInput(""); };
  const screenPoint = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: (event.clientX - rect.left - viewRef.current.x) / viewRef.current.k, y: (event.clientY - rect.top - viewRef.current.y) / viewRef.current.k };
  };
  const hitNode = (x: number, y: number) => {
    let best: SimNode | null = null, distance = 14 / viewRef.current.k;
    for (const node of nodesRef.current) { if (node.x == null || node.y == null) continue; const d = Math.hypot(node.x - x, node.y - y); if (d < distance) { best = node; distance = d; } }
    return best;
  };
  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const point = screenPoint(event); const node = hitNode(point.x, point.y);
    dragRef.current = { kind: node ? "node" : "pan", node: node ?? undefined, px: event.clientX, py: event.clientY, moved: false };
    if (node) { node.fx = node.x; node.fy = node.y; simRef.current?.alphaTarget(.18).restart(); }
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current; if (!drag) return;
    const dx = event.clientX - drag.px, dy = event.clientY - drag.py;
    if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
    if (drag.kind === "pan" || !drag.node) { viewRef.current.x += dx; viewRef.current.y += dy; }
    else { const point = screenPoint(event); drag.node.fx = point.x; drag.node.fy = point.y; }
    drag.px = event.clientX; drag.py = event.clientY; draw();
  };
  const onPointerUp = () => {
    const drag = dragRef.current; if (!drag) return;
    if (drag.kind === "node" && drag.node) {
      if (!drag.moved) setSelected(drag.node.id);
      else { drag.node.fx = null; drag.node.fy = null; }
    }
    simRef.current?.alphaTarget(0); dragRef.current = null; draw();
  };
  const zoom = (factor: number) => { const canvas = canvasRef.current; if (!canvas) return; const rect = canvas.getBoundingClientRect(); const cx = rect.width / 2, cy = rect.height / 2; const view = viewRef.current; const k = Math.max(.15, Math.min(5, view.k * factor)); view.x = cx - (cx - view.x) * (k / view.k); view.y = cy - (cy - view.y) * (k / view.k); view.k = k; draw(); };
  const onWheel = (event: React.WheelEvent<HTMLCanvasElement>) => { event.preventDefault(); const rect = event.currentTarget.getBoundingClientRect(); const x = event.clientX - rect.left, y = event.clientY - rect.top; const view = viewRef.current; const k = Math.max(.15, Math.min(5, view.k * (event.deltaY < 0 ? 1.12 : .89))); view.x = x - (x - view.x) * (k / view.k); view.y = y - (y - view.y) * (k / view.k); view.k = k; draw(); };

  return <main className="fixed inset-0 overflow-hidden bg-[#06070a] text-zinc-100">
    <div ref={hostRef} className="absolute inset-0"><canvas ref={canvasRef} className="absolute inset-0 touch-none cursor-crosshair" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} onWheel={onWheel} aria-label="Interactive full-screen wallet network canvas" /></div>
    <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-[#06070a]/95 to-transparent" />
    <header className="absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 p-4 md:p-6">
      <div className="pointer-events-auto flex items-center gap-3">
        <Link href="/dashboard" className="rounded-xl border border-white/10 bg-[#0b0c11]/80 p-2.5 text-zinc-400 backdrop-blur hover:text-white"><ArrowLeft size={17}/></Link>
        <div><p className="text-[9px] tracking-[.25em] text-red-300 md:text-[10px]">SYBILTRACE / NETWORK INTELLIGENCE</p><h1 className="mt-1 text-base font-semibold md:text-lg">Bubblemap <span className="text-zinc-500">/ live canvas</span></h1><p className="mt-1 text-[10px] text-zinc-600">{nodeCount.toLocaleString()} wallets · {edgeCount.toLocaleString()} relationships · D3 force layout</p></div>
      </div>
      <div className="pointer-events-auto flex max-w-[68vw] flex-wrap items-center justify-end gap-2">
        <div className="flex rounded-xl border border-white/10 bg-[#0b0c11]/85 p-1 backdrop-blur">
          <button onClick={() => setMode("aggregated")} className={`rounded-lg px-3 py-2 text-[10px] transition md:px-4 md:text-xs ${mode === "aggregated" ? "bg-red-500/20 text-red-100" : "text-zinc-500 hover:text-white"}`}>Aggregated TX</button>
          <button onClick={() => setMode("funding")} className={`rounded-lg px-3 py-2 text-[10px] transition md:px-4 md:text-xs ${mode === "funding" ? "bg-orange-500/15 text-orange-100" : "text-zinc-500 hover:text-white"}`}>First-fund</button>
        </div>
        <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#0b0c11]/85 px-3 py-2.5 backdrop-blur"><Search size={13} className="text-zinc-500"/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find wallet…" className="w-24 bg-transparent text-xs outline-none placeholder:text-zinc-700 md:w-40"/></label>
        <button onClick={() => setTourStep(0)} title="Guided tour" className="rounded-xl border border-white/10 bg-[#0b0c11]/85 p-2.5 text-zinc-400 backdrop-blur hover:text-white"><CircleHelp size={16}/></button>
      </div>
    </header>
    {loading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#06070a]/70 backdrop-blur-sm"><div className="text-center"><div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-red-500/20 border-t-red-400"/><p className="text-sm text-zinc-400">Reconstructing wallet network…</p></div></div>}
    {error && <div className="absolute left-1/2 top-28 z-30 w-[min(560px,90vw)] -translate-x-1/2 rounded-xl border border-red-500/30 bg-[#10090c]/95 p-4 text-sm text-red-200">{error} <Link className="ml-2 underline" href="/forensic">Start investigation</Link></div>}
    {!loading && nodeCount === 0 && !error && <div className="absolute inset-0 z-10 flex items-center justify-center text-center"><div><Network className="mx-auto h-10 w-10 text-zinc-700"/><p className="mt-4 text-sm text-zinc-300">No graph nodes in this investigation</p><p className="mt-1 text-xs text-zinc-600">Run a forensic investigation to populate the canvas.</p></div></div>}
    <div className="absolute bottom-5 left-5 z-20 flex items-end gap-2">
      <div className="flex flex-col overflow-hidden rounded-xl border border-white/10 bg-[#090a0e]/85 backdrop-blur">
        <button onClick={() => zoom(1.2)} className="p-3 text-zinc-400 hover:text-white" title="Zoom in"><Plus size={15}/></button><div className="h-px bg-white/10"/><button onClick={() => zoom(.83)} className="p-3 text-zinc-400 hover:text-white" title="Zoom out"><Minus size={15}/></button><div className="h-px bg-white/10"/><button onClick={() => { viewRef.current = { x: (hostRef.current?.clientWidth ?? window.innerWidth) / 2, y: (hostRef.current?.clientHeight ?? window.innerHeight) / 2, k: 1 }; draw(); }} className="p-3 text-zinc-400 hover:text-white" title="Reset view"><Maximize2 size={14}/></button>
      </div>
      <div className="rounded-xl border border-white/10 bg-[#090a0e]/85 px-3 py-2.5 text-[10px] text-zinc-500 backdrop-blur"><div className="mb-1.5 tracking-[.16em] text-zinc-400">NODE KEY</div><div className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-rose-400"/> High connectivity</div><div className="mt-1 flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-sky-400"/> Connected wallet</div><div className="mt-1 flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-zinc-500"/> Peripheral wallet</div></div>
    </div>
    <div className="absolute bottom-5 right-5 z-20 flex items-center gap-2 rounded-xl border border-white/10 bg-[#090a0e]/85 px-3 py-2 text-[10px] text-zinc-500 backdrop-blur"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"/>{canvasReady ? "FORCE SIMULATION ACTIVE" : "INITIALIZING"}<span className="text-zinc-700">·</span>{mode === "funding" ? "FUNDING PROVENANCE" : "TRANSFER NETWORK"}</div>
    <AnimatePresence>
      {selected && selectedFeatures && <motion.aside initial={{ x: 360, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 360, opacity: 0 }} className="absolute bottom-20 right-5 top-24 z-30 w-[min(350px,calc(100vw-2.5rem))] overflow-y-auto rounded-2xl border border-white/10 bg-[#090a0e]/95 p-4 shadow-2xl backdrop-blur-xl">
        <div className="mb-4 flex items-center justify-between"><div><p className="text-[9px] tracking-[.2em] text-red-300">WALLET INSPECTOR</p><h2 className="mt-1 text-sm font-semibold">Node intelligence</h2></div><button onClick={() => setSelected(null)} className="rounded-lg p-2 text-zinc-500 hover:text-white"><X size={15}/></button></div>
        <p className="break-all font-mono text-[11px] leading-5 text-zinc-300">{selected}</p>
        <div className="mt-4 space-y-2">{Object.entries(selectedFeatures).filter(([key, value]) => key !== "id" && key !== "x" && key !== "y" && key !== "vx" && key !== "vy" && key !== "fx" && key !== "fy" && value != null && ["string", "number", "boolean"].includes(typeof value)).slice(0, 24).map(([key, value]) => <div key={key} className="flex items-start justify-between gap-3 border-b border-white/[.05] pb-2"><span className="text-[10px] capitalize text-zinc-600">{key.replaceAll("_", " ")}</span><span className="max-w-[62%] break-all text-right font-mono text-[10px] text-zinc-300">{display(value)}</span></div>)}</div>
      </motion.aside>}
    </AnimatePresence>
    <button onClick={() => setShowChat(true)} aria-label="Open AI analyst" className="absolute bottom-24 right-5 z-30 flex h-14 w-14 items-center justify-center rounded-full border border-red-300/40 bg-gradient-to-br from-red-500/30 to-[#160b10] text-red-200 shadow-[0_0_35px_rgba(239,68,68,.25)] transition hover:scale-105"><Bot size={22}/><span className="absolute inset-[-6px] rounded-full border border-red-400/15 animate-ping"/></button>
    <AnimatePresence>{showChat && <motion.aside initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 30 }} className="absolute bottom-40 right-5 z-40 flex h-[min(500px,62vh)] w-[min(370px,calc(100vw - 2.5rem))] flex-col overflow-hidden rounded-2xl border border-red-400/20 bg-[#0b0c11]/95 shadow-2xl backdrop-blur-xl">
      <div className="flex items-center gap-3 border-b border-white/[.08] p-4"><div className="flex h-9 w-9 items-center justify-center rounded-full border border-red-400/30 bg-red-500/10 text-red-300"><Bot size={17}/></div><div className="flex-1"><p className="text-sm font-semibold">Investigation copilot</p><p className="mt-0.5 text-[9px] text-amber-300">PREVIEW · RESPONSES DISABLED</p></div><button onClick={() => setShowChat(false)} className="text-zinc-500 hover:text-white"><X size={16}/></button></div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4"><div className="max-w-[90%] rounded-xl border border-white/[.07] bg-white/[.035] p-3 text-xs leading-5 text-zinc-400">I’m your investigation copilot preview. Responses are not connected yet.</div>{chatMessages.map((message, index) => <div key={index} className="ml-auto max-w-[88%] rounded-xl border border-red-400/20 bg-red-500/[.09] p-3 text-xs text-zinc-200">{message}</div>)}</div>
      <form onSubmit={(event) => { event.preventDefault(); sendMessage(); }} className="flex gap-2 border-t border-white/[.08] p-3"><input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Ask about this network…" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-xs outline-none focus:border-red-400/40"/><button className="rounded-lg bg-red-500/15 px-3 text-red-200 hover:bg-red-500/25" aria-label="Send message"><Send size={15}/></button></form>
    </motion.aside>}</AnimatePresence>
    <AnimatePresence>{tourStep !== null && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 z-50 flex items-center justify-center bg-black/65 p-5 backdrop-blur-sm"><motion.div initial={{ scale: .94, y: 12 }} animate={{ scale: 1, y: 0 }} className="w-full max-w-md rounded-2xl border border-red-400/25 bg-[#0b0c11] p-6 shadow-[0_0_80px_rgba(127,29,29,.18)]"><div className="mb-4 flex items-center justify-between"><span className="text-[9px] tracking-[.22em] text-red-300">FIELD GUIDE / {String(tourStep + 1).padStart(2, "0")}</span><button onClick={finishTour} className="text-xs text-zinc-500 hover:text-white">Skip tour</button></div><h2 className="text-xl font-semibold">{tour[tourStep].title}</h2><p className="mt-3 text-sm leading-6 text-zinc-400">{tour[tourStep].body}</p><div className="mt-6 flex items-center justify-between"><div className="flex gap-1.5">{tour.map((_, index) => <span key={index} className={`h-1 w-6 rounded-full ${index <= tourStep ? "bg-red-400" : "bg-white/10"}`}/>)}</div><button onClick={() => tourStep === tour.length - 1 ? finishTour() : setTourStep(tourStep + 1)} className="rounded-xl bg-red-500/15 px-4 py-2.5 text-xs font-medium text-red-100 hover:bg-red-500/25">{tourStep === tour.length - 1 ? "Start exploring" : "Continue"}</button></div></motion.div></motion.div>}</AnimatePresence>
  </main>;
}
