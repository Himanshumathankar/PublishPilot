import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SourceForm } from "./source-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

describe("SourceForm", () => {
  beforeEach(() => { push.mockReset(); vi.restoreAllMocks(); });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
  it("enables processing after selecting a DOCX", () => {
    render(<SourceForm />);
    const button = screen.getByRole("button", { name: "Process article" });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Upload DOCX"), {
      target: { files: [new File(["docx"], "article.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })] },
    });

    expect(screen.getByText("article.docx")).toBeInTheDocument();
    expect(button).toBeEnabled();
  });

  it("routes a Google Sheets URL through the Sheets importer", async () => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "article-1" }), { status: 201 }));
    vi.stubGlobal("fetch", request);
    render(<SourceForm />);

    fireEvent.change(screen.getByLabelText("Google document or sheet URL"), {
      target: { value: "https://docs.google.com/spreadsheets/d/sheet-id/edit" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Process article" }));

    await waitFor(() => expect(request).toHaveBeenCalledOnce());
    expect(request.mock.calls[0][0]).toContain("/articles/process-google-sheet");
    expect(push).toHaveBeenCalledWith("/articles/preview/article-1");
  });
});
