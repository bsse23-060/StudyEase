import type { NextResponse } from "next/server";
export const ACCESS = "se_access",
  REFRESH = "se_refresh";
const base = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure:
    process.env.AUTH_COOKIE_SECURE === undefined
      ? process.env.NODE_ENV === "production"
      : process.env.AUTH_COOKIE_SECURE === "true",
  path: "/",
};
export function setTokens(
  response: NextResponse,
  tokens: { access: string; refresh?: string },
) {
  response.cookies.set(ACCESS, tokens.access, { ...base, maxAge: 30 * 60 });
  if (tokens.refresh)
    response.cookies.set(REFRESH, tokens.refresh, {
      ...base,
      maxAge: 7 * 24 * 60 * 60,
    });
}
export function clearTokens(response: NextResponse) {
  response.cookies.set(ACCESS, "", { ...base, maxAge: 0 });
  response.cookies.set(REFRESH, "", { ...base, maxAge: 0 });
}
export function safeReturnTo(value: unknown) {
  return typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//")
    ? value
    : "/dashboard";
}
