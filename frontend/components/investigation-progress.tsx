"use client";

import type { ReactNode } from "react";

export type PipelineStage = {
  step: string;
  title: string;
  detail: string;
  state: "running" | "finished" | "failed";
  elapsed_seconds?: number;
};

type InvestigationProgressProps = {
  stages: PipelineStage[];
  backendStatus: string;
  failed: boolean;
};

function StageIcon({ state }: { state: PipelineStage["state"] }) {
  if (state === "running") {
    return (
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
    );
  }

  if (state === "finished") {
    return <span className="text-sm text-emerald-400">✓</span>;
  }

  return <span className="text-sm font-semibold text-red-400">!</span>;
}

function StageRow({
  stage,
  nested = false,
}: {
  stage: PipelineStage;
  nested?: boolean;
}) {
  return (
    <div
      className={`flex items-start gap-3 rounded-xl border p-3 transition-colors ${
        stage.state === "running"
          ? "border-red-400/20 bg-red-500/[0.045]"
          : stage.state === "failed"
            ? "border-red-400/20 bg-red-950/20"
            : "border-white/[0.06] bg-white/[0.015]"
      } ${nested ? "ml-4" : ""}`}
    >
      <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
        <StageIcon state={stage.state} />
      </div>

      <div className="min-w-0 flex-1">
        <p
          className={`text-xs font-medium ${
            stage.state === "running"
              ? "text-red-200"
              : stage.state === "failed"
                ? "text-red-300"
                : "text-zinc-300"
          }`}
        >
          {stage.title}
        </p>
        <p className="mt-1 text-[11px] leading-5 text-zinc-500">
          {stage.detail}
        </p>
      </div>

      {stage.elapsed_seconds !== undefined && (
        <span className="shrink-0 pt-0.5 font-mono text-[10px] text-zinc-600">
          {stage.elapsed_seconds.toFixed(2)}s
        </span>
      )}
    </div>
  );
}

export default function InvestigationProgress({
  stages,
  backendStatus,
  failed,
}: InvestigationProgressProps) {
  const processMiningParent = stages.find(
    (stage) => stage.step === "12_run_process_mining",
  );
  const processMiningChildren = stages.filter((stage) =>
    /^12_\d{2}_/.test(stage.step),
  );
  const mainStages = stages.filter(
    (stage) =>
      !/^12_\d{2}_/.test(stage.step) &&
      stage.step !== "12_run_process_mining",
  );
  const activeStage = [...stages]
    .reverse()
    .find((stage) => stage.state === "running");
  const completedCount = stages.filter(
    (stage) => stage.state === "finished",
  ).length;

  const parentStage: PipelineStage | undefined = processMiningParent ?? (
    processMiningChildren.length > 0
      ? {
          step: "12_run_process_mining",
          title: "Running Process Mining",
          detail: "Analyzing wallet actions, behavioral variants, and intermediary activity.",
          state: processMiningChildren.some((stage) => stage.state === "running")
            ? "running"
            : processMiningChildren.some((stage) => stage.state === "failed")
              ? "failed"
              : "finished",
        }
      : undefined
  );

  const content: ReactNode[] = [];
  let processMiningGroupAdded = false;

  for (const stage of stages) {
    if (/^12_\\d{2}_/.test(stage.step)) {
      if (!processMiningGroupAdded && !processMiningParent) {
        processMiningGroupAdded = true;
        content.push(
          <div
            key="process-mining-group"
            className="space-y-2 rounded-xl border border-white/[0.07] bg-white/[0.015] p-3"
          >
            {parentStage && <StageRow stage={parentStage} />}
            {processMiningChildren.map((child) => (
              <StageRow key={child.step} stage={child} nested />
            ))}
          </div>,
        );
      }
      continue;
    }

    if (stage.step === "12_run_process_mining") {
      processMiningGroupAdded = true;
      content.push(
        <div
          key="process-mining-group"
          className="space-y-2 rounded-xl border border-white/[0.07] bg-white/[0.015] p-3"
        >
          {parentStage && <StageRow stage={parentStage} />}
          {processMiningChildren.map((child) => (
            <StageRow key={child.step} stage={child} nested />
          ))}
        </div>,
      );
      continue;
    }

    content.push(<StageRow key={stage.step} stage={stage} />);
  }

  if (!processMiningGroupAdded && parentStage) {
    content.push(
      <div
        key="process-mining-group"
        className="space-y-2 rounded-xl border border-white/[0.07] bg-white/[0.015] p-3"
      >
        <StageRow stage={parentStage} />
        {processMiningChildren.map((child) => (
          <StageRow key={child.step} stage={child} nested />
        ))}
      </div>,
    );
  }

  return (
    <div className="min-h-[340px] space-y-5 py-2">
      <div className="flex items-start gap-4">
        <div className="relative mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-red-400/15 bg-red-500/[0.06]">
          {failed ? (
            <span className="text-lg font-semibold text-red-300">!</span>
          ) : activeStage ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
          ) : stages.length > 0 && stages.every((stage) => stage.state === "finished") ? (
            <span className="text-lg text-emerald-300">✓</span>
          ) : (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-red-400" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-zinc-200">
            {failed
              ? "Investigation failed"
              : activeStage?.title ??
                stages[stages.length - 1]?.title ??
                "Preparing investigation results"}
          </p>
          <p className="mt-2 text-xs leading-5 text-zinc-500">
            {failed
              ? "The backend reported an error while processing this investigation."
              : activeStage?.detail ??
                (stages.length === 0
                  ? "Waiting for the backend to start reporting progress."
                  : "The backend is finalizing the investigation results.")}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] uppercase tracking-wider text-zinc-600">
            Backend status
          </span>
          <span className="max-w-[65%] truncate text-right text-[10px] text-zinc-400">
            {backendStatus}
          </span>
        </div>
      </div>

      {stages.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-500">
              Pipeline progress
            </p>
            <p className="text-[10px] tabular-nums text-zinc-600">
              {completedCount} / {stages.length} steps completed
            </p>
          </div>
          <div className="space-y-2">{content}</div>
        </div>
      )}
    </div>
  );
}
