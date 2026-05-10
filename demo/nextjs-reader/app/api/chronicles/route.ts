import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

export const runtime = "nodejs";

type ManifestSummary = {
  slug: string;
  demoTitle: string;
  sourceTitle: string;
  stats: {
    sentences: number;
    chunks: number;
    chapters: number;
    pages: number;
  };
};

/**
 * GET /api/chronicles — discovers all chronicle-* directories in public/
 * that contain a _demo-manifest.json and returns a summary list.
 */
export async function GET() {
  const publicDir = path.join(process.cwd(), "public");

  const books: ManifestSummary[] = [];

  try {
    const entries = await fs.readdir(publicDir);
    const chronicleDirs = entries
      .filter((e) => e.startsWith("chronicle-"))
      .sort();

    for (const dir of chronicleDirs) {
      const manifestPath = path.join(publicDir, dir, "_demo-manifest.json");
      try {
        const raw = await fs.readFile(manifestPath, "utf8");
        const manifest = JSON.parse(raw) as {
          slug?: string;
          demoTitle?: string;
          sourceTitle?: string;
          stats?: {
            sentences: number;
            chunks: number;
            chapters: number;
            pages: number;
          };
        };

        // Extract slug from directory name: chronicle-<slug> → <slug>
        const slug = manifest.slug || dir.replace("chronicle-", "");

        books.push({
          slug,
          demoTitle: manifest.demoTitle || manifest.sourceTitle || slug,
          sourceTitle: manifest.sourceTitle || slug,
          stats: manifest.stats || { sentences: 0, chunks: 0, chapters: 0, pages: 0 },
        });
      } catch {
        // Skip directories without a valid manifest
        continue;
      }
    }
  } catch {
    // public/ doesn't exist or isn't readable
  }

  // Backward compatibility: if no chronicle directories found, check for legacy chronicle-dune
  if (books.length === 0) {
    try {
      const legacyPath = path.join(publicDir, "chronicle-dune", "_demo-manifest.json");
      const raw = await fs.readFile(legacyPath, "utf8");
      const manifest = JSON.parse(raw);
      books.push({
        slug: "dune",
        demoTitle: manifest.demoTitle || "Dune (2021) film transcript",
        sourceTitle: manifest.sourceTitle || "Dune (2021)",
        stats: manifest.stats || { sentences: 0, chunks: 0, chapters: 0, pages: 0 },
      });
    } catch {
      // No legacy data either
    }
  }

  return NextResponse.json({ books });
}
