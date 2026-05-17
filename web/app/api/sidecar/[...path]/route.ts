import { NextRequest } from "next/server";

const SIDECAR_BASE = process.env.ADPILOT_API_BASE ?? "http://127.0.0.1:8000";

type Params = {
  params: Promise<{ path?: string[] }>;
};

async function proxy(request: NextRequest, { params }: Params) {
  const { path = [] } = await params;
  const upstream = new URL(`/${path.join("/")}`, SIDECAR_BASE);
  upstream.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  let response: Response;
  try {
    response = await fetch(upstream, {
      method: request.method,
      headers,
      body: request.body,
      duplex: "half",
      cache: "no-store",
    } as RequestInit & { duplex: "half" });
  } catch {
    return Response.json(
      {
        error: `AdPilot sidecar is unreachable at ${SIDECAR_BASE}. Start the FastAPI server or set ADPILOT_API_BASE.`,
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("transfer-encoding");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
