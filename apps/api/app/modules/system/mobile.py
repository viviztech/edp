from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/public", tags=["client-policy"])


class MobilePolicy(BaseModel):
    platform: Literal["android", "ios", "web"]
    updates_enabled: bool
    minimum_version: str
    latest_version: str
    download_url: str | None


@router.get("/mobile-policy", response_model=MobilePolicy)
def mobile_policy(platform: Literal["android", "ios", "web"]) -> MobilePolicy:
    settings = get_settings()
    destination = {
        "android": settings.mobile_android_download_url,
        "ios": settings.mobile_ios_download_url,
        "web": "",
    }[platform]
    return MobilePolicy(
        platform=platform,
        updates_enabled=settings.mobile_updates_enabled and platform != "web",
        minimum_version=settings.mobile_minimum_version,
        latest_version=settings.mobile_latest_version,
        download_url=destination or None,
    )
