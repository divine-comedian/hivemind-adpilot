import { NextRequest } from "next/server";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

// Repo root is the parent of web/ — server-side image files live at <repo>/workspace/drafts/*.png
const REPO_ROOT = resolve(process.cwd(), "..");
const WORKSPACE_DIR = resolve(REPO_ROOT, "workspace") + sep;

export async function GET(req: NextRequest) {
  const p = req.nextUrl.searchParams.get("p");
  if (!p) return new Response("missing p", { status: 400 });

  // Resolve to absolute path and confirm it's under WORKSPACE_DIR.
  // This blocks path-traversal attempts like /workspace/../../etc/passwd.
  const abs = resolve(p);
  if (!abs.startsWith(WORKSPACE_DIR)) {
    return new Response("forbidden", { status: 403 });
  }

  try {
    const buf = await readFile(abs);
    return new Response(new Uint8Array(buf), {
      headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=3600" },
    });
  } catch {
    return new Response("not found", { status: 404 });
  }
}
