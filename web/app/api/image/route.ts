import { NextRequest } from "next/server";
import { readFile } from "node:fs/promises";

export async function GET(req: NextRequest) {
  const p = req.nextUrl.searchParams.get("p");
  if (!p) return new Response("missing p", { status: 400 });
  // Constrain to workspace/ to avoid arbitrary file reads
  if (!p.includes("/workspace/")) return new Response("forbidden", { status: 403 });
  try {
    const buf = await readFile(p);
    return new Response(new Uint8Array(buf), {
      headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=3600" },
    });
  } catch {
    return new Response("not found", { status: 404 });
  }
}
