"use client";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Question, Quiz, QuizSubmission } from "@/lib/api/types";
import { useEffect, useState } from "react";
import { Button, Confirm, Empty, Skeleton } from "@/components/ui";
import { PageHeading } from "@/components/page-heading";
export default function QuizPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const key = `studyease-quiz-${lessonId}`;
  const quizzes = useQuery({
    queryKey: ["quiz", lessonId],
    queryFn: () => list<Quiz>(endpoints.quizzes, { lesson: lessonId }),
  });
  const history = useQuery({
    queryKey: ["quiz-history", quizzes.data?.results[0]?.id],
    queryFn: () =>
      list<QuizSubmission>(endpoints.quizSubmissions, {
        quiz: quizzes.data!.results[0]!.id,
        status: "submitted",
      }),
    enabled: !!quizzes.data?.results[0],
  });
  const [answers, setAnswers] = useState<Record<number, unknown>>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem(key) ?? "{}") as Record<
        number,
        unknown
      >;
    } catch {
      return {};
    }
  });
  const [review, setReview] = useState(false),
    [result, setResult] = useState<QuizSubmission | null>(null),
    [now] = useState(() => Date.now());
  const quiz = quizzes.data?.results[0];
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(answers));
    const warn = (e: BeforeUnloadEvent) => {
      if (Object.keys(answers).length && !result) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [answers, key, result]);
  const submit = useMutation({
    mutationFn: async () => {
      const idempotency_key = crypto.randomUUID();
      const started = await api<QuizSubmission>(endpoints.quizSubmissions, {
        method: "POST",
        ...json({ quiz: quiz!.id, idempotency_key }),
      });
      return api<QuizSubmission>(
        `${detail(endpoints.quizSubmissions, started.id)}submit/`,
        {
          method: "POST",
          ...json({
            idempotency_key,
            answers: quiz!.questions
              .filter(
                (q) => answers[q.id] !== undefined && answers[q.id] !== "",
              )
              .map((q) => ({ question_id: q.id, answer: answers[q.id] })),
          }),
        },
      );
    },
    onSuccess: (value) => {
      setResult(value);
      setReview(false);
      localStorage.removeItem(key);
      history.refetch();
    },
  });
  if (quizzes.isLoading) return <Skeleton />;
  if (!quiz)
    return (
      <Empty
        title="No quiz available"
        body="This lesson has no published assessment."
      />
    );
  const unavailable =
    (quiz.available_from && now < Date.parse(quiz.available_from)) ||
    (quiz.available_until && now > Date.parse(quiz.available_until));
  const remaining =
    quiz.maximum_attempts === null
      ? null
      : Math.max(0, quiz.maximum_attempts - quiz.attempt_count);
  return (
    <>
      <PageHeading
        eyebrow="Atomic knowledge check"
        title={quiz.title}
        description={
          quiz.instructions ||
          "Answer every required question, review, then submit once."
        }
      />
      <section className="card mb-6 grid gap-2 p-4 text-sm md:grid-cols-4">
        <span>
          Pass mark:{" "}
          {quiz.pass_mark === null ? "Not set" : `${quiz.pass_mark}%`}
        </span>
        <span>
          Attempts: {quiz.attempt_count}
          {remaining !== null ? ` · ${remaining} remaining` : ""}
        </span>
        <span>
          {quiz.time_limit_minutes
            ? `${quiz.time_limit_minutes} minute limit`
            : "No time limit"}
        </span>
        <span>{unavailable ? "Currently unavailable" : "Available now"}</span>
      </section>
      {unavailable || remaining === 0 ? (
        <Empty
          title="Quiz unavailable"
          body={
            remaining === 0
              ? "You have reached the maximum number of attempts."
              : "The availability window does not include the current time."
          }
        />
      ) : result ? (
        <Result result={result} />
      ) : (
        <form
          className="grid gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            setReview(true);
          }}
        >
          {quiz.questions.map((question, i) => (
            <QuestionField
              key={question.id}
              question={question}
              index={i}
              value={answers[question.id]}
              set={(v) => setAnswers((a) => ({ ...a, [question.id]: v }))}
            />
          ))}
          <p aria-live="polite" className="text-sm text-slate-600">
            Answered{" "}
            {
              quiz.questions.filter(
                (q) => answers[q.id] !== undefined && answers[q.id] !== "",
              ).length
            }{" "}
            of {quiz.questions.length}
          </p>
          {submit.isError && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">
              {submit.error.message}
            </p>
          )}
          <Button className="justify-self-start">Review answers</Button>
        </form>
      )}{" "}
      {!!history.data?.results.length && (
        <section className="mt-8">
          <h2 className="text-xl font-bold">Prior attempts</h2>
          <ul className="mt-3 grid gap-2">
            {history.data.results.map((item) => (
              <li className="card flex justify-between p-4" key={item.id}>
                <span>{new Date(item.submitted_at!).toLocaleString()}</span>
                <strong>
                  {item.percentage_score?.toFixed(1)}%{" "}
                  {item.passed === null
                    ? ""
                    : item.passed
                      ? "Passed"
                      : "Not passed"}
                </strong>
              </li>
            ))}
          </ul>
        </section>
      )}
      <Confirm
        open={review}
        title="Submit final answers?"
        body={`You answered ${quiz.questions.filter((q) => answers[q.id] !== undefined && answers[q.id] !== "").length} of ${quiz.questions.length}. Required unanswered questions will be rejected without saving a partial result.`}
        onCancel={() => setReview(false)}
        onConfirm={() => submit.mutate()}
        busy={submit.isPending}
      />
    </>
  );
}
function QuestionField({
  question,
  index,
  value,
  set,
}: {
  question: Question;
  index: number;
  value: unknown;
  set: (v: unknown) => void;
}) {
  const opts = Array.isArray(question.options) ? question.options : [];
  return (
    <fieldset className="card p-5">
      <legend className="px-1 text-lg font-bold">
        {index + 1}. {question.prompt}{" "}
        {question.is_required && (
          <span className="text-red-700">(required)</span>
        )}
      </legend>
      <div className="mt-4 grid gap-2">
        {question.kind === "multiple_choice" &&
          opts.map((o, i) => (
            <label key={i} className="flex gap-3 rounded-xl border p-3">
              <input
                type="radio"
                name={`q${question.id}`}
                checked={value === i}
                onChange={() => set(i)}
              />
              <span>{String(o)}</span>
            </label>
          ))}
        {question.kind === "true_false" &&
          [true, false].map((o) => (
            <label key={String(o)} className="flex gap-3 rounded-xl border p-3">
              <input
                type="radio"
                name={`q${question.id}`}
                checked={value === o}
                onChange={() => set(o)}
              />
              <span>{o ? "True" : "False"}</span>
            </label>
          ))}
        {question.kind === "short_answer" && (
          <textarea
            aria-label="Your answer"
            className="min-h-28 rounded-xl border p-3"
            value={String(value ?? "")}
            onChange={(e) => set(e.target.value)}
          />
        )}
      </div>
    </fieldset>
  );
}
function Result({ result }: { result: QuizSubmission }) {
  return (
    <section
      className={`card p-7 ${result.passed === false ? "border-amber-400" : "border-emerald-400"}`}
    >
      <h2 className="text-2xl font-black">Quiz complete</h2>
      <p className="mt-2 text-3xl font-black">
        {result.percentage_score?.toFixed(1)}%
      </p>
      <p>
        {result.total_score} of {result.maximum_score} points ·{" "}
        {result.passed === null
          ? "No pass mark"
          : result.passed
            ? "Passed"
            : "Not passed"}
      </p>
      <ul className="mt-5 grid gap-3">
        {result.answers.map((answer, i) => (
          <li
            key={answer.id}
            className={`rounded-xl p-4 ${answer.is_correct ? "bg-emerald-50" : "bg-amber-50"}`}
          >
            <strong>
              Question {i + 1}:{" "}
              {answer.is_correct ? "Correct" : "Review needed"}
            </strong>
            <p>{answer.feedback}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
