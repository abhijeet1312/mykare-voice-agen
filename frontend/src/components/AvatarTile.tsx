import { CSSProperties } from "react";
import {
  useTracks,
  VideoTrack,
  useVoiceAssistant,
  BarVisualizer,
} from "@livekit/components-react";
import { Track } from "livekit-client";

const s: Record<string, CSSProperties> = {
  tile: {
    position: "relative",
    aspectRatio: "4 / 5",
    background: "#000",
    borderRadius: 16,
    overflow: "hidden",
    border: "1px solid #1f2937",
  },
  placeholder: {
    width: "100%",
    height: "100%",
    display: "grid",
    placeItems: "center",
    background: "linear-gradient(135deg, #1e3a8a, #312e81)",
    color: "#cbd5e1",
  },
  visualizer: { width: "60%", height: 80 },
  status: {
    position: "absolute",
    top: 12,
    left: 12,
    background: "rgba(0,0,0,0.6)",
    padding: "6px 10px",
    borderRadius: 999,
    fontSize: 12,
    display: "flex",
    alignItems: "center",
    gap: 6,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  dot: { width: 6, height: 6, borderRadius: "50%", background: "#10b981" },
};

export function AvatarTile() {
  // Beyond Presence publishes its avatar as a regular Camera track.
  const tracks = useTracks([Track.Source.Camera], { onlySubscribed: true });
  const avatarTrack = tracks.find((t) =>
    (t.participant?.identity || "").startsWith("bey-avatar")
  );
  const { state } = useVoiceAssistant();

  return (
    <div style={s.tile}>
      {avatarTrack ? (
        // The video element fills the tile; CSS below makes object-fit: cover.
        <div style={{ width: "100%", height: "100%" }}>
          <VideoTrack
            trackRef={avatarTrack}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      ) : (
        <div style={s.placeholder}>
          <div style={s.visualizer}>
            <BarVisualizer state={state} barCount={5} />
          </div>
          <p>Connecting to Maya…</p>
        </div>
      )}
      <div style={s.status}>
        <span style={s.dot} /> {state}
      </div>
    </div>
  );
}
