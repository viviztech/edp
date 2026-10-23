"""Closed, organization-scoped administration of configurable file policies."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.modules.files import service
from app.modules.files.policy_schemas import (
    FilePolicyCommand,
    FilePolicyCreate,
    FilePolicyList,
    FilePolicyQuery,
    FilePolicyUpdate,
    FilePolicyView,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/files/organizations/{org}/policies", tags=["file-policies"])


@router.get("", response_model=FilePolicyList)
def policies(
    org: UUID,
    db: DB,
    identity: Principal,
    filters: Annotated[FilePolicyQuery, Query()],
) -> FilePolicyList:
    return service.list_policies(
        db, org, identity[0], filters.purpose, filters.cursor, filters.limit
    )


@router.get("/{policy_id}", response_model=FilePolicyView)
def policy(org: UUID, policy_id: UUID, db: DB, identity: Principal) -> FilePolicyView:
    return service.get_policy(db, org, policy_id, identity[0])


@router.post("", response_model=FilePolicyView, status_code=201)
def create_policy(
    org: UUID, data: FilePolicyCreate, request: Request, db: DB, identity: Principal
) -> FilePolicyView:
    return service.create_policy(db, org, identity[0], data, request.state.request_id)


@router.patch("/{policy_id}", response_model=FilePolicyView)
def edit_policy(
    org: UUID,
    policy_id: UUID,
    data: FilePolicyUpdate,
    request: Request,
    db: DB,
    identity: Principal,
) -> FilePolicyView:
    return service.update_policy(db, org, policy_id, identity[0], data, request.state.request_id)


@router.post("/{policy_id}/publish", response_model=FilePolicyView)
def publish_policy(
    org: UUID,
    policy_id: UUID,
    data: FilePolicyCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> FilePolicyView:
    return service.publish_policy(db, org, policy_id, identity[0], data, request.state.request_id)


@router.post("/{policy_id}/retire", response_model=FilePolicyView)
def retire_policy(
    org: UUID,
    policy_id: UUID,
    data: FilePolicyCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> FilePolicyView:
    return service.retire_policy(db, org, policy_id, identity[0], data, request.state.request_id)
