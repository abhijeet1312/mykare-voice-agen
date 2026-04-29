# 🩺 Mykare Voice AI Front Desk

A web-based AI receptionist that books, looks up, modifies, and cancels
healthcare appointments via natural voice conversation, with a
lip-synced talking avatar and a live visual feed of every tool call.

Built for the **Mykare Voice AI Engineer Task**.

## ✨ What it does

- 🎤 **Voice in/out** — Deepgram Nova-3 STT + Aura-2 TTS
- 🧠 **Reasoning** — Groq Llama-3.3-70B (≈300 tokens/sec)
- 👤 **Talking avatar** — Beyond Presence (lip-synced video)
- ⚙️ **7 tool calls** — `identify_user`, `fetch_slots`, `book_appointment`,
  `retrieve_appointments`, `cancel_appointment`, `modify_appointment`,
  `end_conversation`
- 🖥️ **Live UI** — every tool call appears as a pill (`Fetching slots…` →
  `Found 8 slots ✅`)
- 📝 **Auto summary** — generated in <10s when the call ends, showing
  patient name, phone, intent, preferences, appointments, timestamp,
  and a 2–3 sentence recap
- 🗄️ **SQLite DB** with a unique-index on `slot_datetime` to prevent
  double-bookings

## 🛠️ Stack

| Layer        | Service               | Free? |
|--------------|-----------------------|-------|
| Voice agent  | LiveKit Agents (Python) | ✅ 1,000 min/mo |
| HTTP API     | FastAPI               | ✅ |
| STT          | Deepgram Nova-3       | ✅ $200 credit |
| LLM          | Groq Llama-3.3-70B    | ✅ Forever free |
| TTS          | Deepgram Aura-2       | ✅ same credit |
| Avatar       | Beyond Presence       | ✅ Free signup |
| Frontend     | Vite + React + TypeScript | ✅ |
| DB           | SQLite                | ✅ |

**No credit card required for any provider.**

## 📁 Repo layout

```
mykare-voice-agent/
├── backend/                  ← Python — runs as TWO processes
│   ├── agent.py              ← LiveKit Agents worker (the voice loop + 7 tools)
│   ├── api.py                ← FastAPI server: GET /token, POST /summary
│   ├── db.py                 ← SQLite schema + queries
│   ├── requirements.txt
│   └── .env.example
└── frontend/                 ← Vite + React + TS SPA
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── .env.example
    └── src/
        ├── main.tsx
        ├── App.tsx
        └── components/
            ├── AvatarTile.tsx
            ├── ToolCallList.tsx
            └── SummaryPanel.tsx
```

## 🚀 Run locally

### 0. Sign up (5 min, no credit cards)

| Service | Where | What you copy |
|---------|-------|---------------|
| LiveKit Cloud | https://cloud.livekit.io | URL + API key + Secret |
| Deepgram      | https://console.deepgram.com | API key |
| Groq          | https://console.groq.com | API key |
| Beyond Presence | https://app.bey.dev | API key |

### 1. Backend (two processes — open two terminals)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # paste all your keys
```

**Terminal 1 — LiveKit agent worker:**

```bash
python agent.py download-files   # one-time: VAD + turn-detector models
python agent.py dev
```

You should see: `registered worker` and `agent listening for jobs`.

**Terminal 2 — FastAPI HTTP server:**

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Smoke test: `curl http://localhost:8000/health` → `{"ok": true}`.

### 2. Frontend (third terminal)

```bash
cd frontend
npm install
cp .env.example .env       # default points at http://localhost:8000
npm run dev
```

Open `http://localhost:5173`, click **Start call**, allow mic, and speak.
Maya will greet you and ask for your phone number.

## 🎬 Demo script (≈90 s, hits every requirement)

> "Hi, my name is Anjali, my number is nine eight seven six five four three two one zero."
> → triggers **identify_user** pill → "New patient registered ✅"
>
> "I'd like to book an appointment please."
> → "Sure, what day works for you?"
>
> "Tomorrow morning at ten."
> → triggers **fetch_slots** pill → triggers **book_appointment** →
>   "Booking confirmed ✅"
>
> "Actually, can you push it to two pm?"
> → triggers **modify_appointment** → "Rescheduled ✅"
>
> "What's on my calendar?"
> → triggers **retrieve_appointments** pill
>
> "Perfect, thanks bye."
> → triggers **end_conversation** → user clicks **End call** →
>   summary panel populates within seconds.

## ☁️ Deployment

### Backend → Render (free tier) — TWO services from the same repo

You'll deploy the same `backend/` folder twice with different start commands.

**Service A: LiveKit Agent Worker**
- Type: Background Worker
- Build: `pip install -r requirements.txt && python agent.py download-files`
- Start: `python agent.py start`
- Env vars: everything in `.env`

**Service B: FastAPI HTTP Server**
- Type: Web Service
- Build: `pip install -r requirements.txt`
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Env vars: same `.env`, plus `FRONTEND_ORIGINS=https://your-app.vercel.app`

### Frontend → Vercel (free)

1. Push `frontend/` to its own GitHub repo.
2. Import on Vercel.
3. Build command: `npm run build`. Output dir: `dist`.
4. Add env var `VITE_API_URL=https://your-fastapi.onrender.com`.
5. Deploy.

## 💰 Cost per call (bonus)

For a 3-minute conversation:

| Item | Rate | Cost |
|------|------|------|
| LiveKit agent session | $0.01 / min | $0.030 |
| Deepgram STT (Nova-3 streaming) | $0.0077 / min | $0.023 |
| Deepgram TTS (Aura-2) | ~$0.030 / 1k chars | $0.018 |
| Groq LLM (Llama-3.3-70B) | $0.59 / 1M in + $0.79 / 1M out | $0.002 |
| Beyond Presence avatar (paid) | from $0.10 / min | $0.30 |
| **Total per call** |  | **≈ $0.37** |

On the free tiers, the first ~60 minutes/month cost **₹0**.

## 🧪 Edge cases handled

- **Double booking** — UNIQUE partial index on
  `slot_datetime WHERE status='booked'`; conflicting insert returns
  `IntegrityError` → tool replies "slot already booked".
- **Cancelled slots reusable** — partial-index excludes `cancelled` rows.
- **Phone-as-ID** — non-digits stripped; same number = same user.
- **Patient hangs up mid-call** — summary is still generated from whatever
  transcript and tool calls happened.
- **Avatar takes longer to connect than voice** — the UI shows a bar
  visualizer placeholder until the avatar video track arrives.
