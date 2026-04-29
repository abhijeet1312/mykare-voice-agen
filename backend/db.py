"""
SQLite database for the healthcare front-desk AI agent.

Tables:
  users         — keyed by phone number (the unique ID per the assignment)
  appointments  — booked slots; double-booking is prevented by a UNIQUE
                  constraint on (slot_datetime) for status='booked'.
"""
from __future__ import annotations

import datetime as dt
import os
import uuid
from pathlib import Path

import aiosqlite

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent / "appointments.db"))


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                phone       TEXT PRIMARY KEY,
                name        TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id              TEXT PRIMARY KEY,
                phone           TEXT NOT NULL,
                name            TEXT,
                slot_datetime   TEXT NOT NULL,   -- ISO 8601, e.g. 2026-04-29T10:00
                reason          TEXT,
                status          TEXT NOT NULL DEFAULT 'booked',  -- booked | cancelled
                created_at      TEXT NOT NULL,
                FOREIGN KEY(phone) REFERENCES users(phone)
            );

            -- One active booking per slot. Cancelled rows can share a slot.
            CREATE UNIQUE INDEX IF NOT EXISTS ux_active_slot
                ON appointments(slot_datetime)
                WHERE status = 'booked';
            """
        )
        await db.commit()


# ─────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────
async def upsert_user(phone: str, name: str | None = None) -> dict:
    now = dt.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE phone=?", (phone,)) as cur:
            existing = await cur.fetchone()

        if existing:
            if name and not existing["name"]:
                await db.execute("UPDATE users SET name=? WHERE phone=?", (name, phone))
                await db.commit()
            return {"phone": phone, "name": name or existing["name"], "is_new": False}

        await db.execute(
            "INSERT INTO users(phone, name, created_at) VALUES (?, ?, ?)",
            (phone, name, now),
        )
        await db.commit()
        return {"phone": phone, "name": name, "is_new": True}


# ─────────────────────────────────────────────────────────────────────────
# Slots — hardcoded availability for the next 7 days, 10am/11am/2pm/4pm
# ─────────────────────────────────────────────────────────────────────────
_DEFAULT_TIMES = ["10:00", "11:00", "14:00", "16:00"]


async def get_available_slots(days_ahead: int = 5) -> list[str]:
    """Return list of ISO datetimes that are NOT yet booked."""
    today = dt.date.today()
    candidates: list[str] = []
    for d in range(1, days_ahead + 1):
        day = today + dt.timedelta(days=d)
        if day.weekday() >= 5:           # skip weekends
            continue
        for t in _DEFAULT_TIMES:
            candidates.append(f"{day.isoformat()}T{t}")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT slot_datetime FROM appointments WHERE status='booked'"
        ) as cur:
            booked = {row[0] async for row in cur}

    return [c for c in candidates if c not in booked]


# ─────────────────────────────────────────────────────────────────────────
# Appointments
# ─────────────────────────────────────────────────────────────────────────
async def book_appointment(
    phone: str, slot_datetime: str, name: str | None = None, reason: str | None = None
) -> dict:
    """Returns {'success': bool, 'appointment_id'?: str, 'error'?: str}."""
    now = dt.datetime.utcnow().isoformat()
    appt_id = str(uuid.uuid4())[:8]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO appointments
                   (id, phone, name, slot_datetime, reason, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'booked', ?)""",
                (appt_id, phone, name, slot_datetime, reason, now),
            )
            await db.commit()
        return {"success": True, "appointment_id": appt_id}
    except aiosqlite.IntegrityError:
        return {"success": False, "error": "That slot is already booked. Please choose another."}


async def list_appointments(phone: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM appointments
               WHERE phone=? AND status='booked'
               ORDER BY slot_datetime""",
            (phone,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def cancel_appointment(appointment_id: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE appointments SET status='cancelled' WHERE id=? AND status='booked'",
            (appointment_id,),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return {"success": False, "error": "Appointment not found or already cancelled."}
    return {"success": True}


async def modify_appointment(appointment_id: str, new_slot: str) -> dict:
    """Cancel old + book new, atomically."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE id=? AND status='booked'", (appointment_id,)
        ) as cur:
            old = await cur.fetchone()
        if not old:
            return {"success": False, "error": "Appointment not found."}

        try:
            await db.execute(
                "UPDATE appointments SET status='cancelled' WHERE id=?", (appointment_id,)
            )
            new_id = str(uuid.uuid4())[:8]
            await db.execute(
                """INSERT INTO appointments
                   (id, phone, name, slot_datetime, reason, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'booked', ?)""",
                (
                    new_id,
                    old["phone"],
                    old["name"],
                    new_slot,
                    old["reason"],
                    dt.datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()
            return {"success": True, "appointment_id": new_id}
        except aiosqlite.IntegrityError:
            await db.rollback()
            return {"success": False, "error": "The new slot is already booked."}
