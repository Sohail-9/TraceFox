import { fireEvent, render, screen } from "@testing-library/react";

import { ToastProvider } from "@/components/ToastProvider";

jest.mock("swr", () => ({
  __esModule: true,
  default: jest.fn(() => ({
    data: null,
    error: undefined,
    isLoading: false,
    mutate: jest.fn(),
  })),
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
  });

  it("renders mission control hero and pipeline overview", async () => {
    const { default: DashboardPage } = await import("@/app/page");
    render(
      <ToastProvider>
        <DashboardPage />
      </ToastProvider>
    );

    expect(
      screen.getByText(/Orchestrate reviews, testing, and RCA with confidence/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Pipeline Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/Webhook Received/i)).toBeInTheDocument();
  });

  it("switches insight tabs when selected", async () => {
    const { default: DashboardPage } = await import("@/app/page");
    render(
      <ToastProvider>
        <DashboardPage />
      </ToastProvider>
    );

    const testsTab = screen.getByRole("button", { name: /Tests/i });
    fireEvent.click(testsTab);
    expect(
      screen.getByText(/No generated tests yet\. Queue test generation to seed execution\./i)
    ).toBeInTheDocument();

    const rcaTab = screen.getByRole("button", { name: /RCA/i });
    fireEvent.click(rcaTab);
    expect(
      screen.getByText(/RCA insights will appear as soon as a test execution produces failures/i)
    ).toBeInTheDocument();
  });
});
