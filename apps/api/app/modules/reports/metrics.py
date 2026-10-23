"""SQL-only operational rollups; no participant rows leave this module."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.definitions import operational_metric_definitions
from app.modules.reports.schemas import ReportBreakdown, ReportMetric

# Membership is deliberately not date-filtered: each metric selects its own dated
# facts. EXISTS/IN on unique identifiers prevents multi-enrollment join fan-out.
SCOPE_SQL = """
WITH scoped_enrollments AS (
 SELECT e.* FROM enrollments e
 WHERE e.organization_id = :organization_id
   AND (CAST(:program_id AS uuid) IS NULL OR e.program_id = :program_id)
   AND (CAST(:cohort_id AS uuid) IS NULL OR e.cohort_id = :cohort_id)
), scoped_courses AS (
 SELECT ce.* FROM course_enrollments ce
 WHERE ce.organization_id = :organization_id
 AND ce.enrollment_id IN (SELECT id FROM scoped_enrollments)
)
"""

APPLICATION_SQL = """
SELECT count(*) AS applications,
 count(*) FILTER (WHERE a.state IN ('selected','enrolled')) AS selected,
 count(*) FILTER (WHERE a.state IN ('selected','enrolled') AND EXISTS (
   SELECT 1 FROM scoped_enrollments e WHERE e.application_id = a.id
 )) AS enrolled
FROM applications a
WHERE a.organization_id = :organization_id
 AND a.submitted_at >= :start_at AND a.submitted_at < :end_at
 AND ((CAST(:program_id AS uuid) IS NULL AND CAST(:cohort_id AS uuid) IS NULL)
 OR EXISTS (SELECT 1 FROM application_cycles c WHERE c.id = a.cycle_id
   AND c.organization_id = :organization_id
   AND (CAST(:program_id AS uuid) IS NULL OR c.program_id = :program_id)
   AND (CAST(:cohort_id AS uuid) IS NULL OR c.cohort_id = :cohort_id)))
"""

LATEST_BUSINESS_SQL = """
, ranked_outcomes AS (
 SELECT o.*, row_number() OVER (
   PARTITION BY p.enrollment_id ORDER BY o.reported_on DESC, o.created_at DESC, o.id DESC
 ) AS position
 FROM business_outcome_snapshots o
 JOIN business_follow_ups f ON f.id = o.follow_up_id AND f.organization_id = o.organization_id
 JOIN business_profiles p ON p.id = f.profile_id AND p.organization_id = f.organization_id
 WHERE o.organization_id = :organization_id
 AND p.enrollment_id IN (SELECT id FROM scoped_enrollments)
 AND o.reported_on >= :from_date AND o.reported_on <= :through_date
)
SELECT count(*) AS reported,
 count(*) FILTER (WHERE business_started) AS started,
 count(*) FILTER (WHERE business_active) AS active,
 coalesce(sum(jobs_created),0) AS jobs
FROM ranked_outcomes WHERE position = 1
"""


def build_operational_metrics(
    db: Session,
    organization_id: UUID,
    *,
    from_date: date,
    through_date: date,
    program_id: UUID | None = None,
    cohort_id: UUID | None = None,
) -> list[ReportMetric]:
    """Return complete aggregates in 18 SELECTs (15 with program/cohort scope).

    The caller validates authorization/filter identities and owns the transaction.
    A snapshot caller must use a coherent REPEATABLE READ transaction.
    """
    params: dict[str, Any] = {
        "organization_id": organization_id,
        "program_id": program_id,
        "cohort_id": cohort_id,
        "from_date": from_date,
        "through_date": through_date,
        "start_at": datetime.combine(from_date, time.min, UTC),
        "end_at": datetime.combine(through_date + timedelta(days=1), time.min, UTC),
    }
    metrics = {item.key: item for item in operational_metric_definitions()}

    def query(sql: str) -> dict[str, Any]:
        return dict(db.execute(text(SCOPE_SQL + sql), params).mappings().one())

    def count(key: str, value: Any) -> None:
        metrics[key].numerator = float(value)
        metrics[key].value = float(value)

    def ratio(key: str, numerator: Any, denominator: Any, *, scale: float = 100) -> None:
        metric = metrics[key]
        metric.numerator = float(numerator)
        metric.denominator = float(denominator)
        metric.value = (
            round(float(numerator) / float(denominator) * scale, 4) if denominator else None
        )

    if program_id is None and cohort_id is None:
        row = query("""
