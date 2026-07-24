import { afterEach, describe, expect, it, vi } from "vitest";
import { api, list } from "./client";
afterEach(() => vi.unstubAllGlobals());
describe("central API client", () => {
  it("uses the same-origin BFF and parses JSON", async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetch);
    await expect(api<{ id: number }>("courses/1/")).resolves.toEqual({ id: 1 });
    expect(fetch).toHaveBeenCalledWith(
      "/api/backend/courses/1",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });
  it("preserves multipart content boundaries", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: 2 }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetch);
    const body = new FormData();
    body.set("title", "Notes");
    await api("documents/", { method: "POST", body });
    const init = fetch.mock.calls[0]![1] as RequestInit;
    expect((init.headers as Headers).has("Content-Type")).toBe(false);
  });
  it("normalises field validation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ title: ["Required."] }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(api("courses/", { method: "POST" })).rejects.toMatchObject({
      status: 400,
      fields: { title: ["Required."] },
    });
  });
  it("builds encoded pagination queries", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetch);
    await list("courses/", { search: "data science", page: 2 });
    expect(fetch.mock.calls[0]![0]).toBe(
      "/api/backend/courses?search=data+science&page=2",
    );
  });
});
