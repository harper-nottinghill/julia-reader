import { execFile } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import os from "os";
import path from "path";

const execFileAsync = promisify(execFile);

const MAX_INPUT_CHARS = 400_000;

function parseValidationCounts(report: string): { errors: number; warnings: number } {
  const warnHeading = "\n## Warnings\n";
  const i = report.indexOf(warnHeading);
  const errBlock = i === -1 ? report : report.slice(0, i);
  const warnBlock = i === -1 ? "" : report.slice(i + warnHeading.length);
  const countBullets = (block: string) =>
    block.split("\n").filter((line) => {
      if (!line.startsWith("- ")) return false;
      const rest = line.slice(2).trim();
      return rest !== "None";
    }).length;
  return { errors: countBullets(errBlock), warnings: countBullets(warnBlock) };
}

export type ReaderRunResult = {
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

export type ReaderRunError = {
  ok: false;
  error: string;
  stderr?: string;
};

export function getRepoRoot(): string {
  const env = process.env.JULIA_READER_REPO_ROOT;
  if (env) return path.resolve(env);
  return path.resolve(process.cwd(), "..", "..");
}

async function resolvePython(repoRoot: string): Promise<string> {
  const custom = process.env.JULIA_READER_PYTHON;
  if (custom) return custom;
  const venvPy = path.join(repoRoot, ".venv", "bin", "python3");
  try {
    await fs.access(venvPy);
    return venvPy;
  } catch {
    return "python3";
  }
}

async function latestRunRoot(outDir: string): Promise<string> {
  const readerDir = path.join(outDir, "_reader");
  const entries = await fs.readdir(readerDir);
  if (!entries.length) throw new Error("Reader finished but _reader/ is empty");
  entries.sort((a, b) => b.localeCompare(a));
  return path.join(readerDir, entries[0]);
}

export async function runJuliaReader(options: {
  text: string;
  noLlm: boolean;
}): Promise<ReaderRunResult | ReaderRunError> {
  const text = (options.text ?? "").trim();
  if (!text) {
    return { ok: false, error: "Provide non-empty text." };
  }
  if (text.length > MAX_INPUT_CHARS) {
    return {
      ok: false,
      error: `Input too long (max ${MAX_INPUT_CHARS.toLocaleString()} characters).`,
    };
  }

  const repoRoot = getRepoRoot();
  const python = await resolvePython(repoRoot);
  const tmpBase = await fs.mkdtemp(path.join(os.tmpdir(), "julia-reader-next-"));
  const inputPath = path.join(tmpBase, "input.txt");
  await fs.writeFile(inputPath, text, "utf8");

  const args = ["-m", "julia_reader", "-f", inputPath, "-o", tmpBase, "--quiet"];
  if (options.noLlm) {
    args.push("--no-llm");
  }

  const env = {
    ...process.env,
    PYTHONPATH: path.join(repoRoot, "src"),
  };

  try {
    await execFileAsync(python, args, {
      cwd: repoRoot,
      env,
      maxBuffer: 64 * 1024 * 1024,
    });
    const runRoot = await latestRunRoot(tmpBase);
    const statePath = path.join(runRoot, "state", "reader_state.json");
    const planPath = path.join(runRoot, "state", "book_plan.json");
    const packetPath = path.join(runRoot, "state", "reader_packet.json");
    const validationPath = path.join(runRoot, "logs", "validation_report.md");
    const livePath = path.join(runRoot, "state", "live_summary.md");
    const indexPath = path.join(runRoot, "book", "00_index.md");

    const [stateRaw, planRaw, packetRaw, validationRaw, liveSummary, bookIndex] =
      await Promise.all([
        fs.readFile(statePath, "utf8"),
        fs.readFile(planPath, "utf8"),
        fs.readFile(packetPath, "utf8"),
        fs.readFile(validationPath, "utf8"),
        fs.readFile(livePath, "utf8"),
        fs.readFile(indexPath, "utf8"),
      ]);

    const state = JSON.parse(stateRaw) as {
      total_sentences?: number;
      total_chunks?: number;
    };
    const plan = JSON.parse(planRaw) as {
      chapters?: Array<{ page_plan?: unknown[] }>;
    };
    const packet = JSON.parse(packetRaw) as { modelUsed?: string };

    const chapters = plan.chapters?.length ?? 0;
    const pages =
      plan.chapters?.reduce((n, ch) => n + (ch.page_plan?.length ?? 0), 0) ?? 0;

    const { errors, warnings } = parseValidationCounts(validationRaw);

    return {
      ok: true,
      summary: {
        folderName: path.basename(runRoot),
        sentences: Number(state.total_sentences ?? 0),
        chunks: Number(state.total_chunks ?? 0),
        chapters,
        pages,
        readerModel:
          packet.modelUsed ??
          (options.noLlm ? "local-fallback" : process.env.JULIA_READER_MODEL ?? "unknown"),
        errors,
        warnings,
      },
      liveSummary,
      bookIndex,
    };
  } catch (e: unknown) {
    const err = e as { stderr?: string; message?: string };
    const stderr = typeof err.stderr === "string" ? err.stderr : undefined;
    return {
      ok: false,
      error: err.message ?? String(e),
      stderr,
    };
  } finally {
    await fs.rm(tmpBase, { recursive: true, force: true }).catch(() => undefined);
  }
}