SELECT count(*) AS leads,
 count(*) FILTER (WHERE EXISTS (
   SELECT 1 FROM crm_lead_conversions c
   WHERE c.lead_id = l.id AND c.organization_id = :organization_id
   AND EXISTS (SELECT 1 FROM applications a
     WHERE a.person_id = c.person_id AND a.organization_id = :organization_id
     AND a.submitted_at IS NOT NULL)
 )) AS applied
FROM crm_leads l WHERE l.organization_id = :organization_id
 AND l.merged_into_id IS NULL AND l.status <> 'merged'
 AND l.created_at >= :start_at AND l.created_at < :end_at
""")
        count("leads", row["leads"])
        ratio("lead_to_application_percent", row["applied"], row["leads"])
        # One canonical first conversion per person makes registration attribution
        # and its source/campaign breakdown reconcile even with several lead links.
        for source, metric_key, population in (
            ("crm_leads", "leads", "merged_into_id IS NULL AND status <> 'merged'"),
            (
                "(SELECT DISTINCT ON (person_id) * FROM crm_lead_conversions "
                "WHERE organization_id = :organization_id ORDER BY person_id,created_at,id)",
                "registrations",
                "true",
            ),
        ):
            rows = (
                db.execute(
                    text(
                        SCOPE_SQL
                        + f"""
, population AS (
 SELECT * FROM {source} x WHERE organization_id = :organization_id
 AND {population} AND created_at >= :start_at AND created_at < :end_at
), dimensions AS (
 SELECT 'source' AS dimension, coalesce(nullif(source,''),'Unspecified') AS label FROM population
 UNION ALL
 SELECT 'campaign', coalesce(nullif(campaign,''),'Unspecified') FROM population
), grouped AS (
 SELECT dimension,label,count(*) AS n FROM dimensions GROUP BY dimension,label
), ranked AS (
 SELECT *,row_number() OVER (PARTITION BY dimension ORDER BY n DESC,label) AS position
 FROM grouped
)
SELECT dimension, CASE WHEN position <= 8 THEN label ELSE 'Other' END AS label,
 sum(n) AS count, min(position) AS position
FROM ranked GROUP BY dimension,CASE WHEN position <= 8 THEN label ELSE 'Other' END
ORDER BY dimension,position
"""
                    ),
                    params,
                )
                .mappings()
                .all()
            )
            metric = metrics[metric_key]
            metric.breakdown = [
                ReportBreakdown(
                    key=f"{r['dimension']}:{r['label']}",
                    label=f"{r['dimension']}: {r['label']}",
                    count=int(r["count"]),
                )
                for r in rows
            ]
            if metric_key == "registrations":
                count(metric_key, sum(r["count"] for r in rows if r["dimension"] == "source"))
    else:
        for key in ("leads", "registrations", "lead_to_application_percent"):
            metrics[key].caveat_en = (
                "Unavailable for program/cohort filters: unconverted leads and registration "
                "attribution have no reliable program/cohort assignment. Use organization scope."
            )
            metrics[key].caveat_ta = (
                "திட்டம்/குழு வடிகட்டலில் கிடைக்காது: மாற்றப்படாத தொடர்புகள் மற்றும் பதிவு மூலங்களுக்கு "
                "நம்பகமான திட்டம்/குழு ஒதுக்கீடு இல்லை. நிறுவன வரம்பைப் பயன்படுத்தவும்."
            )

    row = query(APPLICATION_SQL)
    count("applications", row["applications"])
    count("selected_applications", row["selected"])
    ratio("application_to_selection_percent", row["selected"], row["applications"])
    ratio("selection_to_enrollment_percent", row["enrolled"], row["selected"])

    row = query("""
SELECT count(*) AS enrollments,
 count(*) FILTER (WHERE status = 'withdrawn') AS withdrawn,
 count(*) FILTER (WHERE status = 'completed') AS completed,
 count(DISTINCT participant_id) FILTER (WHERE status = 'active' AND EXISTS (
 SELECT 1 FROM participants p WHERE p.id = participant_id
 AND p.organization_id = :organization_id AND p.status = 'active')) AS active
