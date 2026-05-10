"use client";

import { CHRONICLE_PLAYBACK_STAGES, DIRECTOR_TOUR_FILES } from "@/lib/chronicle-demo-stages";
import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

type Manifest = {
  demoTitle: string;
  demoNote: string;
  bundledReaderModel: string;
  sourceTitle: string;
  slug?: string;
  stats: { sentences: number; chunks: number; chapters: number; pages: number };
  files: string[];
};

type TreeNode = {
  name: string;
  path: string | null;
  children: TreeNode[];
};

function insertPath(root: TreeNode, rel: string): void {
  const parts = rel.split("/").filter(Boolean);
  let node = root;
  let acc = "";
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    acc = acc ? `${acc}/${part}` : part;
    const isFile = i === parts.length - 1;
    let child = node.children.find((c) => c.name === part);
    if (!child) {
      child = { name: part, path: isFile ? acc : null, children: [] };
      node.children.push(child);
      node.children.sort((a, b) => {
        const af = a.path !== null;
        const bf = b.path !== null;
        if (af !== bf) return af ? 1 : -1;
        return a.name.localeCompare(b.name);
      });
    }
    node = child;
  }
}

function buildTree(files: string[], rootName: string = "chronicle"): TreeNode {
  const root: TreeNode = { name: rootName, path: null, children: [] };
  for (const f of files) insertPath(root, f);
  return root;
}

