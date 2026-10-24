"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";

const easeOut = [0.16, 1, 0.3, 1] as const;

export default function InvestigationModePage() {
  const reduceMotion = useReducedMotion();
  const [showSoon, setShowSoon] = useState(false);

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#070708] px-5 py-16 text-white sm:px-8">
      {/* Atmospheric background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_35%,rgba(127,29,29,0.2),transparent_58%)]" />
        <motion.div
          className="absolute left-1/2 top-1/2 h-[650px] w-[650px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-red-500/[0.08]"
          animate={reduceMotion ? undefined : { rotate: 360 }}
          transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
        >
          <span className="absolute left-1/2 top-0 h-2 w-2 -translate-x-1/2 rounded-full bg-red-400 shadow-[0_0_20px_rgba(248,113,113,0.9)]" />
        </motion.div>
        <motion.div
          className="absolute left-1/2 top-1/2 h-[450px] w-[450px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.05]"
          animate={reduceMotion ? undefined : { rotate: -360 }}
          transition={{ duration: 48, repeat: Infinity, ease: "linear" }}
        />
        <div
          className="absolute inset-0 opacity-[0.045]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.3) 1px, transparent 1px)",
            backgroundSize: "54px 54px",
            maskImage: "radial-gradient(ellipse at center, black, transparent 78%)",
          }}
        />
      </div>

      <motion.div
        className="relative z-10 mx-auto w-full max-w-5xl"
        initial={reduceMotion ? false : { opacity: 0, y: 26, filter: "blur(8px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.75, ease: easeOut }}
      >
        <div className="mb-12 text-center">
          <Link
            href="/"
            className="mb-10 inline-flex items-center gap-2 text-xs tracking-[0.2em] text-zinc-500 transition hover:text-white"
          >
            <span aria-hidden="true">←</span> SYBIL<span className="text-red-400">TRACE</span>
          </Link>
          <p className="mb-4 text-[10px] tracking-[0.35em] text-red-300">
            INVESTIGATION PROTOCOL / 01
          </p>
          <h1 className="text-4xl font-semibold tracking-[-0.055em] sm:text-6xl">
            Choose your <span className="text-zinc-500">mode.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-zinc-400 sm:text-base">
            Start with a defined dataset, or explore continuous on-chain monitoring as it becomes available.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <motion.div
            whileHover={reduceMotion ? undefined : { y: -7, scale: 1.01 }}
            transition={{ duration: 0.25, ease: easeOut }}
            className="group relative overflow-hidden rounded-2xl border border-red-400/25 bg-[#0b0b0df0] p-7 shadow-[0_20px_80px_rgba(0,0,0,0.28)] sm:p-9"
          >
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-red-400/80 to-transparent" />
            <div className="absolute right-0 top-0 h-40 w-40 bg-red-500/[0.07] blur-[70px] transition group-hover:bg-red-500/[0.14]" />
            <div className="relative">
              <div className="flex items-start justify-between">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-red-400/20 bg-red-500/[0.08] text-red-300">
                  <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7" stroke="currentColor" strokeWidth="1.5">
                    <path d="M6 3.75h8l4 4V20a.75.75 0 0 1-.75.75h-10.5A.75.75 0 0 1 6 20V3.75Z" />
                    <path d="M14 3.75V8h4M9 12h6M9 15.5h6M9 9h1" />
                  </svg>
                </div>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-3 py-1.5 text-[9px] tracking-[0.18em] text-emerald-300">
                  AVAILABLE NOW
                </span>
              </div>

              <p className="mt-8 font-mono text-[10px] tracking-[0.22em] text-red-300">01 / DATASET-DRIVEN</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight">Forensic Investigation</h2>
              <p className="mt-4 min-h-[72px] text-sm leading-6 text-zinc-400">
                Provide a CSV of token holder addresses and labels at a chosen point in time. You supply the wallet list; SYBILTRACE investigates the relationships and behavioral signals.
              </p>

              <div className="mt-7 space-y-3 border-t border-white/[0.08] pt-5">
                {["Upload your transaction event log", "Specify the target token", "Run an evidence-led investigation"].map((item) => (
                  <div key={item} className="flex items-center gap-3 text-xs text-zinc-300">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border border-red-400/20 text-[10px] text-red-300">✓</span>
                    {item}
                  </div>
                ))}
              </div>

              <Link
                href="/forensic"
                className="group/button mt-8 flex min-h-12 w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200"
              >
                Continue to forensic workspace
                <span className="transition-transform group-hover/button:translate-x-1" aria-hidden="true">→</span>
              </Link>
            </div>
          </motion.div>

          <motion.div
            whileHover={reduceMotion ? undefined : { y: -7, scale: 1.01 }}
            transition={{ duration: 0.25, ease: easeOut }}
            className="group relative overflow-hidden rounded-2xl border border-white/[0.1] bg-[#0b0b0df0] p-7 shadow-[0_20px_80px_rgba(0,0,0,0.28)] sm:p-9"
          >
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />
            <div className="absolute right-0 top-0 h-40 w-40 bg-orange-500/[0.04] blur-[70px] transition group-hover:bg-orange-500/[0.09]" />
            <div className="relative">
              <div className="flex items-start justify-between">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-zinc-300">
                  <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="8.5" />
                    <path d="M12 7v5l3.5 2M12 1v2M23 12h-2M3 12H1" />
                  </svg>
                </div>
                <span className="rounded-full border border-amber-400/20 bg-amber-400/[0.06] px-3 py-1.5 text-[9px] tracking-[0.18em] text-amber-200">
                  IN DEVELOPMENT
                </span>
              </div>

              <p className="mt-8 font-mono text-[10px] tracking-[0.22em] text-zinc-500">02 / CONTINUOUS MONITORING</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight">Real-Time Investigation</h2>
              <p className="mt-4 min-h-[72px] text-sm leading-6 text-zinc-400">
                Monitor on-chain activity as it happens and trigger investigations as new transactions and coordination signals emerge.
              </p>

              <div className="mt-7 space-y-3 border-t border-white/[0.08] pt-5">
                {["Live transaction monitoring", "Continuous signal detection", "Investigation as activity unfolds"].map((item) => (
                  <div key={item} className="flex items-center gap-3 text-xs text-zinc-400">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border border-white/10 text-[10px] text-zinc-500">·</span>
                    {item}
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => setShowSoon(true)}
                className="mt-8 flex min-h-12 w-full items-center justify-center gap-3 rounded-lg border border-white/15 bg-white/[0.04] px-5 py-3 text-sm font-semibold text-white transition hover:border-white/25 hover:bg-white/[0.08]"
              >
                {showSoon ? "Coming soon" : "Explore real-time mode"}
                <span aria-hidden="true">↗</span>
              </button>

              {showSoon && (
                <motion.p
                  role="status"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 rounded-lg border border-amber-400/15 bg-amber-400/[0.05] px-4 py-3 text-center text-xs text-amber-100"
                >
                  Stay tuned — real-time investigation is coming soon.
                </motion.p>
              )}
            </div>
          </motion.div>
        </div>

        <p className="mt-8 text-center text-[10px] tracking-wide text-zinc-600">
          SYBILTRACE · INVESTIGATE WITH EVIDENCE. NOT ASSUMPTIONS.
        </p>
      </motion.div>
    </main>
  );
}
