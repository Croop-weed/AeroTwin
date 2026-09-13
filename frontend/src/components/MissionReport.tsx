import React from "react";
import { AlertTriangle, CheckCircle2, FileText, Milestone } from "lucide-react";
import type { MissionReportResponse } from "../types/api";

interface MissionReportProps {
  report: MissionReportResponse | null;
  onRefresh: () => void;
}

export const MissionReport: React.FC<MissionReportProps> = ({ report, onRefresh }) => {
  if (!report) {
    return (
      <div className="gcs-card" style={{ textAlign: "center", padding: "1.5rem" }}>
        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading Mission Health Analysis...</span>
      </div>
    );
  }

  const getEventIcon = (type: string, severity: string) => {
    if (type === "FAULT" || severity === "CRITICAL") return <AlertTriangle size={14} color="var(--accent-crimson)" />;
    if (type === "ANOMALY" || severity === "WARNING") return <AlertTriangle size={14} color="var(--accent-amber)" />;
    if (type === "RECOVERY") return <CheckCircle2 size={14} color="var(--accent-emerald)" />;
    return <Milestone size={14} color="var(--accent-cyan)" />;
  };

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <FileText size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            MISSION-WISE HEALTH REPORT & EVENT TIMELINE
          </span>
        </div>
        <button
          onClick={onRefresh}
          className="btn-secondary"
          style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem" }}
        >
          Refresh Report
        </button>
      </div>

      {/* Mission Key Indicators */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: "0.65rem",
        marginBottom: "0.75rem",
      }}>
        <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>MISSION ID</div>
          <div className="mono-val" style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--accent-cyan)", marginTop: "2px" }}>
            {report.mission_id}
          </div>
        </div>

        <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>DURATION / POINTS</div>
          <div className="mono-val" style={{ fontSize: "0.88rem", fontWeight: 700, color: "#f1f5f9", marginTop: "2px" }}>
            {report.duration_seconds.toFixed(0)}s ({report.total_telemetry_points} pts)
          </div>
        </div>

        <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>AVG / MIN HEALTH</div>
          <div className="mono-val" style={{ fontSize: "0.88rem", fontWeight: 700, color: report.min_health < 75 ? "var(--accent-amber)" : "var(--accent-emerald)", marginTop: "2px" }}>
            {report.average_health.toFixed(1)}% / {report.min_health.toFixed(1)}%
          </div>
        </div>

        <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>ANOMALIES / FAULTS</div>
          <div className="mono-val" style={{ fontSize: "0.88rem", fontWeight: 700, color: report.fault_events_count > 0 ? "var(--accent-crimson)" : "#f1f5f9", marginTop: "2px" }}>
            {report.anomalies_detected} anom | {report.fault_events_count} faults
          </div>
        </div>
      </div>

      {/* Mission Timeline */}
      <div style={{ flex: 1, minHeight: "120px", maxHeight: "180px", overflowY: "auto", paddingRight: "0.4rem" }}>
        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 700, marginBottom: "0.4rem", textTransform: "uppercase" }}>
          Chronological Event Sequence
        </div>

        {report.timeline_events.length === 0 ? (
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
            No major flight events recorded yet.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
            {report.timeline_events.map((evt, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.5rem",
                  fontSize: "0.75rem",
                  background: "rgba(15, 23, 42, 0.4)",
                  padding: "0.35rem 0.55rem",
                  borderRadius: "6px",
                  borderLeft: `3px solid ${
                    evt.severity === "CRITICAL"
                      ? "var(--accent-crimson)"
                      : evt.severity === "WARNING"
                      ? "var(--accent-amber)"
                      : "var(--accent-cyan)"
                  }`,
                }}
              >
                <div style={{ marginTop: "2px" }}>{getEventIcon(evt.event_type, evt.severity)}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 700, color: "#f8fafc" }}>{evt.event_type}</span>
                    <span className="mono-val" style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "0.72rem", marginTop: "1px" }}>
                    {evt.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Mission Advisory Footer */}
      <div style={{
        marginTop: "0.6rem",
        paddingTop: "0.45rem",
        borderTop: "1px solid rgba(56, 189, 248, 0.08)",
        fontSize: "0.72rem",
        color: "var(--text-secondary)",
      }}>
        <span style={{ fontWeight: 600, color: "var(--accent-cyan)" }}>Flight Status: </span>
        <span>{report.maintenance_advisory}</span>
      </div>

    </div>
  );
};
