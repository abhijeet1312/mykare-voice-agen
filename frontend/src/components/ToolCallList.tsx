import { useEffect, useState, CSSProperties } from "react";

export type ToolCall = {
  id: string;
  tool: string;
  label: string;
  status: "running" | "done" | "error";
  data?: any;
  timestamp: number;
};

const styles: Record<string, CSSProperties> = {
  pill: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "#1f2937",
    border: "1px solid #374151",
    padding: "8px 12px",
    borderRadius: 999,
    color: "#e5e7eb",
    fontSize: 13,
  },
  dot: { width: 8, height: 8, borderRadius: "50%" },
  tool: { color: "#9ca3af", fontFamily: "ui-monospace, SFMono-Regular, monospace" },
  label: { color: "#f3f4f6" },
};

const keyframes = `
  @keyframes pulse  { 0%,100% { opacity: 1 } 50% { opacity: 0.4 } }
  @keyframes slideIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }
`;

export function ToolCallPill({ call }: { call: ToolCall }) {
  const dotColor =
    call.status === "running" ? "#f59e0b" : call.status === "done" ? "#10b981" : "#ef4444";

  return (
    <div style={{ ...styles.pill, animation: "slideIn 240ms ease-out" }}>
      <span
        style={{
          ...styles.dot,
          background: dotColor,
          animation: call.status === "running" ? "pulse 1.2s infinite" : undefined,
        }}
      />
      <span style={styles.tool}>{call.tool}</span>
      <span style={styles.label}>{call.label}</span>
    </div>
  );
}

export function ToolCallList({ calls }: { calls: ToolCall[] }) {
  // Force re-render once a second so timestamps stay fresh if you add them later.
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, []);

  if (calls.length === 0) {
    return <div style={{ color: "#6b7280", fontSize: 13 }}>No tool calls yet…</div>;
  }
  return (
    <>
      <style>{keyframes}</style>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {[...calls].reverse().map((c) => (
          <ToolCallPill key={c.id} call={c} />
        ))}
      </div>
    </>
  );
}
