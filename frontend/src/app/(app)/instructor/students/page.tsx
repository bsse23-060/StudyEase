"use client";
import { useQuery } from "@tanstack/react-query";
import { list } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Enrollment, User } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Empty, Skeleton } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
export default function Students() {
  const { data: user } = useSession();
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => list<User>(endpoints.users),
    enabled: user?.role !== "student",
  });
  const enrollments = useQuery({
    queryKey: ["teaching-enrollments"],
    queryFn: () => list<Enrollment>(endpoints.enrollments),
    enabled: user?.role !== "student",
  });
  if (user?.role === "student")
    return (
      <Empty
        title="Instructor access required"
        body="Student rosters are restricted by the backend."
      />
    );
  if (users.isLoading || enrollments.isLoading) return <Skeleton />;
  const allowed = new Set(enrollments.data?.results.map((x) => x.learner));
  const rows =
    users.data?.results.filter(
      (x) => x.role === "student" && allowed.has(x.id),
    ) ?? [];
  return (
    <>
      <PageHeading
        eyebrow="Instructor"
        title="Enrolled students"
        description="Only learners attached to courses visible to your account are shown."
      />
      {!rows.length ? (
        <Empty
          title="No authorised students"
          body="Enrolled learners will appear when the API grants access."
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b">
                <th scope="col" className="p-4">
                  Student
                </th>
                <th scope="col" className="p-4">
                  Email
                </th>
                <th scope="col" className="p-4">
                  Active enrolments
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((x) => (
                <tr className="border-b last:border-0" key={x.id}>
                  <th scope="row" className="p-4">
                    {x.full_name}
                  </th>
                  <td className="p-4">{x.email}</td>
                  <td className="p-4">
                    {
                      enrollments.data?.results.filter(
                        (e) => e.learner === x.id && e.status === "active",
                      ).length
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
