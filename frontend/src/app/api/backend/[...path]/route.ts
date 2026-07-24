import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { ACCESS, REFRESH, clearTokens, setTokens } from "@/lib/auth/cookies";
const base = () =>
  process.env.DJANGO_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
async function forward(request: NextRequest, path: string, access?: string) {
  const headers = new Headers(request.headers);
  headers.delete("cookie");
  headers.delete("host");
  headers.delete("content-length");
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const body = ["GET", "HEAD"].includes(request.method)
    ? undefined
    : await request.arrayBuffer();
  const upstreamPath = path.endsWith("/") ? path : `${path}/`;
  return fetch(`${base()}/${upstreamPath}${request.nextUrl.search}`, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });
}
async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  const maximum = Number(process.env.BFF_MAX_REQUEST_BYTES ?? 12 * 1024 * 1024);
  if (contentLength > maximum)
    return NextResponse.json(
      { detail: "Request body is too large." },
      { status: 413 },
    );
  const path = (await params).path.join("/");
  const jar = await cookies();
  let access = jar.get(ACCESS)?.value;
  let upstream = await forward(request, path, access);
  let rotated: { access: string; refresh?: string } | undefined;
  if (upstream.status === 401 && jar.get(REFRESH)?.value) {
    const refresh = jar.get(REFRESH)!.value;
    const tokenResponse = await fetch(`${base()}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (tokenResponse.ok) {
      rotated = await tokenResponse.json();
      access = rotated!.access;
      upstream = await forward(request, path, access);
    }
  }
  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
  if (rotated) setTokens(response, rotated);
  if (upstream.status === 401) clearTokens(response);
  return response;
}
export {
  handler as GET,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
};
