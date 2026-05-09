"use client";

import { MarkdownBody } from "@/components/MarkdownBody";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function WhitePaperPage() {
  const [markdown, setMarkdown] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/whitepaper.md");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        if (!cancelled) setMarkdown(text);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--paper)]">
      <main className="mx-auto max-w-3xl px-6 py-10 pb-20">
        <p className="text-sm text-stone-600">
          <Link href="/" className="font-medium text-amber-900 hover:underline">
            ← Chronicle demo
          </Link>
          {" · "}
          <Link href="/playground" className="text-stone-600 hover:text-stone-900 hover:underline">
            Playground
          </Link>
        </p>

        {error && (
          <p className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            Could not load white paper: {error}
          </p>
        )}

        {!error && !markdown && (
          <p className="mt-8 text-sm text-stone-500">Loading white paper…</p>
        )}

        {markdown ? (
          <article className="mt-8 rounded-xl border border-stone-200 bg-white p-6 shadow-sm md:p-10">
            <MarkdownBody markdown={markdown} />
          </article>
        ) : null}

        <footer className="mt-10 text-center text-xs text-stone-500">
          Source files:{" "}
          <code className="rounded bg-stone-200/80 px-1">WHITE_PAPER.md</code> and{" "}
          <code className="rounded bg-stone-200/80 px-1">docs/whitepaper.md</code> in the repo root.
        </footer>
      </main>
    </div>
  );
}
