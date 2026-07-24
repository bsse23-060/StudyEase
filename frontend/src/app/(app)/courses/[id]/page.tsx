"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Course, Enrollment } from "@/lib/api/types";
import { Badge, Button, Empty, Skeleton, useToast } from "@/components/ui";
import { PageHeading } from "@/components/page-heading";
export default function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const course = useQuery({
    queryKey: ["course", id],
    queryFn: () => api<Course>(detail(endpoints.courses, id)),
  });
  const enrollment = useQuery({
    queryKey: ["enrollment", id],
    queryFn: () => list<Enrollment>(endpoints.enrollments, { course: id }),
  });
  const enrol = useMutation({
    mutationFn: () =>
      api<Enrollment>(endpoints.enrollments, {
        method: "POST",
        ...json({ course: Number(id) }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enrollment", id] });
      toast("You are enrolled.");
      router.push(`/learn/${id}`);
    },
    onError: (e: Error) =>
      toast(
        e.message.includes("unique") ? "You are already enrolled." : e.message,
        "error",
      ),
  });
  if (course.isLoading) return <Skeleton />;
  if (!course.data)
    return (
      <Empty
        title="Course unavailable"
        body="It may be unpublished, restricted, or no longer available."
      />
    );
  const c = course.data,
    active = enrollment.data?.results.some((x) => x.status === "active");
  return (
    <>
      <PageHeading
        eyebrow="Course"
        title={c.title}
        description={c.description}
        action={
          active ? (
            <Link
              className="rounded-xl bg-emerald-800 px-4 py-3 font-bold text-white"
              href={`/learn/${id}`}
            >
              Continue learning
            </Link>
          ) : (
            <Button
              disabled={enrol.isPending || enrollment.isLoading}
              onClick={() => enrol.mutate()}
            >
              {enrol.isPending ? "Enrolling…" : "Enrol now"}
            </Button>
          )
        }
      />
      <div className="grid gap-4">
        {c.modules?.map((module) => (
          <section key={module.id} className="card p-5">
            <div className="flex items-center gap-3">
              <Badge>Module {module.position}</Badge>
              <h2 className="text-xl font-bold">{module.title}</h2>
            </div>
            <p className="mt-2 text-slate-600">{module.summary}</p>
            <ol className="mt-4 grid gap-2">
              {module.lessons.map((lesson) => (
                <li
                  key={lesson.id}
                  className="flex justify-between rounded-xl bg-slate-50 p-3"
                >
                  <span>
                    {lesson.position}. {lesson.title}
                  </span>
                  <span className="text-sm text-slate-500">
                    {lesson.estimated_minutes} min
                  </span>
                </li>
              ))}
            </ol>
          </section>
        ))}
        {!c.modules?.length && (
          <Empty
            title="Curriculum not published"
            body="The instructor has not added visible modules yet."
          />
        )}
      </div>
    </>
  );
}
