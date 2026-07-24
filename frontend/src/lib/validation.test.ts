import { describe, expect, it } from "vitest";
import {
  blockSchema,
  loginSchema,
  questionSchema,
  registerSchema,
} from "./validation";
describe("shared validation", () => {
  it("accepts a valid login", () =>
    expect(
      loginSchema.safeParse({
        email: "student@example.com",
        password: "secret",
      }).success,
    ).toBe(true));
  it("rejects malformed email", () =>
    expect(
      loginSchema.safeParse({ email: "nope", password: "secret" }).success,
    ).toBe(false));
  it("requires registration names", () =>
    expect(
      registerSchema.safeParse({
        email: "a@b.com",
        password: "12345678",
        full_name: "x",
        level_preference: "college",
      }).success,
    ).toBe(false));
  it("rejects empty RAG questions", () =>
    expect(questionSchema.safeParse({ question: "", top_k: 5 }).success).toBe(
      false,
    ));
  it("caps retrieval at ten chunks", () =>
    expect(
      questionSchema.safeParse({ question: "why?", top_k: 11 }).success,
    ).toBe(false));
  it("accepts ordered schedule times", () =>
    expect(
      blockSchema.safeParse({
        routine: 1,
        activity_name: "Review",
        start_time: "09:00",
        end_time: "10:00",
        category: "study",
        is_flexible: true,
        notes: "",
      }).success,
    ).toBe(true));
  it("rejects reversed schedule times", () =>
    expect(
      blockSchema.safeParse({
        routine: 1,
        activity_name: "Review",
        start_time: "11:00",
        end_time: "10:00",
        category: "study",
        is_flexible: true,
        notes: "",
      }).success,
    ).toBe(false));
});
