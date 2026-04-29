"""
Production launcher — starts the FastAPI HTTP server in this process and
spawns the LiveKit agent worker as a child process. This is what Render
runs as a single free Web Service.

Local dev: keep using two terminals as before.
Production: python server.py
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time

import uvicorn
from dotenv import load_dotenv

from api import app

load_dotenv()

agent_proc: subprocess.Popen | None = None


def start_agent_worker() -> subprocess.Popen:
    """Spawn `python agent.py start` (production mode, no file watcher)."""
    print("[server] starting LiveKit agent worker…", flush=True)
    return subprocess.Popen(
        [sys.executable, "agent.py", "start"],
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ.copy(),
    )


def _watchdog() -> None:
    """If the agent worker dies, kill the whole process so Render restarts us."""
    global agent_proc
    while True:
        time.sleep(5)
        if agent_proc and agent_proc.poll() is not None:
            print(
                f"[server] agent worker exited with code {agent_proc.returncode} — "
                "shutting down so Render can restart",
                flush=True,
            )
            os.kill(os.getpid(), signal.SIGTERM)
            return


def _shutdown(signum, frame) -> None:
    print(f"[server] received signal {signum}, terminating agent worker…", flush=True)
    if agent_proc and agent_proc.poll() is None:
        agent_proc.terminate()
        try:
            agent_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            agent_proc.kill()
    sys.exit(0)


def main() -> None:
    global agent_proc
    agent_proc = start_agent_worker()
    threading.Thread(target=_watchdog, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    port = int(os.getenv("PORT", "8000"))
    print(f"[server] starting FastAPI on 0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()