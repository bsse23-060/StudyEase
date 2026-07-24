import { z } from "zod";
export const loginSchema = z.object({
  email: z.email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
export const registerSchema = loginSchema.extend({
  full_name: z.string().trim().min(2).max(150),
  level_preference: z.enum(["school", "college", "professional"]),
});
export const courseSchema = z.object({
  title: z.string().trim().min(3).max(255),
  slug: z.string().regex(/^[a-z0-9-]+$/),
  description: z.string().max(5000),
  is_published: z.boolean(),
});
export const documentSchema = z.object({
  title: z.string().trim().min(1).max(255),
  visibility: z.enum(["private", "course"]),
  course: z.coerce.number().positive().optional(),
  lesson: z.coerce.number().positive().optional(),
  file: z
    .instanceof(File)
    .refine((f) => f.size <= 10 * 1024 * 1024, "Maximum file size is 10 MB")
    .refine(
      (f) =>
        [
          "application/pdf",
          "text/plain",
          "text/markdown",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ].includes(f.type) || /\.(pdf|txt|md|docx)$/i.test(f.name),
      "Use PDF, TXT, Markdown, or DOCX",
    ),
});
export const questionSchema = z.object({
  question: z.string().trim().min(1).max(4000),
  top_k: z.number().int().min(1).max(10).default(5),
});
export const routineSchema = z.object({
  name: z.string().trim().min(2).max(255),
  is_active: z.boolean().default(true),
});
export const blockSchema = z
  .object({
    routine: z.number().positive(),
    activity_name: z.string().trim().min(2),
    start_time: z.string(),
    end_time: z.string(),
    category: z.string().trim().min(1),
    is_flexible: z.boolean(),
    notes: z.string(),
  })
  .refine((v) => v.start_time < v.end_time, {
    message: "End time must be after start time",
    path: ["end_time"],
  });
