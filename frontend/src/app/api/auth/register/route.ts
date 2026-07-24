import { NextResponse } from "next/server";
const base = () =>
  process.env.DJANGO_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
export async function POST(request: Request) {
  const upstream = await fetch(`${base()}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
