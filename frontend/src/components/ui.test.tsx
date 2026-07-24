import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Badge,
  Button,
  Confirm,
  Empty,
  Field,
  Progress,
  Skeleton,
  ToastProvider,
  useToast,
} from "./ui";
describe("accessible UI primitives", () => {
  it("exposes progress semantics", () => {
    render(<Progress label="Course progress" value={42} />);
    expect(
      screen.getByRole("progressbar", { name: "Course progress" }),
    ).toHaveAttribute("aria-valuenow", "42");
  });
  it("confirms by keyboard", async () => {
    const confirm = vi.fn();
    render(
      <Confirm
        open
        title="Delete?"
        body="Cannot be undone"
        onCancel={() => {}}
        onConfirm={confirm}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(confirm).toHaveBeenCalledOnce();
  });
  it("closes on Escape", async () => {
    const cancel = vi.fn();
    render(
      <Confirm
        open
        title="Delete?"
        body="Cannot be undone"
        onCancel={cancel}
        onConfirm={() => {}}
      />,
    );
    await userEvent.keyboard("{Escape}");
    expect(cancel).toHaveBeenCalledOnce();
  });
  it("renders labelled fields and status primitives", () => {
    render(
      <>
        <Field label="Course title" error="Required" hint="Public name">
          <input />
        </Field>
        <Badge tone="success">Ready</Badge>
        <Skeleton />
        <Empty title="Nothing here" body="Create the first item." />
        <Button variant="danger" disabled>
          Delete
        </Button>
      </>,
    );
    expect(screen.getByText("Course title")).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Required");
    expect(screen.getByRole("status")).toHaveAccessibleName("Loading");
    expect(screen.getByRole("heading", { name: "Nothing here" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });
  it("announces and dismisses toast messages", async () => {
    function Trigger() {
      const toast = useToast();
      return <button onClick={() => toast("Saved", "success")}>Save</button>;
    }
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("status")).toHaveTextContent("Saved");
    await userEvent.click(
      screen.getByRole("button", { name: "Dismiss notification" }),
    );
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });
});