FROM scoped_enrollments WHERE enrolled_at >= :start_at AND enrolled_at < :end_at
""")
    for key, column in (
        ("enrollments", "enrollments"),
        ("active_participants", "active"),
        ("withdrawn_enrollments", "withdrawn"),
        ("completed_enrollments", "completed"),
    ):
        count(key, row[column])
    row = query("""
SELECT count(*) AS n FROM certificates c WHERE c.organization_id = :organization_id
AND c.course_enrollment_id IN (SELECT id FROM scoped_courses)
AND c.issued_at >= :start_at AND c.issued_at < :end_at AND c.status = 'valid'
""")
    count("valid_certificates", row["n"])

    row = query("""
SELECT count(*) FILTER (WHERE started_at >= :start_at AND started_at < :end_at) AS started,
 count(*) FILTER (WHERE completed_at >= :start_at AND completed_at < :end_at) AS completed
FROM scoped_courses
""")
    count("course_starts", row["started"])
    count("course_completions", row["completed"])
    row = query("""
SELECT count(*) AS n FROM lesson_progress p WHERE p.organization_id = :organization_id
AND p.course_enrollment_id IN (SELECT id FROM scoped_courses)
AND p.completed_at >= :start_at AND p.completed_at < :end_at
""")
    count("lesson_completions", row["n"])
    row = query("""
SELECT count(*) AS n,count(*) FILTER (WHERE passed) AS passed,coalesce(sum(percent),0) AS scores
FROM quiz_attempts q WHERE q.organization_id = :organization_id
AND q.course_enrollment_id IN (SELECT id FROM scoped_courses)
AND q.submitted_at >= :start_at AND q.submitted_at < :end_at
""")
    count("quiz_attempts", row["n"])
    ratio("quiz_pass_percent", row["passed"], row["n"])
    ratio("quiz_mean_percent", row["scores"], row["n"], scale=1)
    row = query("""
, submissions AS (
 SELECT * FROM assignment_submissions s WHERE s.organization_id = :organization_id
 AND s.course_enrollment_id IN (SELECT id FROM scoped_courses)
), grades AS (
 SELECT g.* FROM assignment_grades g WHERE g.organization_id = :organization_id
 AND g.submission_id IN (SELECT id FROM submissions)
 AND g.graded_at >= :start_at AND g.graded_at < :end_at
)
SELECT (SELECT count(*) FROM submissions WHERE submitted_at >= :start_at
 AND submitted_at < :end_at) AS submitted,
 count(*) AS graded,count(*) FILTER (WHERE passed) AS passed FROM grades
""")
    count("assignment_submissions", row["submitted"])
    count("assignment_grades", row["graded"])
    ratio("assignment_pass_percent", row["passed"], row["graded"])
    row = query("""
SELECT count(*) FILTER (WHERE r.status IN ('present','late','absent')) AS marked,
 count(*) FILTER (WHERE r.status IN ('present','late')) AS attending
FROM attendance_records r
JOIN program_sessions s ON s.id = r.session_id AND s.organization_id = r.organization_id
WHERE r.organization_id = :organization_id
AND r.enrollment_id IN (SELECT id FROM scoped_enrollments)
AND s.starts_at >= :start_at AND s.starts_at < :end_at
""")
    count("attendance_recorded", row["marked"])
    ratio("attendance_percent", row["attending"], row["marked"])

    row = query("""
SELECT count(*) AS n FROM business_profiles p WHERE p.organization_id = :organization_id
AND p.enrollment_id IN (SELECT id FROM scoped_enrollments) AND p.stage = 'idea'
AND p.created_at >= :start_at AND p.created_at < :end_at
""")
    count("idea_profiles", row["n"])
    row = query("""
, plans AS (
 SELECT p.id FROM business_plans p WHERE p.organization_id = :organization_id
 AND p.enrollment_id IN (SELECT id FROM scoped_enrollments)
), submissions AS (
 SELECT s.* FROM business_plan_submissions s WHERE s.organization_id = :organization_id
 AND s.plan_id IN (SELECT id FROM plans)
)
SELECT (SELECT count(DISTINCT plan_id) FROM submissions WHERE created_at >= :start_at
 AND created_at < :end_at) AS submitted,
 (SELECT count(DISTINCT s.plan_id) FROM business_plan_reviews r
 JOIN submissions s ON s.id = r.submission_id WHERE r.organization_id = :organization_id
 AND r.decision = 'approved' AND r.created_at >= :start_at AND r.created_at < :end_at) AS approved
