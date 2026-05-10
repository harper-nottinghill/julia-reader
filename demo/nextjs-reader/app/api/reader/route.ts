import { runJuliaReader } from "@/lib/reader-runner";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300;

/**
 * GET /api/reader — returns whether an API key is configured on the server.
 * The playground uses this to show a warning banner when the key is missing.
 */
export async function GET() {
  const configured = Boolean(
    process.env.JULIA_READER_API_KEY?.trim() || process.env.OPENAI_API_KEY?.trim(),
  );
  return NextResponse.json({ configured });
}

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid JSON body." }, { status: 400 });
  }

  const text =
    typeof body === "object" && body !== null && "text" in body
      ? String((body as { text?: unknown }).text ?? "")
      : "";
  const noLlm =
    typeof body === "object" &&
    body !== null &&
    "noLlm" in body &&
    Boolean((body as { noLlm?: unknown }).noLlm);

  // API key: prefer request body, then JULIA_READER_API_KEY env, then OPENAI_API_KEY env
  const bodyApiKey =
    typeof body === "object" && body !== null && "apiKey" in body
      ? String((body as { apiKey?: unknown }).apiKey ?? "")
      : "";
  const apiKey =
    bodyApiKey.trim() || process.env.JULIA_READER_API_KEY || process.env.OPENAI_API_KEY;

  // Model name: prefer request body, then JULIA_READER_MODEL env
  const bodyModelName =
    typeof body === "object" && body !== null && "modelName" in body
      ? String((body as { modelName?: unknown }).modelName ?? "")
      : "";
  const modelName = bodyModelName.trim() || process.env.JULIA_READER_MODEL;

  const result = await runJuliaReader({
    text,
    noLlm,
    apiKey: apiKey ?? undefined,
    modelName: modelName || undefined,
  });
  if (!result.ok) {
    return NextResponse.json(result, { status: 422 });
  }
  return NextResponse.json(result);
}
