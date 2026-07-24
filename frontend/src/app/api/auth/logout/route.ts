import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { ACCESS, REFRESH, clearTokens } from "@/lib/auth/cookies";
export async function POST() {
  const jar = await cookies();
  const refresh = jar.get(REFRESH)?.value;
  const access = jar.get(ACCESS)?.value;
  if (refresh) {
    await fetch(
      `${process.env.DJANGO_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"}/auth/logout/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(access ? { Authorization: `Bearer ${access}` } : {}),
        },
        body: JSON.stringify({ refresh }),
        cache: "no-store",
      },
    ).catch(() => undefined);
  }
  const response = NextResponse.json({ ok: true });
  clearTokens(response);
  return response;
}
