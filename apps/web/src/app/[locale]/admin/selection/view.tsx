"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { selectionMessages } from "../../../../lib/selection-messages";

type Workspace = components["schemas"]["SelectionWorkspace"];
type Cycle = components["schemas"]["SelectionCycleView"];
type Rubric = components["schemas"]["RubricView"];
type Criterion = components["schemas"]["CriterionInput"];
type Assignment = components["schemas"]["AssignmentView"];
type Aggregate = components["schemas"]["ApplicationAggregateView"];
type Interview = components["schemas"]["InterviewView"];
type Catalog = components["schemas"]["CatalogView"];
type Locale = "en" | "ta";

const empty: Workspace = {
  cycles: [], rubrics: [], applications: [], reviewers: [], assignments: [], aggregates: [], interviews: [], decisions: [],
};

const newCriterion = (): Criterion => ({
  key: "", label_en: "", label_ta: "", guidance_en: null, guidance_ta: null,
  weight: 100, minimum_score: 0, maximum_score: 5, required: true,
});

export default function SelectionWorkspace({ org, actor, locale, permissions }: {
  org: string; actor: string; locale: Locale; permissions: string[];
}) {
  const text = selectionMessages[locale];
  const root = `/api/selection/organizations/${org}`;
  const [workspace, setWorkspace] = useState<Workspace>(empty);
  const [catalog, setCatalog] = useState<Catalog>({ programs: [], centers: [], cohorts: [], cycles: [], enrollment_candidates: [], participants: [], enrollments: [], sessions: [] });
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const canManageCycle = permissions.includes("selection.cycle.manage");
  const canManageRubric = permissions.includes("selection.rubric.manage");
  const canPublish = permissions.includes("selection.rubric.publish");
  const canAssign = permissions.includes("selection.assignment.manage");
  const canReview = permissions.includes("selection.review");
  const canModerate = permissions.includes("selection.review.moderate");
  const canManageInterview = permissions.includes("selection.interview.manage");
  const canScoreInterview = permissions.includes("selection.interview.score");
  const canDecide = permissions.includes("selection.decision.manage");
  const canOverride = permissions.includes("selection.decision.override");
  const canFinalize = permissions.includes("selection.finalize");

  const request = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const token = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!token.ok) throw new Error("service_unavailable");
      headers["x-csrf-token"] = (await token.json()).csrf_token;
    }
    const response = await fetch(path, {
      method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error?.code ?? "request_failed");
    return body as T;
  }, []);

  const load = useCallback(async () => {
    const [selection, programs] = await Promise.all([
      request<Workspace>(root + "/workspace"),
      permissions.includes("program.view")
        ? request<Catalog>(`/api/programs/organizations/${org}/catalog`)
        : Promise.resolve({ programs: [], centers: [], cohorts: [], cycles: [], enrollment_candidates: [], participants: [], enrollments: [], sessions: [] } as Catalog),
    ]);
    setWorkspace(selection);
    setCatalog(programs);
  }, [org, permissions, request, root]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try { await load(); if (active) setMessage(""); }
      catch { if (active) setMessage(text.error); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [load, text.error]);

  async function run(action: () => Promise<unknown>, form?: HTMLFormElement) {
    setBusy(true);
    try { await action(); await load(); form?.reset(); setMessage(text.saved); }
    catch { setMessage(text.error); }
    finally { setBusy(false); }
  }

  function createCycle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    void run(() => request(root + "/cycles", "POST", data), form);
  }

  function transition(cycle: Cycle, target: "active" | "closed") {
    const reason = window.prompt(text.reason);
    if (!reason || reason.trim().length < 3) return;
    void run(() => request(`${root}/cycles/${cycle.id}/state`, "POST", {
      expected_version: cycle.version, target, reason: reason.trim(),
    }));
  }

  function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    void run(() => request(root + "/assignments", "POST", data), form);
  }

  function declareConflict(item: Assignment, status: "clear" | "conflict") {
    const note = status === "conflict" ? window.prompt(text.conflictReason) : null;
    if (status === "conflict" && (!note || note.trim().length < 3)) return;
    void run(() => request(`${root}/assignments/${item.id}/conflict`, "POST", {
      expected_version: item.version, status, note: note?.trim() ?? null,
    }));
  }

  function moderate(item: Assignment, status: "included" | "excluded") {
    const reason = window.prompt(status === "excluded" ? text.excludeReason : text.restoreReason);
    if (!reason || reason.trim().length < 3) return;
    void run(() => request(`${root}/assignments/${item.id}/moderation`, "POST", {
      expected_version: item.version, status, reason: reason.trim(),
    }));
  }
  function decide(item: Aggregate, target: "shortlisted" | "selected" | "waitlisted" | "rejected", override = false) {
    const reason = window.prompt(override ? text.overrideReason : text.decisionReason);
    if (!reason || reason.trim().length < 3) return;
    void run(() => request(`${root}/cycles/${item.selection_cycle_id}/applications/${item.application_id}/decision`, "POST", {
      expected_application_version: item.application_version, target, reason: reason.trim(), override,
    }));
  }

  function scheduleInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const starts = String(data.get("starts_at"));
    const ends = String(data.get("ends_at"));
    void run(() => request(root + "/interviews", "POST", {
      selection_cycle_id: String(data.get("selection_cycle_id")),
      application_id: String(data.get("application_id")),
      starts_at: new Date(starts).toISOString(), ends_at: new Date(ends).toISOString(),
      mode: String(data.get("mode")), location: String(data.get("location") || "") || null,
      panel_user_ids: data.getAll("panel_user_ids").map(String),
    }), form);
  }

  function submitPanelScore(event: FormEvent<HTMLFormElement>, interview: Interview) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    const member = interview.panel.find((item) => item.user_id === actor);
    if (!member) return;
    void run(() => request(`${root}/interviews/${interview.id}/score`, "POST", {
      expected_version: member.version, score: Number(data.score),
      comment: String(data.comment || "") || null,
    }), form);
  }

  function completeInterview(interview: Interview) {
    void run(() => request(`${root}/interviews/${interview.id}/complete`, "POST", {
      expected_version: interview.version,
    }));
  }
  const intakeName = (id: string) => {
    const cycle = catalog.cycles.find((item) => item.id === id);
    return cycle ? (locale === "ta" ? cycle.name_ta : cycle.name_en) : id;
  };
  const cycleName = (id: string) => {
    const cycle = workspace.cycles.find((item) => item.id === id);
    return cycle ? (locale === "ta" ? cycle.name_ta : cycle.name_en) : id;
  };
  const eligibleIntakes = catalog.cycles.filter((item) =>
    item.state !== "cancelled" && !workspace.cycles.some((cycle) => cycle.application_cycle_id === item.id)
  );

  return <div className="program-workspace selection-workspace" aria-busy={busy}>
    <p role="status" className="program-message">{busy ? text.loading : message}</p>
    <div className="program-grid">
      <section className="program-panel">
        <h2>{text.cycles}</h2>
        {canManageCycle && <form className="program-form" onSubmit={createCycle}>
          <Field label={text.code} name="code" />
          <Field label={text.englishName} name="name_en" />
          <Field label={text.tamilName} name="name_ta" />
          <Select label={text.intake} name="application_cycle_id" choose={text.choose}
            options={eligibleIntakes.map((item) => [item.id, locale === "ta" ? item.name_ta : item.name_en])} />
          <button disabled={busy}>{text.create}</button>
        </form>}
        <ul className="program-list">{workspace.cycles.map((item) => {
          const hasPublished = workspace.rubrics.some((rubric) =>
            rubric.selection_cycle_id === item.id && rubric.state === "published"
          );
          return <li key={item.id}>
            <Record name={locale === "ta" ? item.name_ta : item.name_en} detail={`${item.code} · ${intakeName(item.application_cycle_id)} · ${text.version} ${item.version}`} state={item.state} />
            {canManageCycle && <div className="program-actions">
              {item.state === "draft" && hasPublished && <button onClick={() => transition(item, "active")}>{text.activate}</button>}
              {item.state === "active" && canFinalize && <button onClick={() => transition(item, "closed")}>{text.finalizeCycle}</button>}
            </div>}
          </li>;
        })}</ul>
        {!workspace.cycles.length && <p>{text.empty}</p>}
      </section>

      <section className="program-panel">
        <h2>{text.assignments}</h2>
        {canAssign && <form className="program-form" onSubmit={assign}>
          <Select label={text.cycles} name="selection_cycle_id" choose={text.choose}
            options={workspace.cycles.filter((item) => item.state === "active").map((item) => [item.id, locale === "ta" ? item.name_ta : item.name_en])} />
          <Select label={text.application} name="application_id" choose={text.choose}
            options={workspace.applications.map((item) => [item.id, item.application_number])} />
          <Select label={text.reviewer} name="reviewer_user_id" choose={text.choose}
            options={workspace.reviewers.map((item) => [item.id, item.display_name])} />
          <button disabled={busy}>{text.assign}</button>
        </form>}
        <ul className="program-list">{workspace.assignments.map((item) =>
          <li key={item.id}>
            <Record name={item.application_number} detail={`${item.reviewer_name} · ${cycleName(item.selection_cycle_id)}`} state={item.status} />
            {item.status === "completed" && <div className="selection-result">
              <strong>{text.weightedScore}: {Number(item.weighted_score).toFixed(2)}</strong>
              <span>{item.moderation_status === "included" ? text.included : text.excluded}</span>
              {item.internal_comment && <p>{text.internalComment}: {item.internal_comment}</p>}
              {canModerate && <button disabled={busy} onClick={() => moderate(item, item.moderation_status === "included" ? "excluded" : "included")}>
                {item.moderation_status === "included" ? text.exclude : text.restore}
              </button>}
            </div>}
          </li>
        )}</ul>
        {!workspace.assignments.length && <p>{text.empty}</p>}
      </section>

      <section className="program-panel program-wide">
        <h2>{text.rubric}</h2>
        <div className="selection-rubrics">{workspace.rubrics.map((item) =>
          <article className="selection-rubric" key={item.id}>
            <Record name={`${cycleName(item.selection_cycle_id)} · ${text.version} ${item.version_number}`}
              detail={item.state === "published" ? text.published : `${item.criteria.reduce((sum, criterion) => sum + criterion.weight, 0)}%`} state={item.state} />
            {item.state === "draft" && canManageRubric
              ? <RubricEditor rubric={item} locale={locale} busy={busy}
                  onSave={(criteria) => run(() => request(`${root}/rubrics/${item.id}`, "PUT", {
                    expected_edit_version: item.edit_version, criteria,
                  }))}
                  onPublish={canPublish ? () => run(() => request(`${root}/rubrics/${item.id}/publish`, "POST", {
                    expected_edit_version: item.edit_version,
                  })) : undefined} />
              : <ol className="selection-criteria">{item.criteria.map((criterion) =>
                  <li key={criterion.id}><strong>{locale === "ta" ? criterion.label_ta : criterion.label_en}</strong><span>{criterion.weight}% · {criterion.minimum_score}–{criterion.maximum_score}</span></li>
                )}</ol>}
            {item.state !== "draft" && canManageRubric &&
              !workspace.rubrics.some((rubric) => rubric.selection_cycle_id === item.selection_cycle_id && rubric.state === "draft") &&
              <button disabled={busy} onClick={() => void run(() => request(`${root}/rubrics/${item.id}/copy`, "POST", {}))}>{text.copy}</button>}
          </article>
        )}</div>
        {!workspace.rubrics.length && <p>{text.empty}</p>}
      </section>

      {canAssign && <section className="program-panel program-wide">
        <h2>{text.aggregates}</h2>
        <ul className="program-list">{workspace.aggregates.map((item) => <li key={`${item.selection_cycle_id}-${item.application_id}`}>
          <Record name={item.application_number} detail={`${cycleName(item.selection_cycle_id)} · ${item.included_reviews}/${item.completed_reviews} ${text.includedReviews}`} state={item.aggregate_score === null ? "pending" : "completed"} />
          <strong>{text.aggregateScore}: {item.aggregate_score === null ? text.notAvailable : Number(item.aggregate_score).toFixed(2)}</strong>
          {item.excluded_reviews > 0 && <small>{item.excluded_reviews} {text.excludedReviews}</small>}          <div className="program-actions">
            {item.application_state === "under_review" && canDecide && <button disabled={busy || item.aggregate_score === null} onClick={() => decide(item, "shortlisted")}>{text.shortlist}</button>}
            {item.application_state === "interview_scheduled" && workspace.interviews.some((interview) => interview.application_id === item.application_id && interview.status === "completed") && canFinalize && <>
              <button disabled={busy} onClick={() => decide(item, "selected")}>{text.select}</button>
              <button disabled={busy} onClick={() => decide(item, "waitlisted")}>{text.waitlist}</button>
              <button disabled={busy} onClick={() => decide(item, "rejected")}>{text.reject}</button>
            </>}
            {["selected", "waitlisted", "rejected"].includes(item.application_state) && canOverride && <>
              {item.application_state !== "selected" && <button disabled={busy} onClick={() => decide(item, "selected", true)}>{text.overrideSelect}</button>}
              {item.application_state !== "waitlisted" && <button disabled={busy} onClick={() => decide(item, "waitlisted", true)}>{text.overrideWaitlist}</button>}
              {item.application_state !== "rejected" && <button disabled={busy} onClick={() => decide(item, "rejected", true)}>{text.overrideReject}</button>}
            </>}
          </div>
        </li>)}</ul>
        {!workspace.aggregates.length && <p>{text.empty}</p>}
      </section>}
      {(canManageInterview || canScoreInterview) && <section className="program-panel program-wide">
        <h2>{text.interviews}</h2>
        {canManageInterview && <form className="program-form selection-interview-form" onSubmit={scheduleInterview}>
          <Select label={text.application} name="application_id" choose={text.choose}
            options={workspace.aggregates.filter((item) => item.application_state === "shortlisted" && !workspace.interviews.some((interview) => interview.application_id === item.application_id)).map((item) => [item.application_id, item.application_number])} />
          <Select label={text.cycles} name="selection_cycle_id" choose={text.choose}
            options={workspace.cycles.filter((item) => item.state === "active").map((item) => [item.id, locale === "ta" ? item.name_ta : item.name_en])} />
          <label>{text.startsAt}<input type="datetime-local" name="starts_at" required /></label>
          <label>{text.endsAt}<input type="datetime-local" name="ends_at" required /></label>
          <label>{text.mode}<select name="mode" required><option value="online">{text.online}</option><option value="in_person">{text.inPerson}</option></select></label>
          <Field label={text.location} name="location" required={false} />
          <label>{text.panelMembers}<select name="panel_user_ids" required multiple size={Math.min(5, Math.max(2, workspace.reviewers.length))}>
            {workspace.reviewers.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}
          </select></label>
          <button disabled={busy}>{text.scheduleInterview}</button>
        </form>}
        <ul className="program-list">{workspace.interviews.map((interview) => {
          const member = interview.panel.find((item) => item.user_id === actor);
          const allScored = interview.panel.every((item) => item.submitted_at !== null);
          return <li key={interview.id}>
            <Record name={interview.application_number} detail={`${new Date(interview.starts_at).toLocaleString(locale)} · ${interview.mode === "online" ? text.online : text.inPerson}`} state={interview.status} />
            <p>{text.panelMembers}: {interview.panel.map((item) => item.display_name).join(", ")}</p>
            {interview.average_score !== null && <strong>{text.interviewScore}: {Number(interview.average_score).toFixed(2)}</strong>}
            {canScoreInterview && member && !member.submitted_at && interview.status === "scheduled" && <form className="program-form" onSubmit={(event) => submitPanelScore(event, interview)}>
              <label>{text.interviewScore}<input name="score" type="number" min="0" max="100" step="0.01" required /></label>
              <label>{text.panelComment}<textarea name="comment" maxLength={4000} /></label>
              <button disabled={busy}>{text.submitInterviewScore}</button>
            </form>}
            {member?.submitted_at && <p>{text.scoreSubmitted}</p>}
            {canManageInterview && interview.status === "scheduled" && <button disabled={busy || !allScored} onClick={() => completeInterview(interview)}>{text.completeInterview}</button>}
          </li>;
        })}</ul>
        {!workspace.interviews.length && <p>{text.empty}</p>}
      </section>}

      {canAssign && <section className="program-panel program-wide">
        <h2>{text.decisionHistory}</h2>
        <ul className="program-list">{workspace.decisions.map((item) => <li key={item.id}>
          <Record name={item.application_number} detail={`${item.from_state} → ${item.to_state}`} state={item.is_override ? "override" : item.to_state} />
          <p>{item.reason}</p>
          <small>{text.reviewScore}: {item.aggregate_score_snapshot ?? text.notAvailable} · {text.interviewScore}: {item.interview_score_snapshot ?? text.notAvailable}</small>
        </li>)}</ul>
        {!workspace.decisions.length && <p>{text.empty}</p>}
      </section>}
      {canReview && <section className="program-panel program-wide">
        <h2>{text.inbox}</h2>
        <ul className="program-list">{workspace.assignments.filter((item) => item.reviewer_user_id === actor).map((item) =>
          <li key={item.id}>
            <Record name={item.application_number} detail={cycleName(item.selection_cycle_id)} state={item.status} />
            <p>{item.conflict_status === "pending" ? text.pendingConflict : item.conflict_status === "clear" ? text.noConflict : text.conflictDeclared}</p>
            {item.conflict_status === "pending" && <div className="program-actions">
              <button onClick={() => declareConflict(item, "clear")}>{text.clear}</button>
              <button className="danger-button" onClick={() => declareConflict(item, "conflict")}>{text.conflict}</button>
            </div>}
            {item.conflict_status === "clear" && <ReviewEditor
              assignment={item}
              rubric={workspace.rubrics.find((rubric) => rubric.id === item.rubric_id)}
              locale={locale}
              busy={busy}
              onSave={(scores, internal_comment) => run(() => request(`${root}/assignments/${item.id}/review`, "PUT", {
                expected_version: item.version, scores, internal_comment,
              }))}
              onSubmit={() => run(() => request(`${root}/assignments/${item.id}/submit`, "POST", {
                expected_version: item.version,
              }))}
            />}
          </li>
        )}</ul>
        {!workspace.assignments.some((item) => item.reviewer_user_id === actor) && <p>{text.empty}</p>}
      </section>}
    </div>
  </div>;
}


