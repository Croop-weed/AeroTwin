import React from "react";
import { AlertTriangle, CheckCircle2, Cpu, ShieldAlert } from "lucide-react";
import type { DashboardAnalytics } from "../types/api";

interface FaultAlertsProps {
  analytics: DashboardAnalytics;
}

export const FaultAlerts: React.FC<FaultAlertsProps> = ({ analytics }) => {
  const { anomaly, faults, degradation, rul } = analytics;
  const activeFault = faults && faults.length > 0 ? faults[0] : null;

  return (
    <div className={`gcs-card ${activeFault ? "gcs-card-fault" : ""}`} style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      
      {/* Title Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ShieldAlert size={18} color={activeFault ? "var(--accent-crimson)" : "var(--accent-cyan)"} />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            FAULT PREDICTION & AI ANOMALIES
          </span>
        </div>
        
        {/* AI Anomaly Status Pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span className={`badge ${anomaly.is_anomaly ? "badge-critical" : "badge-healthy"}`}>
            <Cpu size={12} />
            {anomaly.is_anomaly ? `ANOMALY (SCORE: ${anomaly.score.toFixed(2)})` : "AI: NOMINAL"}
          </span>
        </div>
      </div>

      {/* Main Alert Content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {activeFault ? (
          <div style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "8px",
            padding: "0.85rem 1rem",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <AlertTriangle size={20} color="var(--accent-crimson)" />
                <span style={{ fontSize: "1rem", fontWeight: 800, color: "#fca5a5", letterSpacing: "0.02em" }}>
                  FAULT DETECTED: {activeFault.fault_type}
                </span>
              </div>
              <span className="badge badge-critical" style={{ fontSize: "0.7rem" }}>
                SEVERITY: {(activeFault.severity * 100).toFixed(0)}%
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.4rem" }}>
              <div>
                <span style={{ color: "var(--text-muted)" }}>Confidence: </span>
                <span className="mono-val" style={{ fontWeight: 600, color: "#ffffff" }}>
                  {(activeFault.confidence * 100).toFixed(1)}%
                </span>
              </div>
              {activeFault.timestamp && (
                <div>
                  <span style={{ color: "var(--text-muted)" }}>Timestamp: </span>
                  <span className="mono-val" style={{ color: "#ffffff" }}>
                    {new Date(activeFault.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

            {/* Evidence details if present */}
            {activeFault.evidence && Object.keys(activeFault.evidence).length > 0 && (
              <div style={{
                marginTop: "0.5rem",
                paddingTop: "0.4rem",
                borderTop: "1px solid rgba(239, 68, 68, 0.2)",
                fontSize: "0.72rem",
                color: "#fecaca",
                fontFamily: "var(--font-mono)",
              }}>
                Evidence: {Object.entries(activeFault.evidence).map(([k, v]) => `${k}=${typeof v === 'number' ? v.toFixed(1) : v}`).join(", ")}
              </div>
            )}
          </div>
        ) : (
          <div style={{
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.2)",
            borderRadius: "8px",
            padding: "0.85rem 1rem",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}>
            <CheckCircle2 size={24} color="var(--accent-emerald)" />
            <div>
              <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#6ee7b7" }}>
                No Active Engine Faults
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "1px" }}>
                Propulsion system telemetry matching physics model within baseline tolerances.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Degradation & RUL footer */}
      <div style={{
        marginTop: "0.75rem",
        paddingTop: "0.5rem",
        borderTop: "1px solid rgba(56, 189, 248, 0.08)",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "0.5rem",
        fontSize: "0.73rem",
      }}>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Degradation Index: </span>
          <span className="mono-val" style={{ fontWeight: 700, color: degradation.degradation_index > 0.1 ? "var(--accent-amber)" : "var(--accent-emerald)" }}>
            {(degradation.degradation_index * 100).toFixed(1)}% ({degradation.trend})
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>RUL Status: </span>
          <span className="mono-val" style={{ fontWeight: 600, color: "var(--text-secondary)" }}>
            {rul.status === "AVAILABLE" && rul.remaining_useful_life !== null
              ? `${rul.remaining_useful_life.toFixed(0)} cycles`
              : rul.status}
          </span>
        </div>
      </div>

    </div>
  );
};
