"""Generate the implemented EDP platform flow PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "flows" / "edp-implemented-code-flow.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#17243A")
TEAL = colors.HexColor("#0F766E")
COPPER = colors.HexColor("#C97945")
INK = colors.HexColor("#243244")
MUTED = colors.HexColor("#64748B")
PALE = colors.HexColor("#F3F6F8")
PALE_TEAL = colors.HexColor("#E7F4F1")
PALE_COPPER = colors.HexColor("#FAEEE6")
GREEN = colors.HexColor("#18794E")
RED = colors.HexColor("#B5473C")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=32,
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12.5,
        leading=18,
        textColor=colors.HexColor("#DCE6EE"),
    )
)
styles.add(
    ParagraphStyle(
        name="H1x",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="H2x",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=TEAL,
        spaceBefore=7,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Bodyx",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.6,
        leading=12.1,
        textColor=INK,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Smallx",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.4,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="Tiny",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.2,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="Callout",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=13,
        textColor=NAVY,
        backColor=PALE_TEAL,
        borderColor=TEAL,
        borderWidth=0.6,
        borderPadding=8,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Status",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=GREEN,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHead",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.6,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCellBold",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8.6,
        textColor=INK,
    )
)


def P(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [Paragraph("? " + item, styles["Bodyx"]) for item in items]


def table(headers, rows, widths, header_color=NAVY):
    data = [[P(x, "TableHead") for x in headers]]
    for row in rows:
        data.append([P(str(x), "TableCell") for x in row])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD5DD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


class HorizontalFlow(Flowable):
    def __init__(
        self, labels, width=174 * mm, height=35 * mm, colors_=None, subtitle=None
    ):
        super().__init__()
        self.labels = labels
        self.width = width
        self.height = height
        self.colors = colors_ or [TEAL, NAVY, COPPER]
        self.subtitle = subtitle

    def draw(self):
        c = self.canv
        n = len(self.labels)
        gap = 5 * mm
        box = (self.width - gap * (n - 1)) / n
        y = 8 * mm
        for i, label in enumerate(self.labels):
            x = i * (box + gap)
            fill = self.colors[i % len(self.colors)]
            c.setFillColor(fill)
            c.roundRect(x, y, box, 20 * mm, 3 * mm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            words = label.split()
            lines = []
            line = ""
            for word in words:
                trial = (line + " " + word).strip()
                if c.stringWidth(trial, "Helvetica-Bold", 7.5) > box - 6 * mm and line:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            if line:
                lines.append(line)
            start = y + 12 * mm + (len(lines) - 1) * 2.1 * mm
            for j, text in enumerate(lines):
                c.drawCentredString(x + box / 2, start - j * 4.2 * mm, text)
            if i < n - 1:
                ax = x + box + 1 * mm
                ay = y + 10 * mm
                c.setStrokeColor(MUTED)
                c.setLineWidth(1.2)
                c.line(ax, ay, ax + 3 * mm, ay)
                c.line(ax + 3 * mm, ay, ax + 1.8 * mm, ay + 1.2 * mm)
                c.line(ax + 3 * mm, ay, ax + 1.8 * mm, ay - 1.2 * mm)
        if self.subtitle:
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.8)
            c.drawCentredString(self.width / 2, 2.5 * mm, self.subtitle)


class LayerStack(Flowable):
    def __init__(self, layers, width=174 * mm, height=57 * mm):
        super().__init__()
        self.layers = layers
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        h = 9.5 * mm
        gap = 2 * mm
        y = self.height - h
        palette = [
            NAVY,
            TEAL,
            COPPER,
            colors.HexColor("#52677C"),
            colors.HexColor("#758A9C"),
        ]
        for i, (name, detail) in enumerate(self.layers):
            c.setFillColor(palette[i % len(palette)])
            c.roundRect(0, y, self.width, h, 2 * mm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(4 * mm, y + 5.7 * mm, name)
            c.setFont("Helvetica", 6.7)
            c.drawRightString(self.width - 4 * mm, y + 5.7 * mm, detail)
            y -= h + gap


class Lifecycle(Flowable):
    def __init__(self, rows, width=174 * mm, height=63 * mm):
        super().__init__()
        self.rows = rows
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        y = self.height - 12 * mm
        for title, states, color in self.rows:
            c.setFont("Helvetica-Bold", 7.2)
            c.setFillColor(NAVY)
            c.drawString(0, y + 3 * mm, title)
            start = 34 * mm
            available = self.width - start
            gap = 2.2 * mm
            bw = (available - gap * (len(states) - 1)) / len(states)
            for i, state in enumerate(states):
                x = start + i * (bw + gap)
                c.setFillColor(color)
                c.roundRect(x, y, bw, 8 * mm, 1.5 * mm, fill=1, stroke=0)
                c.setFillColor(WHITE)
                c.setFont("Helvetica-Bold", 5.5)
                c.drawCentredString(x + bw / 2, y + 3 * mm, state)
                if i < len(states) - 1:
                    c.setStrokeColor(MUTED)
                    c.line(
                        x + bw + 0.4 * mm,
                        y + 4 * mm,
                        x + bw + gap - 0.4 * mm,
                        y + 4 * mm,
                    )
            y -= 13 * mm


def header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor("#D7DEE5"))
        canvas.line(18 * mm, 15 * mm, 192 * mm, 15 * mm)
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            18 * mm, 10 * mm, "EDP Digital | Implemented code flow | commit 3f70069"
        )
        canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(
            path,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=17 * mm,
            bottomMargin=20 * mm,
            title="EDP Digital - Implemented Code Flow",
            author="EDP Digital Engineering",
        )
        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height, id="main"
        )
        self.addPageTemplates(
            PageTemplate(id="standard", frames=frame, onPage=header_footer)
        )


story = []
# Cover
cover = Table(
    [
        [P("EDP DIGITAL PLATFORM", "CoverSub")],
        [P("Implemented Code Flow", "CoverTitle")],
        [
            P(
                "Product, architecture, security, data and operational flows completed through P01.2",
                "CoverSub",
            )
        ],
    ],
    colWidths=[174 * mm],
    rowHeights=[18 * mm, 40 * mm, 35 * mm],
)
cover.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm),
        ]
    )
)
story += [
    Spacer(1, 20 * mm),
    cover,
    Spacer(1, 10 * mm),
    P("BASELINE", "H2x"),
    table(
        ["Repository", "Branch", "Commit", "Prepared"],
        [["viviztech/edp-digital", "main", "3f70069", "24 September 2026"]],
        [55 * mm, 25 * mm, 35 * mm, 45 * mm],
        TEAL,
    ),
    Spacer(1, 7 * mm),
    P("Purpose", "H2x"),
    P(
        "This document explains how the code implemented to date works as connected user and system flows. It separates completed behavior from release gates and future modules. It is a technical-product handoff for review, onboarding and planning."
    ),
    Spacer(1, 5 * mm),
    P("Current implemented journey", "H2x"),
    HorizontalFlow(
        [
            "Public discovery",
            "Identity and access",
            "Application",
            "Selection",
            "Enrollment",
            "Participant schedule",
        ],
        subtitle="English/Tamil web experiences backed by FastAPI, PostgreSQL, Redis and Celery",
    ),
    PageBreak(),
]

# Executive map
story += [
    P("1. Implemented capability map", "H1x"),
    P(
        "The platform is a modular monolith. Each vertical slice includes database constraints, service rules, scoped APIs, web/mobile surfaces where implemented, audit evidence and tests."
    ),
    table(
        ["Area", "Completed code flow", "Primary users"],
        [
            (
                "Foundation",
                "Registration, verification, login, refresh rotation, reset, session revocation, scoped RBAC and immutable audit",
                "All users; operators",
            ),
            (
                "CMS and public",
                "Localized pages, editorial content, navigation, SEO, quarantined asset metadata and privacy-safe enquiries",
                "Visitors; Content Managers",
            ),
            (
                "CRM",
                "Attributed leads, assignments, activities, tags, overdue queue, duplicate review/merge, registration link and permissioned CSV exports",
                "CRM Executives; Managers",
            ),
            (
                "Meta integration",
                "Verified webhook inbox, encrypted configuration, mapping, worker claims, recovery/replay and retention enforcement",
                "Marketing; Operations",
            ),
            (
                "Communications",
                "In-app assignment and due reminders, preferences, retention, bounded retries and audited operator replay",
                "Staff recipients; Operations",
            ),
            (
                "Applications",
                "Versioned bilingual definitions, applicant drafts, required answers, declarations/consent, immutable submission and receipt",
                "Applicants; Program staff",
            ),
            (
                "Programs and selection",
                "Programs/centers/cohorts/cycles, rubric/reviews, interviews, decisions, authorized overrides and finalization",
                "Program staff; Reviewers",
            ),
            (
                "Participants",
                "Atomic selected-to-enrolled conversion, participant projection, sessions and self-scoped schedule/timeline",
                "Program staff; Participants",
            ),
        ],
        [34 * mm, 102 * mm, 38 * mm],
    ),
    Spacer(1, 6 * mm),
    P("Completion statement", "H2x"),
    P(
        "The end-to-end synthetic browser journey now reaches enrolled participant and scheduled program session. Learning, attendance, mentoring, funding, support, reporting and production operations remain later work."
    ),
    PageBreak(),
]

# Architecture
story += [
    P("2. Runtime and request flow", "H1x"),
    LayerStack(
        [
            (
                "Clients",
                "Next.js public, applicant, staff and participant web; Flutter auth/public foundation",
            ),
            (
                "Web boundary",
                "Next.js SSR and fixed-route BFF; HttpOnly session cookie; Origin and CSRF checks",
            ),
            (
                "API",
                "FastAPI modular services; typed validation; permission and ownership checks; stable error codes",
            ),
            (
                "Data and jobs",
                "PostgreSQL system of record; Redis broker/cache; Celery workers and beat schedules",
            ),
            (
                "External boundaries",
                "Meta Graph adapter; future messaging/object-storage providers behind interfaces",
            ),
        ]
    ),
    Spacer(1, 4 * mm),
    HorizontalFlow(
        [
            "Browser request",
            "Next.js BFF allowlist",
            "FastAPI route",
            "Domain service",
            "PostgreSQL transaction",
        ],
        subtitle="Every protected mutation carries session, scope, CSRF, request ID, optimistic version and audit context",
    ),
    Spacer(1, 4 * mm),
    table(
        ["Boundary", "What the implementation enforces"],
        [
            (
                "Browser",
                "No access/refresh token in JavaScript; private no-store responses; bounded JSON bodies",
            ),
            (
                "API",
                "Authentication, active-account check, explicit permission, organization/owner scope and typed payload",
            ),
            (
                "Service",
                "Lifecycle transition, dependency validation, row lock/version, audit and outbox in one transaction",
            ),
            (
                "Database",
                "Composite scope keys, unique/check constraints, immutable evidence triggers and indexed queries",
            ),
            (
                "Worker",
                "Record IDs only, bounded retries/leases, dedupe and operator-visible recovery state",
            ),
        ],
        [38 * mm, 136 * mm],
    ),
    PageBreak(),
]

# Identity
story += [
    P("3. Identity, session and authorization flow", "H1x"),
    HorizontalFlow(
        [
            "Register",
            "Verify account",
            "Sign in",
            "Use access session",
            "Rotate or revoke",
        ],
        subtitle="Person is the stable identity; User is the login account",
    ),
    P("Browser session", "H2x"),
    P(
        "The browser authenticates through a server-only Next.js boundary. The API issues opaque sessions, while the browser receives an HttpOnly SameSite cookie and a session-bound CSRF token. Logout, logout-all, password reset, suspension and refresh replay revoke session families."
    ),
    P("Authorization decision", "H2x"),
    HorizontalFlow(
        [
            "Active user",
            "Role in organization",
            "Permission grant",
            "Resource scope",
            "Allow or deny",
        ],
        colors_=[NAVY, TEAL, COPPER],
    ),
    Spacer(1, 4 * mm),
    table(
        ["Control", "Implemented behavior"],
        [
            (
                "Credential storage",
                "Argon2id password hash; hashed reset, verification, access and refresh tokens",
            ),
            (
                "Refresh security",
                "One-use rotation under row lock; replay revokes the token family",
            ),
            (
                "Tenant isolation",
                "Organization ID is checked in permission lookup and resource query; UUID alone grants nothing",
            ),
            (
                "Self access",
                "Applicant and participant queries derive Person from the authenticated User",
            ),
            (
                "Audit",
                "Consequential actions record actor, organization, resource, request ID, version and safe field names",
            ),
        ],
        [40 * mm, 134 * mm],
    ),
    P("Role examples", "H2x"),
    table(
        ["Role", "Implemented access emphasis"],
        [
            (
                "Program Director",
                "Policy publication, selection finalization, overrides, enrollment and schedule administration",
            ),
            (
                "Program Manager",
                "Draft policy/program/selection setup, assignments, enrollment and schedule administration",
            ),
            ("Selection Committee", "Only assigned review and interview scoring"),
            ("Content / CRM / Marketing", "Module-specific organization permissions"),
            (
                "Participant",
                "System access and self-only participant schedule/timeline",
            ),
        ],
        [45 * mm, 129 * mm],
        TEAL,
    ),
    PageBreak(),
]

# Public/CRM
story += [
    P("4. Discovery, lead and communication flow", "H1x"),
    P("Public content to prospect", "H2x"),
    HorizontalFlow(
        [
            "Localized public page",
            "Privacy-safe enquiry",
            "CRM lead",
            "Assignment",
            "Follow-up queue",
        ],
        subtitle="Draft or archived CMS content is never returned by public DTOs",
    ),
    P("Meta lead ingestion", "H2x"),
    HorizontalFlow(
        [
            "Signed webhook",
            "Idempotent inbox",
            "Mapped provider fetch",
            "Attributed CRM lead",
            "Health and replay",
        ],
        colors_=[COPPER, NAVY, TEAL],
    ),
    P("In-app communication", "H2x"),
    HorizontalFlow(
        [
            "Domain event",
            "Notification intent",
            "Eligibility and preference",
            "Visible inbox item",
            "Read or replay",
        ],
        subtitle="Retention immediately hides expired items; bounded tasks purge later",
    ),
    Spacer(1, 4 * mm),
    table(
        ["Flow", "Key safeguards"],
        [
            (
                "CMS publication",
                "Independent English/Tamil revision history, optimistic versions and immutable published evidence",
            ),
            (
                "Enquiry",
                "Generic 202 response, privacy-notice version, bounded contact fields and dedupe hash",
            ),
            (
                "CRM merge",
                "Canonical pair, mandatory reason, survivor link and preserved activity history",
            ),
            (
                "CSV export",
                "Requester-only, 10,000-row bound, spreadsheet-formula escaping, 24-hour expiry",
            ),
            (
                "Meta",
                "Raw-body signature verification, encrypted secrets, provider-ID dedupe, minimal retention metadata",
            ),
            (
                "Notifications",
                "Recipient/scope/preference recheck, unique source/recipient, retry cap and audited replay",
            ),
        ],
        [38 * mm, 136 * mm],
    ),
    PageBreak(),
]

# Application
story += [
    P("5. Application definition and applicant flow", "H1x"),
    P("Policy administration", "H2x"),
    HorizontalFlow(
        [
            "Create draft policy",
            "Add fields and acknowledgements",
            "Validate policy",
            "Publish immutable version",
            "Copy next draft",
        ],
        subtitle="Publishing retires the prior live version; existing applications remain pinned",
    ),
    P("Applicant journey", "H2x"),
    HorizontalFlow(
        [
            "Choose open cycle",
            "Create or resume draft",
            "Save versioned answers",
            "Accept declaration and consent",
            "Submit once",
        ],
        colors_=[TEAL, NAVY, COPPER],
    ),
    Spacer(1, 4 * mm),
    Lifecycle(
        [
            (
                "Application",
                [
                    "draft",
                    "submitted",
                    "under review",
                    "shortlisted",
                    "interview",
                    "selected",
                    "enrolled",
                ],
                TEAL,
            )
        ],
        height=20 * mm,
    ),
    P("Submission transaction", "H2x"),
    table(
        ["Step", "Server-side result"],
        [
            ("Lock and version", "Locks the application and rejects stale writes"),
            (
                "Validate",
                "Open cycle, pinned form, required answers, declaration and consent",
            ),
            (
                "Persist evidence",
                "Immutable revision, acknowledgements with timestamps, submitted timestamp and history",
            ),
            (
                "Generate receipt",
                "Unique non-PII `EDP-{year}-{sequence}` application number",
            ),
            (
                "Audit",
                "Identifiers and changed-field names only; no answers or policy text",
            ),
        ],
        [38 * mm, 136 * mm],
    ),
    P("Supporting documents", "H2x"),
    P(
        "A01.3 is intentionally unavailable until private object storage, malware scanning and retention policy are approved."
    ),
    PageBreak(),
]

# Selection
story += [
    P("6. Selection management flow", "H1x"),
    HorizontalFlow(
        [
            "Create selection cycle",
            "Build weighted rubric",
            "Publish rubric",
            "Assign reviewer",
            "Declare conflict or clearance",
        ],
        subtitle="Assignments pin the published rubric and move submitted applications to under review",
    ),
    Spacer(1, 2 * mm),
    HorizontalFlow(
        [
            "Save criterion scores",
            "Submit immutable review",
            "Moderate inclusion",
            "Aggregate included reviews",
            "Shortlist",
        ],
        colors_=[NAVY, TEAL, COPPER],
    ),
    Spacer(1, 2 * mm),
    HorizontalFlow(
        [
            "Schedule panel",
            "Panel members score",
            "Complete interview",
            "Decide outcome",
            "Finalize cycle",
        ],
        subtitle="Selected, waitlisted and rejected decisions store review/interview score snapshots",
    ),
    Spacer(1, 5 * mm),
    table(
        ["Rule", "Implementation"],
        [
            (
                "Weighted scoring",
                "Server normalizes each criterion to its configured range and applies published weights",
            ),
            (
                "Conflicts",
                "Assigned reviewer must declare clear or a reasoned conflict before scoring",
            ),
            (
                "Moderation",
                "Authorized directors exclude/restore aggregate inclusion without changing submitted evidence",
            ),
            (
                "Interview",
                "One panel per application; every member submits once; mean is server-calculated",
            ),
            (
                "Decision",
                "Shortlist requires completed included review; terminal decisions require finalization permission",
            ),
            (
                "Override",
                "Changing a terminal decision requires explicit override permission, flag and reason",
            ),
            (
                "Finalization",
                "All assigned applications must be terminal and no interview may remain scheduled",
            ),
        ],
        [40 * mm, 134 * mm],
    ),
    PageBreak(),
]

# Enrollment
story += [
    P("7. Enrollment, participant and schedule flow", "H1x"),
    P("Atomic conversion", "H2x"),
    HorizontalFlow(
        [
            "Finalized selected application",
            "Validate active cohort and capacity",
            "Create or reuse Participant",
            "Create unique Enrollment",
            "Set application enrolled",
        ],
        subtitle="Audit, status history, Participant role binding and enrollment.created outbox commit together",
    ),
    P("Schedule delivery", "H2x"),
    HorizontalFlow(
        [
            "Choose active/planned cohort",
            "Create bilingual session",
            "Validate cohort dates and mode",
            "Participant sees schedule",
            "Complete or cancel",
        ],
        colors_=[COPPER, TEAL, NAVY],
    ),
    P("Participant timeline", "H2x"),
    HorizontalFlow(
        ["Application submitted", "Selected", "Enrollment created", "Program session"],
        subtitle="Ordered projection; no reviewer scores, comments or decision reasons",
    ),
    Spacer(1, 4 * mm),
    table(
        ["Invariant", "Database/service enforcement"],
        [
            (
                "Stable identity",
                "Participant references Person; name, email and contact data are not copied",
            ),
            ("One conversion", "Enrollment.application_id is unique"),
            (
                "No duplicate cohort seat",
                "Enrollment is unique by participant and cohort",
            ),
            (
                "Scope",
                "Composite foreign keys bind participant, application, program and cohort to one organization",
            ),
            (
                "Capacity",
                "Active enrollment count is checked under locked conversion dependencies",
            ),
            (
                "Self visibility",
                "Timeline query matches Participant.person_id to authenticated User.person_id",
            ),
        ],
        [43 * mm, 131 * mm],
    ),
    PageBreak(),
]

# Data lineage
story += [
    P("8. Core data lineage", "H1x"),
    HorizontalFlow(
        [
            "Person",
            "User",
            "Application",
            "SelectionDecision",
            "Enrollment",
            "Participant",
        ],
        subtitle="Person is the stable identity root; business stages reference it instead of duplicating it",
    ),
    Spacer(1, 3 * mm),
    table(
        ["Aggregate", "Key relationships and evidence"],
        [
            (
                "Identity",
                "Person 1:1 User; User -> scoped roles -> permissions; User -> refresh sessions/tokens",
            ),
            (
                "Applications",
                "Application -> immutable revisions/answers/acknowledgements/status history; cycle -> form/program/cohort",
            ),
            (
                "Selection",
                "SelectionCycle -> rubric/criteria -> review assignments/scores; Application -> interview/panel -> append-only decisions",
            ),
            (
                "Programs",
                "Program -> Cohort -> ProgramSession; TrainingCenter -> Cohort; ApplicationCycle binds program/cohort/form",
            ),
            (
                "Participants",
                "Person -> Participant per organization; Participant -> Enrollment; Enrollment -> selected Application and Cohort",
            ),
            (
                "Operations",
                "Domain change -> AuditLog; asynchronous change -> outbox/inbox/notification state",
            ),
        ],
        [40 * mm, 134 * mm],
    ),
    P("Database protection model", "H2x"),
    *bullets(
        [
            "Composite foreign keys reject cross-organization and cross-program links even if application code is bypassed.",
            "Unique constraints prevent duplicate submissions, assignments, scores, provider events, enrollments and reminders.",
            "Check constraints encode lifecycle values, timestamps, ranges, completion evidence and mode/location consistency.",
            "PostgreSQL triggers freeze published policy, submitted applications, scores, interviews, decisions, histories and outbox identity evidence.",
            "Editable workflows use optimistic versions; consequential service commands use row locks and one transaction.",
        ]
    ),
    PageBreak(),
]

# Interfaces
story += [
    P("9. User surfaces and API boundaries", "H1x"),
    table(
        ["Surface", "Implemented routes/workspaces", "Boundary"],
        [
            (
                "Public web",
                "Localized home, CMS pages, editorial lists/details, sitemap and robots",
                "Published content only; canonical and language metadata",
            ),
            (
                "Account",
                "Register, verify, sign in, reset, devices and sign-out",
                "Opaque HttpOnly browser session",
            ),
            (
                "Applicant",
                "`/[locale]/applications`",
                "Owner-scoped drafts, submission receipt and status history",
            ),
            (
                "Staff admin",
                "CMS, CRM, Meta, notifications, application definitions, programs and selection",
                "Permission-aware UI plus fixed route-specific BFF allowlists",
            ),
            (
                "Participant",
                "`/[locale]/participant`",
                "Self-scoped enrollment journey and cohort sessions",
            ),
            (
                "Flutter",
                "Authentication and public CMS/editorial foundation",
                "Native-device completion remains deferred",
            ),
            (
                "Swagger",
                "`/docs` in local/test",
                "Generated OpenAPI; disabled in production environment mode",
            ),
        ],
        [29 * mm, 83 * mm, 62 * mm],
    ),
    Spacer(1, 5 * mm),
    P("Representative command APIs", "H2x"),
    table(
        ["Domain", "Command style"],
        [
            (
                "Application",
                "Create/resume draft, save revision, submit with exact version and acknowledgements",
            ),
            (
                "Selection",
                "Explicit publish, conflict, submit review, moderate, interview score/complete, decision and finalize commands",
            ),
            (
                "Programs",
                "Explicit resource state commands; enrollment conversion; participant state; session create/state",
            ),
            (
                "CRM/Meta/Notifications",
                "Versioned lifecycle commands, assignment/merge/replay reasons and bounded collection reads",
            ),
        ],
        [42 * mm, 132 * mm],
        TEAL,
    ),
    P("Contract rule", "H2x"),
    P(
        "FastAPI is the contract source. OpenAPI is exported to `packages/api-contracts/openapi.json`, then TypeScript definitions are generated for Next.js. Clients do not submit calculated scores, participant identity links or enrollment scope."
    ),
    PageBreak(),
]

# Validation
story += [
    P("10. Security and Definition of Done evidence", "H1x"),
    table(
        ["Gate", "Latest evidence at commit 3f70069"],
        [
            ("Backend workflow", "81 PostgreSQL-backed tests passed"),
            (
                "Focused selection/program",
                "4 end-to-end service/database tests passed, including negative authorization and ownership",
            ),
            ("Web", "30 Vitest tests, ESLint and strict TypeScript passed"),
            ("Build", "Next.js production build passed, including participant route"),
            (
                "Database",
                "P01.2 populated downgrade, re-upgrade and Alembic drift check passed",
            ),
            (
                "Static checks",
                "Focused Ruff and strict MyPy passed for selection/program modules",
            ),
            (
                "Browser",
                "Authenticated Chrome passed identity -> application -> selection -> enrollment -> session -> participant timeline",
            ),
            (
                "Browser quality",
                "Responsive layout assertions passed; no JavaScript errors",
            ),
            (
                "Contracts/docs",
                "OpenAPI and TypeScript regenerated; ERD, security, privacy, API, testing and user guides updated",
            ),
        ],
        [47 * mm, 127 * mm],
    ),
    Spacer(1, 6 * mm),
    P("Cross-cutting controls", "H2x"),
    table(
        ["Risk", "Implemented mitigation"],
        [
            (
                "Broken object access",
                "Permission plus tenant/owner query, composite database scope, negative tests",
            ),
            (
                "Evidence tampering",
                "Immutable database triggers and append-only history",
            ),
            (
                "Duplicate actions",
                "Unique constraints, idempotent commands and provider event keys",
            ),
            (
                "Browser token theft/CSRF",
                "HttpOnly session, BFF-held credentials, Origin and double-submit CSRF",
            ),
            (
                "Sensitive telemetry",
                "Allowlisted audit fields, IDs in tasks/outbox, generic external errors",
            ),
            (
                "Job loss/retry",
                "PostgreSQL inbox/outbox concepts, leases, bounded retries and operator replay",
            ),
        ],
        [43 * mm, 131 * mm],
    ),
    PageBreak(),
]

# Chronology and remaining
story += [
    P("11. Delivery chronology and current boundary", "H1x"),
    table(
        ["Milestone", "Implemented result"],
        [
            (
                "Foundation",
                "Repository architecture, FastAPI/Next.js/Flutter/PostgreSQL/Redis/Celery bootstrap, auth/RBAC/audit",
            ),
            (
                "Milestone 2",
                "Localized CMS/public publishing, editorial, asset quarantine, enquiries, SEO and CRM foundation",
            ),
            (
                "Milestone 3",
                "CRM operations, Meta ingestion/recovery/retention, in-app notifications/retries and UI system pilot",
            ),
            (
                "Milestone 4",
                "Application definitions/drafts/submission, program foundation and complete selection workflow",
            ),
            (
                "Milestone 5 / P01.2",
                "Enrollment conversion, participant projection, program sessions and participant timeline",
            ),
        ],
        [39 * mm, 135 * mm],
    ),
    Spacer(1, 6 * mm),
    P("Implemented end-to-end business path", "H2x"),
    HorizontalFlow(
        [
            "Discover",
            "Register",
            "Apply",
            "Review",
            "Interview",
            "Select",
            "Enroll",
            "Attend schedule",
        ],
        width=174 * mm,
        height=34 * mm,
    ),
    P("Explicitly outside completed code", "H2x"),
    table(
        ["Pending area", "Reason / next dependency"],
        [
            (
                "A01.3 supporting documents",
                "Private object storage, malware scanning and approved retention",
            ),
            (
                "Center/cohort staff bindings",
                "Needed before Training Center Coordinators receive mutation permissions",
            ),
            ("LMS and assessments", "Next participant capability based on Enrollment"),
            ("Attendance and QR", "Build against ProgramSession and Enrollment"),
            ("Mentoring, funding, support, impact", "Later P0 vertical slices"),
            (
                "Production release",
                "Remote CI for latest commit, live-provider approvals, monitoring/restore/UAT and native-device gates",
            ),
        ],
        [48 * mm, 126 * mm],
        COPPER,
    ),
    Spacer(1, 6 * mm),
    P("Document status", "Callout"),
    P(
        "This PDF describes completed repository behavior at commit 3f70069. It is not a production approval, compliance certification or claim that deferred native/provider/operations gates have passed."
    ),
    Spacer(1, 8 * mm),
    HRFlowable(width="100%", color=colors.HexColor("#CCD5DD")),
    Spacer(1, 4 * mm),
    P(
        "Source references: `EDP_CODEX_MASTER_INPUT.md`, `docs/sdlc/*-report.md`, `docs/architecture/system-architecture.md`, `docs/database/erd.md`, `docs/security/security-model.md`, generated OpenAPI, tests and browser acceptance runner.",
        "Smallx",
    ),
]

Doc(str(OUT)).build(story)
print(OUT)
