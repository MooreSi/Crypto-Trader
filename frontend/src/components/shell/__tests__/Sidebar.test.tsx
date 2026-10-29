import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar, TABS } from "../Sidebar";

describe("Sidebar", () => {
  it("lists Calendar straight under Trades and navigates to it", async () => {
    expect(TABS.indexOf("Calendar")).toBe(TABS.indexOf("Trades") + 1);
    const go = vi.fn();
    render(<Sidebar tab="Dashboard" go={go} status={null} />);
    await userEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(go).toHaveBeenCalledWith("Calendar");
  });
});
