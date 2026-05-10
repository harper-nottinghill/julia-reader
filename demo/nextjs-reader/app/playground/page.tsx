"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

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

/** Map HTTP status / error text to a user-friendly message with actionable guidance. */
function mapError(status: number, errorBody: string): { message: string; action: string } {
  if (status === 401 || status === 403) {
    return {
      message: "Authentication failed.",
      action: "Check that your API key is valid and has not expired. Update it in .env.local.",
    };
  }
  if (status === 429) {
    return {
      message: "Rate limit reached.",
      action: "Wait a moment and try again. If this persists, check your provider dashboard.",
    };
  }
  if (status === 422 && /api.key/i.test(errorBody)) {
    return {
      message: "API key is missing or invalid.",
      action: "Set JULIA_READER_API_KEY or OPENAI_API_KEY in .env.local and restart the dev server.",
    };
  }
  if (status >= 500) {
    return {
      message: "Server error.",
      action: "Check the terminal running `next dev` for details. The Python backend may have crashed.",
    };
  }
  if (status === 400) {
    return {
      message: "Bad request.",
      action: "The request was malformed. Try refreshing the page.",
    };
  }
  return {
    message: "Something went wrong.",
    action: "Please try again. If the problem persists, check the server logs.",
  };
}

export default function PlaygroundPage() {
  const [text, setText] = useState(SAMPLE);
  const [noLlm, setNoLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"live" | "index">("live");
  const [result, setResult] = useState<OkResponse | null>(null);

  // Error state now holds structured message + actionable guidance
  const [error, setError] = useState<{ message: string; action: string } | null>(null);
  const [stderr, setStderr] = useState<string | null>(null);

  // API key configuration state
  const [apiKeyConfigured, setApiKeyConfigured] = useState<boolean | null>(null); // null = unknown (loading)
  const [bannerDismissed, setBannerDismissed] = useState(false);

  // Check API key status on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/config/status");
        if (!res.ok) return;
        const data = (await res.json()) as { configured: boolean; model: string };
        if (!cancelled) setApiKeyConfigured(data.configured);
      } catch {
        // Silently ignore — the banner simply won't show if we can't check
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist banner dismissal in sessionStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (sessionStorage.getItem("jr-banner-dismissed") === "true") {
        setBannerDismissed(true);
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  const dismissBanner = useCallback(() => {
    setBannerDismissed(true);
    try {
      sessionStorage.setItem("jr-banner-dismissed", "true");
    } catch {
      // Ignore storage errors
    }
  }, []);

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
        // Map to structured error
        if (!res.ok) {
          setError(mapError(res.status, data.error));
        } else {
          setError({
            message: data.error,
            action: "Check the details below and try again.",
          });
        }
        setStderr(data.stderr ?? null);
        return;
      }

      // Success — hide the warning banner
      setResult(data);
      setApiKeyConfigured(true);
    } catch (e) {
      setError({
        message: "Network error.",
        action:
          "Could not reach the server. Make sure the dev server is running (`npm run dev`).",
      });
    } finally {
      setLoading(false);
    }
  }, [text, noLlm]);

  const showBanner = apiKeyConfigured === false && !bannerDismissed;

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

      {/* ── Warning banner: API key not configured ── */}
      {showBanner && (
        <div
          className="mb-6 flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 shadow-sm"
          role="alert"
        >
          <span className="mt-0.5 text-lg leading-none" aria-hidden="true">
            ⚠️
          </span>
          <div className="flex-1">
            <p className="font-semibold">API key not configured</p>
            <p className="mt-1">
              The reader cannot call an LLM without a valid API key. Uncheck <strong>offline mode</strong> after
              configuring your key.
            </p>
            <p className="mt-2">
              <strong>Fix:</strong> Add your key to{" "}
              <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">.env.local</code> as{" "}
              <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">
                JULIA_READER_API_KEY=sk-...
              </code>{" "}
              or{" "}
              <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">
                OPENAI_API_KEY=sk-...
              </code>
              , then restart the dev server. See{" "}
              <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">env.example</code> for all options.
            </p>
          </div>
          <button
            type="button"
            onClick={dismissBanner}
            className="shrink-0 rounded p-1 text-amber-600 hover:bg-amber-100 hover:text-amber-900"
            aria-label="Dismiss warning"
          >
            ✕
          </button>
        </div>
      )}

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

      {/* ── Inline error with actionable guidance ── */}
      {error && (
        <div
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900"
          role="alert"
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-base leading-none" aria-hidden="true">
              ❌
            </span>
            <div className="flex-1">
              <p className="font-semibold">{error.message}</p>
              <p className="mt-1 text-red-800">{error.action}</p>
              {stderr && (
                <pre className="mt-3 max-h-48 overflow-auto rounded bg-red-100/80 p-3 text-xs text-red-950">
                  {stderr}
                </pre>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                setError(null);
                setStderr(null);
              }}
              className="shrink-0 rounded p-1 text-red-400 hover:bg-red-100 hover:text-red-700"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
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
