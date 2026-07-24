"use client";
import { useMutation } from "@tanstack/react-query";
import { api, json } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { PageHeading } from "@/components/page-heading";
import { Button, Empty, Field, inputClass } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { useState } from "react";
interface Result {
  query: string;
  results: {
    chunk_id: number;
    score: number;
    document_title: string;
    page: number | null;
    section_title: string;
  }[];
}
export default function Retrieval() {
  const { data: user } = useSession();
  const [query, setQuery] = useState(""),
    [course, setCourse] = useState(""),
    [lesson, setLesson] = useState(""),
    [topK, setTopK] = useState(5);
  const preview = useMutation({
    mutationFn: () =>
      api<Result>(`${endpoints.documents}retrieval-preview/`, {
        method: "POST",
        ...json({
          query,
          course: course ? Number(course) : null,
          lesson: lesson ? Number(lesson) : null,
          top_k: topK,
        }),
      }),
  });
  if (user?.role === "student")
    return (
      <Empty
        title="Diagnostic access required"
        body="Retrieval preview is restricted to instructors and administrators."
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="Instructor diagnostic"
        title="Retrieval preview"
        description="Inspect which authorised chunks match a query. Scores are diagnostic signals, not answer confidence."
      />
      <form
        className="card grid gap-4 p-5 md:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault();
          preview.mutate();
        }}
      >
        <div className="md:col-span-4">
          <Field label="Retrieval query">
            <input
              className={inputClass}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </Field>
        </div>
        <Field label="Course ID (optional)">
          <input
            className={inputClass}
            inputMode="numeric"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
          />
        </Field>
        <Field label="Lesson ID (optional)">
          <input
            className={inputClass}
            inputMode="numeric"
            value={lesson}
            onChange={(e) => setLesson(e.target.value)}
          />
        </Field>
        <Field label="Top results">
          <select
            className={inputClass}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          >
            {[1, 3, 5, 10].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </Field>
        <Button
          className="self-end"
          disabled={!query.trim() || preview.isPending}
        >
          Preview
        </Button>
      </form>
      {preview.isError && (
        <p role="alert" className="mt-4 rounded-xl bg-red-50 p-4 text-red-800">
          {preview.error.message}
        </p>
      )}
      <div className="mt-6 grid gap-3">
        {preview.data?.results.map((r) => (
          <article className="card p-5" key={r.chunk_id}>
            <div className="flex justify-between">
              <h2 className="font-bold">{r.document_title}</h2>
              <span className="font-mono text-sm">{r.score.toFixed(4)}</span>
            </div>
            <p className="mt-2 text-sm text-slate-500">
              Chunk {r.chunk_id}
              {r.page ? ` · page ${r.page}` : ""}
              {r.section_title ? ` · ${r.section_title}` : ""}
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