function ReviewEditor({ assignment, rubric, locale, busy, onSave, onSubmit }: {
  assignment: Assignment; rubric?: Rubric; locale: Locale; busy: boolean;
  onSave: (scores: { criterion_id: string; score: number }[], comment: string | null) => Promise<void>;
  onSubmit: () => Promise<void>;
}) {
  const text = selectionMessages[locale];
  const [scores, setScores] = useState<Record<string, string>>(() => Object.fromEntries(
    assignment.scores.map((item) => [item.criterion_id, item.score])
  ));
  const [comment, setComment] = useState(assignment.internal_comment ?? "");
  if (!rubric) return <p>{text.rubricUnavailable}</p>;
  if (assignment.status === "completed") return <div className="selection-result">
    <strong>{text.weightedScore}: {Number(assignment.weighted_score).toFixed(2)}</strong>
    <p>{text.submittedReview}</p>
    {assignment.internal_comment && <p>{text.internalComment}: {assignment.internal_comment}</p>}
  </div>;
  const complete = rubric.criteria.filter((item) => item.required).every((item) =>
    assignment.scores.some((score) => score.criterion_id === item.id)
  );
  const payload = Object.entries(scores).filter(([, value]) => value !== "").map(([criterion_id, score]) => ({ criterion_id, score: Number(score) }));
  return <div className="selection-review-editor">
    {rubric.criteria.map((criterion) => <label key={criterion.id}>
      <span>{locale === "ta" ? criterion.label_ta : criterion.label_en} <small>{criterion.weight}% · {criterion.minimum_score}–{criterion.maximum_score}</small></span>
      <input type="number" min={criterion.minimum_score} max={criterion.maximum_score} step="0.01"
        required={criterion.required} value={scores[criterion.id] ?? ""}
        onChange={(event) => setScores((current) => ({ ...current, [criterion.id]: event.target.value }))} />
    </label>)}
    <label>{text.internalComment}<textarea maxLength={4000} value={comment} onChange={(event) => setComment(event.target.value)} /></label>
    <div className="program-actions">
      <button disabled={busy} onClick={() => void onSave(payload, comment.trim() || null)}>{text.saveDraft}</button>
      <button disabled={busy || !complete} onClick={() => void onSubmit()}>{text.submitReview}</button>
    </div>
  </div>;
}
function RubricEditor({ rubric, locale, busy, onSave, onPublish }: {
  rubric: Rubric; locale: Locale; busy: boolean;
  onSave: (criteria: Criterion[]) => Promise<void>;
  onPublish?: () => Promise<void>;
}) {
  const text = selectionMessages[locale];
  const [criteria, setCriteria] = useState<Criterion[]>(
    rubric.criteria.length ? rubric.criteria.map((item) => ({
      key: item.key, label_en: item.label_en, label_ta: item.label_ta,
      guidance_en: item.guidance_en, guidance_ta: item.guidance_ta,
      weight: item.weight, minimum_score: item.minimum_score,
      maximum_score: item.maximum_score, required: item.required,
    })) : [newCriterion()]
  );
  const total = criteria.reduce((sum, item) => sum + Number(item.weight), 0);
  const change = <K extends keyof Criterion>(index: number, key: K, value: Criterion[K]) =>
    setCriteria((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item));

  return <div className="selection-editor">
    {criteria.map((item, index) => <div className="selection-criterion-editor" key={index}>
      <Field label={text.criterionKey} name={`key-${index}`} value={item.key} onChange={(value) => change(index, "key", value)} />
      <Field label={text.englishLabel} name={`en-${index}`} value={item.label_en} onChange={(value) => change(index, "label_en", value)} />
      <Field label={text.tamilLabel} name={`ta-${index}`} value={item.label_ta} onChange={(value) => change(index, "label_ta", value)} />
      <NumberField label={text.weight} value={item.weight} min={1} max={100} onChange={(value) => change(index, "weight", value)} />
      <NumberField label={text.minimum} value={item.minimum_score} min={0} max={99} onChange={(value) => change(index, "minimum_score", value)} />
      <NumberField label={text.maximum} value={item.maximum_score} min={1} max={100} onChange={(value) => change(index, "maximum_score", value)} />
      {criteria.length > 1 && <button type="button" onClick={() => setCriteria((current) => current.filter((_, itemIndex) => itemIndex !== index))}>{text.remove}</button>}
    </div>)}
    <p className={total === 100 ? "selection-total valid" : "selection-total"}>{total}% · {text.weights}</p>
    <div className="program-actions">
      <button type="button" onClick={() => setCriteria((current) => [...current, { ...newCriterion(), weight: 1 }])}>{text.addCriterion}</button>
      <button type="button" disabled={busy || total !== 100} onClick={() => void onSave(criteria)}>{text.save}</button>
      {onPublish && rubric.criteria.length > 0 && <button type="button" disabled={busy} onClick={() => void onPublish()}>{text.publish}</button>}
    </div>
  </div>;
}

function Field({ label, name, value, onChange, required = true }: {
  label: string; name: string; value?: string; onChange?: (value: string) => void; required?: boolean;
}) {
  return <label>{label}<input name={name} required={required} value={value} onChange={onChange ? (event) => onChange(event.target.value) : undefined} /></label>;
}

function NumberField({ label, value, min, max, onChange }: {
  label: string; value: number; min: number; max: number; onChange: (value: number) => void;
}) {
  return <label>{label}<input type="number" required min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

function Select({ label, name, options, choose }: {
  label: string; name: string; options: [string, string][]; choose: string;
}) {
  return <label>{label}<select name={name} required><option value="">{choose}</option>{options.map(([value, labelText]) => <option key={value} value={value}>{labelText}</option>)}</select></label>;
}

function Record({ name, detail, state }: { name: string; detail: string; state: string }) {
  return <div className="program-record"><div><strong>{name}</strong><small>{detail}</small></div><span className={`program-state program-state-${state}`}>{state}</span></div>;
}