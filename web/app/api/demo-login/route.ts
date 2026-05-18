import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "adpilot_demo_auth";

export async function POST(request: NextRequest) {
  const configured = process.env.ADPILOT_DEMO_PASSWORD;
  if (!configured) {
    return NextResponse.json({ ok: true });
  }

  const body = await request.json().catch(() => ({}));
  if (body.password !== configured) {
    return NextResponse.json({ error: "Incorrect password" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, configured, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return response;
}
