"""
Mykare Healthcare Front-Desk Voice Agent
========================================
LiveKit Agent that:
  • listens (Deepgram STT)
  • thinks (Groq Llama-3.3-70B)
  • speaks (Deepgram Aura-2 TTS)
  • shows a lip-synced avatar (Beyond Presence)
  • calls 7 tools to manage appointments in SQLite
  • broadcasts every tool call to the frontend so the UI can show
    "Fetching slots…", "Booking confirmed ✅" etc.

Run:
    python agent.py dev
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Annotated

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import bey, deepgram, groq, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import db

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mykare-agent")


# ════════════════════════════════════════════════════════════════════════
# UI EVENT BROADCASTING
# ════════════════════════════════════════════════════════════════════════
# Every tool call publishes a JSON message on the LiveKit data channel.
# The frontend listens and renders pills like "Fetching slots…".

class UIBroadcaster:
    def __init__(self):
        self._room: rtc.Room | None = None

    def attach(self, room: rtc.Room) -> None:
        self._room = room

    async def emit(self, event: str, payload: dict | None = None) -> None:
        if not self._room:
            return
        msg = json.dumps({"event": event, "payload": payload or {}})
        try:
            await self._room.local_participant.publish_data(
                msg.encode("utf-8"), reliable=True, topic="agent-ui"
            )
        except Exception as e:
            logger.warning(f"UI broadcast failed: {e}")


ui = UIBroadcaster()


# ════════════════════════════════════════════════════════════════════════
# THE AGENT — system prompt + 7 tools
# ════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are Maya, the friendly front-desk AI assistant for Mykare Health clinic.
Your job: help patients book, view, modify, or cancel appointments.

CONVERSATION RULES
1. Keep replies SHORT — 1-2 sentences. This is a voice call.
2. Ask ONE thing at a time.
3. Always start by asking the patient for their phone number, then call
   identify_user. Do NOT skip this — it is the unique ID.
4. After identifying the user, ask how you can help today.
5. Use the tools — never make up slot times, appointment IDs, or
   confirmations. If a tool fails, tell the user what went wrong.
6. When reading dates or times back, speak naturally
   ("Wednesday April 30th at ten in the morning"), not ISO format.
7. If the user wants to end the call, say a brief goodbye and call
   end_conversation. Do NOT call end_conversation otherwise.
8. Currency, code, URLs: spell out naturally for voice.

EXTRACT from the conversation as you go:
  • Name • Phone number • Preferred date • Preferred time • Reason / intent

Do not announce tool calls ("let me check the system…"); just call them
and speak the result naturally.
"""


class FrontDeskAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        # Per-session memory the LLM can rely on between tool calls.
        self.current_phone: str | None = None
        self.current_name: str | None = None

    # ── Tool 1 ──────────────────────────────────────────────────────────
    @function_tool()
    async def identify_user(
        self,
        phone: Annotated[str, "Patient's phone number, digits only or with country code"],
        name: Annotated[str | None, "Patient's name if they have given it"] = None,
    ) -> str:
        """Register or look up a patient by their phone number (the unique ID)."""
        await ui.emit("tool_start", {"tool": "identify_user", "label": "Identifying patient…"})
        clean = "".join(c for c in phone if c.isdigit() or c == "+")
        result = await db.upsert_user(clean, name)
        self.current_phone = clean
        self.current_name = result.get("name") or name
        await ui.emit(
            "tool_done",
            {
                "tool": "identify_user",
                "label": ("New patient registered ✅" if result["is_new"] else "Patient found ✅"),
                "data": result,
            },
        )
        if result["is_new"]:
            return f"New patient registered with phone {clean}. Ask for their name if not yet known."
        return f"Existing patient: {result.get('name') or 'name not on file'}, phone {clean}."

    # ── Tool 2 ──────────────────────────────────────────────────────────
    @function_tool()
    async def fetch_slots(self) -> str:
        """Return available appointment slots for the next few days."""
        await ui.emit("tool_start", {"tool": "fetch_slots", "label": "Fetching slots…"})
        slots = await db.get_available_slots()
        # Offer at most 5 to keep the spoken reply tight
        offered = slots[:5]
        await ui.emit(
            "tool_done",
            {"tool": "fetch_slots", "label": f"Found {len(slots)} slots ✅", "data": {"slots": offered}},
        )
        if not offered:
            return "No slots available in the next few days."
        return "Available slots: " + ", ".join(offered)

    # ── Tool 3 ──────────────────────────────────────────────────────────
    @function_tool()
    async def book_appointment(
        self,
        slot_datetime: Annotated[str, "ISO datetime, e.g. 2026-04-30T10:00"],
        reason: Annotated[str | None, "Reason for visit, optional"] = None,
    ) -> str:
        """Book the given slot for the currently-identified patient."""
        if not self.current_phone:
            return "I need to identify the patient first. Ask for their phone number."
        await ui.emit("tool_start", {"tool": "book_appointment", "label": "Booking appointment…"})
        result = await db.book_appointment(
            phone=self.current_phone,
            slot_datetime=slot_datetime,
            name=self.current_name,
            reason=reason,
        )
        if result["success"]:
            await ui.emit(
                "tool_done",
                {
                    "tool": "book_appointment",
                    "label": "Booking confirmed ✅",
                    "data": {"appointment_id": result["appointment_id"], "slot": slot_datetime},
                },
            )
            return f"Booked. Confirmation ID {result['appointment_id']} for {slot_datetime}."
        await ui.emit("tool_error", {"tool": "book_appointment", "label": "Booking failed ❌", "data": result})
        return f"Booking failed: {result['error']}"

    # ── Tool 4 ──────────────────────────────────────────────────────────
    @function_tool()
    async def retrieve_appointments(self) -> str:
        """List the current patient's upcoming appointments."""
        if not self.current_phone:
            return "I need the patient's phone number first."
        await ui.emit("tool_start", {"tool": "retrieve_appointments", "label": "Looking up appointments…"})
        rows = await db.list_appointments(self.current_phone)
        await ui.emit(
            "tool_done",
            {
                "tool": "retrieve_appointments",
                "label": f"Found {len(rows)} appointment(s) ✅",
                "data": {"appointments": rows},
            },
        )
        if not rows:
            return "No upcoming appointments on file."
        return "Upcoming: " + "; ".join(
            f"ID {r['id']} on {r['slot_datetime']}" + (f" ({r['reason']})" if r['reason'] else "")
            for r in rows
        )

    # ── Tool 5 ──────────────────────────────────────────────────────────
    @function_tool()
    async def cancel_appointment(
        self, appointment_id: Annotated[str, "The appointment ID to cancel"]
    ) -> str:
        """Cancel a specific appointment by its ID."""
        await ui.emit("tool_start", {"tool": "cancel_appointment", "label": "Cancelling…"})
        result = await db.cancel_appointment(appointment_id)
        if result["success"]:
            await ui.emit("tool_done", {"tool": "cancel_appointment", "label": "Cancelled ✅"})
            return f"Appointment {appointment_id} cancelled."
        await ui.emit("tool_error", {"tool": "cancel_appointment", "label": "Cancel failed ❌"})
        return result["error"]

    # ── Tool 6 ──────────────────────────────────────────────────────────
    @function_tool()
    async def modify_appointment(
        self,
        appointment_id: Annotated[str, "The appointment ID to move"],
        new_slot_datetime: Annotated[str, "New ISO datetime, e.g. 2026-05-02T14:00"],
    ) -> str:
        """Reschedule an appointment to a new slot."""
        await ui.emit("tool_start", {"tool": "modify_appointment", "label": "Rescheduling…"})
        result = await db.modify_appointment(appointment_id, new_slot_datetime)
        if result["success"]:
            await ui.emit(
                "tool_done",
                {
                    "tool": "modify_appointment",
                    "label": "Rescheduled ✅",
                    "data": {"new_appointment_id": result["appointment_id"], "slot": new_slot_datetime},
                },
            )
            return f"Rescheduled. New ID {result['appointment_id']} at {new_slot_datetime}."
        await ui.emit("tool_error", {"tool": "modify_appointment", "label": "Reschedule failed ❌"})
        return result["error"]

    # ── Tool 7 ──────────────────────────────────────────────────────────
    @function_tool()
    async def end_conversation(self) -> str:
        """End the call. Call ONLY when the user explicitly wants to hang up."""
        await ui.emit("tool_done", {"tool": "end_conversation", "label": "Ending call…"})
        # Trigger summary generation on the frontend side
        await ui.emit("call_ending", {})
        return "Goodbye sent. End the conversation politely now."


# ════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════

async def entrypoint(ctx: JobContext) -> None:
    await db.init_db()
    await ctx.connect()
    ui.attach(ctx.room)

    # Build the voice pipeline
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=deepgram.TTS(model="aura-2-thalia-en"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    # Stream final transcript lines to the frontend for the summary panel
    @session.on("conversation_item_added")
    def _on_item(ev) -> None:
        item = ev.item
        text = (item.text_content or "").strip()
        if not text:
            return
        asyncio.create_task(
            ui.emit("transcript", {"role": item.role, "text": text})
        )

    # Avatar — Beyond Presence (lip-synced video participant)
    avatar = bey.AvatarSession(
        avatar_id=os.getenv("BEY_AVATAR_ID") or None,  # None → default Ege avatar
    )
    await avatar.start(session, room=ctx.room)

    await session.start(
        agent=FrontDeskAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Speak first
    await session.generate_reply(
        instructions=(
            "Greet the patient warmly as Maya from Mykare Health, then ask "
            "for their phone number so you can pull up their record."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