function TreeList({
  node,
  depth,
  selected,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selected: string | null;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(depth < 2);
  const isFolder = node.children.length > 0;
  const isSelectable = node.path !== null;

  return (
    <div className={depth > 0 ? "ml-2 border-l border-stone-200 pl-2" : ""}>
      <div className="flex min-w-0 items-center gap-1 py-0.5">
        {isFolder && (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className="w-5 shrink-0 text-center text-stone-500 hover:text-stone-800"
          >
            {open ? "▾" : "▸"}
          </button>
        )}
        {!isFolder && <span className="w-5 shrink-0" />}
        {isSelectable ? (
          <button
            type="button"
            onClick={() => onSelect(node.path!)}
            className={`min-w-0 flex-1 truncate rounded px-1.5 text-left text-sm ${
              selected === node.path
                ? "bg-amber-100 font-medium text-amber-950"
                : "text-stone-700 hover:bg-stone-100"
            }`}
          >
            {node.name}
          </button>
        ) : (
          <span className="truncate text-sm font-semibold text-stone-600">{node.name}</span>
        )}
      </div>
      {isFolder && open && (
        <div>
          {node.children.map((ch) => (
            <TreeList
              key={ch.name + (ch.path ?? "")}
              node={ch}
              depth={depth + 1}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChronicleExplorer({ basePath }: { basePath: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>("book/00_index.md");
  const [content, setContent] = useState<string>("");
  const [fileErr, setFileErr] = useState<string | null>(null);
  const [playbackLines, setPlaybackLines] = useState<string[]>([]);
  const [directorPhase, setDirectorPhase] = useState<"idle" | "stages" | "tour">("idle");
  const [tourIndex, setTourIndex] = useState(-1);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${basePath}/_demo-manifest.json`);
        if (!res.ok) throw new Error(`Manifest ${res.status}`);
        const data = (await res.json()) as Manifest;
        if (!cancelled) setManifest(data);
      } catch (e) {
        if (!cancelled) setLoadErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [basePath]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    (async () => {
      setFileErr(null);
      try {
        const res = await fetch(`${basePath}/${selected}`);
        if (!res.ok) throw new Error(`${res.status}`);
        const text = await res.text();
        if (!cancelled) setContent(text);
      } catch (e) {
        if (!cancelled) setFileErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [basePath, selected]);

  const tree = useMemo(() => {
    if (!manifest?.files) return null;
    const rootName = manifest.slug || basePath.replace(/^\/chronicle-?/, "") || "chronicle";
    return buildTree(manifest.files, rootName);
  }, [manifest, basePath]);

  const startPlayback = useCallback(() => {
    clearTimers();
    setDirectorPhase("stages");
    setPlaybackLines([]);
    setTourIndex(-1);
    CHRONICLE_PLAYBACK_STAGES.forEach((line, i) => {
      const id = setTimeout(
        () => {
          setPlaybackLines((prev) => [...prev, line]);
        },
        420 * (i + 1),
      );
      timers.current.push(id);
    });
    const end = setTimeout(() => {
      setDirectorPhase("tour");
      let ti = 0;
      const step = () => {
        if (ti >= DIRECTOR_TOUR_FILES.length) {
          setDirectorPhase("idle");
          setTourIndex(-1);
          return;
        }
        setSelected(DIRECTOR_TOUR_FILES[ti]);
        setTourIndex(ti);
        ti += 1;
        timers.current.push(setTimeout(step, 2200));
      };
      timers.current.push(setTimeout(step, 600));
    }, 420 * (CHRONICLE_PLAYBACK_STAGES.length + 1) + 400);
    timers.current.push(end);
  }, [clearTimers]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  const isJson = selected.endsWith(".json") || selected.endsWith(".jsonl");
  const isMd = selected.endsWith(".md");

  let body: ReactNode;
  if (fileErr) {
    body = <p className="text-sm text-red-700">{fileErr}</p>;
  } else if (isJson && selected.endsWith(".json")) {
    try {
      const parsed = JSON.parse(content) as unknown;
      body = (
        <pre className="overflow-auto text-xs leading-relaxed text-stone-800 md:text-sm">
          {JSON.stringify(parsed, null, 2)}
        </pre>
      );
    } catch {
      body = (
        <pre className="overflow-auto whitespace-pre-wrap font-mono text-xs text-stone-800">{content}</pre>
      );
    }
  } else if (isMd) {
    body = (
      <div className="prose-dune max-w-none text-stone-800">
        <ReactMarkdown
          components={{
            h1: (p) => <h1 className="mb-3 mt-1 text-2xl font-bold text-stone-900" {...p} />,
            h2: (p) => <h2 className="mb-2 mt-6 text-lg font-semibold text-stone-800" {...p} />,
            h3: (p) => <h3 className="mb-2 mt-4 text-base font-semibold text-stone-800" {...p} />,
            p: (p) => <p className="mb-3 text-sm leading-relaxed md:text-base" {...p} />,
            ul: (p) => <ul className="mb-3 list-disc pl-5 text-sm md:text-base" {...p} />,
            ol: (p) => <ol className="mb-3 list-decimal pl-5 text-sm md:text-base" {...p} />,
            li: (p) => <li className="mb-1" {...p} />,
            code: ({ className, children, ...rest }) => {
              const inline = !className;
              if (inline) {
                return (
                  <code
                    className="rounded bg-stone-200/90 px-1 py-0.5 font-mono text-[0.85em] text-stone-900"
                    {...rest}
                  >
                    {children}
                  </code>
                );
              }
              return (
                <code className={`block font-mono text-xs ${className ?? ""}`} {...rest}>
                  {children}
                </code>
              );
            },
            pre: (p) => (
              <pre className="mb-3 overflow-x-auto rounded-lg bg-stone-100 p-3 text-xs text-stone-900" {...p} />
            ),
            a: (p) => (
              <a className="text-amber-800 underline decoration-amber-300 hover:text-amber-950" {...p} />
            ),
            strong: (p) => <strong className="font-semibold text-stone-900" {...p} />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  } else {
    body = (
      <pre className="max-h-[calc(100vh-220px)] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-stone-800 md:text-sm">
        {content}
      </pre>
    );
  }

  if (loadErr) {
    return (
      <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        Could not load bundled Chronicle: {loadErr}
      </p>
    );
  }

  if (!manifest || !tree) {
    return <p className="text-sm text-stone-500">Loading bundled Chronicle…</p>;
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-4 lg:flex-row">
      <aside className="w-full shrink-0 rounded-xl border border-stone-200 bg-white p-4 shadow-sm lg:w-72">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">Artifact tree</p>
        <p className="mt-1 text-xs text-stone-500">Same layout as a real run under _reader/…</p>
        <div className="mt-3 max-h-[60vh] overflow-auto pr-1 lg:max-h-[calc(100vh-12rem)]">
          <TreeList node={tree} depth={0} selected={selected} onSelect={setSelected} />
        </div>
      </aside>

      <div className="min-w-0 flex-1 space-y-4">
        <header className="rounded-xl border border-stone-200 bg-gradient-to-br from-amber-50/80 to-stone-50 p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-900">
            Bundled demo · {manifest.demoTitle}
          </p>
          <h1 className="mt-2 font-serif text-2xl font-semibold text-stone-900 md:text-3xl">
            {manifest.sourceTitle}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-stone-600">{manifest.demoNote}</p>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs uppercase text-stone-500">Model (this bundle)</dt>
              <dd className="font-medium text-stone-900">{manifest.bundledReaderModel}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Sentences</dt>
              <dd className="font-medium text-stone-900">{manifest.stats.sentences}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Chunks</dt>
              <dd className="font-medium text-stone-900">{manifest.stats.chunks}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Chapters / pages</dt>
              <dd className="font-medium text-stone-900">
                {manifest.stats.chapters} / {manifest.stats.pages}
              </dd>
            </div>
          </dl>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={startPlayback}
              disabled={directorPhase !== "idle"}
              className="rounded-lg bg-amber-800 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-amber-900 disabled:opacity-60"
            >
              {directorPhase === "idle" ? "Screen-recording mode" : "Playing…"}
            </button>
            <Link
              href="/playground"
              className="inline-flex items-center rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
            >
              Run your own text (local Python)
            </Link>
          </div>
          {tourIndex >= 0 && (
            <p className="mt-3 text-xs text-amber-900">
              Auto tour: file {tourIndex + 1} of {DIRECTOR_TOUR_FILES.length}
            </p>
          )}
        </header>

        {playbackLines.length > 0 && (
          <div
            className="rounded-xl border border-amber-200 bg-amber-50/90 p-4 shadow-sm"
            aria-live="polite"
          >
            <p className="text-xs font-semibold uppercase text-amber-900">Harness progress (simulated pacing)</p>
            <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto font-mono text-xs text-stone-800">
              {playbackLines.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
        )}

        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2 border-b border-stone-100 pb-3">
            <code className="text-xs text-stone-600 md:text-sm">{selected}</code>
            <span className="text-xs text-stone-400">served from /public{basePath}/</span>
          </div>
          {body}
        </section>
      </div>
    </div>
  );
}
