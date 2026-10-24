
"use client";

import { useEffect, useState } from "react";

const investigationSteps = [
  {
    agent: "DATA INGESTION",
    message: "Parsing transaction events...",
    result: "Transaction dataset loaded",
    color: "text-sky-400",
  },
  {
    agent: "FUNDING ANALYSIS",
    message: "Tracing initial funding sources...",
    result: "Funding relationships mapped",
    color: "text-emerald-400",
  },
  {
    agent: "WALLET CLUSTERING",
    message: "Comparing wallet behavior...",
    result: "Analyzing behavioral similarities",
    color: "text-amber-400",
  },
  {
    agent: "GRAPH INVESTIGATION",
    message: "Examining wallet connectivity...",
    result: "Evaluating connected components",
    color: "text-sky-400",
  },
  {
    agent: "EVIDENCE REVIEW",
    message: "Cross-checking observed patterns...",
    result: "Preparing evidence summary",
    color: "text-emerald-400",
  },
];

export default function AgentTerminal() {
  const [stepIndex, setStepIndex] = useState(0);
  const [history, setHistory] = useState<number[]>([0]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStepIndex((current) => {
        const next = (current + 1) % investigationSteps.length;

        setHistory((previous) => [...previous, next].slice(-4));

        return next;
      });
    }, 2600);

    return () => window.clearInterval(timer);
  }, []);

  const currentStep = investigationSteps[stepIndex];

  return (
    <div className="relative w-full max-w-[490px]">
      <div className="absolute -inset-8 rounded-full bg-red-600/10 blur-3xl" />

      <div className="relative overflow-hidden rounded-xl border border-white/15 bg-[#0b0b0df2] shadow-2xl shadow-black/50 backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </div>

          <div className="flex items-center gap-2 text-[10px] tracking-[0.2em] text-zinc-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
            DEMO ENVIRONMENT
          </div>
        </div>

        <div className="border-b border-white/10 px-5 py-4">
          <div className="text-[10px] tracking-[0.24em] text-zinc-500">
            AUTONOMOUS INVESTIGATION
          </div>

          <div className="mt-2 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-red-500/25 bg-red-500/10">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="h-5 w-5 text-red-400"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M12 3 20 7.5V16.5L12 21 4 16.5V7.5L12 3Z" />
                <path d="M8 12H16M12 8V16" />
              </svg>
            </div>

            <div>
              <div className="text-sm font-semibold text-white">
                Blockchain Forensics Agent
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Multi-stage behavioral investigation
              </div>
            </div>
          </div>
        </div>

        <div className="min-h-[265px] space-y-5 px-5 py-5 font-mono text-xs">
          <div className="text-zinc-500">
            <span className="text-red-400">$</span>{" "}
            initialize_investigation()
          </div>

          {history.map((index, position) => {
            const step = investigationSteps[index];
            const isCurrent = position === history.length - 1;

            return (
              <div
                key={`${position}-${index}`}
                className={`space-y-2 transition-opacity duration-500 ${
                  isCurrent ? "opacity-100" : "opacity-55"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={step.color}>[{step.agent}]</span>
                  {isCurrent && (
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
                  )}
                </div>

                <div className="text-zinc-300">{step.message}</div>

                <div className="flex items-start gap-2 text-emerald-400/90">
                  <span>›</span>
                  <span>{step.result}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-white/10 bg-white/[0.025] px-5 py-3">
          <span className="text-[10px] tracking-wider text-zinc-500">
            PREVIEW · SIMULATED ACTIVITY
          </span>
          <span className="text-[10px] text-zinc-400">
            STEP {stepIndex + 1} / {investigationSteps.length}
          </span>
        </div>
      </div>

      <div className="absolute -bottom-5 -left-5 hidden rounded-lg border border-white/10 bg-[#111113]/95 px-4 py-3 shadow-xl sm:block">
        <div className="text-[10px] tracking-widest text-zinc-500">
          INVESTIGATION ENGINE
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-zinc-200">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          Autonomous analysis preview
        </div>
      </div>
    </div>
  );
}
