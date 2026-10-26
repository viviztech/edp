import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_businesses_db import BUSINESS_FIELDS, participant_context
from test_identity import account, auth  # noqa: F401

from app.modules.applications.models import Application
from app.modules.business_tools.models import (
    BusinessCard,
    CatalogueItem,
    CustomerContact,
    CustomerTask,
    Quotation,
    QuotationLine,
    ToolCommand,
    ToolHistory,
)
from app.modules.identity.models import AuditLog, Role, User, UserRole, now
from app.modules.programs.models import Enrollment, Participant

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)

CARD = {
    "name_en": "Synthetic bakery <script>alert(1)</script>",
    "name_ta": "செயற்கை பேக்கரி",
    "tagline_en": "Fresh bread",
    "tagline_ta": "புதிய ரொட்டி",
    "description_en": "Synthetic business description",
    "description_ta": "செயற்கை வணிக விவரம்",
    "phone": "+91 00000 00000",
    "email": "synthetic@example.com",
    "website": "https://example.com/bakery",
    "address_en": "Synthetic street",
    "address_ta": "செயற்கை தெரு",
}
ITEM = {
    "kind": "product",
    "name_en": "Bread",
    "name_ta": "ரொட்டி",
    "description_en": "Fresh synthetic bread",
    "description_ta": "செயற்கை ரொட்டி",
    "available": True,
    "price": "12.50",
    "currency": "INR",
}
CONTACT = {
    "name": "Synthetic customer",
    "phone": "+91 00000 00000",
    "email": "customer@example.com",
    "notes": "Private customer context",
    "status": "lead",
}


def setup(request):
    context, headers, org, other, _, enrollment, actor = participant_context(request)
    client, engine, _, _ = context
    response = client.post(
        f"/api/v1/businesses/organizations/{org}/profiles",
        headers=headers,
        json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS, "public_opt_in": True},
    )
    assert response.status_code == 201, response.text
    profile = response.json()["id"]
    base = f"/api/v1/business-tools/organizations/{org}/profiles/{profile}"
    return context, headers, org, other, enrollment, actor, profile, base


def write(client, url, headers, data, expected=200):
    response = client.post(url, headers=headers, json={"request_id": str(uuid4()), **data})
    assert response.status_code == expected, response.text
    return response.json()


def quote_fields(**changes):
    return {
        "customer_name": "Synthetic buyer <img src=x onerror=alert(1)>",
        "customer_address": "Synthetic address & text",
        "issued_on": now().date().isoformat(),
        "valid_until": (now() + timedelta(days=15)).date().isoformat(),
        "currency": "INR",
        "notes": "No accounting claims <script>x</script>",
        "discount": "0.01",
        "lines": [
            {"description": "Manual rounding line", "quantity": "0.500", "unit_price": "0.01"},
            {"description": "Other line", "quantity": "2.000", "unit_price": "12.50"},
        ],
        **changes,
    }


def test_card_idempotency_draft_publish_revoke_and_safe_projection(request):
    context, headers, org, _, _, _, profile, base = setup(request)
    client, engine, _, _ = context
    assert client.get(base + "/card", headers=headers).json() is None
    payload = {"request_id": str(uuid4()), "expected_version": 0, **CARD}
    first = write(client, base + "/card", headers, payload)
    retry = write(client, base + "/card", headers, payload)
    assert first == retry and first["published"] is False
    public_url = f"/api/v1/public/business-tools/cards/{first['share_id']}"
    assert client.get(public_url).status_code == 404
    write(client, base + "/card", headers, {**payload, "name_en": "Changed command"}, 409)
    write(client, base + "/card", headers, {"expected_version": 0, **CARD}, 409)
    published = write(
        client,
        base + "/card/sharing",
        headers,
        {"expected_version": first["version"], "published": True},
    )
    public = client.get(public_url)
    assert public.status_code == 200 and public.headers["cache-control"] == "no-store"
    assert public.json() == {"share_id": first["share_id"], **CARD}
    assert (
        not {"id", "profile_id", "enrollment_id", "organization_id", "version"}
        & public.json().keys()
    )
    # Editing published content returns it to private preview until a separate publish decision.
    revised = write(
        client,
        base + "/card",
        headers,
        {"expected_version": published["version"], **CARD, "tagline_en": "Preview"},
    )
    assert revised["published"] is False and client.get(public_url).status_code == 404
    published = write(
        client,
        base + "/card/sharing",
        headers,
        {"expected_version": revised["version"], "published": True},
    )
    assert client.get(public_url).json()["tagline_en"] == "Preview"
    write(
        client,
        base + "/card/sharing",
        headers,
        {"expected_version": published["version"], "published": False},
    )
    assert client.get(public_url).status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(BusinessCard)) == 1
        assert db.scalar(select(func.count()).select_from(ToolCommand)) == 5
        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == org, AuditLog.action.like("business_tool.%")
                )
            )
        )
        assert all("synthetic@example.com" not in row.changed_fields for row in audits)
        assert all(str(profile) not in row.changed_fields for row in audits)


