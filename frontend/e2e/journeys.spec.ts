import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const password = "StudyEaseDemo123!";
async function login(page: import("@playwright/test").Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect
    .poll(async () =>
      (await page.context().cookies()).some(
        (cookie) => cookie.name === "se_access",
      ),
    )
    .toBe(true);
  const session = await page.request.get("/api/backend/auth/me");
  expect(session.ok()).toBe(true);
  await page.goto("/dashboard");
  await expect(page).toHaveURL((url) => url.pathname === "/dashboard");
}
test("student login and learning journey", async ({ page }) => {
  await login(page, "student1@studyease.local");
  await expect(
    page.getByRole("heading", { name: /Good to see you/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "My courses" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Keep your momentum" }),
  ).toBeVisible();
});
test("student document and grounded assistant journey", async ({ page }) => {
  await login(page, "student1@studyease.local");
  await page.getByRole("link", { name: "Documents" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Your documents" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Study assistant" }).click();
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(
    page.getByPlaceholder(/Ask about your study material/),
  ).toBeVisible();
});
test("instructor course-management journey", async ({ page }) => {
  await login(page, "instructor1@studyease.local");
  await page.getByRole("link", { name: "My courses" }).first().click();
  await expect(page.getByRole("heading", { name: "My courses" })).toBeVisible();
  await page.getByRole("link", { name: "Create course" }).click();
  await expect(page.getByLabel("Course title")).toBeVisible();
});
test("cross-instructor course edit is denied", async ({ page, request }) => {
  const auth = await request.post("/api/v1/auth/token/", {
    data: { email: "instructor2@studyease.local", password },
  });
  const token = (await auth.json()).access;
  const meResponse = await request.get("/api/v1/auth/me/", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const instructor2 = (await meResponse.json()) as { id: number };
  const courses = await request.get("/api/v1/courses/", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const visible = (await courses.json()).results as {
    id: number;
    instructor: number;
  }[];
  const own = visible.filter((course) => course.instructor === instructor2.id);
  test.skip(!own.length, "Seed has no instructor 2 course");
  await login(page, "instructor1@studyease.local");
  await page.goto(`/instructor/builder?course=${own[0]!.id}`);
  await expect(
    page.getByRole("heading", { name: "Course unavailable" }),
  ).toBeVisible();
});
test("login page has no serious automated accessibility violations", async ({
  page,
}) => {
  await page.goto("/login");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
});
async function expectAccessible(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
}
test("student completes an atomic quiz and schedule pages are accessible", async ({
  page,
}) => {
  await login(page, "student2@studyease.local");
  const courses = await (await page.request.get("/api/backend/courses")).json();
  const python = courses.results.find(
    (c: { slug: string }) => c.slug === "python-foundations",
  );
  await page.request.post("/api/backend/enrollments", {
    data: { course: python.id },
  });
  const detail = await (
    await page.request.get(`/api/backend/courses/${python.id}`)
  ).json();
  const lesson = detail.modules[0].lessons[0];
  await page.goto(`/quiz/${lesson.id}`);
  await expect(
    page.getByRole("heading", { name: "Python Lists Check" }),
  ).toBeVisible();
  await page.getByLabel("[]").check();
  await page.getByRole("button", { name: "Review answers" }).click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(
    page.getByRole("heading", { name: "Quiz complete" }),
  ).toBeVisible();
  await expectAccessible(page);
  for (const path of [
    "/dashboard",
    "/courses",
    "/schedule",
    "/documents",
    "/assistant",
  ]) {
    await page.goto(path);
    await expectAccessible(page);
  }
});
test("instructor completion builders have no serious accessibility violations", async ({
  page,
}) => {
  await login(page, "instructor1@studyease.local");
  const me = await (await page.request.get("/api/backend/auth/me")).json();
  const courses = await (
    await page.request.get(`/api/backend/courses?instructor=${me.id}`)
  ).json();
  const course = courses.results.find(
    (c: { slug: string }) => c.slug === "python-foundations",
  );
  for (const path of [
    `/instructor/builder?course=${course.id}`,
    `/instructor/courses/${course.id}/concepts`,
    `/instructor/courses/${course.id}/quizzes`,
    "/instructor/retrieval",
  ]) {
    await page.goto(path);
    await expectAccessible(page);
  }
});
