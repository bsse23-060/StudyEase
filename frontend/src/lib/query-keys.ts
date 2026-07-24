export const qk = {
  me: ["me"] as const,
  courses: (p: unknown = {}) => ["courses", p] as const,
  course: (id: string | number) => ["course", id] as const,
  resource: (name: string, p: unknown = {}) => [name, p] as const,
};
