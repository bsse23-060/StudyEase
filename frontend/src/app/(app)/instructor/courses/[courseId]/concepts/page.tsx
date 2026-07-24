"use client";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import { PageHeading } from "@/components/page-heading";
import {
  Button,
  Confirm,
  Empty,
  Field,
  Skeleton,
  inputClass,
  useToast,
} from "@/components/ui";
import { useState } from "react";
interface Concept {
  id: number;
  course: number;
  slug: string;
  name: string;
  description: string;
  prerequisites: number[];
}
export default function Concepts() {
  const { courseId } = useParams<{ courseId: string }>(),
    qc = useQueryClient(),
    toast = useToast();
  const q = useQuery({
    queryKey: ["concepts", courseId],
    queryFn: () => list<Concept>(endpoints.concepts, { course: courseId }),
  });
  const [name, setName] = useState(""),
    [description, setDescription] = useState(""),
    [selected, setSelected] = useState<Concept | null>(null),
    [prerequisites, setPrerequisites] = useState<number[]>([]),
    [remove, setRemove] = useState<Concept | null>(null);
  const refresh = () =>
    qc.invalidateQueries({ queryKey: ["concepts", courseId] });
  const create = useMutation({
    mutationFn: () =>
      api(endpoints.concepts, {
        method: "POST",
        ...json({
          course: Number(courseId),
          name,
          slug: `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${courseId}`,
          description,
          lessons: [],
          prerequisites: [],
        }),
      }),
    onSuccess: () => {
      setName("");
      setDescription("");
      refresh();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  const saveEdges = useMutation({
    mutationFn: () =>
      api(detail(endpoints.concepts, selected!.id), {
        method: "PATCH",
        ...json({ prerequisites }),
      }),
    onSuccess: () => {
      refresh();
      toast("Prerequisite chain updated.");
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.concepts, remove!.id), { method: "DELETE" }),
    onSuccess: () => {
      setRemove(null);
      refresh();
    },
  });
  if (q.isLoading) return <Skeleton />;
  const concepts = q.data?.results ?? [];
  return (
    <>
      <PageHeading
        eyebrow="Course builder · Concepts"
        title="Prerequisite map"
        description="An arrow A → B means A is required before B. The server rejects self-links, cross-course links, duplicates, and direct or indirect cycles."
      />
      <form
        className="card grid gap-3 p-5 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Field label="Concept name">
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Description">
          <input
            className={inputClass}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Button className="justify-self-start" disabled={!name.trim()}>
          Add concept
        </Button>
      </form>
      {!concepts.length ? (
        <Empty
          title="No concepts"
          body="Create the first concept in this course."
        />
      ) : (
        <div className="mt-6 grid gap-3">
          {concepts.map((c) => (
            <article className="card p-5" key={c.id}>
              <div className="flex justify-between">
                <div>
                  <h2 className="font-bold">{c.name}</h2>
                  <p className="text-sm text-slate-600">
                    Requires:{" "}
                    {c.prerequisites
                      .map(
                        (id) => concepts.find((x) => x.id === id)?.name ?? id,
                      )
                      .join(" → ") || "Nothing"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSelected(c);
                      setPrerequisites(c.prerequisites);
                    }}
                  >
                    Edit prerequisites
                  </Button>
                  <Button variant="danger" onClick={() => setRemove(c)}>
                    Delete
                  </Button>
                </div>
              </div>
              {selected?.id === c.id && (
                <div className="mt-4 border-t pt-4">
                  <fieldset>
                    <legend className="font-bold">
                      Select requirements for {c.name}
                    </legend>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      {concepts
                        .filter((x) => x.id !== c.id)
                        .map((option) => (
                          <label
                            className="rounded-xl bg-slate-50 p-3"
                            key={option.id}
                          >
                            <input
                              type="checkbox"
                              checked={prerequisites.includes(option.id)}
                              onChange={(e) =>
                                setPrerequisites((p) =>
                                  e.target.checked
                                    ? [...p, option.id]
                                    : p.filter((id) => id !== option.id),
                                )
                              }
                            />{" "}
                            {option.name} → {c.name}
                          </label>
                        ))}
                    </div>
                  </fieldset>
                  <Button className="mt-3" onClick={() => saveEdges.mutate()}>
                    Save relationships
                  </Button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      <Confirm
        open={!!remove}
        title="Delete this concept?"
        body="Questions and mastery records may be affected. This cannot be undone."
        onCancel={() => setRemove(null)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
    </>
  );
}
