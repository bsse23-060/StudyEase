"use client";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Chunk, DocumentRecord } from "@/lib/api/types";
import {
  Badge,
  Button,
  Confirm,
  Empty,
  Skeleton,
  useToast,
} from "@/components/ui";
import { PageHeading } from "@/components/page-heading";
import { useRef, useState } from "react";
export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>(),
    router = useRouter(),
    qc = useQueryClient(),
    toast = useToast();
  const polls = useRef(0),
    [confirm, setConfirm] = useState(false);
  const q = useQuery({
    queryKey: ["document", id],
    queryFn: () => api<DocumentRecord>(detail(endpoints.documents, id)),
    refetchInterval: (query) => {
      const d = query.state.data;
      if (query.state.fetchStatus === "fetching") polls.current += 1;
      return d &&
        ["uploaded", "queued", "processing"].includes(d.status) &&
        polls.current < 60
        ? 5000
        : false;
    },
  });
  const chunks = useQuery({
    queryKey: ["chunks", id],
    queryFn: () => list<Chunk>(endpoints.chunks, { document: id }),
    enabled: q.data?.status === "ready",
  });
  const action = useMutation({
    mutationFn: (name: "retry" | "reprocess") =>
      api(`${detail(endpoints.documents, id)}${name}/`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document", id] });
      toast("Processing request accepted.");
    },
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.documents, id), { method: "DELETE" }),
    onSuccess: () => router.replace("/documents"),
  });
  if (q.isLoading) return <Skeleton />;
  if (!q.data)
    return (
      <Empty
        title="Document unavailable"
        body="It may have been deleted or belongs to another account."
      />
    );
  const d = q.data;
  return (
    <>
      <PageHeading
        eyebrow="Document"
        title={d.title}
        description={`${d.original_filename || "External source"} · ${(d.file_size / 1024).toFixed(1)} KB`}
        action={
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
        }
      />
      <section className="card p-6">
        <dl className="grid gap-4 sm:grid-cols-3">
          <Info label="Scope" value={d.visibility} />
          <Info label="Chunks" value={String(d.chunk_count)} />
          <Info
            label="Updated"
            value={new Date(d.updated_at).toLocaleString()}
          />
        </dl>
        {d.status === "failed" && (
          <div
            role="alert"
            className="mt-5 rounded-xl bg-red-50 p-4 text-red-800"
          >
            <strong>Processing failed</strong>
            <p>{d.processing_error || "No safe error detail was provided."}</p>
          </div>
        )}
        {["uploaded", "queued", "processing"].includes(d.status) && (
          <p role="status" className="mt-5 rounded-xl bg-amber-50 p-4">
            Processing is in progress. This page checks every 5 seconds and
            stops after 5 minutes.
          </p>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          {d.status === "failed" && (
            <Button onClick={() => action.mutate("retry")}>Retry</Button>
          )}
          {d.status === "ready" && (
            <Button
              variant="secondary"
              onClick={() => action.mutate("reprocess")}
            >
              Reprocess
            </Button>
          )}
          <Button variant="danger" onClick={() => setConfirm(true)}>
            Delete
          </Button>
        </div>
      </section>
      {d.status === "ready" && (
        <section className="mt-7">
          <h2 className="mb-4 text-xl font-bold">Authorised chunks</h2>
          {chunks.isLoading ? (
            <Skeleton />
          ) : (
            <div className="grid gap-3">
              {chunks.data?.results.map((c) => (
                <article className="card p-4" key={c.id}>
                  <p className="text-xs font-bold text-emerald-800">
                    Chunk {c.position}
                    {c.page ? ` · page ${c.page}` : ""}
                    {c.section_title ? ` · ${c.section_title}` : ""}
                  </p>
                  <p className="mt-2 line-clamp-4 text-sm text-slate-600">
                    {c.text}
                  </p>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
      <Confirm
        open={confirm}
        title="Delete this document?"
        body="It will be soft-deleted and removed from retrieval. Existing citations remain auditable on the server."
        onCancel={() => setConfirm(false)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
    </>
  );
}
function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 capitalize">{value}</dd>
    </div>
  );
}
