import { CSSProperties } from "react";

export type CallSummary = {
  patient_name?: string | null;
  phone?: string | null;
  intent?: string;
  preferences?: string[];
  appointments?: { id: string; date: string; time: string; action: string }[];
  summary?: string;
  timestamp?: string;
};

const s: Record<string, CSSProperties> = {
  wrap: {
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: 12,
    padding: 16,
    color: "#e5e7eb",
  },
  h3: { margin: "0 0 12px", fontSize: 16 },
  grid: { display: "flex", flexDirection: "column", gap: 10, fontSize: 14 },
  rowLabel: {
    width: 100,
    color: "#9ca3af",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  apptHeading: {
    color: "#9ca3af",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    marginBottom: 4,
  },
  code: {
    background: "#1f2937",
    padding: "1px 6px",
    borderRadius: 4,
    fontSize: 12,
    fontFamily: "ui-monospace, monospace",
  },
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      <div style={s.rowLabel}>{label}</div>
      <div style={{ flex: 1 }}>{value}</div>
    </div>
  );
}

export function SummaryPanel({
  summary,
  loading,
}: {
  summary: CallSummary | null;
  loading: boolean;
}) {
  return (
    <div style={s.wrap}>
      <h3 style={s.h3}>📝 Call Summary</h3>
      {loading && <p style={{ color: "#9ca3af" }}>Generating summary…</p>}
      {!loading && !summary && (
        <p style={{ color: "#6b7280" }}>The summary will appear here when the call ends.</p>
      )}
      {summary && (
        <div style={s.grid}>
          <Row label="Patient" value={summary.patient_name || "—"} />
          <Row label="Phone" value={summary.phone || "—"} />
          <Row label="Intent" value={summary.intent || "—"} />
          <Row
            label="Timestamp"
            value={summary.timestamp ? new Date(summary.timestamp).toLocaleString() : "—"}
          />
          {summary.preferences && summary.preferences.length > 0 && (
            <Row label="Preferences" value={summary.preferences.join(", ")} />
          )}
          {summary.appointments && summary.appointments.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <div style={s.apptHeading}>Appointments</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {summary.appointments.map((a, i) => (
                  <li key={i} style={{ margin: "4px 0" }}>
                    <span style={s.code}>{a.id}</span> — {a.date} {a.time}{" "}
                    <em>({a.action})</em>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {summary.summary && (
            <div style={{ marginTop: 6 }}>
              <div style={s.apptHeading}>Recap</div>
              <p style={{ margin: 0, lineHeight: 1.5 }}>{summary.summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
