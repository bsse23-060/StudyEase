"use client";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { list } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Course } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Empty, Skeleton, inputClass } from "@/components/ui";
export default function Courses() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const deferred = useDeferredValue(search);
  const q = useQuery({
    queryKey: ["courses", deferred, page],
    queryFn: () =>
      list<Course>(endpoints.courses, {
        search: deferred,
        page,
        ordering: "title",
      }),
  });
  return (
    <>
      <PageHeading
        eyebrow="Course catalogue"
        title="Find your next subject"
        description="Only published courses available to your account appear here."
      />
      <div className="mb-6 flex max-w-xl gap-3">
        <label className="sr-only" htmlFor="course-search">
          Search courses
        </label>
        <input
          id="course-search"
          className={inputClass}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Search title or description…"
        />
      </div>
      {q.isLoading ? (
        <Skeleton />
      ) : q.isError ? (
        <Empty
          title="Courses could not load"
          body="Check your connection and try again."
        />
      ) : !q.data?.results.length ? (
        <Empty
          title="No matching courses"
          body="Try another search or check back after an instructor publishes a course."
        />
      ) : (
        <>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {q.data.results.map((course) => (
              <Link
                key={course.id}
                href={`/courses/${course.id}`}
                className="card group overflow-hidden"
              >
                <div className="h-28 bg-gradient-to-br from-emerald-800 to-emerald-500 p-5 text-lime-100">
                  <span className="text-sm font-bold">
                    {course.modules?.length ?? 0} modules
                  </span>
                </div>
                <div className="p-5">
                  <h2 className="text-xl font-black group-hover:text-emerald-800">
                    {course.title}
                  </h2>
                  <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                    {course.description || "Course details are coming soon."}
                  </p>
                  <p className="mt-5 font-bold text-emerald-800">
                    View course →
                  </p>
                </div>
              </Link>
            ))}
          </div>
          <nav
            aria-label="Course pages"
            className="mt-7 flex justify-center gap-3"
          >
            <button
              className="rounded-xl border px-4 py-2 disabled:opacity-40"
              disabled={!q.data.previous}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span className="py-2">Page {page}</span>
            <button
              className="rounded-xl border px-4 py-2 disabled:opacity-40"
              disabled={!q.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </>
  );
}
