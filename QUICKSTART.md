# ⚡ QUICKSTART

## 0. One-time setup (5 min, no credit cards)

Get free API keys from:
- **LiveKit Cloud** → https://cloud.livekit.io  → URL + API key + secret
- **Deepgram**      → https://console.deepgram.com  → API key
- **Groq**          → https://console.groq.com  → API key
- **Beyond Presence** → https://app.bey.dev  → API key

## 1. Configure keys

```bash
cd backend
cp .env.example .env       # then open .env and paste your keys
```

(Frontend `.env` will be auto-created by the run script — default works.)

## 2. Run it — TWO terminals

### 🐧 Linux / macOS

**Terminal 1 — backend:**
```bash
cd backend
chmod +x run.sh
./run.sh
```

**Terminal 2 — frontend:**
```bash
cd frontend
chmod +x run.sh
./run.sh
```

### 🪟 Windows

**Terminal 1 — backend:** double-click `backend\run.bat`
(this opens TWO console windows: the agent worker + the HTTP API)

**Terminal 2 — frontend:** double-click `frontend\run.bat`

## 3. Open the app

Go to **http://localhost:5173**, click **Start call**, allow microphone,
and start talking to Maya.

## 🎬 Demo script (try this!)

> "Hi, my name is Anjali, my number is nine eight seven six five four three two one zero."
>
> "I'd like to book an appointment please."
>
> "Tomorrow morning at ten works."
>
> "Actually, can you push it to two pm?"
>
> "What's on my calendar?"
>
> "Perfect, thanks bye!"
>
> Then click **End call** → summary appears.

For deployment, troubleshooting, and architecture details, see `README.md`.