def test_card_artifact_is_escaped_private_and_audited(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client, engine, _, _ = context
    card = write(client, base + "/card", headers, {"expected_version": 0, **CARD})
    assert client.get(base + "/card/artifact").status_code == 401
    artifact = client.get(base + "/card/artifact", headers=headers)
    assert artifact.status_code == 200 and "attachment" in artifact.headers["content-disposition"]
    assert "<script>" not in artifact.text and "&lt;script&gt;" in artifact.text
    assert "செயற்கை பேக்கரி" in artifact.text
    assert "default-src 'none'" in artifact.headers["content-security-policy"]
    with Session(engine) as db:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.resource_id == card["id"],
                AuditLog.action == "business_tool.card_downloaded",
            )
        )
        assert audit is not None


@pytest.mark.parametrize(
    "field,value",
    [
        ("website", "javascript:alert(1)"),
        ("website", "https://user:pass@example.com"),
        ("email", "bad address"),
        ("name_en", "   "),
        ("description_en", "x" * 4001),
    ],
)
def test_card_rejects_invalid_public_fields(request, field, value):
    context, headers, _, _, _, _, _, base = setup(request)
    write(context[0], base + "/card", headers, {"expected_version": 0, **CARD, field: value}, 422)


def test_owner_permission_peer_staff_org_and_current_lifecycle(request):
    context, headers, org, other, enrollment, actor, profile, base = setup(request)
    client, engine, _, _ = context
    card = write(client, base + "/card", headers, {"expected_version": 0, **CARD})
    published = write(
        client,
        base + "/card/sharing",
        headers,
        {"expected_version": card["version"], "published": True},
    )
    public = f"/api/v1/public/business-tools/cards/{published['share_id']}"
    for address, role_name, expected in [
        ("tools-peer@example.com", "Participant", 404),
        ("tools-staff@example.com", "Program Director", 403),
    ]:
        credentials = account(context, address)
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == address))
            role = db.scalar(select(Role).where(Role.name == role_name))
            db.add(UserRole(user_id=user.id, organization_id=org, role_id=role.id))
            db.commit()
        login = client.post("/api/v1/auth/login", json=credentials)
        peer_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        for path in ("/card", "/catalogue", "/quotes", "/contacts", "/tasks", "/history"):
            assert client.get(base + path, headers=peer_headers).status_code == expected
        write(client, base + "/card", peer_headers, {"expected_version": 1, **CARD}, expected)
    other_base = f"/api/v1/business-tools/organizations/{other}/profiles/{profile}"
    assert client.get(other_base + "/card", headers=headers).status_code == 403
    # Existing explicit share does not survive withdrawal, and exact retries reauthorize first.
    payload = {"request_id": str(uuid4()), "expected_version": published["version"], **CARD}
    write(client, base + "/card", headers, payload)
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="withdrawn"))
        db.commit()
    for path in ("/card", "/catalogue", "/quotes", "/contacts", "/tasks", "/history"):
        assert client.get(base + path, headers=headers).status_code == 404
    write(client, base + "/card", headers, payload, 404)
    assert client.get(public).status_code == 404
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="active"))
        db.execute(
            update(Participant)
            .where(Participant.person_id == db.get(User, actor).person_id)
            .values(status="withdrawn")
        )
        db.commit()
    assert client.get(base + "/card", headers=headers).status_code == 404


