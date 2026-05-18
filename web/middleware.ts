import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "adpilot_demo_auth";

function gateEnabled() {
  return !!process.env.ADPILOT_DEMO_PASSWORD;
}

function isAuthed(request: NextRequest) {
  return request.cookies.get(COOKIE_NAME)?.value === process.env.ADPILOT_DEMO_PASSWORD;
}

export function middleware(request: NextRequest) {
  if (!gateEnabled() || isAuthed(request)) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = "/demo-login";
  url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    "/",
    "/onboard/:path*",
    "/workspace/:path*",
    "/api/sidecar/:path*",
    "/api/image/:path*",
  ],
};
