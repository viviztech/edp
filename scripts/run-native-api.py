"""Run the host API with the event loop required by psycopg on Windows."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    api_root = root / "apps" / "api"
    os.chdir(api_root)
    sys.path.insert(0, str(api_root))
    config = uvicorn.Config("app.main:app", host=args.host, port=args.port)
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