def test_public_card_rechecks_permission_revocation(request):
    context, headers, org, _, _, actor, _, base = setup(request)
    client, engine, _, _ = context
    card = write(client, base + "/card", headers, {"expected_version": 0, **CARD})
    write(client, base + "/card/sharing", headers, {"expected_version": 1, "published": True})
    public = f"/api/v1/public/business-tools/cards/{card['share_id']}"
    assert client.get(public).status_code == 200
    with Session(engine) as db:
        db.execute(
            delete(UserRole).where(UserRole.user_id == actor, UserRole.organization_id == org)
        )
        db.commit()
    assert client.get(public).status_code == 404
    assert client.get(base + "/card", headers=headers).status_code == 403


def test_catalogue_explicit_sharing_exact_price_history_and_revoke(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client = context[0]
    first = write(client, base + "/catalogue/items", headers, ITEM, 201)
    second = write(
        client,
        base + "/catalogue/items",
        headers,
        {**ITEM, "name_en": "Unavailable item", "available": False},
        201,
    )
    assert Decimal(first["price"]) == Decimal("12.50")
    page = client.get(base + "/catalogue?limit=1&offset=1", headers=headers).json()
    assert len(page["items"]) == 1 and page["offset"] == 1 and page["limit"] == 1
    settings = page["settings"]
    shared = write(
        client,
        base + "/catalogue/sharing",
        headers,
        {"expected_version": settings["version"], "published": True},
    )
    url = f"/api/v1/public/business-tools/catalogues/{shared['share_id']}"
    public = client.get(url)
    assert public.status_code == 200 and public.headers["cache-control"] == "no-store"
    assert public.json()["items"] == [ITEM]
    changed = write(
        client,
        base + f"/catalogue/items/{first['id']}/update",
        headers,
        {**ITEM, "expected_version": first["version"], "price": "14.10"},
    )
    assert changed["version"] == 2 and client.get(url).status_code == 404
    write(
        client,
        base + f"/catalogue/items/{first['id']}/update",
        headers,
        {**ITEM, "expected_version": first["version"]},
        409,
    )
    history = client.get(
        base + f"/history?kind=catalogue_item&resource_id={first['id']}", headers=headers
    ).json()["items"]
    assert [row["version"] for row in history] == [2, 1]
    assert second["id"] != first["id"]
    write(client, base + "/catalogue/items", headers, {**ITEM, "price": "1.001"}, 422)
    write(client, base + "/catalogue/items", headers, {**ITEM, "price": "-0.01"}, 422)
    write(client, base + "/catalogue/items", headers, {**ITEM, "currency": "XYZ"}, 422)
    assert client.get(base + "/catalogue?limit=101", headers=headers).status_code == 422


def test_quotation_decimal_rounding_issue_immutability_and_safe_export(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client, engine, _, _ = context
    data = {"request_id": str(uuid4()), **quote_fields()}
    draft = write(client, base + "/quotes", headers, data, 201)
    assert draft == write(client, base + "/quotes", headers, data, 201)
    assert draft["subtotal"] == "25.01" and draft["discount"] == "0.01"
    assert draft["total"] == "25.00" and draft["lines"][0]["line_total"] == "0.01"
    issue = {"request_id": str(uuid4()), "expected_version": draft["version"]}
    issued = write(client, base + f"/quotes/{draft['id']}/issue", headers, issue)
    assert issued == write(client, base + f"/quotes/{draft['id']}/issue", headers, issue)
    assert issued["status"] == "issued" and issued["version"] == 2 and issued["issued_at"]
    write(
        client,
        base + f"/quotes/{draft['id']}/update",
        headers,
        {**quote_fields(), "expected_version": 2},
        409,
    )
    write(client, base + f"/quotes/{draft['id']}/issue", headers, {"expected_version": 2}, 409)
    assert client.get(base + f"/quotes/{draft['id']}", headers=headers).json() == issued
    artifact = client.get(base + f"/quotes/{draft['id']}/artifact", headers=headers)
    assert (
        artifact.status_code == 200
        and 'filename="quotation.html"' in artifact.headers["content-disposition"]
    )
    assert "<img" not in artifact.text and "&lt;img" in artifact.text
    assert "<script>" not in artifact.text and "25.00 INR" in artifact.text
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Quotation)) == 1
        assert db.scalar(select(func.count()).select_from(QuotationLine)) == 2
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "business_tool.quote_downloaded")
        )
        quote = db.get(Quotation, UUID(issued["id"]))
        with pytest.raises(DBAPIError):
            db.execute(
                update(Quotation)
                .where(Quotation.id == quote.id)
                .values(customer_name="Tampered", version=3)
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(delete(QuotationLine).where(QuotationLine.quotation_id == quote.id))
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(delete(Quotation).where(Quotation.id == quote.id))
            db.commit()


def test_quotation_draft_update_stale_catalogue_and_issued_snapshot(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client = context[0]
    item = write(client, base + "/catalogue/items", headers, ITEM, 201)
    fields = quote_fields(
        discount="0.00",
        lines=[
            {
                "description": "Client cannot replace catalogue snapshot",
                "quantity": "2.000",
                "unit_price": item["price"],
                "catalogue_item_id": item["id"],
                "catalogue_version": item["version"],
            }
        ],
    )
    quote = write(client, base + "/quotes", headers, fields, 201)
    assert quote["lines"][0]["description"] == "Bread / ரொட்டி"
    item = write(
        client,
        base + f"/catalogue/items/{item['id']}/update",
        headers,
        {**ITEM, "expected_version": item["version"], "price": "20.00"},
    )
    write(client, base + f"/quotes/{quote['id']}/issue", headers, {"expected_version": 1}, 409)
    write(client, base + "/quotes", headers, fields, 409)
    fields["lines"][0].update(unit_price=item["price"], catalogue_version=item["version"])
    saved = write(
        client, base + f"/quotes/{quote['id']}/update", headers, {**fields, "expected_version": 1}
    )
    assert saved["total"] == "40.00" and saved["version"] == 2
    write(
        client,
        base + f"/quotes/{quote['id']}/update",
        headers,
        {**fields, "expected_version": 1},
        409,
    )
    issued = write(client, base + f"/quotes/{quote['id']}/issue", headers, {"expected_version": 2})
    write(
        client,
        base + f"/catalogue/items/{item['id']}/update",
        headers,
        {**ITEM, "expected_version": item["version"], "price": "99.99", "available": False},
    )
    assert client.get(base + f"/quotes/{quote['id']}", headers=headers).json() == issued


@pytest.mark.parametrize(
    "changes",
    [
        {"discount": "999.99"},
        {"lines": []},
        {
            "lines": [
                {"description": "Overflow", "quantity": "1000000", "unit_price": "999999999999.99"}
            ]
        },
        {"lines": [{"description": "Bad precision", "quantity": "1.0001", "unit_price": "1.00"}]},
        {"lines": [{"description": "Bad price", "quantity": "1", "unit_price": "0.001"}]},
        {"valid_until": "2000-01-01"},
        {"lines": [{"description": "x", "quantity": "1", "unit_price": "1.00"}] * 51},
    ],
)
def test_quotation_rejects_precision_overflow_dates_and_row_limits(request, changes):
    context, headers, _, _, _, _, _, base = setup(request)
    write(context[0], base + "/quotes", headers, quote_fields(**changes), 422)


def test_mini_crm_private_contacts_utc_tasks_terminal_history_and_retries(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client, engine, _, _ = context
    data = {"request_id": str(uuid4()), **CONTACT}
    contact = write(client, base + "/contacts", headers, data, 201)
    assert contact == write(client, base + "/contacts", headers, data, 201)
    contact = write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": 1, "status": "customer"},
    )
    write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": 1},
        409,
    )
    task_data = {
        "request_id": str(uuid4()),
        "contact_id": contact["id"],
        "title": "Synthetic call",
        "notes": "Stored only; no provider",
        "due_at": "2026-10-25T10:00:00+05:30",
    }
    task = write(client, base + "/tasks", headers, task_data, 201)
    assert task == write(client, base + "/tasks", headers, task_data, 201)
    assert task["due_at"] == "2026-10-25T04:30:00Z"
    assert client.get(base + "/contacts?status=customer&search=Synthetic", headers=headers).json()[
        "items"
    ] == [contact]
    assert client.get(
        base + f"/tasks?contact_id={contact['id']}&status=pending", headers=headers
    ).json()["items"] == [task]
    settled_data = {
        "request_id": str(uuid4()),
        "expected_version": task["version"],
        "title": task["title"],
        "notes": task["notes"],
        "due_at": task["due_at"],
        "status": "completed",
    }
    settled = write(client, base + f"/tasks/{task['id']}/update", headers, settled_data)
    assert settled == write(client, base + f"/tasks/{task['id']}/update", headers, settled_data)
    assert settled["completed_at"] is not None
    write(
        client,
        base + f"/tasks/{task['id']}/update",
        headers,
        {**settled_data, "request_id": str(uuid4()), "expected_version": 2, "status": "pending"},
        409,
    )
    history = client.get(base + "/history?kind=task", headers=headers).json()["items"]
    assert [row["version"] for row in history] == [2, 1]
    assert all("Stored only" not in str(row) for row in history)
    contact = write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": contact["version"], "status": "archived"},
    )
    write(client, base + "/tasks", headers, {**task_data, "request_id": str(uuid4())}, 409)
    write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": contact["version"]},
        409,
    )
    assert client.get(base + "/tasks?status=completed", headers=headers).json()["items"] == [
        settled
    ]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(CustomerContact)) == 1
        assert db.scalar(select(func.count()).select_from(CustomerTask)) == 1


