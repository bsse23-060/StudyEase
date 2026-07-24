"use client";
import { useSearchParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Course, Lesson, Module } from "@/lib/api/types";
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
import { useSession } from "@/hooks/use-session";
import { useState } from "react";
import Link from "next/link";
export default function Builder() {
  const { data: user } = useSession(),
    params = useSearchParams(),
    router = useRouter(),
    qc = useQueryClient(),
    toast = useToast();
  const id = params.get("course");
  const course = useQuery({
    queryKey: ["course", id],
    queryFn: () => api<Course>(detail(endpoints.courses, id!)),
    enabled: !!id,
  });
  const [form, setForm] = useState({
    title: "",
    slug: "",
    description: "",
    is_published: false,
  });
  const create = useMutation({
    mutationFn: () =>
      api<Course>(endpoints.courses, { method: "POST", ...json(form) }),
    onSuccess: (c) => {
      toast("Course created.");
      router.replace(`/instructor/builder?course=${c.id}`);
    },
  });
  if (user?.role === "student")
    return (
      <Empty
        title="Instructor access required"
        body="Course authoring is restricted by role and object ownership."
      />
    );
  if (id && course.isLoading) return <Skeleton />;
  if (id && !course.data)
    return (
      <Empty
        title="Course unavailable"
        body="The course does not exist or belongs to another instructor. The backend returned no editable object."
      />
    );
  if (
    id &&
    course.data &&
    user?.role !== "admin" &&
    course.data.instructor !== user?.id
  )
    return (
      <Empty
        title="Course unavailable"
        body="You can view this published course, but only its owner or an administrator can open it in the builder."
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="Course builder"
        title={course.data?.title ?? "Create a course"}
        description="Ordering uses explicit numeric positions because the backend has no reorder action. Unsaved fields are not sent."
      />
      {course.data && (
        <nav
          aria-label="Course builder sections"
          className="mb-6 flex flex-wrap gap-2"
        >
          {(
            [
              [
                "Curriculum",
                `/instructor/courses/${course.data.id}/curriculum`,
              ],
              ["Concepts", `/instructor/courses/${course.data.id}/concepts`],
              ["Quizzes", `/instructor/courses/${course.data.id}/quizzes`],
              ["Documents", `/instructor/courses/${course.data.id}/documents`],
              ["Students", `/instructor/courses/${course.data.id}/students`],
            ] as const
          ).map(([label, href]) => (
            <Link
              className="rounded-xl border bg-white px-4 py-2 font-semibold"
              href={href}
              key={href}
            >
              {label}
            </Link>
          ))}
        </nav>
      )}
      {!course.data ? (
        <form
          className="card grid max-w-2xl gap-4 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <Field label="Course title">
            <input
              className={inputClass}
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  title: e.target.value,
                  slug: e.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, "-")
                    .replace(/^-|-$/g, ""),
                }))
              }
            />
          </Field>
          <Field label="Slug">
            <input
              className={inputClass}
              value={form.slug}
              onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
            />
          </Field>
          <Field label="Description">
            <textarea
              className={`${inputClass} min-h-32`}
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
            />
          </Field>
          <label className="flex gap-2">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(e) =>
                setForm((f) => ({ ...f, is_published: e.target.checked }))
              }
            />
            Publish course immediately
          </label>
          <Button disabled={create.isPending || !form.title.trim()}>
            Create course
          </Button>
        </form>
      ) : (
        <CourseEditor
          course={course.data}
          refresh={() => qc.invalidateQueries({ queryKey: ["course", id] })}
          onCourseDeleted={() => router.replace("/instructor/courses")}
        />
      )}
    </>
  );
}
function CourseEditor({
  course,
  refresh,
  onCourseDeleted,
}: {
  course: Course;
  refresh: () => void;
  onCourseDeleted: () => void;
}) {
  const [settings, setSettings] = useState({
    title: course.title,
    description: course.description,
    is_published: course.is_published,
  });
  const [remove, setRemove] = useState<{
    resource: string;
    id: number;
    label: string;
  } | null>(null);
  const update = useMutation({
    mutationFn: () =>
      api(detail(endpoints.courses, course.id), {
        method: "PATCH",
        ...json(settings),
      }),
    onSuccess: refresh,
  });
  const destroy = useMutation({
    mutationFn: () =>
      api(detail(remove!.resource, remove!.id), { method: "DELETE" }),
    onSuccess: () => {
      const deletedCourse = remove?.resource === endpoints.courses;
      setRemove(null);
      if (deletedCourse) onCourseDeleted();
      else refresh();
    },
  });
  return (
    <div className="grid gap-6">
      <section className="card grid gap-3 p-6 md:grid-cols-2">
        <h2 className="text-xl font-black md:col-span-2">Course settings</h2>
        <Field label="Title">
          <input
            className={inputClass}
            value={settings.title}
            onChange={(e) =>
              setSettings((s) => ({ ...s, title: e.target.value }))
            }
          />
        </Field>
        <Field label="Description">
          <textarea
            className={inputClass}
            value={settings.description}
            onChange={(e) =>
              setSettings((s) => ({ ...s, description: e.target.value }))
            }
          />
        </Field>
        <label className="flex gap-2">
          <input
            type="checkbox"
            checked={settings.is_published}
            onChange={(e) =>
              setSettings((s) => ({ ...s, is_published: e.target.checked }))
            }
          />{" "}
          Published
        </label>
        <div className="flex gap-2">
          <Button onClick={() => update.mutate()}>Save course</Button>
          <Button
            variant="danger"
            onClick={() =>
              setRemove({
                resource: endpoints.courses,
                id: course.id,
                label: course.title,
              })
            }
          >
            Delete course
          </Button>
        </div>
      </section>
      <section className="card p-6">
        <div className="flex justify-between">
          <div>
            <h2 className="text-xl font-black">Curriculum</h2>
            <p className="text-sm text-slate-500">
              Add modules, then lessons and quiz questions.
            </p>
          </div>
        </div>
        <ModuleForm
          course={course.id}
          next={course.modules.length + 1}
          refresh={refresh}
        />
      </section>
      {course.modules.map((m) => (
        <section className="card p-6" key={m.id}>
          <div className="flex justify-between">
            <h2 className="text-xl font-black">
              {m.position}. {m.title}
            </h2>
            <Button
              variant="danger"
              onClick={() =>
                setRemove({
                  resource: endpoints.modules,
                  id: m.id,
                  label: m.title,
                })
              }
            >
              Delete module
            </Button>
          </div>
          <p className="text-slate-600">{m.summary}</p>
          <LessonForm
            module={m.id}
            next={m.lessons.length + 1}
            refresh={refresh}
          />
          <div className="mt-4 grid gap-2">
            {m.lessons.map((l) => (
              <div key={l.id} className="rounded-xl bg-slate-50 p-4">
                <div className="float-right">
                  <Button
                    variant="danger"
                    onClick={() =>
                      setRemove({
                        resource: endpoints.lessons,
                        id: l.id,
                        label: l.title,
                      })
                    }
                  >
                    Delete lesson
                  </Button>
                </div>
                <strong>
                  {l.position}. {l.title}
                </strong>
                <span className="ml-2 text-sm text-slate-500">
                  {l.kind} · {l.questions.length} questions
                </span>
                <QuestionForm lesson={l} refresh={refresh} />
              </div>
            ))}
          </div>
        </section>
      ))}
      <Confirm
        open={!!remove}
        title={`Delete ${remove?.label ?? "resource"}?`}
        body="Nested content will also be deleted. This action cannot be undone."
        onCancel={() => setRemove(null)}
        onConfirm={() => destroy.mutate()}
        busy={destroy.isPending}
      />
    </div>
  );
}
function ModuleForm({
  course,
  next,
  refresh,
}: {
  course: number;
  next: number;
  refresh: () => void;
}) {
  const [title, setTitle] = useState("");
  const m = useMutation({
    mutationFn: () =>
      api<Module>(endpoints.modules, {
        method: "POST",
        ...json({ course, title, summary: "", position: next }),
      }),
    onSuccess: () => {
      setTitle("");
      refresh();
    },
  });
  return (
    <form
      className="mt-4 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
    >
      <input
        aria-label="New module title"
        className={inputClass}
        placeholder="New module title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <Button disabled={!title.trim()}>Add module</Button>
    </form>
  );
}
function LessonForm({
  module,
  next,
  refresh,
}: {
  module: number;
  next: number;
  refresh: () => void;
}) {
  const [title, setTitle] = useState("");
  const m = useMutation({
    mutationFn: () =>
      api<Lesson>(endpoints.lessons, {
        method: "POST",
        ...json({
          module,
          title,
          kind: "text",
          content: "",
          resource_url: "",
          estimated_minutes: 20,
          position: next,
        }),
      }),
    onSuccess: () => {
      setTitle("");
      refresh();
    },
  });
  return (
    <form
      className="mt-4 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
    >
      <input
        aria-label="New lesson title"
        className={inputClass}
        placeholder="New lesson title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <Button variant="secondary" disabled={!title.trim()}>
        Add lesson
      </Button>
    </form>
  );
}
function QuestionForm({
  lesson,
  refresh,
}: {
  lesson: Lesson;
  refresh: () => void;
}) {
  const [prompt, setPrompt] = useState("");
  const m = useMutation({
    mutationFn: () =>
      api(endpoints.questions, {
        method: "POST",
        ...json({
          lesson: lesson.id,
          kind: "true_false",
          prompt,
          options: [],
          correct_answer: true,
          explanation: "",
          difficulty: 0.5,
          points: 1,
          concept: null,
        }),
      }),
    onSuccess: () => {
      setPrompt("");
      refresh();
    },
  });
  return (
    <form
      className="mt-3 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
    >
      <input
        aria-label={`New question for ${lesson.title}`}
        className={inputClass}
        placeholder="Add a true/false question"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <Button variant="secondary" disabled={!prompt.trim()}>
        Add question
      </Button>
    </form>
  );
}
