"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Course } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Badge, Button, Empty, Skeleton, useToast } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
export default function InstructorCourses() {
  const qc = useQueryClient(),
    toast = useToast();
  const { data: user } = useSession();
  const q = useQuery({
    queryKey: ["instructor-courses"],
    queryFn: () => list<Course>(endpoints.courses, { ordering: "-updated_at" }),
    enabled: user?.role !== "student",
  });
  const lifecycle = useMutation({
    mutationFn: ({
      course,
      action,
    }: {
      course: Course;
      action: "archive" | "restore";
    }) =>
      api<Course>(`${detail(endpoints.courses, course.id)}${action}/`, {
        method: "POST",
      }),
    onSuccess: (course) => {
      toast(
        course.is_archived
          ? "Course archived; history remains available."
          : "Course restored.",
        "success",
      );
      qc.invalidateQueries({ queryKey: ["instructor-courses"] });
    },
    onError: (error: Error) => toast(error.message, "error"),
  });
  if (user?.role === "student")
    return (
      <Empty
        title="Instructor access required"
        body="This workspace is available only to instructors and administrators."
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="Instructor"
        title="My courses"
        description="The backend returns only courses you own unless you are an administrator."
        action={
          <Link
            href="/instructor/builder"
            className="rounded-xl bg-emerald-800 px-4 py-3 font-bold text-white"
          >
            Create course
          </Link>
        }
      />
      {q.isLoading ? (
        <Skeleton />
      ) : !q.data?.results.length ? (
        <Empty
          title="No authored courses"
          body="Create your first course to begin building modules and lessons."
        />
      ) : (
        <div className="grid gap-4">
          {q.data.results.map((c) => (
            <div
              key={c.id}
              className="card flex items-center justify-between p-5"
            >
              <Link href={`/instructor/courses/${c.id}`} className="grow">
                <h2 className="text-xl font-black">{c.title}</h2>
                <p className="text-sm text-slate-500">
                  {c.modules.length} modules · updated{" "}
                  {new Date(c.updated_at).toLocaleDateString()}
                </p>
              </Link>
              <div className="flex items-center gap-2">
                <Badge
                  tone={
                    c.is_archived
                      ? "warning"
                      : c.is_published
                        ? "success"
                        : "warning"
                  }
                >
                  {c.is_archived
                    ? "Archived"
                    : c.is_published
                      ? "Published"
                      : "Draft"}
                </Badge>
                {(!c.is_archived || user?.role === "admin") && (
                  <Button
                    variant="secondary"
                    disabled={lifecycle.isPending}
                    onClick={() =>
                      lifecycle.mutate({
                        course: c,
                        action: c.is_archived ? "restore" : "archive",
                      })
                    }
                  >
                    {c.is_archived ? "Restore" : "Archive"}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
