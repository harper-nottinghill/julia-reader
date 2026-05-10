import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

interface ConfigStatus {
  configured: boolean;
  model: string;
}

/**
 * GET /api/config/status — lightweight config check for the playground UI.
 * Reports whether an API key is present and which model is configured,
 * without ever exposing the secret value.
 */
export async function GET() {
  const apiKey =
    process.env.JULIA_READER_API_KEY?.trim() ||
    process.env.OPENAI_API_KEY?.trim() ||
    "";
  const model = process.env.JULIA_READER_MODEL || "gpt-4o-mini";

  const body: ConfigStatus = {
    configured: apiKey.length > 0,
    model,
  };

  return NextResponse.json(body, {
    headers: { "Cache-Control": "no-store" },
  });
}