def test_mini_crm_rejects_naive_times_foreign_refs_request_reuse_and_invalid_filters(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client = context[0]
    contact = write(client, base + "/contacts", headers, CONTACT, 201)
    task = {"contact_id": contact["id"], "title": "Synthetic", "due_at": "2026-10-25T10:00:00"}
    write(client, base + "/tasks", headers, task, 422)
    write(
        client,
        base + "/tasks",
        headers,
        {**task, "due_at": "2026-10-25T10:00:00Z", "contact_id": str(uuid4())},
        404,
    )
    data = {"request_id": str(uuid4()), **CONTACT}
    write(client, base + "/contacts", headers, data, 201)
    write(client, base + "/contacts", headers, {**data, "notes": "Changed same UUID"}, 409)
    for path in (
        "/contacts?limit=0",
        "/tasks?status=bogus",
        "/history?kind=bogus",
        "/tasks?offset=10001",
        "/contacts?search=",
    ):
        assert client.get(base + path, headers=headers).status_code == 422


def test_concurrent_exact_commands_create_only_one_resource(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client, engine, _, _ = context
    payload = {"request_id": str(uuid4()), **CONTACT}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(base + "/contacts", headers=headers, json=payload), range(2)
            )
        )
    assert all(response.status_code == 201 for response in responses)
    assert responses[0].json() == responses[1].json()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(CustomerContact)) == 1
        assert db.scalar(select(func.count()).select_from(ToolCommand)) == 1
        assert db.scalar(select(func.count()).select_from(ToolHistory)) == 1


