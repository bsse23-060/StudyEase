"use client";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Course, Quiz } from "@/lib/api/types";
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
export default function QuizBuilder() {
  const { courseId } = useParams<{ courseId: string }>(),
    qc = useQueryClient(),
    toast = useToast();
  const course = useQuery({
    queryKey: ["course", courseId],
    queryFn: () => api<Course>(detail(endpoints.courses, courseId)),
  });
  const quizzes = useQuery({
    queryKey: ["course-quizzes", courseId],
    queryFn: async () => {
      const lessons = course.data!.modules.flatMap((m) => m.lessons);
      const pages = await Promise.all(
        lessons.map((l) => list<Quiz>(endpoints.quizzes, { lesson: l.id })),
      );
      return pages.flatMap((p) => p.results);
    },
    enabled: !!course.data,
  });
  const [lesson, setLesson] = useState<number | null>(null),
    [title, setTitle] = useState(""),
    [remove, setRemove] = useState<Quiz | null>(null);
  const refresh = () =>
    qc.invalidateQueries({ queryKey: ["course-quizzes", courseId] });
  const create = useMutation({
    mutationFn: () =>
      api(endpoints.quizzes, {
        method: "POST",
        ...json({
          lesson,
          title,
          instructions: "",
          pass_mark: 60,
          maximum_attempts: 3,
          is_published: false,
        }),
      }),
    onSuccess: () => {
      setTitle("");
      refresh();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.quizzes, remove!.id), { method: "DELETE" }),
    onSuccess: () => {
      setRemove(null);
      refresh();
    },
  });
  if (course.isLoading || quizzes.isLoading) return <Skeleton />;
  const lessons = course.data?.modules.flatMap((m) => m.lessons) ?? [];
  return (
    <>
      <PageHeading
        eyebrow="Course builder · Quizzes"
        title="Assessments"
        description="Configure lifecycle rules, then create ordered questions. Correct answers remain write-only."
      />
      <form
        className="card grid gap-3 p-5 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Field label="Lesson">
          <select
            className={inputClass}
            value={lesson ?? ""}
            onChange={(e) => setLesson(Number(e.target.value))}
          >
            <option value="">Choose lesson</option>
            {lessons.map((l) => (
              <option key={l.id} value={l.id}>
                {l.title}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Quiz title">
          <input
            className={inputClass}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>
        <Button className="self-end" disabled={!lesson || !title.trim()}>
          Create quiz
        </Button>
      </form>
      {!quizzes.data?.length ? (
        <Empty
          title="No quizzes"
          body="Create a quiz for one of this course’s lessons."
        />
      ) : (
        <div className="mt-6 grid gap-4">
          {quizzes.data.map((q) => (
            <QuizCard
              key={q.id}
              quiz={q}
              refresh={refresh}
              remove={() => setRemove(q)}
            />
          ))}
        </div>
      )}
      <Confirm
        open={!!remove}
        title="Delete this quiz?"
        body="Questions are deleted with the quiz. Submitted attempts remain protected by the backend and may prevent deletion."
        onCancel={() => setRemove(null)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
    </>
  );
}
function QuizCard({
  quiz,
  refresh,
  remove,
}: {
  quiz: Quiz;
  refresh: () => void;
  remove: () => void;
}) {
  const toast = useToast();
  const [form, setForm] = useState({
    title: quiz.title,
    pass_mark: quiz.pass_mark ?? 60,
    maximum_attempts: quiz.maximum_attempts ?? 3,
    time_limit_minutes: quiz.time_limit_minutes ?? 15,
    is_published: quiz.is_published,
  });
  const [prompt, setPrompt] = useState(""),
    [options, setOptions] = useState("Yes\nNo"),
    [correct, setCorrect] = useState(0);
  const update = useMutation({
    mutationFn: () =>
      api(detail(endpoints.quizzes, quiz.id), {
        method: "PATCH",
        ...json(form),
      }),
    onSuccess: refresh,
  });
  const question = useMutation({
    mutationFn: () =>
      api(endpoints.questions, {
        method: "POST",
        ...json({
          quiz: quiz.id,
          lesson: quiz.lesson,
          position: quiz.questions.length + 1,
          kind: "multiple_choice",
          prompt,
          options: options.split("\n").filter(Boolean),
          correct_answer: correct,
          points: 1,
          is_required: true,
        }),
      }),
    onSuccess: () => {
      setPrompt("");
      refresh();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  return (
    <article className="card p-5">
      <div className="flex justify-between">
        <h2 className="text-xl font-black">{quiz.title}</h2>
        <Button variant="danger" onClick={remove}>
          Delete quiz
        </Button>
      </div>
      <form
        className="mt-4 grid gap-3 md:grid-cols-5"
        onSubmit={(e) => {
          e.preventDefault();
          update.mutate();
        }}
      >
        <input
          aria-label="Quiz title"
          className={inputClass}
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
        />
        <input
          aria-label="Pass mark"
          type="number"
          min="0"
          max="100"
          className={inputClass}
          value={form.pass_mark}
          onChange={(e) =>
            setForm((f) => ({ ...f, pass_mark: Number(e.target.value) }))
          }
        />
        <input
          aria-label="Maximum attempts"
          type="number"
          min="1"
          className={inputClass}
          value={form.maximum_attempts}
          onChange={(e) =>
            setForm((f) => ({ ...f, maximum_attempts: Number(e.target.value) }))
          }
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_published}
            onChange={(e) =>
              setForm((f) => ({ ...f, is_published: e.target.checked }))
            }
          />{" "}
          Published
        </label>
        <Button variant="secondary">Save rules</Button>
      </form>
      <div className="mt-4 grid gap-2">
        {quiz.questions.map((q) => (
          <QuestionEditor key={q.id} question={q} refresh={refresh} />
        ))}
      </div>
      <form
        className="mt-4 grid gap-3 border-t pt-4 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          question.mutate();
        }}
      >
        <Field label="Question prompt">
          <input
            className={inputClass}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </Field>
        <Field label="Options, one per line">
          <textarea
            className={inputClass}
            value={options}
            onChange={(e) => setOptions(e.target.value)}
          />
        </Field>
        <Field label="Correct option index (0-based)">
          <input
            type="number"
            min="0"
            className={inputClass}
            value={correct}
            onChange={(e) => setCorrect(Number(e.target.value))}
          />
        </Field>
        <Button disabled={!prompt.trim()}>Add ordered question</Button>
      </form>
    </article>
  );
}
function QuestionEditor({
  question,
  refresh,
}: {
  question: import("@/lib/api/types").Question;
  refresh: () => void;
}) {
  const [prompt, setPrompt] = useState(question.prompt),
    [points, setPoints] = useState(question.points),
    [position, setPosition] = useState(question.position),
    [confirm, setConfirm] = useState(false);
  const save = useMutation({
    mutationFn: () =>
      api(detail(endpoints.questions, question.id), {
        method: "PATCH",
        ...json({ prompt, points, position }),
      }),
    onSuccess: refresh,
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.questions, question.id), { method: "DELETE" }),
    onSuccess: refresh,
  });
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <div className="grid gap-2 md:grid-cols-[1fr_90px_90px_auto]">
        <input
          aria-label="Question prompt"
          className={inputClass}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <input
          aria-label="Question points"
          type="number"
          min="0"
          className={inputClass}
          value={points}
          onChange={(e) => setPoints(Number(e.target.value))}
        />
        <input
          aria-label="Question position"
          type="number"
          min="1"
          className={inputClass}
          value={position}
          onChange={(e) => setPosition(Number(e.target.value))}
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => save.mutate()}>
            Save
          </Button>
          <Button variant="danger" onClick={() => setConfirm(true)}>
            Delete
          </Button>
        </div>
      </div>
      <Confirm
        open={confirm}
        title="Delete this question?"
        body="Submitted answers keep their protected audit records and may prevent deletion."
        onCancel={() => setConfirm(false)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
    </div>
  );
}
