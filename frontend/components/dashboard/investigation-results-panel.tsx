
"use client";

import { useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Braces,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Copy,
  GitBranch,
  Network,
  Wallet,
} from "lucide-react";
import InvestigationProgress, {
  type PipelineStage,
} from "@/components/investigation-progress";

type GraphSummary = {
  nodes?: number;
  edges?: number;
  data?: unknown;
};

type Investigation = {
  final_response?: string | null;
  initial_observation?: unknown;
  investigation_round?: number;
  investigation_complete?: boolean;
};

type Analysis = {
  first_fund_graph?: GraphSummary;
  aggregated_tx_graph?: GraphSummary;
  wallet_features?: unknown;
  investigation?: Investigation;
};

type Ingestion = {
  filename?: string;
  token_address?: string;
  addresses_processed?: number;
  addresses_skipped?: number;
  data?: unknown[];
};

type InvestigationPayload = {
  ingestion?: Ingestion;
  analysis?: Analysis;
};

type Props = {
  result: InvestigationPayload | null;
  resultStatus: string;
  pipelineStages: PipelineStage[];
  isFailed: boolean;
};

function formatNumber(value: unknown) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US").format(value)
    : "—";
}

function getConclusion(value: unknown): string | null {
  if (typeof value === "string") return value;

  if (value && typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return null;
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-white">
        {value}
      </div>
    </div>
  );
}

function GraphCard({
  title,
  description,
  graph,
  icon: Icon,
}: {
  title: string;
  description: string;
  graph?: GraphSummary;
  icon: typeof Network;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0c0c0f]/90 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-zinc-100">{title}</h3>
          <p className="mt-1 text-xs text-zinc-500">{description}</p>
        </div>

        <div className="rounded-lg border border-red-500/20 bg-red-500/[0.08] p-2">
          <Icon className="h-4 w-4 text-red-400" />
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Stat label="Nodes" value={formatNumber(graph?.nodes)} />
        <Stat label="Edges" value={formatNumber(graph?.edges)} />
      </div>

      <div className="mt-3 text-[11px] text-zinc-600">
        {graph?.data ? "Graph data available" : "Graph data unavailable"}
      </div>
    </div>
  );
}