def test_database_scope_versions_immutable_history_and_totals(request):
    context, headers, org, other, _, _, profile, base = setup(request)
    client, engine, _, _ = context
    item = write(client, base + "/catalogue/items", headers, ITEM, 201)
    contact = write(client, base + "/contacts", headers, CONTACT, 201)
    draft = write(client, base + "/quotes", headers, quote_fields(), 201)
    with Session(engine) as db:
        for statement in (
            update(CatalogueItem)
            .where(CatalogueItem.id == item["id"])
            .values(organization_id=other, version=2),
            update(CustomerContact).where(CustomerContact.id == contact["id"]).values(version=1),
            update(ToolHistory).where(ToolHistory.profile_id == profile).values(action="tampered"),
            delete(ToolCommand).where(ToolCommand.profile_id == profile),
            update(Quotation)
            .where(Quotation.id == draft["id"])
            .values(subtotal=100, total=Decimal("99.99"), version=2),
        ):
            with pytest.raises(DBAPIError):
                db.execute(statement)
                db.commit()
            db.rollback()
        # Even valid-looking arithmetic cannot assign a line reference to another tenant.
        line = db.scalar(select(QuotationLine).where(QuotationLine.quotation_id == draft["id"]))
        with pytest.raises(DBAPIError):
            db.execute(
                update(QuotationLine)
                .where(QuotationLine.id == line.id)
                .values(catalogue_item_id=item["id"], catalogue_version=None)
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(
                update(QuotationLine)
                .where(QuotationLine.id == line.id)
                .values(organization_id=other, catalogue_item_id=item["id"], catalogue_version=1)
            )
            db.commit()
        db.rollback()
        assert db.get(CustomerContact, UUID(contact["id"])).organization_id == org


def test_existing_peer_references_cannot_be_reused_by_owner(request):
    context, headers, org, _, enrollment, _, _, base = setup(request)
    client, engine, _, _ = context
    credentials = account(context, "tools-second-owner@example.com")
    with Session(engine) as db:
        peer = db.scalar(select(User).where(User.email == credentials["email"]))
        participant_role = db.scalar(select(Role).where(Role.name == "Participant"))
        db.add(UserRole(user_id=peer.id, role_id=participant_role.id, organization_id=org))
        first_enrollment = db.get(Enrollment, enrollment)
        first_application = db.get(Application, first_enrollment.application_id)
        application = Application(
            organization_id=org,
            person_id=peer.person_id,
            form_id=first_application.form_id,
            cycle_id=first_application.cycle_id,
            state="enrolled",
            version=8,
            application_number="EDP-TOOLS-PEER",
            submitted_at=now(),
        )
        participant = Participant(organization_id=org, person_id=peer.person_id, status="active")
        db.add_all([application, participant])
        db.flush()
        peer_enrollment = Enrollment(
            organization_id=org,
            participant_id=participant.id,
            program_id=first_enrollment.program_id,
            cohort_id=first_enrollment.cohort_id,
            application_id=application.id,
            status="active",
        )
        db.add(peer_enrollment)
        db.commit()
        peer_enrollment_id = peer_enrollment.id
    login = client.post("/api/v1/auth/login", json=credentials)
    peer_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    response = client.post(
        f"/api/v1/businesses/organizations/{org}/profiles",
        headers=peer_headers,
        json={"enrollment_id": str(peer_enrollment_id), **BUSINESS_FIELDS},
    )
    assert response.status_code == 201, response.text
    peer_base = base.rsplit("/", 1)[0] + "/" + response.json()["id"]
    item = write(client, peer_base + "/catalogue/items", peer_headers, ITEM, 201)
    contact = write(client, peer_base + "/contacts", peer_headers, CONTACT, 201)
    quote = write(client, peer_base + "/quotes", peer_headers, quote_fields(), 201)
    write(
        client,
        base + "/quotes",
        headers,
        quote_fields(
            lines=[
                {
                    "description": "Foreign catalogue item",
                    "quantity": "1.000",
                    "unit_price": item["price"],
                    "catalogue_item_id": item["id"],
                    "catalogue_version": item["version"],
                }
            ]
        ),
        404,
    )
    write(
        client,
        base + "/tasks",
        headers,
        {
            "contact_id": contact["id"],
            "title": "Foreign contact",
            "due_at": now().isoformat(),
        },
        404,
    )
    write(
        client,
        base + f"/catalogue/items/{item['id']}/update",
        headers,
        {**ITEM, "expected_version": item["version"]},
        404,
    )
    write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": contact["version"]},
        404,
    )
    assert client.get(base + f"/quotes/{quote['id']}", headers=headers).status_code == 404
    assert client.get(base + f"/catalogue/items/{item['id']}", headers=headers).status_code == 404
    assert client.get(base + f"/contacts/{contact['id']}", headers=headers).status_code == 404
    assert client.get(peer_base + "/history", headers=headers).status_code == 404


