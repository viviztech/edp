import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../lib/api-contracts";
import BusinessTracking from "./view";

type Profile = components["schemas"]["app__modules__businesses__schemas__ProfileView"];
type CreateProfile = components["schemas"]["CreateProfile"];
const organization = "11111111-1111-4111-8111-111111111111";
const enrollment = "22222222-2222-4222-8222-222222222222";
const program = "33333333-3333-4333-8333-333333333333";
const profileId = "44444444-4444-4444-8444-444444444444";
const root = `/api/businesses/organizations/${organization}`;
const fields: Omit<CreateProfile, "enrollment_id"> = {
  name: "Repair workshop", sector: "Services", products_services: "Bicycle repairs",
  stage: "idea", registration_info: null, started_on: null, team_size: 1,
  investment_band: "none", funding_status: "none", revenue_band: "none",
  support_needs: null, public_opt_in: false,
};
const timestamp = "2026-10-21T08:00:00Z";

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  }));
}

function profileFixture(): Profile {
  return { ...fields, id: profileId, enrollment_id: enrollment, version: 1,
    created_at: timestamp, updated_at: timestamp,
    revisions: [{ id: "revision-1", version: 1, snapshot: { ...fields }, created_at: timestamp }],
    follow_ups: [],
  };
}

// Like the API's extra="forbid" models, reject every response-only or unknown property.
function mockApi(initialProfile: Profile | null = null) {
  let saved = initialProfile;
  const writes: { body: Record<string, unknown>; status: number }[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
    if (url === `${root}/mine` && !init?.method) {
      return response({ entries: [{ enrollment_id: enrollment, program_id: program, profile: saved }] });
    }
    if (init?.method === "POST" && (url === `${root}/profiles` || url === `${root}/profiles/${profileId}/update`)) {
      expect(new Headers(init.headers).get("x-csrf-token")).toBe("test-csrf");
      const body = JSON.parse(String(init.body)) as Record<string, unknown>;
      const updating = url.endsWith("/update");
      const allowed = [...Object.keys(fields), updating ? "expected_version" : "enrollment_id"];
      if (Object.keys(body).some((key) => !allowed.includes(key))) {
        writes.push({ body, status: 422 });
        return response({ error: { code: "validation_failed" } }, 422);
      }
      if (updating && body.expected_version !== saved?.version) {
        writes.push({ body, status: 409 });
        return response({ error: { code: "version_conflict" } }, 409);
      }
      const writable = Object.fromEntries(Object.keys(fields).map((key) => [key, body[key]])) as typeof fields;
      const version = (saved?.version ?? 0) + 1;
      saved = { ...profileFixture(), ...writable, version,
        revisions: [...(saved?.revisions ?? []), {
          id: `revision-${version}`, version, snapshot: writable, created_at: timestamp,
        }],
      };
      writes.push({ body, status: 200 });
      return response(saved);
    }
    throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { writes, fetchMock, get saved() { return saved; }, advanceVersion() {
    if (saved) saved = { ...saved, version: saved.version + 1 };
  } };
}

function historyVersions() {
  return within(screen.getByText("Profile versions").closest("details")!)
    .getAllByRole("listitem").map((item) => item.textContent?.split(" · ")[0]);
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("business profile editing", () => {
  it("creates, reloads, edits and reloads without sending metadata or losing revision history", async () => {
    const api = mockApi();
    let view = render(<BusinessTracking org={organization} locale="en" />);
    fireEvent.change(await screen.findByLabelText("Business name"), { target: { value: fields.name } });
    fireEvent.change(screen.getByLabelText("Sector"), { target: { value: fields.sector } });
    fireEvent.change(screen.getByLabelText("Products and services"), { target: { value: fields.products_services } });
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await screen.findByText("Saved.");
    expect(api.writes[0]).toEqual({ status: 200, body: { ...fields, enrollment_id: enrollment } });

    view.unmount();
    view = render(<BusinessTracking org={organization} locale="en" />);
    expect((await screen.findByLabelText("Business name") as HTMLInputElement).value).toBe(fields.name);
    expect(historyVersions()).toEqual(["v1"]);
    fireEvent.change(screen.getByLabelText("Business name"), { target: { value: "Expanded repair workshop" } });
    fireEvent.change(screen.getByLabelText("Support needed"), { target: { value: "Equipment advice" } });
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await screen.findByText("Saved.");
    expect(api.writes[1]).toEqual({ status: 200, body: {
      ...fields, name: "Expanded repair workshop", support_needs: "Equipment advice", expected_version: 1,
    } });
    expect(api.saved?.revisions[0].snapshot.name).toBe(fields.name);
    expect(api.saved?.revisions[1].snapshot.name).toBe("Expanded repair workshop");

    view.unmount();
    render(<BusinessTracking org={organization} locale="en" />);
    expect((await screen.findByLabelText("Business name") as HTMLInputElement).value).toBe("Expanded repair workshop");
    expect((screen.getByLabelText("Support needed") as HTMLTextAreaElement).value).toBe("Equipment advice");
    expect(historyVersions()).toEqual(["v1", "v2"]);
  });

  it("preserves edits and clears the previous success message when the server rejects a stale version", async () => {
    const api = mockApi(profileFixture());
    render(<BusinessTracking org={organization} locale="en" />);
    await screen.findByLabelText("Business name");
    fireEvent.change(screen.getByLabelText("Business name"), { target: { value: "Saved workshop" } });
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await screen.findByText("Saved.");
    api.advanceVersion();

    fireEvent.change(screen.getByLabelText("Business name"), { target: { value: "Unsaved local workshop" } });
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await screen.findByText("Refresh saved progress before another save. Your input is kept.");
    expect(screen.queryByText("Saved.")).toBeNull();
    expect((screen.getByLabelText("Business name") as HTMLInputElement).value).toBe("Unsaved local workshop");
    expect(api.writes.at(-1)?.status).toBe(409);
    expect(api.writes.at(-1)?.body.expected_version).toBe(2);
    expect(api.saved?.name).toBe("Saved workshop");
    expect(historyVersions()).toEqual(["v1", "v2"]);
    expect((screen.getByRole("button", { name: "Save business" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Refresh saved progress" }));
    await screen.findByText("Latest progress loaded. Your input is kept; compare it before saving.");
    expect((screen.getByLabelText("Business name") as HTMLInputElement).value).toBe("Unsaved local workshop");
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await screen.findByText("Saved.");
    expect(api.writes.at(-1)?.body.expected_version).toBe(3);
    expect(api.saved?.name).toBe("Unsaved local workshop");
  });

  it("freezes fields during a write and reconciles a committed response that was lost", async () => {
    const api = mockApi(profileFixture());
    const original = api.fetchMock.getMockImplementation()!;
    let finish: (() => void) | undefined;
    api.fetchMock.mockImplementation((input, init) => {
      const result = original(input, init);
      if (init?.method === "POST") return new Promise<Response>((_resolve, reject) => {
        finish = () => reject(new Error("connection_lost"));
      });
      return result;
    });
    render(<BusinessTracking org={organization} locale="en" />);
    fireEvent.change(await screen.findByLabelText("Business name"), { target: { value: "Committed workshop" } });
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    await waitFor(() => expect(finish).toBeDefined());
    expect((screen.getByLabelText("Business name").closest("fieldset") as HTMLFieldSetElement).disabled).toBe(true);
    finish!();
    await screen.findByText("Refresh saved progress before another save. Your input is kept.");
    fireEvent.click(screen.getByRole("button", { name: "Save business" }));
    expect(api.writes).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Refresh saved progress" }));
    await screen.findByText("Latest progress loaded. Your input is kept; compare it before saving.");
    expect(api.saved?.version).toBe(2);
    expect((screen.getByLabelText("Business name") as HTMLInputElement).value).toBe("Committed workshop");
  });

  it("keeps separate follow-up drafts and applies the authoritative outcome without a second read", async () => {
    const profile = profileFixture();
    profile.follow_ups = ["follow-1", "follow-2"].map((id, index) => ({ id,
      offset_days: index + 1, due_on: `2026-10-${22 + index}`, status: "pending", outcome: null }));
    const api = mockApi(profile);
    const original = api.fetchMock.getMockImplementation()!;
    api.fetchMock.mockImplementation((input, init) => {
      if (String(input).endsWith("/follow-ups/follow-1/outcome") && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.challenges).toBe("First report");
        return response({ ...body, id: "outcome-1", created_at: timestamp });
      }
      return original(input, init);
    });
    render(<BusinessTracking org={organization} locale="en" />);
    await screen.findByLabelText("Business name");
    const reports = screen.getAllByText("Report outcome", { selector: "summary" }).map((node) => within(node.closest("details")!));
    fireEvent.change(reports[0].getByLabelText("Challenges"), { target: { value: "First report" } });
    fireEvent.change(reports[1].getByLabelText("Challenges"), { target: { value: "Other report" } });
    fireEvent.click(reports[0].getByRole("button", { name: "Report outcome" }));
    await screen.findByText("Jobs created: 0");
    expect((screen.getByLabelText("Challenges") as HTMLTextAreaElement).value).toBe("Other report");
    expect(api.fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/mine"))).toHaveLength(1);
  });
});
