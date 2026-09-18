from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def database(request: Request) -> Generator[Session]:
    with Session(request.app.state.identity_engine, expire_on_commit=False) as session:
        yield session
