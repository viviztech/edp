import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from test_cms import cms  # noqa: F401
from test_identity import auth  # noqa: F401

from app.modules.cms.models import EditorialEntry
from app.modules.identity.models import AuditLog, Organization

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def editorial(request):
    return request.getfixturevalue("cms")


def test_editorial_publication_requires_explicit_draft_transition(editorial):
    client, engine, page_base, _ = editorial
    base = page_base.removesuffix("pages") + "editorial"
    public = base.replace("/cms/", "/public/")
    created = client.post(
        base,
        json={
            "kind": "news",
            "slug": "synthetic-story",
            "locale": "en",
            "title": "Approved story",
            "body": "Approved public content",
        },
    )
    assert created.status_code == 201, created.text
    entry = created.json()
    path = base + "/" + entry["id"]
    live = public + "/news/synthetic-story?locale=en"
    assert client.get(live).status_code == 404
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 200
    edit = {"expected_version": 2, "title": "Unpublished edit", "body": "Private draft"}
    rejected = client.patch(path, json=edit)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "published_entry_read_only"
    assert client.get(live).json()["body"] == "Approved public content"
    assert client.get(live.replace("locale=en", "locale=ta")).status_code == 404
    assert client.post(path + "/archive", json={"expected_version": 2}).status_code == 409
    archived = client.post(
        path + "/archive", json={"expected_version": 2, "reason": "Prepare a revised draft"}
    )
    assert archived.status_code == 200
    assert client.get(live).status_code == 404
    assert client.patch(path, json={**edit, "expected_version": 3}).status_code == 409
    assert client.post(path + "/restore", json={"expected_version": 2}).status_code == 409
    restored = client.post(path + "/restore", json={"expected_version": 3})
    assert restored.status_code == 200
    assert restored.json()["state"] == "draft"
    assert client.patch(path, json={**edit, "expected_version": 4}).status_code == 200
    assert client.get(live).status_code == 404
    assert client.post(path + "/publish", json={"expected_version": 5}).status_code == 200
    assert client.get(live).json()["body"] == "Private draft"
    with Session(engine) as db:
        actions = list(
            db.scalars(select(AuditLog.action).where(AuditLog.resource_id == UUID(entry["id"])))
        )
    assert sorted(actions) == sorted(
        [
            "cms.editorial.created",
            "cms.editorial.published",
            "cms.editorial.archived",
            "cms.editorial.restored",
            "cms.editorial.updated",
            "cms.editorial.published",
        ]
    )


def test_staff_editorial_exact_address_lookup_is_bounded_and_scoped(editorial):
    client, engine, page_base, _ = editorial
    base = page_base.removesuffix("pages") + "editorial"
    org = UUID(page_base.split("/")[-2])
    ids = []
    for kind, locale, slug in [
        ("news", "en", "target-address"),
        ("news", "ta", "target-address"),
        ("event", "en", "target-address"),
        ("news", "en", "target-address-other"),
    ]:
        created = client.post(
            base,
            json={"kind": kind, "locale": locale, "slug": slug, "title": "Entry", "body": "Body"},
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])
    with Session(engine) as db:
        foreign = Organization(name="Foreign address lookup scope")
        db.add(foreign)
        db.flush()
        foreign_id = foreign.id
        db.add(
            EditorialEntry(
                organization_id=foreign_id,
                kind="news",
                locale="en",
                slug="target-address",
                title="Foreign entry",
                body="Foreign body",
            )
        )
        db.commit()
    params = {"kind": "news", "locale": "en", "slug": "target-address", "limit": 1}
    found = client.get(base, params=params)
    assert found.status_code == 200
    assert [item["id"] for item in found.json()["items"]] == [ids[0]]
    assert found.json()["next_cursor"] is None
    assert client.get(base, params={**params, "slug": "target"}).json()["items"] == []
    denied = client.get(base.replace(str(org), str(foreign_id)), params=params)
    assert denied.status_code == 403
    for slug in ["", "../address", "Bad", "a" * 121]:
        assert client.get(base, params={**params, "slug": slug}).status_code == 422


@pytest.mark.parametrize("kind", ["news", "event"])
def test_public_editorial_keyset_matches_order_and_has_bounded_query_count(editorial, kind):
    client, engine, page_base, _ = editorial
    org = UUID(page_base.split("/")[-2])
    public = page_base.replace("/cms/", "/public/").removesuffix("pages") + "editorial"
    early = datetime(2026, 10, 23, 8, tzinfo=UTC)
    late = datetime(2026, 10, 24, 8, tzinfo=UTC)
    values = [
        (1, 20, late),
        (8, 0, early),
        (2, 10, early),
        (4, 0, None),
        (5, 10, None),
        (3, 0, early),
    ]
    with Session(engine) as db:
        for number, order, starts in values:
            db.add(
                EditorialEntry(
                    id=UUID(int=number),
                    organization_id=org,
                    kind=kind,
                    locale="en",
                    slug=f"entry-{number}",
                    title=f"Entry {number}",
                    body="Synthetic content",
                    state="published",
                    version=1,
                    sort_order=order,
                    starts_at=starts,
                    published_at=early,
                )
            )
        db.commit()
    expected = [3, 4, 8, 2, 5, 1] if kind == "news" else [3, 8, 2, 1, 4, 5]
    found = []
    cursor = None
    queries = []

    def count_queries(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT") and "cms_editorial_entries" in statement:
            queries.append(statement)

    while True:
        queries.clear()
        event.listen(Engine, "before_cursor_execute", count_queries)
        try:
            response = client.get(
                public,
                params={
                    "kind": kind,
                    "locale": "en",
                    "limit": 2,
                    **({"cursor": cursor} if cursor else {}),
                },
            )
        finally:
            event.remove(Engine, "before_cursor_execute", count_queries)
        assert response.status_code == 200, response.text
        assert len(queries) == (2 if cursor else 1)
        page = response.json()
        found.extend(UUID(item["id"]).int for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
        assert len(found) <= len(expected)
    assert found == expected
    assert len(set(found)) == len(found)


def test_public_editorial_cursor_is_bound_to_scope_kind_locale_and_publication(editorial):
    client, engine, page_base, _ = editorial
    org = UUID(page_base.split("/")[-2])
    public = page_base.replace("/cms/", "/public/").removesuffix("pages") + "editorial"
    with Session(engine) as db:
        foreign = Organization(name="Other synthetic editorial scope")
        db.add(foreign)
        db.flush()
        ids = []
        for organization_id, kind, locale, state in [
            (foreign.id, "news", "en", "published"),
            (org, "event", "en", "published"),
            (org, "news", "ta", "published"),
            (org, "news", "en", "draft"),
            (org, "news", "en", "archived"),
        ]:
            entry = EditorialEntry(
                organization_id=organization_id,
                kind=kind,
                locale=locale,
                slug=f"scoped-entry-{state}",
                title="Scoped entry",
                body="Synthetic content",
                state=state,
            )
            db.add(entry)
            db.flush()
            ids.append(entry.id)
        db.commit()
    for cursor in [*ids, uuid4()]:
        response = client.get(
            public, params={"kind": "news", "locale": "en", "cursor": str(cursor)}
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_cursor"
