import { ApiError } from "./client";
import type { DocumentRecord } from "./types";
export interface UploadHandle {
  promise: Promise<DocumentRecord>;
  cancel: () => void;
}
export function uploadDocument(
  form: FormData,
  onProgress: (percent: number) => void,
  xhrFactory: () => XMLHttpRequest = () => new XMLHttpRequest(),
): UploadHandle {
  const xhr = xhrFactory();
  const promise = new Promise<DocumentRecord>((resolve, reject) => {
    xhr.open("POST", "/api/backend/documents");
    xhr.responseType = "json";
    xhr.withCredentials = true;
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100));
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300)
        resolve(xhr.response as DocumentRecord);
      else {
        const body = (xhr.response ?? {}) as Record<string, unknown>;
        reject(
          new ApiError(
            xhr.status,
            typeof body.detail === "string"
              ? body.detail
              : "Upload failed. Please check the file and try again.",
            Object.fromEntries(
              Object.entries(body).filter(([, v]) => Array.isArray(v)) as [
                string,
                string[],
              ][],
            ),
          ),
        );
      }
    });
    xhr.addEventListener("error", () =>
      reject(new ApiError(0, "Network failure during upload.")),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError(0, "Upload cancelled.")),
    );
    xhr.send(form);
  });
  return { promise, cancel: () => xhr.abort() };
}
