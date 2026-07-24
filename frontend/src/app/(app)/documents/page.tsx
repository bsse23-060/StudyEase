"use client";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { list } from "@/lib/api/client";
import { uploadDocument, type UploadHandle } from "@/lib/api/upload";
import { endpoints } from "@/lib/api/endpoints";
import type { DocumentRecord } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import {
  Badge,
  Button,
  Empty,
  Field,
  Skeleton,
  inputClass,
  useToast,
} from "@/components/ui";
import { useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { documentSchema } from "@/lib/validation";
export default function Documents() {
  const courseParam = useSearchParams().get("course");
  const qc = useQueryClient(),
    toast = useToast();
  const q = useQuery({
    queryKey: ["documents"],
    queryFn: () => list<DocumentRecord>(endpoints.documents),
    refetchInterval: (query) =>
      query.state.data?.results.some((d) =>
        ["uploaded", "queued", "processing"].includes(d.status),
      )
        ? 5000
        : false,
  });
  const [title, setTitle] = useState(""),
    [visibility, setVisibility] = useState<"private" | "course">(
      courseParam ? "course" : "private",
    ),
    [file, setFile] = useState<File | null>(null),
    [error, setError] = useState(""),
    [progress, setProgress] = useState<number | null>(null),
    [stage, setStage] = useState<"idle" | "uploading" | "uploaded">("idle");
  const activeUpload = useRef<UploadHandle | null>(null);
  async function beginUpload() {
    const parsed = documentSchema.safeParse({ title, visibility, file });
    if (!parsed.success) throw new Error(parsed.error.issues[0]?.message);
    const form = new FormData();
    form.set("title", title);
    form.set("visibility", visibility);
    form.set("file", file!);
    if (courseParam) form.set("course", courseParam);
    setStage("uploading");
    setProgress(0);
    const handle = uploadDocument(form, setProgress);
    activeUpload.current = handle;
    await handle.promise;
    setStage("uploaded");
    setProgress(100);
    setTitle("");
    setFile(null);
    qc.invalidateQueries({ queryKey: ["documents"] });
    toast("Upload complete. Document processing is now queued.");
  }
  return (
    <>
      <PageHeading
        eyebrow="Source library"
        title="Your documents"
        description="Upload PDF, TXT, Markdown, or DOCX files up to 10 MB. Processing runs asynchronously in production."
      />
      <form
        className="card mb-7 grid gap-4 p-5 md:grid-cols-[1fr_180px_1fr_auto] md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          setError("");
          beginUpload().catch((reason: Error) => {
            setError(reason.message);
            setStage("idle");
            setProgress(null);
          });
        }}
      >
        <Field label="Document title">
          <input
            className={inputClass}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>
        <Field label="Visibility">
          <select
            className={inputClass}
            value={visibility}
            onChange={(e) => setVisibility(e.target.value as typeof visibility)}
          >
            <option value="private">Personal</option>
            <option value="course">Course material</option>
          </select>
        </Field>
        <Field label="Choose file" hint="PDF, TXT, MD, DOCX · max 10 MB">
          <input
            className="block w-full rounded-xl border bg-white p-2"
            type="file"
            accept=".pdf,.txt,.md,.docx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
        <Button disabled={stage === "uploading"}>
          {stage === "uploading" ? `Uploading ${progress ?? 0}%` : "Upload"}
        </Button>
        {stage === "uploading" && (
          <div className="md:col-span-4">
            <div
              role="progressbar"
              aria-label="Document upload"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress ?? 0}
              className="h-3 overflow-hidden rounded-full bg-slate-200"
            >
              <div
                className="h-full bg-emerald-700"
                style={{ width: `${progress ?? 0}%` }}
              />
            </div>
            <Button
              type="button"
              className="mt-2"
              variant="secondary"
              onClick={() => activeUpload.current?.cancel()}
            >
              Cancel upload
            </Button>
            <p className="mt-2 text-sm">
              Uploading transfers the file. Extraction and embedding use the
              separate queued and processing states.
            </p>
          </div>
        )}
        {stage === "uploaded" && (
          <p role="status" className="text-sm text-emerald-800 md:col-span-4">
            Upload complete; processing status will update below.
          </p>
        )}
        {error && (
          <p className="text-sm text-red-700 md:col-span-4" role="alert">
            {error}
          </p>
        )}
      </form>
      {q.isLoading ? (
        <Skeleton />
      ) : !q.data?.results.length ? (
        <Empty
          title="No documents"
          body="Upload study material to make it available for cited retrieval."
        />
      ) : (
        <div className="grid gap-3">
          {q.data.results.map((d) => (
            <Link
              key={d.id}
              href={`/documents/${d.id}`}
              className="card flex items-center justify-between gap-4 p-4"
            >
              <div className="min-w-0">
                <h2 className="truncate font-bold">{d.title}</h2>
                <p className="text-sm text-slate-500">
                  {d.original_filename || "Linked source"} · {d.chunk_count}{" "}
                  chunks
                </p>
              </div>
              <Badge
                tone={
                  d.status === "ready"
                    ? "success"
                    : d.status === "failed"
                      ? "danger"
                      : "warning"
                }
              >
                {d.status}
              </Badge>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
