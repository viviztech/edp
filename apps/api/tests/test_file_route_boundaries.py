from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.parametrize("kind", ["application", "cms", "assignment", "material", "helpdesk"])
def test_only_registered_raw_put_paths_bypass_json_cap_and_still_require_authentication(kind):
    org, resource, document, assignment = uuid4(), uuid4(), uuid4(), uuid4()
    path = {
        "application": f"/api/v1/applications/organizations/{org}/applications/{resource}"
        f"/documents/{document}/content",
        "cms": f"/api/v1/cms/organizations/{org}/assets/{resource}/source/content",
        "assignment": f"/api/v1/courses/organizations/{org}/my-learning/{resource}"
        f"/assignments/{assignment}/files/{document}/content",
        "material": f"/api/v1/courses/organizations/{org}/courses/{resource}"
        f"/material-files/{document}/content",
        "helpdesk": f"/api/v1/helpdesk/organizations/{org}/tickets/{resource}"
        f"/files/{document}/content",
    }[kind]
    # An unauthenticated raw body reaches the domain's authentication boundary;
    # it cannot allocate a private buffer or gain a generic file endpoint.
    with TestClient(create_app()) as client:
        response = client.put(
            path, content=b"x" * 262145, headers={"Content-Type": "application/pdf"}
        )
        assert response.status_code in {401, 403}
        for command in (
            client.post(path, content=b"x" * 262145),
            client.patch(path, content=b"x" * 262145),
            client.put(path + "/arbitrary", content=b"x" * 262145),
            client.put(path.replace(str(resource), "invalid-resource"), content=b"x" * 262145),
            client.request("DELETE", path.removesuffix("/content"), content=b"x" * 262145),
        ):
            assert command.status_code == 413


@pytest.mark.parametrize("kind", ["assignment", "material", "helpdesk"])
def test_learning_and_helpdesk_metadata_never_receive_the_raw_byte_exception(kind):
    org, resource, assignment = uuid4(), uuid4(), uuid4()
    paths = {
        "assignment": f"/api/v1/courses/organizations/{org}/my-learning/{resource}"
        f"/assignments/{assignment}/files",
        "material": f"/api/v1/courses/organizations/{org}/material-files",
        "helpdesk": f"/api/v1/helpdesk/organizations/{org}/tickets/{resource}/files",
    }
    with TestClient(create_app()) as client:
        result = client.post(
            paths[kind], content=b"x" * 262145, headers={"Content-Type": "application/json"}
        )
        assert result.status_code == 413
        assert result.json()["error"]["code"] == "body_too_large"


def test_policy_json_keeps_64k_boundary_without_a_generic_upload_exception():
    org, policy = uuid4(), uuid4()
    with TestClient(create_app()) as client:
        response = client.post(f"/api/v1/files/organizations/{org}/policies", content=b"x" * 65537)
        assert response.status_code == 413
        response = client.put(
            f"/api/v1/files/organizations/{org}/policies/{policy}/content", content=b"x" * 65537
        )
        assert response.status_code == 413
