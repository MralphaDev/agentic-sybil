"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
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

const easeOut = [0.16, 1, 0.3, 1] as const;

const staggerContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.13,
      delayChildren: 0.15,
    },
  },
};

const heroItem = {
  hidden: {
    opacity: 0,
    y: 32,
    filter: "blur(8px)",
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: 0.85,
      ease: easeOut,
    },
  },
};

const sectionReveal = {
  hidden: {
    opacity: 0,
    y: 38,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: easeOut,
    },
  },
};

export default function Home() {
  const reduceMotion = useReducedMotion();
  const router = useRouter();
  const [transitioning, setTransitioning] = useState(false);

  const beginTransition = () => {
    if (transitioning) return;
    setTransitioning(true);
    window.setTimeout(() => router.push("/investigation-mode"), reduceMotion ? 100 : 1050);
  };

  const revealInitial = reduceMotion ? false : "hidden";
  const revealVisible = reduceMotion ? undefined : "visible";

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080809] text-white">
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

        {/* Animated grid */}
        <motion.div
          className="absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px)",
            backgroundSize: "76px 76px",
            maskImage:
              "linear-gradient(to bottom, transparent, black 25%, black 75%, transparent)",
          }}
          animate={
            reduceMotion
              ? undefined
              : {
                  backgroundPosition: ["0px 0px", "76px 76px"],
                }
          }
          transition={{
            duration: 18,
            repeat: Infinity,
            ease: "linear",
          }}
        />

        {/* Red energy glow */}
        <motion.div
          className="absolute -right-32 top-[12%] h-[500px] w-[500px] rounded-full bg-red-600/[0.13] blur-[140px]"
          animate={
            reduceMotion
              ? undefined
              : {
                  x: [0, -80, 20, 0],
                  y: [0, 50, -30, 0],
                  scale: [1, 1.18, 0.92, 1],
                }
          }
          transition={{
            duration: 16,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        <motion.div
          className="absolute -left-40 top-[55%] h-[380px] w-[380px] rounded-full bg-orange-600/[0.08] blur-[120px]"
          animate={
            reduceMotion
              ? undefined
              : {
                  x: [0, 60, -20, 0],
                  y: [0, -45, 25, 0],
                }
          }
          transition={{
            duration: 13,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Moving scan beam */}
        {!reduceMotion && (
          <motion.div
            className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-red-400/30 to-transparent"
            animate={{ top: ["8%", "92%", "8%"] }}
            transition={{
              duration: 14,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        )}
      </div>

      {/* Navigation */}
      <motion.header
        className="relative z-10 border-b border-white/[0.09]"
        initial={reduceMotion ? false : { opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: easeOut }}
      >
        <nav className="mx-auto flex h-[72px] max-w-[1400px] items-center justify-between px-6 lg:px-12">
          <Link href="/" className="group flex items-center gap-3">
            <motion.div
              whileHover={
                reduceMotion
                  ? undefined
                  : {
                      rotate: -8,
                      scale: 1.08,
                    }
              }
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-red-500/30 bg-red-500/10 transition-colors group-hover:border-red-400/60"
            >
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
            </motion.div>

            <span className="text-sm font-bold tracking-[0.2em]">
              SYBIL<span className="text-red-400">TRACE</span>
            </span>
          </Link>

          <div className="hidden items-center gap-8 text-sm text-zinc-400 md:flex">
            {[
              ["Platform", "#platform"],
              ["Methodology", "#methodology"],
              ["About", "#about"],
            ].map(([label, href]) => (
              <a
                key={label}
                href={href}
                className="relative py-2 transition hover:text-white"
              >
                {label}
                <motion.span
                  className="absolute inset-x-0 bottom-0 h-px origin-left bg-red-400"
                  initial={{ scaleX: 0 }}
                  whileHover={{ scaleX: 1 }}
                  transition={{ duration: 0.25 }}
                />
              </a>
            ))}
          </div>

          <Link
            href="/investigation-mode"
            onClick={(event) => {
              event.preventDefault();
              beginTransition();
            }}
            className="group inline-flex items-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-zinc-200"
          >
            Run Investigation
            <motion.span
              aria-hidden="true"
              className="inline-block"
              whileHover={reduceMotion ? undefined : { x: 3, y: -3 }}
            >
              ↗
            </motion.span>
          </Link>
        </nav>
      </motion.header>

      {/* Hero */}
      <section className="relative z-10 mx-auto grid min-h-[calc(100svh-72px)] max-w-[1400px] items-center gap-16 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-12 lg:py-24">
        {/* Hero copy */}
        <motion.div
          className="max-w-2xl"
          variants={staggerContainer}
          initial={revealInitial}
          animate={revealVisible}
        >
          <motion.div
            variants={heroItem}
            className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-zinc-300 backdrop-blur-sm"
          >
            <motion.span
              className="h-1.5 w-1.5 rounded-full bg-red-400 shadow-[0_0_12px_rgba(248,113,113,0.8)]"
              animate={
                reduceMotion
                  ? undefined
                  : {
                      opacity: [1, 0.35, 1],
                      scale: [1, 1.45, 1],
                    }
              }
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            AUTONOMOUS ON-CHAIN INVESTIGATION
          </motion.div>

          <motion.h1
            variants={heroItem}
            className="text-5xl leading-[1.06] font-semibold tracking-[-0.055em] sm:text-6xl lg:text-7xl"
          >
            Follow the
            <br />
            <span className="text-zinc-400">evidence.</span>
            <br />
            Uncover the
            <br />
            <span className="relative inline-block bg-gradient-to-r from-red-400 via-red-500 to-orange-400 bg-clip-text text-transparent">
              coordination.
              {!reduceMotion && (
                <motion.span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/70 to-transparent bg-clip-text text-transparent"
                  style={{
                    backgroundSize: "200% 100%",
                  }}
                  animate={{
                    backgroundPosition: ["100% 0%", "-100% 0%"],
                  }}
                  transition={{
                    duration: 3.5,
                    repeat: Infinity,
                    repeatDelay: 2.5,
                    ease: "linear",
                  }}
                >
                  coordination.
                </motion.span>
              )}
            </span>
          </motion.h1>

          <motion.p
            variants={heroItem}
            className="mt-7 max-w-xl text-base leading-7 text-zinc-300 sm:text-lg sm:leading-8"
          >
            Investigate suspicious on-chain activity with an autonomous
            blockchain forensics agent. Trace funding networks, examine
            wallet behavior and turn transaction data into explainable evidence.
          </motion.p>

          <motion.div
            variants={heroItem}
            className="mt-9 flex flex-col gap-3 sm:flex-row"
          >
            <Link
              href="/investigation-mode"
            onClick={(event) => {
              event.preventDefault();
              beginTransition();
            }}
              className="group relative inline-flex min-h-12 items-center justify-center gap-3 overflow-hidden rounded-md bg-white px-6 text-sm font-semibold text-black transition hover:bg-zinc-200"
            >
              {!reduceMotion && (
                <motion.span
                  aria-hidden="true"
                  className="absolute inset-y-0 -left-1/2 w-1/3 skew-x-[-20deg] bg-gradient-to-r from-transparent via-black/10 to-transparent"
                  animate={{ left: ["-40%", "140%"] }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    repeatDelay: 2,
                    ease: "easeInOut",
                  }}
                />
              )}
              <span className="relative">Run Investigation</span>
              <span className="relative transition-transform group-hover:translate-x-1">
                ↗
              </span>
            </Link>

            <a
              href="#platform"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-md border border-white/15 bg-white/[0.03] px-6 text-sm font-medium text-zinc-200 transition hover:border-white/30 hover:bg-white/[0.07]"
            >
              Explore the platform
              <span aria-hidden="true">↓</span>
            </a>
          </motion.div>

          <motion.div
            variants={heroItem}
            className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-white/10 pt-6 text-xs tracking-wide text-zinc-300"
          >
            <span>GRAPH-BASED ANALYSIS</span>
            <span className="hidden text-zinc-500 sm:inline">/</span>
            <span>BEHAVIORAL FORENSICS</span>
            <span className="hidden text-zinc-500 sm:inline">/</span>
            <span>EXPLAINABLE EVIDENCE</span>
          </motion.div>
        </motion.div>

        {/* Agent terminal visual */}
        <motion.div
          className="relative flex items-center justify-center py-8 lg:py-0"
          initial={
            reduceMotion
              ? false
              : {
                  opacity: 0,
                  x: 55,
                  scale: 0.94,
                  filter: "blur(12px)",
                }
          }
          animate={{
            opacity: 1,
            x: 0,
            scale: 1,
            filter: "blur(0px)",
          }}
          transition={{
            duration: 1.2,
            delay: 0.45,
            ease: easeOut,
          }}
        >
          {/* Ambient core */}
          <motion.div
            className="absolute h-[440px] w-[440px] rounded-full bg-red-600/[0.08] blur-[80px]"
            animate={
              reduceMotion
                ? undefined
                : {
                    scale: [0.85, 1.12, 0.85],
                    opacity: [0.3, 0.7, 0.3],
                  }
            }
            transition={{
              duration: 6,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />

          {/* Outer rotating scan ring */}
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute h-[420px] w-[420px] rounded-full border border-red-500/20"
            animate={reduceMotion ? undefined : { rotate: 360 }}
            transition={{
              duration: 32,
              repeat: Infinity,
              ease: "linear",
            }}
          >
            <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full bg-red-400 shadow-[0_0_18px_rgba(248,113,113,0.95)]" />
            <span className="absolute right-[13%] top-[19%] h-1.5 w-1.5 rounded-full bg-orange-300 shadow-[0_0_14px_rgba(253,186,116,0.8)]" />
          </motion.div>

          {/* Inner ring */}
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute h-[320px] w-[320px] rounded-full border border-white/[0.08]"
            animate={
              reduceMotion
                ? undefined
                : {
                    rotate: -360,
                    scale: [1, 1.035, 1],
                  }
            }
            transition={{
              rotate: {
                duration: 45,
                repeat: Infinity,
                ease: "linear",
              },
              scale: {
                duration: 5,
                repeat: Infinity,
                ease: "easeInOut",
              },
            }}
          >
            <span className="absolute left-[8%] top-1/2 h-1 w-1 rounded-full bg-red-300/80" />
          </motion.div>

          {/* Terminal itself remains interactive */}
          <div className="relative z-[1] w-full">
            <AgentTerminal />
          </div>
        </motion.div>
      </section>

      {/* Platform features */}
      <section
        id="platform"
        className="relative z-10 border-t border-white/10 bg-[#09090bf0] px-6 py-24 backdrop-blur-sm lg:px-12"
      >
        <div className="mx-auto max-w-[1400px]">
          <motion.div
            variants={sectionReveal}
            initial={revealInitial}
            whileInView={revealVisible}
            viewport={{ once: true, amount: 0.3 }}
            className="max-w-2xl"
          >
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
          </motion.div>

          <div
            id="methodology"
            className="mt-14 grid gap-px overflow-hidden rounded-xl border border-white/10 bg-white/10 md:grid-cols-3"
          >
            {features.map((feature, index) => (
              <motion.article
                key={feature.number}
                variants={sectionReveal}
                initial={revealInitial}
                whileInView={revealVisible}
                viewport={{ once: true, amount: 0.25 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.7,
                  delay: reduceMotion ? 0 : index * 0.15,
                  ease: easeOut,
                }}
                whileHover={
                  reduceMotion
                    ? undefined
                    : {
                        y: -7,
                        transition: { duration: 0.22 },
                      }
                }
                className="group relative overflow-hidden bg-[#0b0b0df5] p-7 transition-colors duration-300 hover:bg-[#111114]"
              >
                {/* Hover sweep */}
                {!reduceMotion && (
                  <motion.div
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-x-0 top-0 h-px origin-left bg-gradient-to-r from-transparent via-red-400 to-transparent"
                    initial={{ scaleX: 0, opacity: 0 }}
                    whileHover={{ scaleX: 1, opacity: 1 }}
                    transition={{ duration: 0.35 }}
                  />
                )}

                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-red-400">
                    / {feature.number}
                  </span>

                  <motion.span
                    className="text-xl text-zinc-600 transition-colors group-hover:text-red-400"
                    whileHover={reduceMotion ? undefined : { x: 3, y: -3 }}
                  >
                    ↗
                  </motion.span>
                </div>

                <h3 className="mt-10 text-lg font-semibold">
                  {feature.title}
                </h3>

                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  {feature.description}
                </p>
              </motion.article>
            ))}
          </div>

          <motion.div
            id="about"
            variants={sectionReveal}
            initial={revealInitial}
            whileInView={revealVisible}
            viewport={{ once: true, amount: 0.3 }}
            className="mt-16 flex flex-col justify-between gap-6 border-t border-white/10 pt-7 text-xs text-zinc-500 sm:flex-row"
          >
            <span>SYBILTRACE · ON-CHAIN FORENSICS</span>
            <span>INVESTIGATE WITH EVIDENCE. NOT ASSUMPTIONS.</span>
          </motion.div>
        </div>
      </section>

      {/* Cinematic route transition */}
      {transitioning && (
        <motion.div
          aria-live="polite"
          role="status"
          className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-[#050506] text-white"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.22 }}
        >
          <motion.div
            aria-hidden="true"
            className="absolute left-1/2 top-1/2 h-[20rem] w-[20rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-600/25 blur-[90px]"
            initial={{ scale: 0.15, opacity: 0.2 }}
            animate={{ scale: 3.8, opacity: 1 }}
            transition={{ duration: 0.95, ease: [0.16, 1, 0.3, 1] }}
          />
          <motion.div
            aria-hidden="true"
            className="absolute inset-0"
            initial={{ clipPath: "circle(0% at 50% 50%)" }}
            animate={{ clipPath: "circle(150% at 50% 50%)" }}
            transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
            style={{
              background:
                "radial-gradient(ellipse at center, rgba(127,29,29,0.26) 0%, rgba(5,5,6,0.96) 62%)",
            }}
          />
          {!reduceMotion && (
            <motion.div
              aria-hidden="true"
              className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-red-300/80 to-transparent shadow-[0_0_24px_rgba(248,113,113,0.8)]"
              initial={{ top: "0%", opacity: 0 }}
              animate={{ top: ["0%", "100%"], opacity: [0, 1, 0.7] }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
            />
          )}
          <motion.div
            className="relative z-10 px-6 text-center"
            initial={{ opacity: 0, y: 24, filter: "blur(12px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ delay: 0.12, duration: 0.55, ease: easeOut }}
          >
            <div className="mb-5 flex items-center justify-center gap-3 font-mono text-[10px] tracking-[0.35em] text-red-300">
              <span className="h-px w-8 bg-red-400/60" />
              SYBILTRACE / INITIALIZING
              <span className="h-px w-8 bg-red-400/60" />
            </div>
            <h2 className="text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">
              Follow the <span className="text-red-400">evidence.</span>
            </h2>
            <p className="mt-4 text-xs tracking-[0.2em] text-zinc-500">
              SELECTING INVESTIGATION MODE
            </p>
            <div className="mx-auto mt-7 h-px w-48 overflow-hidden bg-white/10">
              <motion.div
                className="h-full origin-left bg-red-400"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.82, ease: "easeInOut" }}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </main>
  );
}
