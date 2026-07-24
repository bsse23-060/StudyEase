"use client";
import { clsx } from "clsx";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useState,
} from "react";
import { X } from "lucide-react";
export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  return (
    <button
      className={clsx(
        "inline-flex min-h-11 items-center justify-center rounded-xl px-4 py-2 font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "bg-emerald-800 text-white hover:bg-emerald-900",
        variant === "secondary" &&
          "border border-slate-300 bg-white hover:bg-slate-50",
        variant === "danger" && "bg-red-700 text-white",
        className,
      )}
      {...props}
    />
  );
}
export function Field({
  label,
  error,
  children,
  hint,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
  hint?: string;
}) {
  const id = useId();
  return (
    <label className="grid gap-1.5">
      <span className="text-sm font-semibold">{label}</span>
      <span id={id} className="contents">
        {children}
      </span>
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
      {error && (
        <span role="alert" className="text-sm text-red-700">
          {error}
        </span>
      )}
    </label>
  );
}
export const inputClass =
  "min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-950 placeholder:text-slate-400 focus:border-emerald-700";
export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  return (
    <span
      className={clsx(
        "inline-flex rounded-full px-2.5 py-1 text-xs font-bold",
        tone === "neutral" && "bg-slate-100 text-slate-700",
        tone === "success" && "bg-emerald-100 text-emerald-800",
        tone === "warning" && "bg-amber-100 text-amber-900",
        tone === "danger" && "bg-red-100 text-red-800",
      )}
    >
      {children}
    </span>
  );
}
export function Progress({ value, label }: { value: number; label: string }) {
  const n = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span>{Math.round(n)}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-label={label}
        aria-valuenow={n}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full bg-emerald-700" style={{ width: `${n}%` }} />
      </div>
    </div>
  );
}
export function Skeleton() {
  return (
    <div
      aria-label="Loading"
      role="status"
      className="grid animate-pulse gap-3"
    >
      <div className="h-7 w-1/3 rounded bg-slate-200" />
      <div className="h-28 rounded-xl bg-slate-200" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
export function Empty({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card p-8 text-center">
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-slate-600">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
type ToastFn = (message: string, tone?: "success" | "error") => void;
const ToastContext = createContext<ToastFn>(() => {});
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<{ message: string; tone: string } | null>(
    null,
  );
  const show = useCallback<ToastFn>(
    (message, tone = "success") => setToast({ message, tone }),
    [],
  );
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(t);
  }, [toast]);
  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div
          role={toast.tone === "error" ? "alert" : "status"}
          className={clsx(
            "fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-3 rounded-xl px-4 py-3 text-white shadow-xl",
            toast.tone === "error" ? "bg-red-800" : "bg-emerald-800",
          )}
        >
          {toast.message}
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast(null)}
          >
            <X size={18} />
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}
export const useToast = () => useContext(ToastContext);
export function Confirm({
  open,
  title,
  body,
  onCancel,
  onConfirm,
  busy = false,
}: {
  open: boolean;
  title: string;
  body: string;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const key = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [open, onCancel]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(e) => e.target === e.currentTarget && onCancel()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="card max-w-md p-6"
      >
        <h2 id="confirm-title" className="text-xl font-bold">
          {title}
        </h2>
        <p className="mt-2 text-slate-600">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button autoFocus variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" disabled={busy} onClick={onConfirm}>
            Confirm
          </Button>
        </div>
      </div>
    </div>
  );
}
