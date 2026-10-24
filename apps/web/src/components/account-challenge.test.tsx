import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import AccountChallenge, { challengeMessages } from "./account-challenge";
import { authMessages } from "../lib/auth-messages";
import VerifyPage from "../app/[locale]/account/verify/page";
import ResetPage from "../app/[locale]/account/reset/page";

vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not_found"); } }));
const token = "synthetic-manually-entered-code-123456789";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); window.history.replaceState(null, "", "/"); });
function fill(purpose: "verify" | "reset") {
  fireEvent.change(screen.getByLabelText(authMessages.en.token), { target: { value: token } });
  if (purpose === "reset") fireEvent.change(screen.getByLabelText(authMessages.en.password), { target: { value: "Synthetic-new-password-123" } });
}
async function submit() { await act(async () => { fireEvent.submit(document.querySelector("form")!); }); }
describe("fixed account challenge pages", () => {
  it.each([["verify", VerifyPage], ["reset", ResetPage]] as const)("keeps %s purpose fixed and never reads query secrets or the signed-in account", async (purpose, Page) => {
    window.history.replaceState(null, "", `/en/account/${purpose}?token=query-secret&purpose=other`);
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    render(await Page({ params: Promise.resolve({ locale: "en" }) }));
    expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(authMessages.en[purpose]);
    expect(screen.getByLabelText(authMessages.en.token)).toHaveProperty("value", "");
    expect(mock).not.toHaveBeenCalled();
  });
  it.each(["verify", "reset"] as const)("posts %s explicitly with endpoint CSRF and clears secret fields after success", async purpose => {
    const store = vi.spyOn(Storage.prototype, "setItem");
    const mock = vi.fn(async (url: string) => Response.json(url === "/api/session/csrf" ? { csrf_token: "endpoint-csrf" } : { status: "completed" }));
    vi.stubGlobal("fetch", mock); render(<AccountChallenge locale="en" purpose={purpose} />);
    fill(purpose); expect(mock).not.toHaveBeenCalled(); await submit();
    expect(mock.mock.calls[1]).toEqual([`/api/session/${purpose}`, expect.objectContaining({
      method: "POST", body: JSON.stringify({ token, ...(purpose === "reset" ? { password: "Synthetic-new-password-123" } : {}) }),
      headers: { "Content-Type": "application/json", "x-csrf-token": "endpoint-csrf" },
    })]);
    expect(screen.getByRole("status").textContent).toBe(authMessages.en.completed);
    expect(document.querySelector("input[name=token]")).toBeNull(); expect(document.querySelector("input[name=password]")).toBeNull();
    expect(store).not.toHaveBeenCalled(); expect(window.location.search).toBe("");
  });
  it("keeps input after an ambiguous command without automatic replay or server diagnostics", async () => {
    let posts = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url === "/api/session/csrf") return Response.json({ csrf_token: "csrf" });
      posts++; throw new Error("Private server details");
    }));
    render(<AccountChallenge locale="en" purpose="reset" />); fill("reset"); await submit();
    expect(screen.getByRole("status").textContent).toBe(challengeMessages.en.uncertain);
    expect(screen.getByLabelText(authMessages.en.token)).toHaveProperty("value", token);
    expect(screen.getByLabelText(authMessages.en.password)).toHaveProperty("value", "Synthetic-new-password-123");
    expect(posts).toBe(1); expect(screen.queryByText("Private server details")).toBeNull();
  });
  it("prevents concurrent submits and never posts if CSRF is unavailable", async () => {
    const mock = vi.fn().mockResolvedValue(Response.json({}, { status: 503 })); vi.stubGlobal("fetch", mock);
    render(<AccountChallenge locale="en" purpose="verify" />); fill("verify");
    await act(async () => { fireEvent.submit(document.querySelector("form")!); fireEvent.submit(document.querySelector("form")!); });
    expect(mock).toHaveBeenCalledTimes(1); expect(screen.getByRole("status").textContent).toBe(authMessages.en.unavailable);
  });
  it("renders Tamil purpose and a safe account destination", () => {
    render(<AccountChallenge locale="ta" purpose="reset" />);
    expect(screen.getByRole("button", { name: authMessages.ta.reset })).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toBe("/ta/account");
    expect(Object.keys(challengeMessages.ta).sort()).toEqual(Object.keys(challengeMessages.en).sort());
  });
});
