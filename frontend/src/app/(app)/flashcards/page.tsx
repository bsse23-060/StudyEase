"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Deck, Flashcard } from "@/lib/api/types";
import { PageHeading } from "@/components/page-heading";
import {
  Button,
  Confirm,
  Empty,
  Field,
  Skeleton,
  inputClass,
  useToast,
} from "@/components/ui";
import { useEffect, useState } from "react";
export default function Flashcards() {
  const qc = useQueryClient(),
    toast = useToast();
  const [name, setName] = useState(""),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState<number | null>(null),
    [reviewing, setReviewing] = useState<Deck | null>(null);
  const q = useQuery({
    queryKey: ["decks"],
    queryFn: () => list<Deck>(endpoints.decks),
  });
  const cards = useQuery({
    queryKey: ["cards", selected, search],
    queryFn: () =>
      list<Flashcard>(endpoints.cards, { deck: selected!, search }),
    enabled: selected !== null,
  });
  const createDeck = useMutation({
    mutationFn: () =>
      api<Deck>(endpoints.decks, {
        method: "POST",
        ...json({ name, description: "", topics: [] }),
      }),
    onSuccess: (d) => {
      setName("");
      setSelected(d.id);
      qc.invalidateQueries({ queryKey: ["decks"] });
      toast("Deck created.");
    },
  });
  return (
    <>
      <PageHeading
        eyebrow="Spaced repetition"
        title="Flashcards"
        description="Create and manage cards here. Ease, intervals, repetitions, and next-review dates remain server controlled."
      />
      <form
        className="card mb-6 flex items-end gap-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) createDeck.mutate();
        }}
      >
        <div className="flex-1">
          <Field label="New deck name">
            <input
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
        </div>
        <Button disabled={!name.trim() || createDeck.isPending}>
          Create deck
        </Button>
      </form>
      {reviewing ? (
        <Review
          deck={reviewing}
          done={() => {
            setReviewing(null);
            qc.invalidateQueries({ queryKey: ["decks"] });
          }}
        />
      ) : q.isLoading ? (
        <Skeleton />
      ) : !q.data?.results.length ? (
        <Empty
          title="No flashcard decks"
          body="Create a deck to add your first card."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <aside className="card h-fit p-4">
            <h2 className="font-bold">Decks</h2>
            <div className="mt-3 grid gap-2">
              {q.data.results.map((d) => (
                <button
                  className={`rounded-xl p-3 text-left ${selected === d.id ? "bg-emerald-100" : "bg-slate-50"}`}
                  key={d.id}
                  onClick={() => setSelected(d.id)}
                >
                  <strong>{d.name}</strong>
                  <span className="block text-xs">{d.cards.length} cards</span>
                </button>
              ))}
            </div>
            {selected && (
              <Button
                className="mt-4 w-full"
                variant="secondary"
                onClick={() =>
                  setReviewing(q.data!.results.find((d) => d.id === selected)!)
                }
              >
                Review due
              </Button>
            )}
          </aside>
          <section>
            {selected ? (
              <CardManager
                deck={selected}
                search={search}
                setSearch={setSearch}
                cards={cards.data?.results ?? []}
                loading={cards.isLoading}
                refresh={() => {
                  cards.refetch();
                  qc.invalidateQueries({ queryKey: ["decks"] });
                }}
              />
            ) : (
              <Empty
                title="Choose a deck"
                body="Select a deck to search, create, edit, or delete cards."
              />
            )}
          </section>
        </div>
      )}
    </>
  );
}
function CardManager({
  deck,
  search,
  setSearch,
  cards,
  loading,
  refresh,
}: {
  deck: number;
  search: string;
  setSearch: (v: string) => void;
  cards: Flashcard[];
  loading: boolean;
  refresh: () => void;
}) {
  const [editing, setEditing] = useState<Flashcard | null>(null),
    [question, setQuestion] = useState(""),
    [answer, setAnswer] = useState(""),
    [remove, setRemove] = useState<Flashcard | null>(null);
  const toast = useToast();
  function reset() {
    setEditing(null);
    setQuestion("");
    setAnswer("");
  }
  const save = useMutation({
    mutationFn: () =>
      api<Flashcard>(
        editing ? detail(endpoints.cards, editing.id) : endpoints.cards,
        {
          method: editing ? "PATCH" : "POST",
          ...json({ deck, question, answer }),
        },
      ),
    onSuccess: () => {
      reset();
      refresh();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.cards, remove!.id), { method: "DELETE" }),
    onSuccess: () => {
      setRemove(null);
      refresh();
    },
  });
  return (
    <>
      <div className="card p-5">
        <h2 className="text-xl font-black">
          {editing ? "Edit card" : "Add a card"}
        </h2>
        <form
          className="mt-4 grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <Field label="Prompt">
            <textarea
              className={`${inputClass} min-h-20`}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </Field>
          <Field label="Answer">
            <textarea
              className={`${inputClass} min-h-20`}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </Field>
          <div className="flex gap-2">
            <Button
              disabled={!question.trim() || !answer.trim() || save.isPending}
            >
              {editing ? "Save changes" : "Add card"}
            </Button>
            {editing && (
              <Button type="button" variant="secondary" onClick={reset}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </div>
      <label className="mt-5 block">
        <span className="sr-only">Search cards</span>
        <input
          className={inputClass}
          placeholder="Search cards…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {loading ? (
        <Skeleton />
      ) : (
        <div className="mt-4 grid gap-3">
          {cards.map((card) => (
            <article className="card p-4" key={card.id}>
              <h3 className="font-bold">{card.question}</h3>
              <p className="mt-1 text-slate-600">{card.answer}</p>
              <p className="mt-2 text-xs text-slate-500">
                Next review:{" "}
                {card.next_review_at
                  ? new Date(card.next_review_at).toLocaleString()
                  : "Due now"}
              </p>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(card);
                    setQuestion(card.question);
                    setAnswer(card.answer);
                  }}
                >
                  Edit
                </Button>
                <Button variant="danger" onClick={() => setRemove(card)}>
                  Delete
                </Button>
              </div>
            </article>
          ))}
          {!cards.length && (
            <Empty
              title="No matching cards"
              body="Create a card or change your search."
            />
          )}
        </div>
      )}
      <Confirm
        open={!!remove}
        title="Delete this flashcard?"
        body="Its scheduling and review history will also be deleted."
        onCancel={() => setRemove(null)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
    </>
  );
}
function Review({ deck, done }: { deck: Deck; done: () => void }) {
  const due = useQuery({
    queryKey: ["due", deck.id],
    queryFn: () => api<Flashcard[]>(`${detail(endpoints.decks, deck.id)}due/`),
  });
  const [index, setIndex] = useState(0),
    [revealed, setRevealed] = useState(false),
    [selectedRating, setSelectedRating] = useState<number | null>(null);
  const card = due.data?.[index];
  const review = useMutation({
    mutationFn: (quality: number) =>
      api(`${detail(endpoints.decks, deck.id)}cards/${card!.id}/review/`, {
        method: "POST",
        ...json({ quality, idempotency_key: crypto.randomUUID() }),
      }),
    onSuccess: () => {
      setIndex((i) => i + 1);
      setRevealed(false);
      setSelectedRating(null);
    },
  });
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;
      if (e.code === "Space") {
        e.preventDefault();
        setRevealed(true);
      }
      if (revealed && /^[0-5]$/.test(e.key)) {
        const n = Number(e.key);
        setSelectedRating(n);
        review.mutate(n);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [revealed, review]);
  if (due.isLoading) return <Skeleton />;
  if (!card)
    return (
      <Empty
        title="Review complete"
        body="No more cards are due right now."
        action={<Button onClick={done}>Back to decks</Button>}
      />
    );
  return (
    <section className="card mx-auto max-w-2xl p-7 text-center">
      <p className="text-sm font-bold text-emerald-800">
        Card {index + 1} of {due.data?.length}
      </p>
      <h2 className="mt-8 text-2xl font-black">{card.question}</h2>
      {revealed ? (
        <>
          <div className="prose-safe mt-8 rounded-xl bg-slate-50 p-5">
            {card.answer}
          </div>
          <p id="rating-help" className="mt-6 text-sm text-slate-600">
            Keyboard 0–5 · 0–2 forgot · 3 difficult · 4 good · 5 effortless
          </p>
          <div
            aria-describedby="rating-help"
            aria-label="Review quality"
            className="mt-3 flex flex-wrap justify-center gap-2"
          >
            {[0, 1, 2, 3, 4, 5].map((n) => (
              <Button
                variant={n < 3 ? "secondary" : "primary"}
                disabled={review.isPending}
                aria-pressed={selectedRating === n}
                key={n}
                onClick={() => {
                  setSelectedRating(n);
                  review.mutate(n);
                }}
              >
                {n}
              </Button>
            ))}
          </div>
          {review.isError && (
            <p role="alert" className="mt-3 text-red-700">
              {review.error.message} Your rating {selectedRating} is still
              selected; try again.
            </p>
          )}
        </>
      ) : (
        <Button className="mt-8" onClick={() => setRevealed(true)}>
          Reveal answer <span className="sr-only">(Space)</span>
        </Button>
      )}
    </section>
  );
}
