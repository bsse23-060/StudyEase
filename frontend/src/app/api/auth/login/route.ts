import { NextResponse } from "next/server";
import { setTokens } from "@/lib/auth/cookies";
const base = () =>
  process.env.DJANGO_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
export async function POST(request: Request) {
  const body = await request.text();
  const upstream = await fetch(`${base()}/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cache: "no-store",
  });
  const data = await upstream.json();
  if (!upstream.ok) return NextResponse.json(data, { status: upstream.status });
  const response = NextResponse.json({ ok: true });
  setTokens(response, data);
  return response;
}
