import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PublicEnquiryForm } from "./public-enquiry-form";
import { enquiryWords, type EnquiryPolicy } from "../lib/enquiry-content";
const policy: EnquiryPolicy = { enabled: true, consent_version: "synthetic-v1", consent_text: "Synthetic consent for local acceptance", privacy_notice_url: "/en/pages/privacy" };
const reference = "22222222-2222-4222-8222-222222222222";
const response = (data: object, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function fill() {
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Synthetic Enquirer" } });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "enquirer@example.test" } });
  fireEvent.change(screen.getByLabelText("Your enquiry"), { target: { value: "Question about the programme" } });
  fireEvent.click(screen.getByLabelText(policy.consent_text));
}
describe("public enquiry journey", () => {
  it("does not collect details before approved privacy configuration is available", () => {
    render(<PublicEnquiryForm locale="en" policy={null} />);
    expect(screen.getByText(enquiryWords.en.unavailable)).toBeTruthy(); expect(screen.queryByRole("textbox")).toBeNull();
  });
  it("requires consent, sends only the approved version and clears contact details after confirmation", async () => {
    const writes: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
      expect(new Headers(init?.headers).get("x-csrf-token")).toBe("csrf"); writes.push(JSON.parse(String(init?.body)));
      return response({ accepted: true, reference }, 202);
    }));
    render(<PublicEnquiryForm locale="en" policy={policy} />);
    expect((screen.getByRole("button", { name: "Send enquiry" }) as HTMLButtonElement).disabled).toBe(true);
    fill(); fireEvent.click(screen.getByRole("button", { name: "Send enquiry" }));
    await screen.findByText(reference); expect(screen.queryByDisplayValue("enquirer@example.test")).toBeNull();
    expect(writes).toEqual([{ name: "Synthetic Enquirer", email: "enquirer@example.test", phone: "", message: "Question about the programme", website: "", locale: "en", consent: true, consent_version: "synthetic-v1" }]);
  });
  it("preserves input after an uncertain request and retries only after another explicit submit", async () => {
    let writes = 0;
    vi.stubGlobal("fetch", vi.fn((url: string) => {
      if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
      writes += 1; return writes === 1 ? Promise.reject(new Error("network interrupted")) : response({ accepted: true, reference }, 202);
    }));
    render(<PublicEnquiryForm locale="en" policy={policy} />); fill(); fireEvent.click(screen.getByRole("button", { name: "Send enquiry" }));
    await screen.findByText(enquiryWords.en.error); expect(writes).toBe(1); expect(screen.getByDisplayValue("Question about the programme")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Send enquiry" })); await screen.findByText(reference); expect(writes).toBe(2);
  });
  it("renders Tamil labels and stops on outdated consent", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => url === "/api/session/csrf" ? response({ csrf_token: "csrf" }) : response({ error: { code: "consent_required" } }, 422)));
    render(<PublicEnquiryForm locale="ta" policy={policy} />);
    fireEvent.change(screen.getByLabelText(enquiryWords.ta.name), { target: { value: "Synthetic" } });
    fireEvent.change(screen.getByLabelText(enquiryWords.ta.email), { target: { value: "synthetic@example.test" } });
    fireEvent.change(screen.getByLabelText(enquiryWords.ta.message), { target: { value: "தமிழ் விசாரணை" } });
    fireEvent.click(screen.getByLabelText(policy.consent_text)); fireEvent.click(screen.getByRole("button", { name: enquiryWords.ta.send }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(enquiryWords.ta.changed));
  });
});
