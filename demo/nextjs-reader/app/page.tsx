"use client";

import ChronicleExplorer from "@/components/ChronicleExplorer";
import { useEffect, useState } from "react";

type ManifestSummary = {
  slug: string;
  demoTitle: string;
  sourceTitle: string;
  stats: { sentences: number; chunks: number; chapters: number; pages: number };
};

/**
 * Home page — discovers all chronicle directories in public/ and either:
 * - Shows a single ChronicleExplorer if only one chronicle exists
 * - Shows a book selector if multiple chronicles are found
 * - Falls back to /chronicle-dune for backward compatibility
 */
export default function Home() {
  const [books, setBooks] = useState<ManifestSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Try the discover API first
        const res = await fetch("/api/chronicles");
        if (res.ok) {
          const data = (await res.json()) as { books: ManifestSummary[] };
          if (!cancelled) {
            setBooks(data.books);
            // Auto-select the first book
            if (data.books.length > 0) {
              setSelected(data.books[0].slug);
            }
          }
        }
      } catch {
        // API not available — fall through to default
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--paper)]">
        <main className="mx-auto max-w-7xl px-6 py-8">
          <p className="text-sm text-stone-500">Loading chronicles…</p>
        </main>
      </div>
    );
  }

  // Determine which basePath to use
  const basePath = selected
    ? `/chronicle-${selected}`
    : books.length > 0
      ? `/chronicle-${books[0].slug}`
      : "/chronicle-dune";

  return (
    <div className="min-h-screen bg-[var(--paper)]">
      <main className="mx-auto max-w-7xl px-6 py-8">
        {books.length > 1 && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-amber-900">
              Select chronicle:
            </span>
            {books.map((b) => (
              <button
                key={b.slug}
                type="button"
                onClick={() => setSelected(b.slug)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  selected === b.slug
                    ? "bg-amber-800 text-white"
                    : "border border-stone-300 bg-white text-stone-700 hover:bg-stone-50"
                }`}
              >
                {b.demoTitle || b.sourceTitle || b.slug}
              </button>
            ))}
          </div>
        )}
        <ChronicleExplorer basePath={basePath} />
      </main>
    </div>
  );
}
