import { CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import { RoomEvent } from "livekit-client";
import { ToolCall, ToolCallList } from "./components/ToolCallList";
import { CallSummary, SummaryPanel } from "./components/SummaryPanel";
import { AvatarTile } from "./components/AvatarTile";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── Styles ───────────────────────────────────────────────────────────────
const css: Record<string, CSSProperties> = {
  landing: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: 24,
  },
  card: {
    maxWidth: 480,
    textAlign: "center",
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: 16,
    padding: 32,
  },
  ctaBtn: {
    marginTop: 20,
    background: "#2563eb",
    color: "white",
    border: 0,
    padding: "12px 24px",
    borderRadius: 8,
    fontSize: 15,
    cursor: "pointer",
    fontWeight: 600,
  },
  screen: {
    display: "grid",
    gridTemplateColumns: "1.3fr 1fr",
    gap: 24,
    padding: 24,
    minHeight: "100vh",
  },
  panel: {
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: 12,
    padding: 16,
  },
  controls: { display: "flex", gap: 12 },
  btn: {
    padding: "10px 20px",
    borderRadius: 8,
    border: 0,
    background: "#1f2937",
    color: "#e5e7eb",
    cursor: "pointer",
    fontWeight: 600,
  },
  hangupBtn: {
    padding: "10px 20px",
    borderRadius: 8,
    border: 0,
    background: "#dc2626",
    color: "white",
    cursor: "pointer",
    fontWeight: 600,
  },
};

// ─────────────────────────────────────────────────────────────────────────
// ROOT
// ─────────────────────────────────────────────────────────────────────────
export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCall = async () => {
    setConnecting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/token`);
      if (!r.ok) throw new Error(`Token request failed: ${r.status}`);
      const j = await r.json();
      setToken(j.token);
      setUrl(j.url);
    } catch (e: any) {
      setError(e?.message || "Failed to fetch token");
    } finally {
      setConnecting(false);
    }
  };

  if (!token || !url) {
    return (
      <div style={css.landing}>
        <div style={css.card}>
          <h1 style={{ margin: "0 0 12px" }}>🩺 Mykare Health Front Desk</h1>
          <p style={{ color: "#9ca3af", lineHeight: 1.5 }}>
            Talk to Maya, our AI receptionist. She can book, look up, change, or
            cancel your appointments.
          </p>
          <button
            onClick={startCall}
            disabled={connecting}
            style={{ ...css.ctaBtn, opacity: connecting ? 0.6 : 1 }}
          >
            {connecting ? "Connecting…" : "Start call"}
          </button>
          {error && (
            <p style={{ color: "#ef4444", marginTop: 12, fontSize: 13 }}>{error}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={url}
      token={token}
      connect
      audio
      video={false}
      connectOptions={{ autoSubscribe: true }}
    >
      <CallScreen
        onLeave={() => {
          setToken(null);
          setUrl(null);
        }}
      />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// CALL SCREEN
// ─────────────────────────────────────────────────────────────────────────
function CallScreen({ onLeave }: { onLeave: () => void }) {
  const room = useRoomContext();
  const [tools, setTools] = useState<ToolCall[]>([]);
  const [transcript, setTranscript] = useState<{ role: string; text: string }[]>([]);
  const [summary, setSummary] = useState<CallSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const summaryRequested = useRef(false);

  // Listen for data messages from the agent ────────────────────────────
  useEffect(() => {
    const handler = (
      payload: Uint8Array,
      _participant: any,
      _kind: any,
      topic?: string
    ) => {
      if (topic && topic !== "agent-ui") return;
      let msg: any;
      try {
        msg = JSON.parse(new TextDecoder().decode(payload));
      } catch {
        return;
      }
      const { event, payload: p } = msg;

      if (event === "tool_start") {
        setTools((prev) => [
          ...prev,
          {
            id: `${p.tool}-${Date.now()}`,
            tool: p.tool,
            label: p.label,
            status: "running",
            data: p.data,
            timestamp: Date.now(),
          },
        ]);
      } else if (event === "tool_done") {
        setTools((prev) => {
          // Find the most recent matching running tool and complete it.
          const reversed = [...prev].reverse();
          const idx = reversed.findIndex(
            (c) => c.tool === p.tool && c.status === "running"
          );
          if (idx === -1) {
            return [
              ...prev,
              {
                id: `${p.tool}-${Date.now()}`,
                tool: p.tool,
                label: p.label,
                status: "done",
                data: p.data,
                timestamp: Date.now(),
              },
            ];
          }
          const realIdx = prev.length - 1 - idx;
          const next = [...prev];
          next[realIdx] = {
            ...next[realIdx],
            status: "done",
            label: p.label,
            data: p.data,
          };
          return next;
        });
      } else if (event === "tool_error") {
        setTools((prev) => [
          ...prev,
          {
            id: `${p.tool}-${Date.now()}`,
            tool: p.tool,
            label: p.label,
            status: "error",
            data: p.data,
            timestamp: Date.now(),
          },
        ]);
      } else if (event === "transcript") {
        setTranscript((prev) => [...prev, { role: p.role, text: p.text }]);
      } else if (event === "call_ending") {
        // Agent invoked end_conversation. UI will show summary
        // once the user clicks End call.
      }
    };

    room.on(RoomEvent.DataReceived, handler);
    return () => {
      room.off(RoomEvent.DataReceived, handler);
    };
  }, [room]);

  // ── Generate summary ────────────────────────────────────────────────
  const generateSummary = useCallback(async () => {
    if (summaryRequested.current) return;
    summaryRequested.current = true;
    setSummaryLoading(true);
    try {
      const r = await fetch(`${API_URL}/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
          toolCalls: tools
            .filter((t) => t.status === "done")
            .map((t) => ({ tool: t.tool, data: t.data })),
        }),
      });
      const j = await r.json();
      setSummary(j);
    } catch (e) {
      console.error(e);
    } finally {
      setSummaryLoading(false);
    }
  }, [transcript, tools]);

  const hangup = async () => {
    await generateSummary();
    await room.disconnect();
    // Don't call onLeave — keep the summary visible.
  };

  const newCall = () => {
    setSummary(null);
    summaryRequested.current = false;
    onLeave();
  };

  const isMobile = typeof window !== "undefined" && window.innerWidth < 900;
  const screenStyle: CSSProperties = {
    ...css.screen,
    gridTemplateColumns: isMobile ? "1fr" : "1.3fr 1fr",
  };

  return (
    <div style={screenStyle}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <AvatarTile />
        <div style={css.controls}>
          <button onClick={hangup} style={css.hangupBtn}>
            End call
          </button>
          <button onClick={newCall} style={css.btn}>
            New call
          </button>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={css.panel}>
          <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>⚡ Live Tool Calls</h3>
          <ToolCallList calls={tools} />
        </div>
        <SummaryPanel summary={summary} loading={summaryLoading} />
      </div>
    </div>
  );
}
