"""Versioned, bilingual dictionary for the operational aggregate dashboard."""

from app.modules.reports.schemas import ReportMetric

METRIC_DICTIONARY_VERSION = "2026-10-21.1"

CURRENT_EN = (
    "Current state observed when generated; it is not a historical state at the period end."
)
CURRENT_TA = "உருவாக்கிய நேரத்தின் தற்போதைய நிலை; கால முடிவின் வரலாற்று நிலை அல்ல."
MEMBERSHIP_EN = (
    "Program/cohort scope uses enrollment membership, not causal attribution. "
    "Each fact is counted once even when the participant has several enrollments."
)
MEMBERSHIP_TA = (
    "திட்டம்/குழு வரம்பு சேர்க்கை உறுப்புரிமையைப் பயன்படுத்துகிறது; காரண விளைவு அல்ல. "
    "பல சேர்க்கைகள் இருந்தாலும் ஒவ்வொரு பதிவும் ஒருமுறை கணக்கிடப்படும்."
)


def _definition(
    key: str,
    group: str,
    en: str,
    ta: str,
    explanation: str,
    explanation_ta: str,
    source: str,
    temporal: str,
    unit: str = "count",
    caveat: tuple[str, str] = ("", ""),
) -> ReportMetric:
    return ReportMetric(
        key=key,
        group=group,
        label_en=en,
        label_ta=ta,
        definition_en=explanation,
        definition_ta=explanation_ta,
        source=source,
        temporal_basis=temporal,
        unit=unit,
        caveat_en=caveat[0],
        caveat_ta=caveat[1],
    )


