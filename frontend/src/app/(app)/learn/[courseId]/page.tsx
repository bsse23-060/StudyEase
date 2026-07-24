"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Course, Lesson } from "@/lib/api/types";
import { Empty, Skeleton } from "@/components/ui";
export default function LearnCourse() {
  const { courseId } = useParams<{ courseId: string }>();
  const params = useSearchParams();
  const q = useQuery({
    queryKey: ["course", courseId],
    queryFn: () => api<Course>(detail(endpoints.courses, courseId)),
  });
  if (q.isLoading) return <Skeleton />;
  if (!q.data)
    return (
      <Empty
        title="Course unavailable"
        body="Confirm that you are actively enrolled."
      />
    );
  const lessons = q.data.modules.flatMap((m) => m.lessons);
  const lesson =
    lessons.find((x) => String(x.id) === params.get("lesson")) ?? lessons[0];
  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <aside className="card h-fit p-4">
        <Link href="/learn" className="text-sm font-bold text-emerald-800">
          ← My courses
        </Link>
        <h1 className="mt-3 text-xl font-black">{q.data.title}</h1>
        <nav aria-label="Course lessons" className="mt-4 grid gap-3">
          {q.data.modules.map((m) => (
            <div key={m.id}>
              <p className="mb-1 text-xs font-bold uppercase text-slate-500">
                {m.title}
              </p>
              {m.lessons.map((l) => (
                <Link
                  className={`block rounded-lg px-3 py-2 text-sm ${l.id === lesson?.id ? "bg-emerald-100 font-bold" : "hover:bg-slate-50"}`}
                  key={l.id}
                  href={`/learn/${courseId}?lesson=${l.id}`}
                >
                  {l.position}. {l.title}
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      {lesson ? (
        <LessonView lesson={lesson} lessons={lessons} courseId={courseId} />
      ) : (
        <Empty
          title="No lessons yet"
          body="This course does not have visible lessons."
        />
      )}
    </div>
  );
}
function LessonView({
  lesson,
  lessons,
  courseId,
}: {
  lesson: Lesson;
  lessons: Lesson[];
  courseId: string;
}) {
  const i = lessons.findIndex((x) => x.id === lesson.id);
  return (
    <article className="card p-6 md:p-9">
      <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">
        {lesson.kind} · {lesson.estimated_minutes} minutes
      </p>
      <h2 className="mt-2 text-3xl font-black">{lesson.title}</h2>
      <div className="prose-safe mt-6">
        {lesson.content || "The instructor has not added text content."}
      </div>
      {lesson.resource_url && (
        <a
          className="mt-5 block font-bold text-emerald-800 underline"
          href={lesson.resource_url}
          target="_blank"
          rel="noreferrer"
        >
          Open lesson resource
        </a>
      )}
      {lesson.questions.length > 0 && (
        <Link
          href={`/quiz/${lesson.id}`}
          className="mt-7 inline-block rounded-xl bg-emerald-800 px-5 py-3 font-bold text-white"
        >
          Take quiz ({lesson.questions.length})
        </Link>
      )}
      <nav
        aria-label="Lesson navigation"
        className="mt-10 flex justify-between border-t pt-5"
      >
        {lessons[i - 1] ? (
          <Link href={`/learn/${courseId}?lesson=${lessons[i - 1]!.id}`}>
            ← Previous
          </Link>
        ) : (
          <span />
        )}
        {lessons[i + 1] && (
          <Link href={`/learn/${courseId}?lesson=${lessons[i + 1]!.id}`}>
            Next →
          </Link>
        )}
      </nav>
    </article>
  );
}
