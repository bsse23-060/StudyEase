"use client";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Conversation, Message } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import { Button, Empty, Skeleton, inputClass, useToast } from "@/components/ui";
import { useEffect, useRef, useState } from "react";
export default function Assistant() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);
  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => list<Conversation>(endpoints.conversations),
  });
  const active = useQuery({
    queryKey: ["conversation", selected],
    queryFn: () =>
      api<Conversation>(detail(endpoints.conversations, selected!)),
    enabled: selected !== null,
  });
  const create = useMutation({
    mutationFn: () =>
      api<Conversation>(endpoints.conversations, {
        method: "POST",
        ...json({ title: "New study conversation" }),
      }),
    onSuccess: (c) => {
      setSelected(c.id);
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  return (
    <>
      <PageHeading
        eyebrow="Grounded study assistant"
        title="Ask, then inspect the evidence"
        description="Answers use only sources authorised for this conversation. AI output is displayed as untrusted plain text."
      />
      <div className="grid min-h-[620px] gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="card p-4">
          <Button className="w-full" onClick={() => create.mutate()}>
            New conversation
          </Button>
          <div className="mt-4 grid gap-2">
            {conversations.data?.results.map((c) => (
              <button
                className={`rounded-xl p-3 text-left ${selected === c.id ? "bg-emerald-100" : "bg-slate-50"}`}
                key={c.id}
                onClick={() => setSelected(c.id)}
              >
                <span className="line-clamp-1 font-bold">
                  {c.title || "Untitled conversation"}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(c.updated_at).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        </aside>
        <section className="card flex min-h-[620px] flex-col p-4 md:p-6">
          {selected ? (
            active.isLoading ? (
              <Skeleton />
            ) : (
              <Chat
                conversation={active.data!}
                onChanged={() =>
                  qc.invalidateQueries({ queryKey: ["conversation", selected] })
                }
              />
            )
          ) : (
            <Empty
              title="Start a sourced conversation"
              body="Create a conversation, then ask a focused question about your ready documents or enrolled course materials."
            />
          )}
        </section>
      </div>
    </>
  );
}
function Chat({
  conversation,
  onChanged,
}: {
  conversation: Conversation;
  onChanged: () => void;
}) {
  const [question, setQuestion] = useState("");
  const toast = useToast();
  const end = useRef<HTMLDivElement>(null);
  const history = useInfiniteQuery({
    queryKey: ["conversation-history", conversation.id],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<import("@/lib/api/types").Page<Message>>(
        `${detail(endpoints.conversations, conversation.id)}history/?page=${pageParam}`,
      ),
    getNextPageParam: (last) =>
      last.next
        ? Number(new URL(last.next).searchParams.get("page") ?? 2)
        : undefined,
  });
  const messages = (history.data?.pages ?? [])
    .slice()
    .reverse()
    .flatMap((page) => page.results);
  const ask = useMutation({
    mutationFn: () =>
      api<Message>(`${detail(endpoints.conversations, conversation.id)}ask/`, {
        method: "POST",
        ...json({ question, top_k: 5 }),
      }),
    onSuccess: () => {
      setQuestion("");
      onChanged();
      history.refetch();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages.length]);
  return (
    <>
      <div aria-live="polite" className="flex-1 space-y-5 overflow-y-auto pr-1">
        {history.hasNextPage && (
          <div className="text-center">
            <Button
              variant="secondary"
              disabled={history.isFetchingNextPage}
              onClick={() => history.fetchNextPage()}
            >
              {history.isFetchingNextPage
                ? "Loading…"
                : "Load earlier messages"}
            </Button>
          </div>
        )}
        {messages.map((m) => (
          <article
            key={m.id}
            className={
              m.role === "user"
                ? "ml-auto max-w-2xl rounded-2xl bg-emerald-800 p-4 text-white"
                : "max-w-3xl"
            }
          >
            <p className="text-xs font-bold uppercase opacity-70">{m.role}</p>
            <p className="prose-safe mt-1">{m.content}</p>
            {m.role === "assistant" && <Citations citations={m.citations} />}
          </article>
        ))}
        {ask.isPending && (
          <p role="status" className="text-sm text-slate-500">
            Finding authorised sources and composing an answer…
          </p>
        )}
        <div ref={end} />
      </div>
      <form
        className="mt-5 flex gap-2 border-t pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim() && !ask.isPending) ask.mutate();
        }}
      >
        <label className="sr-only" htmlFor="question">
          Ask a question
        </label>
        <textarea
          id="question"
          className={`${inputClass} min-h-14 resize-none`}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about your study material…"
        />
        <Button disabled={!question.trim() || ask.isPending}>Ask</Button>
      </form>
    </>
  );
}
function Citations({ citations = [] }: { citations: Message["citations"] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!citations.length)
    return (
      <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
        <strong>Insufficient source support.</strong> Verify this answer before
        relying on it.
      </p>
    );
  return (
    <div className="mt-4 border-t pt-3">
      <p className="text-xs font-bold uppercase text-slate-500">Sources</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {citations.map((c, i) => (
          <button
            key={i}
            aria-expanded={open === i}
            className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-900"
            onClick={() => setOpen(open === i ? null : i)}
          >
            [{i + 1}]{" "}
            {c.document_title || c.source_filename || `Source ${i + 1}`}
          </button>
        ))}
      </div>
      {open !== null && (
        <div className="mt-3 rounded-xl border bg-white p-4 text-sm">
          <strong>
            {citations[open]?.document_title ||
              citations[open]?.source_filename}
          </strong>
          <p className="text-slate-500">
            {[
              citations[open]?.page && `Page ${citations[open]?.page}`,
              citations[open]?.section_title,
              citations[open]?.chunk_position !== undefined &&
                `Chunk ${citations[open]?.chunk_position}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {citations[open]?.quote && (
            <blockquote className="mt-2 border-l-4 border-emerald-700 pl-3">
              {citations[open]?.quote}
            </blockquote>
          )}
        </div>
      )}
    </div>
  );
}