def test_body_limits_and_competing_stale_commands(request):
    context, headers, _, _, _, _, _, base = setup(request)
    client = context[0]
    response = client.post(
        base + "/contacts",
        headers={**headers, "Content-Type": "application/json"},
        content=b" " * 262145,
    )
    assert response.status_code == 413
    contact = write(client, base + "/contacts", headers, CONTACT, 201)
    url = base + f"/contacts/{contact['id']}/update"
    payloads = [
        {"request_id": str(uuid4()), **CONTACT, "expected_version": 1, "notes": note}
        for note in ("First concurrent edit", "Second concurrent edit")
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda data: client.post(url, headers=headers, json=data), payloads)
        )
    assert sorted(response.status_code for response in responses) == [200, 409]
    current = client.get(base + "/contacts", headers=headers).json()["items"][0]
    assert current["version"] == 2
    assert current["notes"] in {payload["notes"] for payload in payloads}


def test_detail_reads_recover_filtered_or_paginated_edits_and_reauthorize(request):
    context, headers, org, _, enrollment, _, _, base = setup(request)
    client, engine, _, _ = context
    item = write(client, base + "/catalogue/items", headers, ITEM, 201)
    write(client, base + "/catalogue/items", headers, {**ITEM, "name_en": "Newer item"}, 201)
    item = write(
        client,
        base + f"/catalogue/items/{item['id']}/update",
        headers,
        {**ITEM, "expected_version": 1, "available": False},
    )
    contact = write(client, base + "/contacts", headers, CONTACT, 201)
    write(client, base + "/contacts", headers, {**CONTACT, "name": "Newer contact"}, 201)
    due = (now() + timedelta(days=2)).isoformat()
    task = write(
        client,
        base + "/tasks",
        headers,
        {"contact_id": contact["id"], "title": "Original task", "due_at": due},
        201,
    )
    write(
        client,
        base + "/tasks",
        headers,
        {
            "contact_id": contact["id"],
            "title": "Earlier task",
            "due_at": (now() + timedelta(days=1)).isoformat(),
        },
        201,
    )
    task = write(
        client,
        base + f"/tasks/{task['id']}/update",
        headers,
        {
            "expected_version": 1,
            "title": "Original task",
            "notes": "Completed elsewhere",
            "due_at": due,
            "status": "completed",
        },
    )
    contact = write(
        client,
        base + f"/contacts/{contact['id']}/update",
        headers,
        {**CONTACT, "expected_version": 1, "status": "archived"},
    )
    assert item["id"] not in {
        row["id"]
        for row in client.get(base + "/catalogue?limit=1", headers=headers).json()["items"]
    }
    assert contact["id"] not in {
        row["id"]
        for row in client.get(base + "/contacts?status=lead&limit=1", headers=headers).json()[
            "items"
        ]
    }
    assert task["id"] not in {
        row["id"]
        for row in client.get(base + "/tasks?status=pending&limit=1", headers=headers).json()[
            "items"
        ]
    }
    paths = [
        (f"/catalogue/items/{item['id']}", item),
        (f"/contacts/{contact['id']}", contact),
        (f"/tasks/{task['id']}", task),
    ]
    for path, expected in paths:
        assert client.get(base + path, headers=headers).json() == expected
        assert client.get(base + path).status_code == 401
    for address, role_name, status in (
        ("detail-peer@example.com", "Participant", 404),
        ("detail-staff@example.com", "Program Director", 403),
    ):
        credentials = account(context, address)
        with Session(engine) as db:
            peer = db.scalar(select(User).where(User.email == address))
            role = db.scalar(select(Role).where(Role.name == role_name))
            db.add(UserRole(user_id=peer.id, organization_id=org, role_id=role.id))
            db.commit()
        login = client.post("/api/v1/auth/login", json=credentials)
        peer_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        for path, _ in paths:
            assert client.get(base + path, headers=peer_headers).status_code == status
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="withdrawn"))
        db.commit()
    for path, _ in paths:
        assert client.get(base + path, headers=headers).status_code == 404
