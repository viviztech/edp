import type { components } from "../../../lib/api-contracts";

export type Plan = components["schemas"]["PlanView"];
export type Entry = components["schemas"]["PlanEntry"];
export type SectionCode = components["schemas"]["SaveSection"]["section_code"];
type Drafts = Record<string, string>;
type Attempt = { code: SectionCode; body: string; version: number };
export type Phase = "ready" | "saving" | "creating" | "submitting" | "refreshing" | "conflict" | "refresh_failed" | "save_failed" | "locked";
export type EditorState = {
  plan: Plan | null;
  drafts: Drafts;
  phase: Phase;
  conflicts: string[];
  attempt: Attempt | null;
  pauseOnDirty: boolean;
  uncertain: boolean;
  forced: Record<string, number>;
  notice: "" | "saved" | "saving" | "refreshing" | "recovered";
};

// Match Python str.strip(), which the API applies before storing section text.
export function normalized(body = "") {
  return body.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g, "");
}

export function editable(plan: Plan | null) {
  return plan !== null && ["draft", "changes_requested"].includes(plan.status);
}

export function dirtyCodes(state: Pick<EditorState, "drafts" | "plan"> & Partial<Pick<EditorState, "forced">>) {
  return Object.keys(state.drafts).filter((code) =>
    Object.hasOwn(state.forced ?? {}, code) || normalized(state.drafts[code]) !== normalized(state.plan?.sections[code]));
}

export function initialState(plan: Plan | null): EditorState {
  return { plan, drafts: { ...plan?.sections }, phase: "ready", conflicts: [], attempt: null,
    pauseOnDirty: false, uncertain: false, forced: {}, notice: "" };
}

type Action =
  | { type: "edit"; code: SectionCode; body: string }
  | { type: "save"; attempt: Attempt }
  | { type: "start"; phase: "creating" | "submitting" }
  | { type: "saved"; plan: Plan }
  | { type: "refresh"; pauseOnDirty?: boolean; uncertain?: boolean }
  | { type: "refreshed"; plan: Plan | null }
  | { type: "refresh_failed" }
  | { type: "keep" }
  | { type: "discard" };

function reconcile(state: EditorState, remote: Plan | null, acknowledged: boolean): EditorState {
  const base = { ...state.plan?.sections };
  const attempt = state.attempt;
  const committed = attempt && remote && remote.version > attempt.version && (normalized(remote.sections[attempt.code]) === normalized(attempt.body) ||
    remote.revisions.some((revision) => revision.version === attempt.version + 1 &&
      revision.section_code === attempt.code && normalized(revision.body) === normalized(attempt.body)));
  if (attempt && (acknowledged || committed)) base[attempt.code] = normalized(attempt.body);
  const forced = { ...state.forced };
  for (const [code, version] of Object.entries(forced)) {
    if (remote && remote.version > version && normalized(state.drafts[code]) === normalized(remote.sections[code])) delete forced[code];
  }
  if (attempt && (acknowledged || committed)) delete forced[attempt.code];
  // A failed connection can precede the server commit. Retain that section's intent even if
  // another dirty section is retried first or the user later reverts to the old saved text.
  if (state.uncertain && attempt && remote?.version === attempt.version && !acknowledged && !committed) {
    forced[attempt.code] = attempt.version;
  }
  const unresolvedAttempt = state.uncertain && attempt && !acknowledged && !committed &&
    remote?.version === attempt.version && editable(remote) ? attempt : null;
  const drafts: Drafts = {};
  const conflicts: string[] = [];
  const codes = new Set([...Object.keys(base), ...Object.keys(state.drafts), ...Object.keys(remote?.sections ?? {})]);
  for (const code of codes) {
    const local = normalized(state.drafts[code]);
    const saved = normalized(remote?.sections[code]);
    // A revert typed during a pending request is still an edit if that request may have committed.
    const typedAfterAttempt = attempt?.code === code && state.drafts[code] !== attempt.body;
    const localChanged = local !== normalized(base[code]) || typedAfterAttempt || Object.hasOwn(forced, code);
    if (!localChanged || local === saved) drafts[code] = remote?.sections[code] ?? "";
    else {
      drafts[code] = state.drafts[code] ?? "";
      if (saved !== normalized(base[code])) conflicts.push(code);
    }
  }
  const paused = state.pauseOnDirty && (dirtyCodes({ plan: remote, drafts, forced }).length > 0 || unresolvedAttempt !== null);
  return { plan: remote, drafts, conflicts, attempt: unresolvedAttempt, pauseOnDirty: false,
    uncertain: unresolvedAttempt !== null, forced,
    phase: remote && !editable(remote) ? "locked" : conflicts.length ? "conflict" : paused ? "save_failed" : "ready",
    notice: paused ? "" : acknowledged ? "saved" : "recovered" };
}

export function editorReducer(state: EditorState, action: Action): EditorState {
  switch (action.type) {
    case "edit": {
      const conflicts = state.conflicts.filter((code) => code !== action.code ||
        normalized(action.body) !== normalized(state.plan?.sections[code]));
      return { ...state, drafts: { ...state.drafts, [action.code]: action.body }, conflicts,
        phase: state.phase === "conflict" && !conflicts.length ? "ready" : state.phase,
        notice: "" };
    }
    case "save": return { ...state, phase: "saving", attempt: action.attempt, notice: "saving" };
    case "start": return { ...state, phase: action.phase, notice: "saving" };
    case "saved": return reconcile(state, action.plan, true);
    case "refresh": return { ...state, phase: "refreshing", pauseOnDirty: action.pauseOnDirty ?? false,
      uncertain: action.uncertain ?? state.uncertain, notice: "refreshing" };
    case "refreshed": return reconcile(state, action.plan, false);
    case "refresh_failed": return { ...state, phase: "refresh_failed", notice: "" };
    case "keep": return editable(state.plan) ? { ...state, phase: "ready", conflicts: [], notice: "recovered" } : state;
    case "discard": return { ...state, drafts: { ...state.plan?.sections }, conflicts: [], attempt: null, forced: {}, uncertain: false,
      phase: editable(state.plan) ? "ready" : "locked", notice: "saved" };
  }
}
