"use client";

import type { ReactNode } from "react";
import { useCallback, useState } from "react";

type OkResponse = {
  ok: true;
  summary: {
    folderName: string;
    sentences: number;
    chunks: number;
    chapters: number;
    pages: number;
    readerModel: string;
    errors: number;
    warnings: number;
  };
  liveSummary: string;
  bookIndex: string;
};

type ErrResponse = {
  ok: false;
  error: string;
  stderr?: string;
};

const SAMPLE = `# Demo transcript

This is a short piece of source text for the Julia Reader harness. It will be split into sentences, chunked, and summarized.

The Reader builds a Chronicle: a live summary, a book plan, markdown pages, and validation. Toggle "offline mode" to run without calling an LLM API — useful for CI or quick layout checks.

Second paragraph: the Next.js route shells out to the Python package in this repo (\`python -m julia_reader\`), reads the artifacts from a temp directory, and returns the live summary plus the book index here in the browser.
`;

export default function PlaygroundPage() {
  const [text, setText] = useState(SAMPLE);
  const [noLlm, setNoLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"live" | "index">("live");
  const [result, setResult] = useState<OkResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stderr, setStderr] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    setStderr(null);
    setResult(null);
    try {
      const res = await fetch("/api/reader", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, noLlm }),
      });
      const data = (await res.json()) as OkResponse | ErrResponse;
      if (!data.ok) {
        setError(data.error);
        setStderr(data.stderr ?? null);
        return;
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [text, noLlm]);

  return (
    <main className="mx-auto max-w-4xl bg-[var(--paper)] px-6 py-10">
      <header className="mb-10 border-b border-stone-200 pb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-amber-800">Julia Reader</p>
        <h1 className="mt-2 font-serif text-3xl font-semibold text-stone-900 md:text-4xl">Playground</h1>
        <p className="mt-4 max-w-2xl text-stone-600">
          Runs <code className="rounded bg-stone-200/80 px-1.5 py-0.5 text-sm">python -m julia_reader</code> on
          this machine via <code className="rounded bg-stone-200/80 px-1.5 py-0.5 text-sm">/api/reader</code>.
          Set keys in the repo root <code className="text-sm">.env</code> and turn off offline mode to hit your
          model.
        </p>
      </header>

      <section className="space-y-4">
        <label className="block text-sm font-medium text-stone-700">Source text</label>
        <textarea
          className="min-h-[220px] w-full rounded-lg border border-stone-300 bg-white p-4 font-mono text-sm text-stone-800 shadow-sm outline-none ring-amber-700/30 focus:border-amber-600 focus:ring-2"
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
        />
        <div className="flex flex-wrap items-center gap-6">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-stone-700">
            <input
              type="checkbox"
              checked={noLlm}
              onChange={(e) => setNoLlm(e.target.checked)}
              className="size-4 rounded border-stone-400 text-amber-700 focus:ring-amber-600"
            />
            Offline mode (<code className="text-xs">--no-llm</code>) — no API calls
          </label>
          <button
            type="button"
            onClick={() => void run()}
            disabled={loading}
            className="rounded-lg bg-amber-700 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-amber-800 disabled:opacity-50"
          >
            {loading ? "Running reader…" : "Run Julia Reader"}
          </button>
        </div>
      </section>

      {error && (
        <div
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900"
          role="alert"
        >
          <p className="font-medium">Run failed</p>
          <p className="mt-1 whitespace-pre-wrap">{error}</p>
          {stderr && (
            <pre className="mt-3 max-h-48 overflow-auto rounded bg-red-100/80 p-3 text-xs text-red-950">
              {stderr}
            </pre>
          )}
        </div>
      )}

      {result && (
        <section className="mt-10 space-y-6">
          <div className="grid gap-3 rounded-lg border border-stone-200 bg-white p-5 text-sm shadow-sm sm:grid-cols-2 md:grid-cols-4">
            <Stat label="Run folder" value={result.summary.folderName} wide />
            <Stat label="Model" value={result.summary.readerModel} wide />
            <Stat label="Sentences" value={String(result.summary.sentences)} />
            <Stat label="Chunks" value={String(result.summary.chunks)} />
            <Stat label="Chapters" value={String(result.summary.chapters)} />
            <Stat label="Pages" value={String(result.summary.pages)} />
            <Stat label="Validation errors" value={String(result.summary.errors)} />
            <Stat label="Warnings" value={String(result.summary.warnings)} />
          </div>

          <div className="flex gap-2 border-b border-stone-200">
            <TabButton active={tab === "live"} onClick={() => setTab("live")}>
              Live summary
            </TabButton>
            <TabButton active={tab === "index"} onClick={() => setTab("index")}>
              Book index
            </TabButton>
          </div>

          <article className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
            <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-stone-800 md:text-sm">
              {tab === "live" ? result.liveSummary : result.bookIndex}
            </pre>
          </article>
        </section>
      )}
    </main>
  );
}

function Stat({
  label,
  value,
  wide,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2 md:col-span-4" : undefined}>
      <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-0.5 font-medium text-stone-900">{value}</p>
    </div>
  );
}

function TabButton({
  children,
  active,
  onClick,
}: {
  children: ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? "-mb-px border-b-2 border-amber-700 px-3 py-2 text-sm font-medium text-amber-900"
          : "px-3 py-2 text-sm text-stone-600 hover:text-stone-900"
      }
    >
      {children}
    </button>
  );
}
