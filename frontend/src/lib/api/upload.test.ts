import { describe, expect, it, vi } from "vitest";
import { uploadDocument } from "./upload";
class FakeXhr {
  status = 201;
  response: unknown = { id: 1, title: "Notes" };
  withCredentials = false;
  responseType = "";
  listeners: Record<string, () => void> = {};
  uploadListeners: Record<string, (e: ProgressEvent) => void> = {};
  upload = {
    addEventListener: (name: string, fn: (e: ProgressEvent) => void) => {
      this.uploadListeners[name] = fn;
    },
  };
  open = vi.fn();
  send = vi.fn(() => {
    this.uploadListeners.progress?.({
      lengthComputable: true,
      loaded: 5,
      total: 10,
    } as ProgressEvent);
    this.listeners.load?.();
  });
  abort = vi.fn(() => this.listeners.abort?.());
  addEventListener(name: string, fn: () => void) {
    this.listeners[name] = fn;
  }
}
describe("document uploader", () => {
  it("reports measurable progress and returns the response", async () => {
    const xhr = new FakeXhr(),
      progress = vi.fn();
    const handle = uploadDocument(
      new FormData(),
      progress,
      () => xhr as unknown as XMLHttpRequest,
    );
    await expect(handle.promise).resolves.toMatchObject({ id: 1 });
    expect(progress).toHaveBeenCalledWith(50);
    expect(xhr.withCredentials).toBe(true);
  });
  it("supports cancellation", async () => {
    const xhr = new FakeXhr();
    xhr.send = vi.fn();
    const handle = uploadDocument(
      new FormData(),
      () => {},
      () => xhr as unknown as XMLHttpRequest,
    );
    handle.cancel();
    await expect(handle.promise).rejects.toThrow("Upload cancelled");
    expect(xhr.abort).toHaveBeenCalled();
  });
  it("returns backend upload errors", async () => {
    const xhr = new FakeXhr();
    xhr.status = 400;
    xhr.response = { file: ["Unsupported type."] };
    await expect(
      uploadDocument(
        new FormData(),
        () => {},
        () => xhr as unknown as XMLHttpRequest,
      ).promise,
    ).rejects.toMatchObject({
      status: 400,
      fields: { file: ["Unsupported type."] },
    });
  });
  it("reports network failures", async () => {
    const xhr = new FakeXhr();
    xhr.send = vi.fn(() => xhr.listeners.error?.());
    await expect(
      uploadDocument(
        new FormData(),
        () => {},
        () => xhr as unknown as XMLHttpRequest,
      ).promise,
    ).rejects.toThrow("Network failure");
  });
});