""")
    count("submitted_plans", row["submitted"])
    count("approved_plans", row["approved"])
    row = query(LATEST_BUSINESS_SQL)
    for key, column in (
        ("business_outcome_reports", "reported"),
        ("businesses_started", "started"),
        ("businesses_active", "active"),
        ("jobs_created", "jobs"),
    ):
        count(key, row[column])

    row = query("""
SELECT count(DISTINCT h.case_id) FILTER (WHERE h.status = 'applied') AS applied,
 count(DISTINCT h.case_id) FILTER (WHERE h.status = 'approved') AS approved,
 count(DISTINCT h.case_id) FILTER (WHERE h.status = 'disbursed') AS disbursed
FROM funding_history h JOIN funding_cases c
 ON c.id = h.case_id AND c.organization_id = h.organization_id
WHERE h.organization_id = :organization_id AND EXISTS (
 SELECT 1 FROM scoped_enrollments e WHERE e.participant_id = c.participant_id)
AND h.created_at >= :start_at AND h.created_at < :end_at
""")
    for status in ("applied", "approved", "disbursed"):
        count(f"funding_{status}_cases", row[status])

    row = query("""
, tickets AS (
 SELECT t.id,t.created_at,(SELECT min(h.created_at) FROM helpdesk_history h
 WHERE h.ticket_id = t.id AND h.organization_id = :organization_id
 AND h.status = 'resolved') AS resolved_at
 FROM helpdesk_tickets t WHERE t.organization_id = :organization_id
 AND t.created_at >= :start_at AND t.created_at < :end_at
 AND EXISTS (SELECT 1 FROM scoped_enrollments e WHERE e.participant_id = t.owner_participant_id)
)
SELECT count(*) AS tickets,
 count(*) FILTER (WHERE resolved_at >= created_at) AS resolved,
 coalesce(sum(extract(epoch FROM resolved_at-created_at)/3600)
 FILTER (WHERE resolved_at >= created_at),0) AS hours FROM tickets
""")
    count("tickets_created", row["tickets"])
    count("tickets_resolved", row["resolved"])
    ratio("ticket_resolution_hours", row["hours"], row["resolved"], scale=1)
    row = query("""
SELECT count(*) AS n FROM mentoring_sessions s
JOIN mentor_assignments a ON a.id = s.assignment_id AND a.organization_id = s.organization_id
WHERE s.organization_id = :organization_id
AND a.enrollment_id IN (SELECT id FROM scoped_enrollments)
AND s.completed_at >= :start_at AND s.completed_at < :end_at
""")
    count("mentor_sessions", row["n"])
    rows = (
        db.execute(
            text(
                SCOPE_SQL
                + """
SELECT 'mentor' AS kind,f.state AS status,count(*) AS n FROM mentoring_follow_ups f
JOIN mentor_assignments a ON a.id = f.assignment_id AND a.organization_id = f.organization_id
WHERE f.organization_id = :organization_id
AND a.enrollment_id IN (SELECT id FROM scoped_enrollments)
AND f.due_at >= :start_at AND f.due_at < :end_at GROUP BY f.state
UNION ALL
SELECT 'business',f.status,count(*) FROM business_follow_ups f
JOIN business_profiles p ON p.id = f.profile_id AND p.organization_id = f.organization_id
WHERE f.organization_id = :organization_id
AND p.enrollment_id IN (SELECT id FROM scoped_enrollments)
AND f.due_on >= :from_date AND f.due_on <= :through_date GROUP BY f.status
ORDER BY kind,status
"""
            ),
            params,
        )
        .mappings()
        .all()
    )
    for kind in ("mentor", "business"):
        key = f"{kind}_follow_ups"
        selected_rows = [r for r in rows if r["kind"] == kind]
        count(key, sum(r["n"] for r in selected_rows))
        metrics[key].breakdown = [
            ReportBreakdown(key=r["status"], label=r["status"], count=r["n"]) for r in selected_rows
        ]
    return list(metrics.values())
