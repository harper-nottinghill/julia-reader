import { runJuliaReader } from "@/lib/reader-runner";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300;

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

  const result = await runJuliaReader({ text, noLlm });
  if (!result.ok) {
    return NextResponse.json(result, { status: 422 });
  }
  return NextResponse.json(result);
}