def operational_metric_definitions() -> list[ReportMetric]:
    """Return fresh models so values and breakdowns cannot mutate the dictionary."""
    specs = [
        (
            "leads",
            "marketing",
            "Leads created",
            "உருவாக்கிய முன்னணி தொடர்புகள்",
            "Non-merged organization leads created in the window, with source and campaign counts.",
            "காலத்தில் உருவாக்கிய, ஒன்றிணைக்கப்படாத நிறுவன தொடர்புகள்; மூலம், பிரச்சார எண்ணிக்கைகளுடன்.",
            "crm_leads",
            "created_at; current merge state",
        ),
        (
            "registrations",
            "marketing",
            "CRM-linked registrations",
            "மூலத்துடன் இணைந்த பதிவுகள்",
            "Distinct people whose first organization CRM registration link was recorded "
            "in the window; attribution uses that first immutable conversion, "
            "not account creation time.",
            "காலத்தில் முதல் நிறுவன தொடர்பு மாற்றம் பதிவான தனித்த நபர்கள்; "
            "மூலம் அந்த முதல் மாற்றத்திலிருந்து பெறப்படும்.",
            "crm_lead_conversions → people",
            "first organization conversion.created_at",
        ),
        (
            "applications",
            "marketing",
            "Submitted applications",
            "சமர்ப்பித்த விண்ணப்பங்கள்",
            "Applications whose submitted_at is in the window; program/cohort follows their cycle.",
            "காலத்தில் சமர்ப்பித்த விண்ணப்பங்கள்; திட்டம்/குழு அதன் விண்ணப்ப சுற்றிலிருந்து பெறப்படும்.",
            "applications → application_cycles",
            "submitted_at",
        ),
        (
            "selected_applications",
            "marketing",
            "Currently selected applications",
            "தற்போது தேர்ந்தெடுத்த விண்ணப்பங்கள்",
            "Submitted-window applications currently selected or enrolled.",
            "காலத்தில் சமர்ப்பித்து தற்போது தேர்ந்தெடுக்கப்பட்ட அல்லது சேர்க்கப்பட்ட விண்ணப்பங்கள்.",
            "applications",
            "submitted_at population; current state",
        ),
        (
            "lead_to_application_percent",
            "marketing",
            "Lead to application",
            "தொடர்பிலிருந்து விண்ணப்பம்",
            "Percent of non-merged window-created leads with a conversion "
            "person linked to an actual "
            "submitted application in this organization. The application may be submitted later.",
            "காலத்தில் உருவாக்கிய தொடர்புகளில் மாற்றப்பட்ட நபரின் உண்மையான "
            "நிறுவன விண்ணப்பம் உள்ள சதவீதம்; "
            "விண்ணப்பம் பின்னர் சமர்ப்பிக்கப்பட்டிருக்கலாம்.",
            "crm_leads → crm_lead_conversions → applications",
            "lead.created_at population; linked facts",
        ),
        (
            "application_to_selection_percent",
            "marketing",
            "Application to selection",
            "விண்ணப்பத்திலிருந்து தேர்வு",
            "Currently selected/enrolled divided by the same submitted-window applications.",
            "காலத்தில் சமர்ப்பித்த அதே விண்ணப்பங்களில் தற்போது தேர்ந்தெடுத்த/சேர்க்கப்பட்ட விகிதம்.",
            "applications",
            "submitted_at population; current state",
        ),
        (
            "selection_to_enrollment_percent",
            "marketing",
            "Selection to enrollment",
            "தேர்விலிருந்து சேர்க்கை",
            "Actual enrollment links divided by selected/enrolled submitted-window applications.",
            "காலத்தில் சமர்ப்பித்து தேர்ந்தெடுத்த/சேர்க்கப்பட்ட விண்ணப்பங்களில் உண்மையான சேர்க்கை இணைப்பு விகிதம்.",
            "applications → enrollments",
            "submitted_at population; current links",
        ),
        (
            "enrollments",
            "program",
            "Enrollments",
            "சேர்க்கைகள்",
            "Enrollment records enrolled in the window; a person may have more "
            "than one enrollment.",
            "காலத்தில் சேர்க்கப்பட்ட பதிவுகள்; ஒருவருக்கு ஒன்றுக்கும் மேற்பட்ட சேர்க்கை இருக்கலாம்.",
            "enrollments",
            "enrolled_at",
        ),
        (
            "active_participants",
            "program",
            "Active participants",
            "செயலில் உள்ள பங்கேற்பாளர்கள்",
            "Distinct currently active participants with a currently active "
            "enrollment enrolled in the window.",
            "காலத்தில் சேர்க்கப்பட்ட செயலில் உள்ள சேர்க்கையுடன் தற்போது செயலில் உள்ள தனித்த பங்கேற்பாளர்கள்.",
            "participants → enrollments",
            "enrolled_at population; current statuses",
        ),
        (
            "withdrawn_enrollments",
            "program",
            "Withdrawn enrollments",
            "விலகிய சேர்க்கைகள்",
            "Window-enrolled records currently withdrawn; no dropout inference is made.",
            "காலத்தில் சேர்க்கப்பட்டு தற்போது விலகிய பதிவுகள்; இடைநிற்றல் ஊகிக்கப்படாது.",
            "enrollments",
            "enrolled_at population; current status",
        ),
        (
            "completed_enrollments",
            "program",
            "Completed enrollments",
            "நிறைவுற்ற சேர்க்கைகள்",
            "Window-enrolled records currently completed; not completion events in the window.",
            "காலத்தில் சேர்க்கப்பட்டு தற்போது முடிவுற்ற பதிவுகள்; காலத்தில் முடித்த நிகழ்வுகள் அல்ல.",
            "enrollments",
            "enrolled_at population; current status",
        ),
        (
            "valid_certificates",
            "program",
            "Valid certificates issued",
            "வழங்கிய செல்லுபடியான சான்றிதழ்கள்",
            "Certificates issued in the window that remain valid at observation time.",
            "காலத்தில் வழங்கப்பட்டு கணக்கிடும் நேரத்தில் செல்லுபடியாகும் சான்றிதழ்கள்.",
            "certificates → course_enrollments → enrollments",
            "issued_at; current status",
        ),
        (
            "course_starts",
            "learning",
            "Course starts",
            "பாடநெறி தொடக்கங்கள்",
            "Course enrollments started in the window, counted per enrollment and course.",
            "காலத்தில் தொடங்கிய பாடநெறி சேர்க்கைகள்; சேர்க்கை மற்றும் பாடநெறி அடிப்படையில்.",
            "course_enrollments → enrollments",
            "started_at",
        ),
        (
            "course_completions",
            "learning",
            "Course completions",
            "பாடநெறி நிறைவுகள்",
            "Course enrollments with a recorded completion time in the window, "
            "regardless of start date.",
            "தொடக்கத் தேதியைப் பொருட்படுத்தாமல் காலத்தில் பதிவான நிறைவு நேரமுள்ள பாடநெறிகள்.",
            "course_enrollments → enrollments",
            "completed_at",
        ),
        (
            "lesson_completions",
            "learning",
            "Recorded lesson completions",
            "பதிவான பாட நிறைவுகள்",
            "Recorded completed lesson progress in the window; missing progress is not imputed.",
            "காலத்தில் பதிவான பாட நிறைவுகள்; இல்லாத முன்னேற்றம் ஊகிக்கப்படாது.",
            "lesson_progress → course_enrollments → enrollments",
            "completed_at",
        ),
        (
            "quiz_attempts",
            "learning",
            "Quiz attempts",
            "வினாடி வினா முயற்சிகள்",
            "All submitted quiz attempts in the window, including repeated attempts.",
            "மீண்டும் எடுத்த முயற்சிகள் உட்பட காலத்தில் சமர்ப்பித்த அனைத்து வினாடி வினா முயற்சிகள்.",
            "quiz_attempts → course_enrollments → enrollments",
            "submitted_at",
        ),
        (
            "quiz_pass_percent",
            "learning",
            "Quiz attempt pass rate",
            "வினாடி வினா தேர்ச்சி விகிதம்",
            "Passed attempts divided by all attempts submitted in the window; "
            "not a learner pass rate.",
            "காலத்தின் அனைத்து முயற்சிகளில் தேர்ச்சி பெற்ற முயற்சி விகிதம்; நபர் அடிப்படையிலான விகிதம் அல்ல.",
            "quiz_attempts → course_enrollments → enrollments",
            "submitted_at",
        ),
        (
            "quiz_mean_percent",
            "learning",
            "Mean quiz attempt score",
            "சராசரி வினாடி வினா மதிப்பெண்",
            "Sum of recorded attempt percentage scores divided by attempts in "
            "the window; each attempt equally weighted.",
            "காலத்தில் முயற்சிகளின் சதவீத மதிப்பெண் கூட்டுத்தொகை / முயற்சிகள்; ஒவ்வொரு முயற்சிக்கும் சம எடை.",
            "quiz_attempts → course_enrollments → enrollments",
            "submitted_at",
        ),
        (
            "assignment_submissions",
            "learning",
            "Assignment submissions",
            "ஒப்படைப்பு சமர்ப்பிப்புகள்",
            "Submission revisions submitted in the window, including resubmissions.",
            "மறுசமர்ப்பிப்புகள் உட்பட காலத்தில் சமர்ப்பித்த ஒப்படைப்பு திருத்தப்பதிவுகள்.",
            "assignment_submissions → course_enrollments → enrollments",
            "submitted_at",
        ),
        (
            "assignment_grades",
            "learning",
            "Assignment grades",
            "ஒப்படைப்பு மதிப்பீடுகள்",
            "Grades recorded in the window; ungraded submissions are excluded.",
            "காலத்தில் பதிவான மதிப்பீடுகள்; மதிப்பிடப்படாத சமர்ப்பிப்புகள் விலக்கப்படும்.",
            "assignment_grades → assignment_submissions → course_enrollments → enrollments",
            "graded_at",
        ),
        (
            "assignment_pass_percent",
            "learning",
            "Graded assignment pass rate",
            "மதிப்பிட்ட ஒப்படைப்பு தேர்ச்சி",
            "Passed grades divided by grades recorded in the window; missing grades are excluded.",
            "காலத்தில் பதிவான மதிப்பீடுகளில் தேர்ச்சி விகிதம்; இல்லாத மதிப்பீடுகள் விலக்கப்படும்.",
            "assignment_grades → assignment_submissions → course_enrollments → enrollments",
            "graded_at",
        ),
        (
            "attendance_recorded",
            "learning",
            "Recorded attendance marks",
            "பதிவான வருகைக் குறிகள்",
            "Recorded present/late/absent marks for sessions starting in the "
            "window; excused and missing excluded.",
            "காலத்தில் தொடங்கிய அமர்வுகளின் வருகை/தாமதம்/வராமை பதிவுகள்; விலக்கு மற்றும் இல்லாத பதிவுகள் நீக்கம்.",
            "attendance_records → program_sessions → enrollments",
            "session.starts_at; current mark",
        ),
        (
            "attendance_percent",
            "learning",
            "Attendance among recorded marks",
            "பதிவான குறிகளில் வருகை",
            "Present plus late divided by present plus late plus absent for "
            "sessions starting in the window. "
            "Excused and missing marks never enter the denominator.",
            "கால அமர்வுகளில் வருகை + தாமதம் / வருகை + தாமதம் + வராமை; விலக்கு, இல்லாத குறிகள் விகிதத்தில் சேராது.",
            "attendance_records → program_sessions → enrollments",
            "session.starts_at; current mark",
        ),
        (
            "idea_profiles",
            "entrepreneurship",
            "Idea-stage business profiles",
            "யோசனை நிலையிலுள்ள தொழில்கள்",
            "Profiles created in the window currently at idea stage; one profile per enrollment.",
            "காலத்தில் உருவாக்கப்பட்டு தற்போது யோசனை நிலையிலுள்ள தொழில் விவரங்கள்; சேர்க்கைக்கு ஒரு விவரம்.",
            "business_profiles → enrollments",
            "profile.created_at population; current stage",
        ),
        (
            "submitted_plans",
            "entrepreneurship",
            "Business plans submitted",
            "சமர்ப்பித்த தொழில் திட்டங்கள்",
            "Distinct plans with at least one submission recorded in the "
            "window; resubmission does not duplicate a plan.",
            "காலத்தில் சமர்ப்பித்த தனித்த தொழில் திட்டங்கள்; மறுசமர்ப்பிப்பு ஒரே திட்டத்தை மீண்டும் எண்ணாது.",
            "business_plan_submissions → business_plans → enrollments",
            "submission.created_at",
        ),
        (
            "approved_plans",
            "entrepreneurship",
            "Business plans approved",
            "ஒப்புதல் பெற்ற தொழில் திட்டங்கள்",
            "Distinct plans with an approved review recorded in the window; "
            "counts approval evidence, not current status.",
            "காலத்தில் ஒப்புதல் மதிப்பாய்வு பதிவான தனித்த திட்டங்கள்; தற்போதைய நிலை அல்ல, ஒப்புதல் சான்று எண்ணிக்கை.",
            "business_plan_reviews → business_plan_submissions → business_plans → enrollments",
            "review.created_at",
        ),
        (
            "business_outcome_reports",
            "entrepreneurship",
            "Latest B02 business outcomes",
            "சமீபத்திய B02 தொழில் முடிவுகள்",
            "One latest reported-on outcome per enrollment within the window; "
            "ties use recorded time then ID.",
            "காலத்தில் சேர்க்கை ஒன்றிற்கு சமீபத்திய அறிக்கை தேதி முடிவு ஒன்று; "
            "சமதேதி பதிவுநேரம், அடையாளத்தால் தீர்வு.",
            "business_outcome_snapshots → business_follow_ups → business_profiles → enrollments",
            "reported_on; latest per enrollment",
        ),
        (
            "businesses_started",
            "entrepreneurship",
            "Self-reported businesses started",
            "சுய அறிக்கையின் தொடங்கிய தொழில்கள்",
            "Business-started flags from the latest B02 outcome per enrollment in the window.",
            "காலத்தில் சேர்க்கை ஒன்றின் சமீபத்திய B02 முடிவில் தொழில் தொடங்கியதாகக் கூறிய பதிவுகள்.",
            "business_outcome_snapshots",
            "reported_on; latest per enrollment",
        ),
        (
            "businesses_active",
            "entrepreneurship",
            "Self-reported active businesses",
            "சுய அறிக்கையின் செயல் தொழில்கள்",
            "Business-active flags from the latest B02 outcome per enrollment in the window.",
            "காலத்தில் சேர்க்கை ஒன்றின் சமீபத்திய B02 முடிவில் தொழில் செயலில் இருப்பதாகக் கூறிய பதிவுகள்.",
            "business_outcome_snapshots",
            "reported_on; latest per enrollment",
        ),
        (
            "jobs_created",
            "entrepreneurship",
            "Self-reported jobs",
            "சுய அறிக்கையின் வேலைகள்",
            "Sum of jobs from one latest B02 outcome per enrollment in the "
            "window; repeated snapshots are not added.",
            "காலத்தில் சேர்க்கை ஒன்றின் சமீபத்திய B02 முடிவிலுள்ள வேலைகளின் "
            "கூட்டுத்தொகை; தொடர்முடிவுகள் சேர்க்கப்படாது.",
            "business_outcome_snapshots",
            "reported_on; latest per enrollment",
        ),
        (
            "funding_applied_cases",
            "funding",
            "Funding applications recorded",
            "பதிவான நிதி விண்ணப்பங்கள்",
            "Distinct cases with an applied history event in the window; case "
            "creation date does not restrict events.",
            "காலத்தில் விண்ணப்பித்த வரலாற்று நிகழ்வுள்ள தனித்த நிதி பதிவுகள்; "
            "உருவாக்கிய தேதியால் நிகழ்வு கட்டுப்படாது.",
            "funding_history → funding_cases",
            "applied history.created_at",
        ),
        (
            "funding_approved_cases",
            "funding",
            "Funding approvals recorded",
            "பதிவான நிதி ஒப்புதல்கள்",
            "Distinct cases with an approved history event in the window; "
            "participant-reported, not provider-verified.",
            "காலத்தில் ஒப்புதல் வரலாற்றுள்ள தனித்த பதிவுகள்; பங்கேற்பாளர் அறிக்கை, வழங்குநர் சரிபார்ப்பு அல்ல.",
            "funding_history → funding_cases",
            "approved history.created_at",
        ),
        (
            "funding_disbursed_cases",
            "funding",
            "Funding disbursements recorded",
            "பதிவான நிதி வழங்கல்கள்",
            "Distinct cases with a disbursed history event in the window; "
            "participant-reported, not provider-verified.",
            "காலத்தில் வழங்கிய வரலாற்றுள்ள தனித்த பதிவுகள்; பங்கேற்பாளர் அறிக்கை, வழங்குநர் சரிபார்ப்பு அல்ல.",
            "funding_history → funding_cases",
            "disbursed history.created_at",
        ),
        (
            "funding_facilitated_amount",
            "funding",
            "Funding facilitated amount",
            "ஏற்பாடு செய்யப்பட்ட நிதித் தொகை",
            "Unavailable: no exact transaction/disbursement amounts or "
            "verified facilitation attribution are stored.",
            "கிடைக்கவில்லை: சரியான பரிவர்த்தனை/வழங்கல் தொகை அல்லது ஏற்பாட்டின் உறுதிப்படுத்திய பங்கு பதிவாகவில்லை.",
            "No transaction amount source",
            "unavailable",
        ),
        (
            "tickets_created",
            "support",
            "Helpdesk tickets created",
            "உருவாக்கிய உதவி சீட்டுகள்",
            "Distinct tickets created in the window with participant enrollment membership scope.",
            "பங்கேற்பாளர் சேர்க்கை வரம்பில் காலத்தில் உருவாக்கிய தனித்த உதவி சீட்டுகள்.",
            "helpdesk_tickets → enrollment membership",
            "ticket.created_at",
        ),
        (
            "tickets_resolved",
            "support",
            "Tickets with a recorded resolution",
            "தீர்வு பதிவான உதவி சீட்டுகள்",
            "Window-created tickets with a first resolved history event by "
            "generation time, even if reopened later.",
            "காலத்தில் உருவாக்கி முதல் தீர்வு வரலாறு உள்ள சீட்டுகள்; பின்னர் மீண்டும் திறந்திருந்தாலும் சேரும்.",
            "helpdesk_tickets → helpdesk_history",
            "ticket.created_at population; first resolved event",
        ),
        (
            "ticket_resolution_hours",
            "support",
            "Mean first resolution time",
            "முதல் தீர்வின் சராசரி நேரம்",
            "Total hours from creation to first recorded resolved history "
            "event divided by resolved window-created tickets.",
            "காலத்தில் உருவாக்கிய தீர்வுள்ள சீட்டுகளின் உருவாக்கம் முதல் முதல் தீர்வு வரையிலான மொத்த மணிநேரம் / சீட்டுகள்.",
            "helpdesk_tickets → helpdesk_history",
            "ticket.created_at population; immutable first resolution",
        ),
        (
            "mentor_sessions",
            "support",
            "Completed mentor sessions",
            "நிறைவுற்ற வழிகாட்டி அமர்வுகள்",
            "Mentor sessions with completed_at in the window, scoped by the assignment enrollment.",
            "ஒதுக்கீட்டுச் சேர்க்கை வரம்பில் காலத்தில் நிறைவு நேரம் பதிவான வழிகாட்டி அமர்வுகள்.",
            "mentoring_sessions → mentor_assignments → enrollments",
            "completed_at",
        ),
        (
            "mentor_follow_ups",
            "support",
            "Mentor follow-ups due",
            "நிலுவை வழிகாட்டி தொடர் பணிகள்",
            "Mentor follow-ups due in the window, with their current state breakdown.",
            "காலத்தில் செய்ய வேண்டிய வழிகாட்டி தொடர் பணிகள்; தற்போதைய நிலைப் பிரிவுடன்.",
            "mentoring_follow_ups → mentor_assignments → enrollments",
            "due_at; current state",
        ),
        (
            "business_follow_ups",
            "support",
            "Business follow-ups due",
            "நிலுவை தொழில் தொடர் பணிகள்",
            "Business follow-ups due in the window, with their current status breakdown.",
            "காலத்தில் செய்ய வேண்டிய தொழில் தொடர் பணிகள்; தற்போதைய நிலைப் பிரிவுடன்.",
            "business_follow_ups → business_profiles → enrollments",
            "due_on; current status",
        ),
    ]
    result = [_definition(*spec) for spec in specs]
    percent_keys = {
        "lead_to_application_percent",
        "application_to_selection_percent",
        "selection_to_enrollment_percent",
        "quiz_pass_percent",
        "quiz_mean_percent",
        "assignment_pass_percent",
        "attendance_percent",
    }
    for metric in result:
        metric.caveat_en = "Only recorded source facts are included; missing data is not imputed."
        metric.caveat_ta = "பதிவான மூலத் தகவல்கள் மட்டும் சேர்க்கப்படும்; இல்லாத தரவு ஊகிக்கப்படாது."
        if metric.key in percent_keys:
            metric.unit = "percent"
            metric.caveat_en = "A zero denominator is unavailable, not zero percent."
            metric.caveat_ta = "பகுதி எண் பூஜ்ஜியம் என்றால் விகிதம் கிடைக்காது; பூஜ்ஜிய சதவீதம் அல்ல."
        if "current" in metric.temporal_basis:
            metric.caveat_en += (" " if metric.caveat_en else "") + CURRENT_EN
            metric.caveat_ta += (" " if metric.caveat_ta else "") + CURRENT_TA
        if metric.key.startswith("funding_") or metric.key.startswith("ticket"):
            metric.caveat_en += (" " if metric.caveat_en else "") + MEMBERSHIP_EN
            metric.caveat_ta += (" " if metric.caveat_ta else "") + MEMBERSHIP_TA
        if metric.key in {
            "business_outcome_reports",
            "businesses_started",
            "businesses_active",
            "jobs_created",
        }:
            metric.caveat_en = (
                "Self-reported B02 evidence, separate from impact "
                "measurements; coverage may be incomplete. "
                "Enrollment counts are not unique-person counts or verified causal impact."
            )
            metric.caveat_ta = (
                "சுய அறிக்கையின் B02 சான்று; தாக்க அளவீடுகளிலிருந்து தனியானது; "
                "முழுமையற்றிருக்கலாம். "
                "சேர்க்கை எண்ணிக்கை தனித்த நபர் எண்ணிக்கையோ உறுதிசெய்த காரண விளைவோ அல்ல."
            )
        if metric.key == "funding_facilitated_amount":
            metric.unit = "INR"
        if metric.key == "ticket_resolution_hours":
            metric.unit = "hours"
    return result
