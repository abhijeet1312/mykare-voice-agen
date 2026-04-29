"""
Production launcher — runs the FastAPI HTTP server AND the LiveKit agent
worker together in ONE process. This is what Render runs as a single free
Web Service.

Locally you can still run them separately during development:
    Terminal A:  python agent.py dev
    Terminal B:  uvicorn api:app --reload --port 8000

In production:
    python server.py
"""
from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from dotenv import load_dotenv
from livekit.agents import WorkerOptions, Worker

import agent  # imports entrypoint() and registers everything
from api import app  # the FastAPI app

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")


async def run_agent_worker() -> None:
    """Run the LiveKit agent worker (the same thing `python agent.py dev` runs,
    minus the file-watcher / dev features)."""
    opts = WorkerOptions(entrypoint_fnc=agent.entrypoint)
    worker = Worker(opts)
    await worker.run()


async def run_http_server() -> None:
    """Run the FastAPI app via uvicorn programmatically."""
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    log.info("Starting Mykare Voice Agent — HTTP + LiveKit worker in one process")
    await asyncio.gather(
        run_agent_worker(),
        run_http_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())