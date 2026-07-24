"use client";
import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { list, api } from "@/lib/api/client";
import { endpoints, detail } from "@/lib/api/endpoints";
import type { Course, Enrollment } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Empty, Skeleton } from "@/components/ui";
export default function MyCourses() {
  const e = useQueries({
    queries: [
      {
        queryKey: ["enrollments"],
        queryFn: () => list<Enrollment>(endpoints.enrollments),
      },
    ],
  });
  const enrollments = e[0].data?.results ?? [];
  const courses = useQueries({
    queries: enrollments.map((x) => ({
      queryKey: ["course", x.course],
      queryFn: () => api<Course>(detail(endpoints.courses, x.course)),
    })),
  });
  if (e[0].isLoading || courses.some((x) => x.isLoading)) return <Skeleton />;
  return (
    <>
      <PageHeading
        eyebrow="My courses"
        title="Keep your momentum"
        description="Your active and completed enrolments."
      />
      {!enrollments.length ? (
        <Empty
          title="No enrolled courses"
          body="Explore the catalogue to start learning."
          action={
            <Link
              className="font-bold text-emerald-800 underline"
              href="/courses"
            >
              Browse courses
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {enrollments.map((x, i) => (
            <Link key={x.id} href={`/learn/${x.course}`} className="card p-5">
              <p className="text-xs font-bold uppercase text-emerald-800">
                {x.status}
              </p>
              <h2 className="mt-2 text-xl font-black">
                {courses[i]?.data?.title ?? `Course ${x.course}`}
              </h2>
              <p className="mt-4 font-bold text-emerald-800">Open course →</p>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
