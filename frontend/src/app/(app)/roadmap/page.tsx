"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Mastery, RoadmapStep } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Button, Empty, Progress, Skeleton } from "@/components/ui";
export default function Roadmap() {
  const qc = useQueryClient();
  const road = useQuery({
    queryKey: ["roadmap"],
    queryFn: () =>
      list<RoadmapStep>(endpoints.roadmap, { ordering: "position" }),
  });
  const mastery = useQuery({
    queryKey: ["masteries"],
    queryFn: () => list<Mastery>(endpoints.masteries),
  });
  const complete = useMutation({
    mutationFn: (id: number) =>
      api(`${detail(endpoints.roadmap, id)}complete/`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roadmap"] }),
  });
  if (road.isLoading || mastery.isLoading) return <Skeleton />;
  const avg = mastery.data?.results.length
    ? (mastery.data.results.reduce((n, x) => n + x.probability, 0) /
        mastery.data.results.length) *
      100
    : 0;
  return (
    <>
      <PageHeading
        eyebrow="Learning progress"
        title="Your roadmap"
        description="Roadmap steps are instructor-authored. Mastery is server-controlled and updated from quiz evidence."
      />
      <section className="card mb-6 p-5">
        <Progress label="Average concept mastery" value={avg} />
      </section>
      {!road.data?.results.length ? (
        <Empty
          title="No roadmap items"
          body="A roadmap becomes available when learning steps are created for your enrolment."
        />
      ) : (
        <ol className="relative ml-3 border-l-2 border-emerald-200 pl-7">
          {road.data.results.map((step) => (
            <li className="mb-7" key={step.id}>
              <span
                className={`absolute -left-3 grid h-6 w-6 place-items-center rounded-full text-xs ${step.completed_at ? "bg-emerald-700 text-white" : "bg-white border-2 border-emerald-700"}`}
              >
                {step.completed_at ? "✓" : step.position}
              </span>
              <div className="card p-5">
                <h2 className="font-bold">Module {step.module}</h2>
                <p className="mt-1 text-slate-600">
                  {step.rationale ||
                    "Continue this module as part of your learning plan."}
                </p>
                {step.target_date && (
                  <p className="mt-2 text-sm">
                    Target:{" "}
                    {new Date(
                      `${step.target_date}T00:00:00`,
                    ).toLocaleDateString()}
                  </p>
                )}
                {!step.completed_at && (
                  <Button
                    className="mt-4"
                    variant="secondary"
                    onClick={() => complete.mutate(step.id)}
                  >
                    Mark complete
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
