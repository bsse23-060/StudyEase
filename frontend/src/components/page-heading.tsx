export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-3xl font-black md:text-4xl">{title}</h1>
        {description && (
          <p className="mt-2 max-w-2xl text-slate-600">{description}</p>
        )}
      </div>
      {action}
    </header>
  );
}
