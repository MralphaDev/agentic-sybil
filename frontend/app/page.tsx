import Link from "next/link";
import AgentTerminal from "@/components/agent-terminal";

const features = [
  {
    number: "01",
    title: "Trace funding relationships",
    description:
      "Map initial funding sources and uncover suspicious wallet connections.",
  },
  {
    number: "02",
    title: "Analyze coordinated behavior",
    description:
      "Compare wallet activity, behavioral similarities and transaction patterns.",
  },
  {
    number: "03",
    title: "Build explainable evidence",
    description:
      "Connect on-chain signals into an investigation with traceable supporting evidence.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#080809] text-white">
      {/* Cinematic background */}
      <div className="pointer-events-none fixed inset-0">
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/images/hero-poster.jpg"
          className="absolute inset-0 h-full w-full object-cover opacity-100"
        >
          <source src="/videos/bg.mp4" type="video/mp4" />
        </video>

        <div className="absolute inset-0 bg-gradient-to-r from-[#080809]/85 via-[#080809]/45 to-[#080809]/15" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#080809]/75 via-transparent to-black/20" />

        <div
          className="absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px)",
            backgroundSize: "76px 76px",
            maskImage:
              "linear-gradient(to bottom, transparent, black 25%, black 75%, transparent)",
          }}
        />
      </div>

      {/* Navigation */}
      <header className="relative z-10 border-b border-white/[0.09]">
        <nav className="mx-auto flex h-[72px] max-w-[1400px] items-center justify-between px-6 lg:px-12">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-red-500/30 bg-red-500/10">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="h-5 w-5 text-red-400"
                stroke="currentColor"
                strokeWidth="1.6"
              >
                <path d="M12 2.8 20 7v5.5c0 4.1-3.1 7.1-8 8.7-4.9-1.6-8-4.6-8-8.7V7l8-4.2Z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
            </div>

            <span className="text-sm font-bold tracking-[0.2em]">
              SYBIL<span className="text-red-400">TRACE</span>
            </span>
          </Link>

          <div className="hidden items-center gap-8 text-sm text-zinc-400 md:flex">
            <a href="#platform" className="transition hover:text-white">
              Platform
            </a>
            <a href="#methodology" className="transition hover:text-white">
              Methodology
            </a>
            <a href="#about" className="transition hover:text-white">
              About
            </a>
          </div>

          <Link
            href="/forensic"
            className="inline-flex items-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-zinc-200"
          >
            Run Investigation
            <span aria-hidden="true">↗</span>
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto grid min-h-[calc(100svh-72px)] max-w-[1400px] items-center gap-16 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-12 lg:py-24">
        <div className="max-w-2xl">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-zinc-300 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-red-400 shadow-[0_0_12px_rgba(248,113,113,0.8)]" />
            AUTONOMOUS ON-CHAIN INVESTIGATION
          </div>

          <h1 className="text-5xl leading-[1.06] font-semibold tracking-[-0.055em] sm:text-6xl lg:text-7xl">
            Follow the
            <br />
            <span className="text-zinc-400">evidence.</span>
            <br />
            Uncover the
            <br />
            <span className="bg-gradient-to-r from-red-400 via-red-500 to-orange-400 bg-clip-text text-transparent">
              coordination.
            </span>
          </h1>

          <p className="mt-7 max-w-xl text-base leading-7 text-zinc-300 sm:text-lg sm:leading-8">
            Investigate suspicious on-chain activity with an autonomous
            blockchain forensics agent. Trace funding networks, examine
            wallet behavior and turn transaction data into explainable evidence.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/forensic"
              className="inline-flex min-h-12 items-center justify-center gap-3 rounded-md bg-white px-6 text-sm font-semibold text-black transition hover:bg-zinc-200"
            >
              Run Investigation
              <span aria-hidden="true">↗</span>
            </Link>

            <a
              href="#platform"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-md border border-white/15 bg-white/[0.03] px-6 text-sm font-medium text-zinc-200 transition hover:border-white/30 hover:bg-white/[0.07]"
            >
              Explore the platform
              <span aria-hidden="true">↓</span>
            </a>
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-white/10 pt-6 text-xs tracking-wide text-zinc-300">
            <span>GRAPH-BASED ANALYSIS</span>
            <span className="hidden text-zinc-500 sm:inline">/</span>
            <span>BEHAVIORAL FORENSICS</span>
            <span className="hidden text-zinc-500 sm:inline">/</span>
            <span>EXPLAINABLE EVIDENCE</span>
          </div>
        </div>

        <div className="relative flex items-center justify-center py-8 lg:py-0">
          <div className="absolute h-[420px] w-[420px] rounded-full border border-white/[0.06]" />
          <div className="absolute h-[320px] w-[320px] rounded-full border border-white/[0.06]" />
          <div className="absolute h-[220px] w-[220px] rounded-full bg-red-500/[0.06] blur-3xl" />

          <AgentTerminal />
        </div>
      </section>

      {/* Platform features */}
      <section
        id="platform"
        className="relative z-10 border-t border-white/10 bg-[#09090bf0] px-6 py-24 backdrop-blur-sm lg:px-12"
      >
        <div className="mx-auto max-w-[1400px]">
          <div className="max-w-2xl">
            <p className="text-xs tracking-[0.25em] text-red-400">
              INVESTIGATION CAPABILITIES
            </p>

            <h2 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">
              From raw transactions
              <br />
              to actionable evidence.
            </h2>

            <p className="mt-5 leading-7 text-zinc-400">
              A structured investigation workflow that combines on-chain
              relationships, wallet behavior and agent-led evidence analysis.
            </p>
          </div>

          <div
            id="methodology"
            className="mt-14 grid gap-px overflow-hidden rounded-xl border border-white/10 bg-white/10 md:grid-cols-3"
          >
            {features.map((feature) => (
              <article
                key={feature.number}
                className="group bg-[#0b0b0df5] p-7 transition hover:bg-[#111114]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-red-400">
                    / {feature.number}
                  </span>
                  <span className="text-xl text-zinc-600 transition group-hover:text-red-400">
                    ↗
                  </span>
                </div>

                <h3 className="mt-10 text-lg font-semibold">
                  {feature.title}
                </h3>

                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>

          <div
            id="about"
            className="mt-16 flex flex-col justify-between gap-6 border-t border-white/10 pt-7 text-xs text-zinc-500 sm:flex-row"
          >
            <span>SYBILTRACE · ON-CHAIN FORENSICS</span>
            <span>INVESTIGATE WITH EVIDENCE. NOT ASSUMPTIONS.</span>
          </div>
        </div>
      </section>
    </main>
  );
}