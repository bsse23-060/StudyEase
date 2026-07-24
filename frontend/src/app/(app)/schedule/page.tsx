"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json, list } from "@/lib/api/client";
import { detail, endpoints } from "@/lib/api/endpoints";
import type { Routine, ScheduleBlock } from "@/lib/api/types";
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
import { useMemo, useState } from "react";
const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
export default function Schedule() {
  const qc = useQueryClient();
  const routines = useQuery({
    queryKey: ["routines"],
    queryFn: () => list<Routine>(endpoints.routines),
  });
  const [name, setName] = useState(""),
    [view, setView] = useState<"week" | "upcoming">("week");
  const create = useMutation({
    mutationFn: () =>
      api<Routine>(endpoints.routines, {
        method: "POST",
        ...json({ name, is_active: true, preferences: {} }),
      }),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({ queryKey: ["routines"] });
    },
  });
  const blocks = routines.data?.results.flatMap((r) => r.blocks) ?? [];
  return (
    <>
      <PageHeading
        eyebrow="Timezone-aware planning"
        title="Study schedule"
        description={`Browser timezone: ${Intl.DateTimeFormat().resolvedOptions().timeZone}. Every block stores its own IANA timezone; wall-clock times are presented in that stored zone.`}
      />
      <div className="mb-5 flex flex-wrap gap-2">
        <Button
          variant={view === "week" ? "primary" : "secondary"}
          onClick={() => setView("week")}
        >
          Weekly view
        </Button>
        <Button
          variant={view === "upcoming" ? "primary" : "secondary"}
          onClick={() => setView("upcoming")}
        >
          Upcoming blocks
        </Button>
      </div>
      <form
        className="card mb-6 flex items-end gap-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <div className="flex-1">
          <Field label="Routine name">
            <input
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
        </div>
        <Button disabled={!name.trim()}>Create routine</Button>
      </form>
      {routines.isLoading ? (
        <Skeleton />
      ) : !routines.data?.results.length ? (
        <Empty
          title="No routines"
          body="Create a routine to group study blocks."
        />
      ) : (
        <>
          {view === "week" ? (
            <Week blocks={blocks} />
          ) : (
            <Upcoming blocks={blocks} />
          )}
          <div className="mt-7 grid gap-6">
            {routines.data.results.map((r) => (
              <RoutineCard key={r.id} routine={r} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
function Week({ blocks }: { blocks: ScheduleBlock[] }) {
  return (
    <section aria-label="Weekly schedule" className="grid gap-3 md:grid-cols-7">
      {DAYS.map((day, index) => (
        <div className="card min-h-28 p-3" key={day}>
          <h2 className="text-sm font-bold">{day}</h2>
          {blocks
            .filter((b) => b.recurrence === "weekly" && b.weekday === index)
            .map((b) => (
              <p
                className="mt-2 rounded-lg bg-emerald-50 p-2 text-xs"
                key={b.id}
              >
                <strong>{b.activity_name}</strong>
                <br />
                {b.start_time.slice(0, 5)}–{b.end_time.slice(0, 5)}
                <br />
                {b.timezone}
              </p>
            ))}
        </div>
      ))}
    </section>
  );
}
function Upcoming({ blocks }: { blocks: ScheduleBlock[] }) {
  const upcoming = useMemo(
    () =>
      blocks
        .filter(
          (b) =>
            b.recurrence === "once" &&
            b.calendar_date &&
            new Date(`${b.calendar_date}T23:59:59`) >= new Date(),
        )
        .sort((a, b) => a.calendar_date!.localeCompare(b.calendar_date!)),
    [blocks],
  );
  return (
    <section className="card p-5">
      <h2 className="text-xl font-bold">Upcoming one-time blocks</h2>
      {upcoming.map((b) => (
        <p className="mt-3 border-t pt-3" key={b.id}>
          <strong>{b.activity_name}</strong> ·{" "}
          {new Date(`${b.calendar_date}T00:00:00`).toLocaleDateString()} ·{" "}
          {b.start_time.slice(0, 5)} {b.timezone}
        </p>
      ))}
      {!upcoming.length && (
        <p className="mt-3 text-slate-500">No upcoming one-time blocks.</p>
      )}
    </section>
  );
}
function RoutineCard({ routine }: { routine: Routine }) {
  const qc = useQueryClient(),
    toast = useToast();
  const [editingName, setEditingName] = useState(routine.name),
    [removeRoutine, setRemoveRoutine] = useState(false),
    [remove, setRemove] = useState<ScheduleBlock | null>(null),
    [editingBlock, setEditingBlock] = useState<number | null>(null),
    [form, setForm] = useState({
      activity_name: "",
      start_time: "09:00",
      end_time: "10:00",
      category: "study",
      notes: "",
      is_flexible: true,
      recurrence: "weekly" as "once" | "weekly",
      weekday: 0,
      calendar_date: "",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      recurrence_start: new Date().toISOString().slice(0, 10),
      recurrence_end: "",
      is_active: true,
    });
  const refresh = () => qc.invalidateQueries({ queryKey: ["routines"] });
  const updateRoutine = useMutation({
    mutationFn: () =>
      api(detail(endpoints.routines, routine.id), {
        method: "PATCH",
        ...json({ name: editingName }),
      }),
    onSuccess: refresh,
  });
  const add = useMutation({
    mutationFn: () =>
      api<ScheduleBlock>(
        editingBlock
          ? detail(endpoints.blocks, editingBlock)
          : endpoints.blocks,
        {
          method: editingBlock ? "PATCH" : "POST",
          ...json({
            ...form,
            routine: routine.id,
            weekday: form.recurrence === "weekly" ? form.weekday : null,
            calendar_date:
              form.recurrence === "once" ? form.calendar_date : null,
            recurrence_end: form.recurrence_end || null,
            recurrence_start:
              form.recurrence === "weekly" ? form.recurrence_start : null,
          }),
        },
      ),
    onSuccess: (saved) => {
      if (saved.warnings?.length)
        toast(
          saved.warnings.map((warning) => warning.message).join(" "),
          "error",
        );
      setEditingBlock(null);
      refresh();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
  const del = useMutation({
    mutationFn: () =>
      api(detail(endpoints.blocks, remove!.id), { method: "DELETE" }),
    onSuccess: () => {
      setRemove(null);
      refresh();
    },
  });
  const delRoutine = useMutation({
    mutationFn: () =>
      api(detail(endpoints.routines, routine.id), { method: "DELETE" }),
    onSuccess: refresh,
  });
  return (
    <section className="card p-5">
      <div className="flex gap-2">
        <input
          aria-label="Routine name"
          className={inputClass}
          value={editingName}
          onChange={(e) => setEditingName(e.target.value)}
        />
        <Button variant="secondary" onClick={() => updateRoutine.mutate()}>
          Rename
        </Button>
        <Button variant="danger" onClick={() => setRemoveRoutine(true)}>
          Delete routine
        </Button>
      </div>
      <div className="mt-4 grid gap-2">
        {routine.blocks.map((b) => (
          <div
            className="flex flex-wrap justify-between rounded-xl bg-slate-50 p-3"
            key={b.id}
          >
            <span>
              <strong>{b.activity_name}</strong> ·{" "}
              {b.recurrence === "weekly"
                ? DAYS[b.weekday ?? 0]
                : b.calendar_date}{" "}
              · {b.timezone}
            </span>
            <span>
              <time>
                {b.start_time.slice(0, 5)}–{b.end_time.slice(0, 5)}
              </time>{" "}
              <Button
                variant="secondary"
                onClick={() => {
                  setEditingBlock(b.id);
                  setForm((f) => ({
                    ...f,
                    activity_name: b.activity_name,
                    start_time: b.start_time.slice(0, 5),
                    end_time: b.end_time.slice(0, 5),
                    category: b.category,
                    notes: b.notes,
                    is_flexible: b.is_flexible,
                    recurrence: b.recurrence,
                    weekday: b.weekday ?? 0,
                    calendar_date: b.calendar_date ?? "",
                    timezone: b.timezone,
                    recurrence_start: b.recurrence_start ?? "",
                    recurrence_end: b.recurrence_end ?? "",
                    is_active: b.is_active,
                  }));
                }}
              >
                Edit
              </Button>
              <Button variant="danger" onClick={() => setRemove(b)}>
                Delete
              </Button>
            </span>
          </div>
        ))}
      </div>
      <form
        className="mt-5 grid gap-3 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <Field label="Title">
          <input
            className={inputClass}
            value={form.activity_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, activity_name: e.target.value }))
            }
          />
        </Field>
        <Field label="Recurrence">
          <select
            className={inputClass}
            value={form.recurrence}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                recurrence: e.target.value as "once" | "weekly",
              }))
            }
          >
            <option value="weekly">Weekly</option>
            <option value="once">One time</option>
          </select>
        </Field>
        {form.recurrence === "weekly" ? (
          <Field label="Weekday">
            <select
              className={inputClass}
              value={form.weekday}
              onChange={(e) =>
                setForm((f) => ({ ...f, weekday: Number(e.target.value) }))
              }
            >
              {DAYS.map((d, i) => (
                <option value={i} key={d}>
                  {d}
                </option>
              ))}
            </select>
          </Field>
        ) : (
          <Field label="Date">
            <input
              type="date"
              className={inputClass}
              value={form.calendar_date}
              onChange={(e) =>
                setForm((f) => ({ ...f, calendar_date: e.target.value }))
              }
            />
          </Field>
        )}
        <Field label="Start">
          <input
            type="time"
            className={inputClass}
            value={form.start_time}
            onChange={(e) =>
              setForm((f) => ({ ...f, start_time: e.target.value }))
            }
          />
        </Field>
        <Field label="End">
          <input
            type="time"
            className={inputClass}
            value={form.end_time}
            onChange={(e) =>
              setForm((f) => ({ ...f, end_time: e.target.value }))
            }
          />
        </Field>
        <Field label="IANA timezone">
          <input
            className={inputClass}
            value={form.timezone}
            onChange={(e) =>
              setForm((f) => ({ ...f, timezone: e.target.value }))
            }
          />
        </Field>
        <Button
          className="self-end"
          disabled={!form.activity_name.trim() || add.isPending}
        >
          {editingBlock ? "Save block" : "Add block"}
        </Button>
      </form>
      <Confirm
        open={!!remove}
        title="Delete this study block?"
        body="The recurring definition will be removed; no other blocks are affected."
        onCancel={() => setRemove(null)}
        onConfirm={() => del.mutate()}
        busy={del.isPending}
      />
      <Confirm
        open={removeRoutine}
        title="Delete this routine?"
        body="All schedule blocks in this routine will be deleted."
        onCancel={() => setRemoveRoutine(false)}
        onConfirm={() => delRoutine.mutate()}
        busy={delRoutine.isPending}
      />
    </section>
  );
}
