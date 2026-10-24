"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { uploadForensicCsv } from "@/lib/api/forensic";
import { useRouter } from "next/navigation";

export default function ForensicPage() {
  const [file, setFile] = useState<File | null>(null);
  const [tokenAddress, setTokenAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
 
  function selectFile(selected: File | null) {
    setError(null);

    if (selected && !selected.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    setFile(selected);
    setResult(null);
  }

  
    async function handleSubmit(
    event: Parameters<
        NonNullable<React.ComponentProps<"form">["onSubmit"]>
    >[0]
    ) {
    event.preventDefault();

    if (!file || !tokenAddress.trim()) {
        setError("Upload a transaction CSV and enter the token address.");
        return;
    }

    setLoading(true);
    setError(null);

    try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("token_address", tokenAddress.trim());

        const response = await fetch(
        "/backend/api/investigations/upload",
        {
            method: "POST",
            body: formData,
        }
        );

        if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(
            body?.detail ?? `Failed to start investigation (${response.status})`
        );
        }

        const data: { run_id: string; status?: string } =
        await response.json();

        if (!data.run_id) {
        throw new Error("The backend did not return a run ID.");
        }

        sessionStorage.setItem("sybiltrace_run_id", data.run_id);
        router.push("/dashboard");
    } catch (err: unknown) {
        setError(
        err instanceof Error
            ? err.message
            : "An unexpected error occurred."
        );
    } finally {
        setLoading(false);
    }
    }


  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080809] text-white">
      {/* Cinematic background — same as the landing page */}
      <div className="pointer-events-none fixed inset-0">
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          className="absolute inset-0 h-full w-full object-cover opacity-100"
        >
          <source src="/videos/bg.mp4" type="video/mp4" />
        </video>

        <div className="absolute inset-0 bg-gradient-to-r from-[#080809]/90 via-[#080809]/75 to-[#080809]/60" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#080809] via-transparent to-[#080809]/40" />

        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px)",
            backgroundSize: "76px 76px",
          }}
        />

        <div className="absolute -left-40 top-1/3 h-[420px] w-[420px] rounded-full bg-red-600/[0.09] blur-[120px]" />
        <div className="absolute -right-40 bottom-0 h-[420px] w-[420px] rounded-full bg-orange-600/[0.06] blur-[120px]" />
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

          <div className="flex items-center gap-4 text-xs text-zinc-400 sm:gap-6">
            <span className="hidden items-center gap-2 sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
              SYSTEM READY
            </span>

            <Link
              href="/"
              className="transition hover:text-white"
            >
              ← Back to home
            </Link>
          </div>
        </nav>
      </header>

      {/* Main content */}
      <section className="relative z-10 mx-auto max-w-[1400px] px-6 py-12 sm:py-16 lg:px-12 lg:py-20">
        {/* Page heading */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/[0.07] px-3.5 py-2 text-[10px] font-medium tracking-[0.2em] text-red-300 sm:text-xs">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
            INVESTIGATION INITIALIZATION
          </div>

          <h1 className="text-4xl leading-tight font-semibold tracking-[-0.045em] sm:text-5xl lg:text-6xl">
            Start with the{" "}
            <span className="bg-gradient-to-r from-red-400 via-red-500 to-orange-400 bg-clip-text text-transparent">
              evidence.
            </span>
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-sm leading-7 text-zinc-400 sm:text-base">
            Provide your transaction dataset and target token address.
            SYBILTRACE will prepare the data for an investigation into
            funding relationships, coordinated wallet activity and
            suspicious behavioral patterns.
          </p>
        </div>

        {/* Workflow indicators */}
        <div className="mx-auto mt-10 flex max-w-2xl items-center justify-center">
          {[
            { number: "01", label: "INPUT DATA", active: true },
            { number: "02", label: "INVESTIGATE", active: false },
            { number: "03", label: "REVIEW EVIDENCE", active: false },
          ].map((step, index) => (
            <div key={step.number} className="flex flex-1 items-center">
              <div className="flex min-w-0 flex-col items-center gap-2">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full border font-mono text-xs ${
                    step.active
                      ? "border-red-400/50 bg-red-500/15 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.12)]"
                      : "border-white/10 bg-white/[0.03] text-zinc-600"
                  }`}
                >
                  {step.number}
                </div>
                <span
                  className={`whitespace-nowrap text-[9px] tracking-[0.12em] sm:text-[10px] ${
                    step.active ? "text-zinc-200" : "text-zinc-600"
                  }`}
                >
                  {step.label}
                </span>
              </div>

              {index < 2 && (
                <div className="mx-2 mb-5 h-px flex-1 bg-gradient-to-r from-red-500/30 to-white/10 sm:mx-5" />
              )}
            </div>
          ))}
        </div>

        {/* Upload workspace */}
        <div className="mx-auto mt-10 grid max-w-5xl gap-5 lg:grid-cols-[1fr_300px] lg:gap-6">
          <form
            onSubmit={handleSubmit}
            className="overflow-hidden rounded-2xl border border-white/[0.12] bg-[#0b0b0de8] shadow-[0_25px_100px_rgba(0,0,0,0.35)] backdrop-blur-xl"
          >
            {/* Panel header */}
            <div className="flex items-center justify-between border-b border-white/[0.09] px-6 py-5 sm:px-8">
              <div>
                <p className="text-sm font-semibold tracking-wide">
                  Investigation parameters
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Configure the dataset and target
                </p>
              </div>

              <div className="flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  className="h-3.5 w-3.5 text-red-400"
                  stroke="currentColor"
                  strokeWidth="1.6"
                >
                  <path d="M12 3 20 7v5c0 4-3 7-8 9-5-2-8-5-8-9V7l8-4Z" />
                </svg>
                <span className="text-[9px] tracking-[0.12em] text-zinc-400">
                  SECURE WORKSPACE
                </span>
              </div>
            </div>

            <div className="space-y-8 p-6 sm:p-8">
              {/* CSV upload */}
              <div>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <label
                    htmlFor="csv-file"
                    className="text-sm font-medium text-zinc-200"
                  >
                    Transaction dataset
                    <span className="ml-2 text-red-400">*</span>
                  </label>
                  <span className="font-mono text-[10px] text-zinc-500">
                    CSV FORMAT
                  </span>
                </div>

                <input
                  ref={fileInputRef}
                  id="csv-file"
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(event) =>
                    selectFile(event.target.files?.[0] ?? null)
                  }
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragging(false);
                    selectFile(event.dataTransfer.files?.[0] ?? null);
                  }}
                  className={`group w-full rounded-xl border border-dashed p-6 text-left transition sm:p-8 ${
                    dragging
                      ? "border-red-400 bg-red-500/[0.08]"
                      : file
                        ? "border-emerald-500/30 bg-emerald-500/[0.035] hover:border-emerald-400/50"
                        : "border-white/15 bg-white/[0.015] hover:border-red-400/50 hover:bg-red-500/[0.025]"
                  }`}
                >
                  <div className="flex flex-col items-center text-center sm:flex-row sm:gap-5 sm:text-left">
                    <div
                      className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border transition ${
                        file
                          ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                          : "border-red-500/20 bg-red-500/[0.08] text-red-300 group-hover:border-red-400/40"
                      }`}
                    >
                      {file ? (
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          className="h-7 w-7"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <path d="m5 12 4 4L19 6" />
                          <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />
                        </svg>
                      ) : (
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          className="h-7 w-7"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <path d="M12 16V4m0 0L7 9m5-5 5 5" />
                          <path d="M20 16.5v2A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5v-2" />
                        </svg>
                      )}
                    </div>

                    <div className="mt-4 min-w-0 flex-1 sm:mt-0">
                      <p className="break-all text-sm font-medium text-zinc-100">
                        {file ? file.name : "Drop your CSV file here"}
                      </p>
                      <p className="mt-2 text-xs leading-5 text-zinc-500">
                        {file
                          ? `${(file.size / 1024).toFixed(1)} KB · Ready for submission`
                          : "Drag and drop your dataset, or click to browse files"}
                      </p>
                      <p className="mt-2 text-[10px] tracking-wide text-zinc-600">
                        ACCEPTED FORMAT: .CSV
                      </p>
                    </div>

                    <span className="mt-4 shrink-0 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-zinc-300 transition group-hover:bg-white/[0.08] sm:mt-0">
                      Browse files
                    </span>
                  </div>
                </button>
              </div>

              {/* Token address */}
              <div>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <label
                    htmlFor="token-address"
                    className="text-sm font-medium text-zinc-200"
                  >
                    Target token address
                    <span className="ml-2 text-red-400">*</span>
                  </label>
                  <span className="font-mono text-[10px] text-zinc-500">
                    ON-CHAIN IDENTIFIER
                  </span>
                </div>

                <div className="group relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-zinc-500 transition group-focus-within:text-red-400">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      className="h-5 w-5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <circle cx="12" cy="12" r="8.5" />
                      <circle cx="12" cy="12" r="3" />
                      <path d="M12 1v2.5M12 20.5V23M1 12h2.5M20.5 12H23" />
                    </svg>
                  </div>

                  <input
                    id="token-address"
                    type="text"
                    value={tokenAddress}
                    onChange={(event) => {
                      setTokenAddress(event.target.value);
                      setError(null);
                    }}
                    placeholder="Enter token mint / contract address"
                    autoComplete="off"
                    spellCheck={false}
                    className="w-full rounded-lg border border-white/10 bg-black/30 py-3.5 pl-12 pr-4 font-mono text-sm text-white outline-none transition placeholder:font-sans placeholder:text-zinc-600 hover:border-white/20 focus:border-red-400/60 focus:ring-2 focus:ring-red-500/10"
                    required
                  />
                </div>

                <p className="mt-2 text-[11px] leading-5 text-zinc-500">
                  Enter the token address associated with the transactions
                  you want to investigate.
                </p>
              </div>

              {/* Error */}
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-lg border border-red-500/25 bg-red-500/[0.07] p-4 text-sm text-red-300"
                >
                  <span className="mt-0.5">⚠</span>
                  <p className="break-words">{error}</p>
                </div>
              )}

              {/* Submit */}
              <div className="border-t border-white/[0.08] pt-6">
                <button
                  type="submit"
                  disabled={loading}
                  className="group flex min-h-13 w-full items-center justify-center gap-3 rounded-lg bg-gradient-to-r from-red-500 to-red-600 px-5 py-3.5 text-sm font-semibold text-white shadow-[0_6px_30px_rgba(220,38,38,0.15)] transition hover:from-red-400 hover:to-red-500 hover:shadow-[0_8px_35px_rgba(220,38,38,0.25)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Submitting investigation...
                    </>
                  ) : (
                    <>
                      Initialize investigation
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        className="h-4 w-4 transition group-hover:translate-x-1"
                        stroke="currentColor"
                        strokeWidth="1.8"
                      >
                        <path d="M5 12h14m-6-6 6 6-6 6" />
                      </svg>
                    </>
                  )}
                </button>

                <p className="mt-3 text-center text-[10px] leading-5 text-zinc-600">
                  Investigation begins after submission. Processing time
                  depends on dataset size and on-chain analysis.
                </p>
              </div>
            </div>
          </form>

          {/* Right-side information panel */}
          <aside className="space-y-5">
            <div className="rounded-2xl border border-white/[0.1] bg-[#0b0b0de8] p-6 backdrop-blur-xl">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-red-500/20 bg-red-500/[0.08] text-red-300">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="h-5 w-5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <circle cx="5" cy="6" r="2" />
                    <circle cx="19" cy="6" r="2" />
                    <circle cx="12" cy="18" r="2" />
                    <path d="m7 7 4 9m6-9-4 9M7 6h10" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-sm font-semibold">What gets analyzed</h2>
                  <p className="mt-1 text-[10px] tracking-wide text-zinc-500">
                    INVESTIGATION SCOPE
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-5">
                {[
                  {
                    number: "01",
                    title: "Funding relationships",
                    description:
                      "Trace shared funders and connected wallet structures.",
                  },
                  {
                    number: "02",
                    title: "Behavioral patterns",
                    description:
                      "Compare transaction timing and wallet activity.",
                  },
                  {
                    number: "03",
                    title: "Coordinated activity",
                    description:
                      "Examine evidence of shared or synchronized behavior.",
                  },
                ].map((item) => (
                  <div key={item.number} className="flex gap-3">
                    <span className="pt-0.5 font-mono text-[10px] text-red-400">
                      {item.number}
                    </span>
                    <div>
                      <h3 className="text-xs font-medium text-zinc-200">
                        {item.title}
                      </h3>
                      <p className="mt-1.5 text-[11px] leading-5 text-zinc-500">
                        {item.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.1] bg-[#0b0b0de8] p-6 backdrop-blur-xl">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <h2 className="text-xs font-semibold tracking-wide text-zinc-200">
                  INPUT CHECKLIST
                </h2>
              </div>

              <div className="mt-5 space-y-3">
                {[
                  { label: "Transaction CSV selected", done: !!file },
                  {
                    label: "Token address provided",
                    done: !!tokenAddress.trim(),
                  },
                  { label: "Ready to submit", done: !!file && !!tokenAddress.trim() },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center gap-3 text-xs"
                  >
                    <span
                      className={`flex h-4 w-4 items-center justify-center rounded-full border ${
                        item.done
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                          : "border-white/15 text-transparent"
                      }`}
                    >
                      {item.done ? "✓" : ""}
                    </span>
                    <span
                      className={
                        item.done ? "text-zinc-300" : "text-zinc-600"
                      }
                    >
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <p className="px-2 text-[10px] leading-5 text-zinc-600">
              SYBILTRACE supports evidence-led analysis. Connections and
              behavioral similarities are investigative signals, not
              automatic proof of malicious intent.
            </p>
          </aside>
        </div>

        {/* API response — shown only when the request succeeds */}
        {result !== null && (
          <section className="mx-auto mt-8 max-w-5xl overflow-hidden rounded-2xl border border-emerald-500/20 bg-[#0b0b0de8] backdrop-blur-xl">
            <div className="flex items-center gap-3 border-b border-white/10 px-6 py-5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                ✓
              </span>
              <div>
                <h2 className="text-sm font-semibold">
                  API response received
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Raw backend response for debugging
                </p>
              </div>
            </div>

            <pre className="max-h-[500px] overflow-auto p-6 font-mono text-xs leading-6 whitespace-pre-wrap break-words text-zinc-300">
              {JSON.stringify(result, null, 2)}
            </pre>
          </section>
        )}

        <footer className="mx-auto mt-12 flex max-w-5xl flex-col justify-between gap-3 border-t border-white/[0.08] pt-6 text-[10px] tracking-wide text-zinc-600 sm:flex-row">
          <span>SYBILTRACE · ON-CHAIN FORENSICS</span>
          <span>INVESTIGATE WITH EVIDENCE. NOT ASSUMPTIONS.</span>
        </footer>
      </section>
    </main>
  );
}