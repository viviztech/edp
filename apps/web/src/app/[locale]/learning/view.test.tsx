import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import LearnerWorkspace from "./view";
import { learningMessages } from "../../../lib/learning-messages";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("learner workspace states", () => {
  it("does not report an empty course list when loading failed", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
    render(<LearnerWorkspace org="org-one" locale="en" />);
    expect(await screen.findByText(learningMessages.en.error)).toBeTruthy();
    expect(screen.queryByText(learningMessages.en.empty)).toBeNull();
  });
});
