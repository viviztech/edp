import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { serverApi } from "../lib/server-api";
import ParticipantPage from "../app/[locale]/participant/page";
import LearningPage from "../app/[locale]/learning/page";
import AttendancePage from "../app/[locale]/attendance/page";
import MentoringPage from "../app/[locale]/mentoring/page";
import BusinessPlanPage from "../app/[locale]/business-plan/page";
import BusinessPage from "../app/[locale]/businesses/page";
import KnowledgePage from "../app/[locale]/knowledge/page";
import HelpdeskPage from "../app/[locale]/helpdesk/page";
import ImpactPage from "../app/[locale]/impact/page";

vi.mock("../lib/server-api", () => ({ serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not found"); }, redirect: (path: string) => { throw new Error(`redirect:${path}`); } }));
vi.mock("../app/[locale]/participant/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/learning/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/attendance/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/mentoring/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/business-plan/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/businesses/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/knowledge/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/helpdesk/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/impact/view", () => ({ default: () => <div data-testid="workspace" /> }));

const organization = "11111111-1111-4111-8111-111111111111";
const foreignOrganization = "22222222-2222-4222-8222-222222222222";
const pages = [
  ["participant", ParticipantPage], ["learning", LearningPage], ["attendance", AttendancePage],
  ["mentoring", MentoringPage], ["business-plan", BusinessPlanPage], ["businesses", BusinessPage],
  ["knowledge", KnowledgePage], ["helpdesk", HelpdeskPage], ["impact", ImpactPage],
] as const;

beforeEach(() => {
  vi.mocked(serverApi).mockImplementation(async () => new Response(JSON.stringify({
    id: "person", display_name: "Synthetic participant", email: "person@example.test", locale: "ta",
    grants: [{ organization_id: organization, organization_name: "Program", permissions: ["participant.self", "lms.learn"] }],
  }), { status: 200 }));
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("participant page boundaries", () => {
  it.each(pages)("provides a focusable skip target and scoped Tamil navigation on %s", async (route, Page) => {
    render(await Page({ params: Promise.resolve({ locale: "ta" }), searchParams: Promise.resolve({ organization }) }));
    const main = screen.getByRole("main");
    expect(main.id).toBe("main");
    expect(main.getAttribute("tabindex")).toBe("-1");
    const current = screen.getAllByRole("link").find(link => link.getAttribute("aria-current") === "page");
    expect(current?.getAttribute("href")).toBe(`/ta/${route}?organization=${organization}`);
    expect(screen.getByRole("link", { name: "எனது கற்றல்" }).getAttribute("href")).toBe(`/ta/learning?organization=${organization}`);
    expect(screen.getByTestId("workspace")).toBeTruthy();
  });

  it.each(pages)("does not fall back to another organization for an ungranted %s destination", async (_route, Page) => {
    render(await Page({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ organization: foreignOrganization }) }));
    expect(screen.queryByTestId("workspace")).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Participant navigation" })).toBeNull();
    expect(screen.getByRole("main").id).toBe("main");
  });

  it("does not expose learning to participant grants without lms.learn", async () => {
    vi.mocked(serverApi).mockResolvedValue(new Response(JSON.stringify({ grants: [{ organization_id: organization, permissions: ["participant.self"] }] }), { status: 200 }));
    render(await LearningPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ organization }) }));
    expect(screen.queryByTestId("workspace")).toBeNull();
  });
});
