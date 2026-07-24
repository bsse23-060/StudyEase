"use client";
import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { list } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type {
  Conversation,
  Deck,
  DocumentRecord,
  Enrollment,
  RoadmapStep,
  Routine,
} from "@/lib/api/types";
import { useSession } from "@/hooks/use-session";
import { PageHeading } from "@/components/page-heading";
import { Badge, Skeleton } from "@/components/ui";
export default function Dashboard() {
  const { data: user } = useSession();
  const queries = useQueries({
    queries: [
      {
        queryKey: ["enrollments", "dashboard"],
        queryFn: () =>
          list<Enrollment>(endpoints.enrollments, { page_size: 5 }),
      },
      {
        queryKey: ["roadmap", "dashboard"],
        queryFn: () => list<RoadmapStep>(endpoints.roadmap, { page_size: 5 }),
      },
      {
        queryKey: ["decks", "dashboard"],
        queryFn: () => list<Deck>(endpoints.decks, { page_size: 5 }),
      },
      {
        queryKey: ["routines", "dashboard"],
        queryFn: () => list<Routine>(endpoints.routines, { page_size: 5 }),
      },
      {
        queryKey: ["documents", "dashboard"],
        queryFn: () =>
          list<DocumentRecord>(endpoints.documents, { page_size: 5 }),
      },
      {
        queryKey: ["conversations", "dashboard"],
        queryFn: () =>
          list<Conversation>(endpoints.conversations, { page_size: 5 }),
      },
    ],
  });
  if (queries.some((q) => q.isLoading)) return <Skeleton />;
  const enrol = queries[0]?.data?.results ?? [];
  const road = queries[1]?.data?.results ?? [];
  const decks = queries[2]?.data?.results ?? [];
  const routines = queries[3]?.data?.results ?? [];
  const docs = queries[4]?.data?.results ?? [];
  const chats = queries[5]?.data?.results ?? [];
  if (user?.role !== "student")
    return (
      <>
        <PageHeading
          eyebrow="Instructor workspace"
          title={`Welcome, ${user?.full_name.split(" ")[0]}`}
          description="Build learning experiences and keep course sources ready for grounded retrieval."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <Stat
            label="Your active courses"
            value="Open builder"
            href="/instructor/courses"
          />
          <Stat
            label="Course documents"
            value={String(docs.length)}
            href="/documents"
          />
          <Stat
            label="Retrieval diagnostics"
            value="Preview"
            href="/instructor/retrieval"
          />
        </div>
      </>
    );
  return (
    <>
      <PageHeading
        eyebrow="Your learning day"
        title={`Good to see you, ${user?.full_name.split(" ")[0]}`}
        description="Continue where you left off or choose a focused next step."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Active courses"
          value={String(enrol.filter((x) => x.status === "active").length)}
          href="/learn"
        />
        <Stat
          label="Roadmap remaining"
          value={String(road.filter((x) => !x.completed_at).length)}
          href="/roadmap"
        />
        <Stat
          label="Flashcard decks"
          value={String(decks.length)}
          href="/flashcards"
        />
        <Stat
          label="Study routines"
          value={String(routines.length)}
          href="/schedule"
        />
      </div>
      <div className="mt-7 grid gap-6 lg:grid-cols-2">
        <section className="card p-6">
          <h2 className="text-xl font-bold">Next recommended actions</h2>
          <div className="mt-4 grid gap-3">
            {enrol.length ? (
              <Action
                href="/learn"
                title="Continue your active course"
                body="Open your enrolled curriculum and choose the next lesson."
              />
            ) : (
              <Action
                href="/courses"
                title="Find your first course"
                body="Browse published courses and enrol when you are ready."
              />
            )}
            {road.some((x) => !x.completed_at) && (
              <Action
                href="/roadmap"
                title="Advance your roadmap"
                body="Complete the next planned module."
              />
            )}
            <Action
              href="/assistant"
              title="Ask with your sources"
              body="Use ready documents for a cited answer."
            />
          </div>
        </section>
        <section className="card p-6">
          <h2 className="text-xl font-bold">Recent source activity</h2>
          <div className="mt-4 grid gap-3">
            {docs.slice(0, 3).map((d) => (
              <Link
                key={d.id}
                href={`/documents/${d.id}`}
                className="flex items-center justify-between rounded-xl border p-3"
              >
                <span className="truncate font-semibold">{d.title}</span>
                <Badge
                  tone={
                    d.status === "ready"
                      ? "success"
                      : d.status === "failed"
                        ? "danger"
                        : "warning"
                  }
                >
                  {d.status}
                </Badge>
              </Link>
            ))}
            {!docs.length && (
              <p className="text-slate-500">No documents yet.</p>
            )}
            <p className="text-sm text-slate-500">
              {chats.length} recent conversation{chats.length === 1 ? "" : "s"}
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
function Stat({
  label,
  value,
  href,
}: {
  label: string;
  value: string;
  href: string;
}) {
  return (
    <Link href={href} className="card p-5 hover:border-emerald-400">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-black">{value}</p>
    </Link>
  );
}
function Action({
  href,
  title,
  body,
}: {
  href: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl bg-slate-50 p-4 hover:bg-emerald-50"
    >
      <p className="font-bold">{title} →</p>
      <p className="mt-1 text-sm text-slate-600">{body}</p>
    </Link>
  );
}