export default function InvestigationResultsPanel({
  result,
  resultStatus,
  pipelineStages,
  isFailed,
}: Props) {
  const [showRawResult, setShowRawResult] = useState(false);
  const [copied, setCopied] = useState(false);

  // Live pipeline progress occupies the original loading state.
  if (!result) {
    return (
      <section className="rounded-xl border border-white/10 bg-[#101013]/90 p-6">
        <div className="mb-5">
          <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">
            Forensic report
          </div>

          <h2 className="mt-2 text-xl font-semibold tracking-tight text-white">
            Investigation Results
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Live analysis pipeline progress
          </p>
        </div>

        <InvestigationProgress
          stages={pipelineStages}
          backendStatus={resultStatus}
          failed={isFailed}
        />
      </section>
    );
  }

  // Existing completed-results UI.
  const ingestion = result.ingestion;
  const analysis = result.analysis;
  const investigation = analysis?.investigation;
  const tokenAddress = ingestion?.token_address;
  const conclusion = getConclusion(investigation?.final_response);
  const processed = ingestion?.addresses_processed ?? 0;
  const skipped = ingestion?.addresses_skipped ?? 0;
  const totalAddresses = processed + skipped;

  async function copyAddress() {
    if (!tokenAddress) return;

    await navigator.clipboard.writeText(tokenAddress);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-zinc-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Forensic report
          </div>

          <h2 className="mt-2 text-xl font-semibold tracking-tight text-white">
            Investigation Results
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            On-chain graph analysis and agent assessment
          </p>
        </div>

        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/[0.07] px-3 py-1.5 text-xs text-emerald-300">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Results available
        </div>
      </div>

      {/* Target token */}
      <div className="rounded-xl border border-white/10 bg-[#101013]/90 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-2.5">
            <Wallet className="h-5 w-5 text-zinc-300" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="text-xs uppercase tracking-wider text-zinc-500">
              Target token · Solana
            </div>

            <div className="mt-2 break-all font-mono text-sm text-zinc-100">
              {tokenAddress ?? "Token address unavailable"}
            </div>

            {tokenAddress && (
              <button
                type="button"
                onClick={copyAddress}
                className="mt-3 inline-flex items-center gap-2 text-xs text-zinc-400 transition hover:text-white"
              >
                <Copy className="h-3.5 w-3.5" />
                {copied ? "Copied" : "Copy address"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Ingestion overview */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4 text-zinc-400" />
          <h3 className="text-sm font-medium text-zinc-200">
            Data ingestion
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat
            label="Total addresses"
            value={formatNumber(totalAddresses)}
          />
          <Stat
            label="Ingested"
            value={formatNumber(processed)}
          />
          <Stat
            label="Cached"
            value={formatNumber(skipped)}
          />

          <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
            <div className="text-xs text-zinc-500">Source CSV</div>
            <div
              className="mt-2 truncate text-sm font-medium text-zinc-200"
              title={ingestion?.filename ?? undefined}
            >
              {ingestion?.filename ?? "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Graph metrics */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-zinc-400" />
          <h3 className="text-sm font-medium text-zinc-200">
            Network analysis
          </h3>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <GraphCard
            title="First-fund graph"
            description="Initial funding relationships"
            graph={analysis?.first_fund_graph}
            icon={Network}
          />

          <GraphCard
            title="Aggregated transaction graph"
            description="Observed wallet transfer connections"
            graph={analysis?.aggregated_tx_graph}
            icon={GitBranch}
          />
        </div>
      </div>

      {/* Agent conclusion */}
      <div className="overflow-hidden rounded-xl border border-red-500/20 bg-[#100d0f]/90">
        <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
          <div className="rounded-md bg-red-500/10 p-1.5">
            <ArrowUpRight className="h-4 w-4 text-red-400" />
          </div>

          <div className="flex-1">
            <h3 className="text-sm font-medium text-white">
              Agent assessment
            </h3>
            <p className="mt-0.5 text-xs text-zinc-500">
              Final investigation response
            </p>
          </div>

          {typeof investigation?.investigation_round === "number" && (
            <span className="text-xs text-zinc-500">
              {investigation.investigation_round} rounds
            </span>
          )}
        </div>

        <div className="p-4">
          {conclusion ? (
            <div className="whitespace-pre-wrap break-words text-sm leading-7 text-zinc-300">
              {conclusion}
            </div>
          ) : (
            <p className="text-sm text-zinc-500">
              The backend did not return a final agent response.
            </p>
          )}
        </div>
      </div>

      {/* Advanced data */}
      <div className="overflow-hidden rounded-xl border border-white/10 bg-[#101013]/90">
        <button
          type="button"
          onClick={() => setShowRawResult((value) => !value)}
          aria-expanded={showRawResult}
          className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition hover:bg-white/[0.03]"
        >
          <Braces className="h-4 w-4 text-zinc-400" />

          <div className="flex-1">
            <div className="text-sm font-medium text-zinc-200">
              Advanced data
            </div>
            <div className="mt-0.5 text-xs text-zinc-500">
              Inspect the complete backend payload
            </div>
          </div>

          <span className="text-xs text-zinc-500">
            {showRawResult ? "Hide JSON" : "View JSON"}
          </span>

          <ChevronDown
            className={`h-4 w-4 text-zinc-500 transition-transform ${
              showRawResult ? "rotate-180" : ""
            }`}
          />
        </button>

        {showRawResult && (
          <div className="border-t border-white/10 p-4">
            <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/40 p-4 font-mono text-xs leading-5 text-zinc-400">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </section>
  );
}
