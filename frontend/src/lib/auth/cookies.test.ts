import { describe, expect, it } from "vitest";
import { safeReturnTo } from "./cookies";
describe("safe return paths", () => {
  it("keeps local paths", () =>
    expect(safeReturnTo("/documents/2")).toBe("/documents/2"));
  it("rejects protocol-relative redirects", () =>
    expect(safeReturnTo("//evil.example")).toBe("/dashboard"));
  it("rejects absolute redirects", () =>
    expect(safeReturnTo("https://evil.example")).toBe("/dashboard"));
  it("defaults missing values", () =>
    expect(safeReturnTo(null)).toBe("/dashboard"));
});
