"""
FastAPI HTTP server for the React frontend.

Exposes:
  GET  /health          → liveness probe
  GET  /token           → issues a LiveKit access token for a new room
  POST /summary         → generates the post-call summary via Groq

Run:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import json
import os
import random
import string
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api as lk_api
from pydantic import BaseModel

load_dotenv()

# ── App + CORS ────────────────────────────────────────────────────────────
app = FastAPI(title="Mykare Voice Agent API")

origins = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────
# /health
# ──────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# /token — issue a LiveKit access token for the React frontend
# ──────────────────────────────────────────────────────────────────────────
def _rand(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


@app.get("/token")
async def get_token(room: str | None = None, identity: str | None = None) -> dict:
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")
    if not (api_key and api_secret and livekit_url):
        raise HTTPException(500, "LiveKit credentials missing on server")

    room = room or f"clinic-{_rand()}"
    identity = identity or f"patient-{_rand()}"

    token = (
        lk_api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            lk_api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )
    return {"token": token, "url": livekit_url, "room": room, "identity": identity}


# ──────────────────────────────────────────────────────────────────────────
# /summary — post-call summary via Groq
# ──────────────────────────────────────────────────────────────────────────
class TranscriptLine(BaseModel):
    role: str
    text: str


class ToolCallRecord(BaseModel):
    tool: str
    data: Any | None = None


class SummaryRequest(BaseModel):
    transcript: list[TranscriptLine] = []
    toolCalls: list[ToolCallRecord] = []


SUMMARY_SYSTEM = """You are summarizing a healthcare front-desk voice call.
Return ONLY valid JSON with this exact shape, no markdown, no commentary:

{
  "patient_name": string | null,
  "phone": string | null,
  "intent": string,
  "preferences": [string],
  "appointments": [{"id": string, "date": string, "time": string, "action": "booked" | "cancelled" | "modified"}],
  "summary": string
}

Rules:
- "summary" is 2-3 short sentences in plain English.
- "preferences" lists anything the patient said they liked or wanted.
- If a field is unknown, use null or [].
- Output JSON only."""


@app.post("/summary")
async def make_summary(req: SummaryRequest) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(500, "GROQ_API_KEY missing on server")

    # Lazy import so the server still starts if groq isn't installed yet
    from groq import Groq

    client = Groq(api_key=api_key)

    lines = "\n".join(f"{t.role.upper()}: {t.text}" for t in req.transcript) or "(empty)"
    tools = "\n".join(f"- {t.tool}: {json.dumps(t.data or {})}" for t in req.toolCalls) or "(none)"
    user_msg = f"TRANSCRIPT:\n{lines}\n\nTOOL CALLS:\n{tools}\n\nNow output the JSON."

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "summary": raw,
                "patient_name": None,
                "phone": None,
                "intent": "",
                "preferences": [],
                "appointments": [],
            }
    except Exception as e:
        raise HTTPException(500, f"summary failed: {e}")

    from datetime import datetime, timezone
    parsed["timestamp"] = datetime.now(timezone.utc).isoformat()
    return parsed
